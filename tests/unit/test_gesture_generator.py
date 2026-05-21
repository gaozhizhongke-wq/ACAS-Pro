# -*- coding: utf-8 -*-
"""Tests for gesture_generator.py"""

import sys
from unittest.mock import MagicMock

# Mock numpy before importing gesture_generator
sys.modules['numpy'] = MagicMock()

import pytest
from acas_pro.avatar.gesture_generator import (
    GestureType, BodyPart, JointRotation, PoseFrame,
    Gesture, GestureGenerator
)


class TestGestureType:
    def test_enum_values(self):
        assert GestureType.WELCOME.value == "welcome"
        assert GestureType.EMPHASIS.value == "emphasis"
        assert GestureType.IDLE.value == "idle"


class TestBodyPart:
    def test_enum_values(self):
        assert BodyPart.HEAD.value == "head"
        assert BodyPart.HAND_LEFT.value == "hand_l"


class TestJointRotation:
    def test_to_dict(self):
        jr = JointRotation(pitch=10.0, yaw=20.0, roll=30.0)
        d = jr.to_dict()
        assert d == {"pitch": 10.0, "yaw": 20.0, "roll": 30.0}


class TestPoseFrame:
    def test_get_joint_existing(self):
        jr = JointRotation(pitch=5.0)
        pf = PoseFrame(
            timestamp=0.0, duration=1.0,
            joint_rotations={BodyPart.HEAD: jr}
        )
        result = pf.get_joint(BodyPart.HEAD)
        assert result.pitch == 5.0

    def test_get_joint_missing(self):
        pf = PoseFrame(timestamp=0.0, duration=1.0)
        result = pf.get_joint(BodyPart.HEAD)
        assert result.pitch == 0.0


class TestGesture:
    def test_get_duration_with_keyframes(self):
        pf1 = PoseFrame(timestamp=0.0, duration=1.0)
        pf2 = PoseFrame(timestamp=1.5, duration=0.5)
        g = Gesture(
            id="g1", name="Test", type=GestureType.IDLE,
            keyframes=[pf1, pf2]
        )
        assert g.get_duration() == 2.0

    def test_get_duration_without_keyframes(self):
        g = Gesture(
            id="g1", name="Test", type=GestureType.IDLE,
            duration=5.0
        )
        assert g.get_duration() == 5.0


class TestGestureGenerator:
    def setup_method(self):
        self.gg = GestureGenerator()

    def test_init_loads_library(self):
        assert len(self.gg._gesture_library) > 0

    def test_get_gesture_found(self):
        g = self.gg.get_gesture("gesture_welcome_01")
        assert g is not None
        assert g.type == GestureType.WELCOME

    def test_get_gesture_not_found(self):
        g = self.gg.get_gesture("nonexistent")
        assert g is None

    def test_get_gestures_by_type(self):
        gestures = self.gg.get_gestures_by_type(GestureType.WELCOME)
        assert isinstance(gestures, list)
        assert all(g.type == GestureType.WELCOME for g in gestures)

    def test_get_finger_pose(self):
        pose = self.gg._get_finger_pose(3)
        assert isinstance(pose, dict)
        assert "thumb" in pose

    def test_analyze_script_empty(self):
        result = self.gg._analyze_script("")
        assert isinstance(result, list)

    def test_analyze_script_with_content(self):
        result = self.gg._analyze_script("大家好\n欢迎")
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_select_gesture_for_segment(self):
        segment = {"text": "欢迎", "type": "welcome", "duration": 2.0}
        g = self.gg._select_gesture_for_segment(segment, "natural")
        assert g is not None

    def test_interpolate_pose(self):
        pf1 = PoseFrame(
            timestamp=0.0, duration=1.0,
            joint_rotations={BodyPart.HEAD: JointRotation(pitch=0.0)}
        )
        pf2 = PoseFrame(
            timestamp=1.0, duration=1.0,
            joint_rotations={BodyPart.HEAD: JointRotation(pitch=10.0)}
        )
        result = self.gg.interpolate_pose(pf1, pf2, 0.5)
        assert result.timestamp == 0.5
        head = result.get_joint(BodyPart.HEAD)
        assert head.pitch == 5.0

    def test_export_gesture(self, tmp_path):
        g = self.gg.get_gesture("gesture_idle_01")
        output_path = tmp_path / "gesture.json"
        result = self.gg.export_gesture(g, str(output_path))
        assert result is True
        assert output_path.exists()

    def test_generate_gestures_for_script(self):
        result = self.gg.generate_gestures_for_script("欢迎", 5.0)
        assert isinstance(result, list)
