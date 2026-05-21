#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for avatar modules."""

import sys
from unittest.mock import MagicMock, patch
import pytest


class TestLipSync:
    """Test lip_sync module."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self._saved = dict(sys.modules)
        sys.modules['acas_pro.core.config'] = MagicMock(config=MagicMock())
        sys.modules['acas_pro.core.logging'] = MagicMock(get_logger=MagicMock())
        sys.modules['numpy'] = MagicMock()
        yield
        for m in list(sys.modules.keys()):
            if m not in self._saved:
                del sys.modules[m]

    def test_lipsync_enum(self):
        from acas_pro.avatar.lip_sync import LipSyncModel
        assert LipSyncModel.WAV2LIP.value == "wav2lip"
        assert LipSyncModel.SADTALKER.value == "sadtalker"
        assert LipSyncModel.VIDEO_RETALKING.value == "retalking"
        assert LipSyncModel.IP_LAP.value == "ip_lap"

    def test_viseme_frame(self):
        from acas_pro.avatar.lip_sync import VisemeFrame
        vf = VisemeFrame(timestamp=0.0, duration=0.1)
        assert vf.timestamp == 0.0
        assert vf.duration == 0.1
        assert vf.jaw_open == 0.0
        assert vf.lip_roundness == 0.0

    def test_viseme_frame_with_visemes(self):
        from acas_pro.avatar.lip_sync import VisemeFrame
        vf = VisemeFrame(
            timestamp=0.0, duration=0.1,
            visemes={"A": 0.5, "E": 0.3, "I": 0.2},
            jaw_open=0.3, lip_roundness=0.5, lip_width=0.1
        )
        assert vf.visemes["A"] == 0.5
        assert vf.jaw_open == 0.3

    def test_phoneme(self):
        from acas_pro.avatar.lip_sync import Phoneme
        ph = Phoneme(symbol="A", start_time=0.0, end_time=0.1)
        assert ph.symbol == "A"
        assert ph.start_time == 0.0
        assert ph.end_time == 0.1


class TestGestureGenerator:
    """Test gesture_generator module."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self._saved = dict(sys.modules)
        sys.modules['acas_pro.core.config'] = MagicMock(config=MagicMock())
        sys.modules['acas_pro.core.logging'] = MagicMock(get_logger=MagicMock())
        sys.modules['numpy'] = MagicMock()
        yield
        for m in list(sys.modules.keys()):
            if m not in self._saved:
                del sys.modules[m]

    def test_gesture_type_enum(self):
        from acas_pro.avatar.gesture_generator import GestureType
        assert GestureType.WELCOME.name == "WELCOME"
        assert GestureType.GREETING.name == "GREETING"
        assert GestureType.FAREWELL.name == "FAREWELL"
        assert GestureType.POINTING.name == "POINTING"
        assert GestureType.THINKING.name == "THINKING"

    def test_body_part_enum(self):
        from acas_pro.avatar.gesture_generator import BodyPart
        assert BodyPart.HEAD.name == "HEAD"
        assert BodyPart.HAND_LEFT.name == "HAND_LEFT"
        assert BodyPart.HAND_RIGHT.name == "HAND_RIGHT"

    def test_joint_rotation(self):
        from acas_pro.avatar.gesture_generator import JointRotation
        jr = JointRotation(pitch=0.0, yaw=0.0, roll=0.0)
        assert jr.pitch == 0.0
        assert jr.yaw == 0.0
        assert jr.roll == 0.0

    def test_pose_frame(self):
        from acas_pro.avatar.gesture_generator import PoseFrame
        pf = PoseFrame(timestamp=0.0, duration=0.5)
        assert pf.timestamp == 0.0
        assert pf.duration == 0.5
        assert pf.facial_expression == "neutral"
        assert pf.expression_intensity == 0.5

    def test_gesture(self):
        from acas_pro.avatar.gesture_generator import Gesture, GestureType
        g = Gesture(
            id="gesture_01", name="Test Gesture",
            type=GestureType.WELCOME, duration=1.0,
            intensity=0.8, priority=1
        )
        assert g.id == "gesture_01"
        assert g.name == "Test Gesture"
        assert g.type == GestureType.WELCOME
        assert g.intensity == 0.8

    def test_gesture_get_duration(self):
        from acas_pro.avatar.gesture_generator import Gesture, GestureType
        g = Gesture(id="g1", name="g1", type=GestureType.GREETING)
        assert g.get_duration() == 0.0


class TestSceneAdapter:
    """Test scene_adapter module."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self._saved = dict(sys.modules)
        sys.modules['acas_pro.core.config'] = MagicMock(config=MagicMock())
        sys.modules['acas_pro.core.logging'] = MagicMock(get_logger=MagicMock())
        sys.modules['numpy'] = MagicMock()
        yield
        for m in list(sys.modules.keys()):
            if m not in self._saved:
                del sys.modules[m]

    def test_scene_type_enum(self):
        from acas_pro.avatar.scene_adapter import SceneType
        assert SceneType.PRODUCT_SHOWCASE.name == "PRODUCT_SHOWCASE"
        assert SceneType.LIVE_STREAMING.name == "LIVE_STREAMING"
        assert SceneType.E_COMMERCE.name == "E_COMMERCE"

    def test_background_type_enum(self):
        from acas_pro.avatar.scene_adapter import BackgroundType
        assert BackgroundType.STUDIO.name == "STUDIO"
        assert BackgroundType.VIRTUAL.name == "VIRTUAL"
        assert BackgroundType.GREEN_SCREEN.name == "GREEN_SCREEN"

    def test_lighting_preset_enum(self):
        from acas_pro.avatar.scene_adapter import LightingPreset
        vals = [e.name for e in LightingPreset]
        assert "STANDARD" in vals or len(vals) > 0

    def test_camera_angle_enum(self):
        from acas_pro.avatar.scene_adapter import CameraAngle
        vals = [e.name for e in CameraAngle]
        assert len(vals) > 0

    def test_lighting_config(self):
        from acas_pro.avatar.scene_adapter import LightingConfig
        lc = LightingConfig()
        assert lc is not None

    def test_camera_config(self):
        from acas_pro.avatar.scene_adapter import CameraConfig
        cc = CameraConfig()
        assert cc is not None

    def test_scene_config(self):
        from acas_pro.avatar.scene_adapter import SceneConfig, SceneType, BackgroundType
        sc = SceneConfig(
            id="scene_01", name="Test Scene",
            scene_type=SceneType.PRODUCT_SHOWCASE,
            background_type=BackgroundType.STUDIO
        )
        assert sc.id == "scene_01"
        assert sc.scene_type == SceneType.PRODUCT_SHOWCASE
        assert sc.background_type == BackgroundType.STUDIO


class TestAvatarEngine:
    """Test avatar_engine module."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self._saved = dict(sys.modules)
        sys.modules['acas_pro.core.config'] = MagicMock(config=MagicMock())
        sys.modules['acas_pro.core.logging'] = MagicMock(get_logger=MagicMock())
        sys.modules['numpy'] = MagicMock()
        yield
        for m in list(sys.modules.keys()):
            if m not in self._saved:
                del sys.modules[m]

    def test_avatar_type_enum(self):
        from acas_pro.avatar.avatar_engine import AvatarType
        assert AvatarType.BRAND_EXCLUSIVE.name == "BRAND_EXCLUSIVE"
        assert AvatarType.SCENE_ADAPTIVE.name == "SCENE_ADAPTIVE"
        assert AvatarType.TEMPLATE_BASED.name == "TEMPLATE_BASED"

    def test_avatar_style_enum(self):
        from acas_pro.avatar.avatar_engine import AvatarStyle
        assert AvatarStyle.REALISTIC.name == "REALISTIC"
        assert AvatarStyle.CARTOON.name == "CARTOON"
        assert AvatarStyle.ANIME.name == "ANIME"

    def test_avatar_gender_enum(self):
        from acas_pro.avatar.avatar_engine import AvatarGender
        vals = [e.name for e in AvatarGender]
        assert len(vals) > 0

    def test_avatar_age_group_enum(self):
        from acas_pro.avatar.avatar_engine import AvatarAgeGroup
        vals = [e.name for e in AvatarAgeGroup]
        assert len(vals) > 0

    def test_avatar_appearance(self):
        from acas_pro.avatar.avatar_engine import AvatarAppearance
        ap = AvatarAppearance()
        assert ap is not None

    def test_avatar_expression(self):
        from acas_pro.avatar.avatar_engine import AvatarExpression
        ae = AvatarExpression(name="smile", intensity=0.7)
        assert ae.name == "smile"
        assert ae.intensity == 0.7

    def test_digital_avatar(self):
        from acas_pro.avatar.avatar_engine import DigitalAvatar, AvatarType, AvatarStyle, AvatarGender, AvatarAgeGroup
        at_list = list(AvatarType); as_list = list(AvatarStyle); ag_list = list(AvatarGender); aag_list = list(AvatarAgeGroup)
        da = DigitalAvatar(
            id="avatar_01", name="Test Avatar",
            type=at_list[0], style=as_list[0],
            gender=ag_list[0], age_group=aag_list[0]
        )
        assert da.id == "avatar_01"
        assert da.name == "Test Avatar"
        assert da.type == at_list[0]
