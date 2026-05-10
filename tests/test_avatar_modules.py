"""
Phase 3: Avatar 模块测试
覆盖: gesture_generator, lip_sync, scene_adapter
"""
import pytest
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import dataclass

# 导入被测模块
from acas_pro.avatar.gesture_generator import (
    GestureGenerator, Gesture, GestureType, PoseFrame
)
from acas_pro.avatar.lip_sync import (
    LipSyncEngine, Phoneme, VisemeFrame, LipSyncModel
)
from acas_pro.avatar.scene_adapter import (
    SceneAdapter, SceneType, SceneConfig, LightingPreset, LightingConfig
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def gesture_generator():
    return GestureGenerator()


@pytest.fixture
def lip_sync_engine():
    return LipSyncEngine()


@pytest.fixture
def scene_adapter():
    return SceneAdapter()


@pytest.fixture
def sample_pose_frame():
    return PoseFrame(
        timestamp=0.0,
        duration=0.5,
        joint_rotations={},
        hand_pose_left={},
        hand_pose_right={},
        facial_expression="neutral",
        expression_intensity=0.5
    )


@pytest.fixture
def sample_phonemes():
    return [
        Phoneme(symbol="n", start_time=0.0, end_time=0.1, viseme="AA", intensity=0.8),
        Phoneme(symbol="ih", start_time=0.1, end_time=0.2, viseme="IH", intensity=0.9),
        Phoneme(symbol="h", start_time=0.2, end_time=0.3, viseme="HH", intensity=0.7),
    ]


@pytest.fixture
def sample_scene_config():
    return SceneConfig(
        id="test_scene_001",
        name="测试场景",
        description="测试用场景配置",
        scene_type=SceneType.PRODUCT_SHOWCASE,
        background_type="solid",
        background_path="",
        background_color="#FFFFFF",
        lighting_preset=LightingPreset.STANDARD,
        lighting_config=LightingConfig(
            key_light_intensity=1.0, key_light_angle=45, key_light_color="#FFFFFF",
            fill_light_intensity=0.5, fill_light_angle=90, fill_light_color="#FFFFFF",
            back_light_intensity=0.3, back_light_angle=135, back_light_color="#FFFFFF",
            ambient_intensity=0.2, ambient_color="#FFFFFF"
        ),
        camera_config=None,
        avatar_position={"x": 0, "y": 0},
        avatar_scale=1.0,
        avatar_layer=0,
        props=[],
        effects=[],
        created_at=datetime.now(),
        owner_id="test_user"
    )


# ============================================================================
# GestureGenerator Tests
# ============================================================================

class TestGestureGenerator:
    """GestureGenerator 测试"""

    def test_init(self):
        engine = GestureGenerator()
        assert engine is not None

    def test_generate_gestures_for_script(self, gesture_generator):
        gestures = gesture_generator.generate_gestures_for_script(
            script="大家好，今天给大家介绍一款新产品。",
            duration=5.0,
            style="natural"
        )
        assert gestures is not None
        assert isinstance(gestures, list)

    def test_generate_gestures_different_styles(self, gesture_generator):
        for style in ["natural", "energetic", "calm", "formal"]:
            gestures = gesture_generator.generate_gestures_for_script(
                script="测试脚本", duration=3.0, style=style
            )
            assert isinstance(gestures, list)

    def test_get_gestures_by_type(self, gesture_generator):
        gestures = gesture_generator.get_gestures_by_type(GestureType.GREETING)
        assert gestures is not None
        assert isinstance(gestures, list)

    def test_get_gestures_all_types(self, gesture_generator):
        for gt in GestureType:
            gestures = gesture_generator.get_gestures_by_type(gt)
            assert isinstance(gestures, list)

    def test_interpolate_pose(self, gesture_generator, sample_pose_frame):
        pose1 = sample_pose_frame
        pose2 = PoseFrame(
            timestamp=1.0, duration=0.5, joint_rotations={},
            hand_pose_left={}, hand_pose_right={},
            facial_expression="smile", expression_intensity=0.8
        )
        interp = gesture_generator.interpolate_pose(pose1, pose2, 0.5)
        assert interp is not None
        assert 0.0 <= interp.timestamp <= 1.0

    def test_export_gesture(self, gesture_generator):
        gestures = gesture_generator.generate_gestures_for_script("测试", 2.0)
        if gestures:
            with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
                path = f.name
            try:
                result = gesture_generator.export_gesture(gestures[0], path)
                assert isinstance(result, bool)
            finally:
                if os.path.exists(path):
                    os.remove(path)
        else:
            pytest.skip("无手势可导出")


# ============================================================================
# LipSyncEngine Tests
# ============================================================================

class TestLipSyncEngine:
    """LipSyncEngine 测试"""

    def test_init_default(self):
        engine = LipSyncEngine()
        assert engine is not None

    def test_init_with_model(self):
        for model in LipSyncModel:
            engine = LipSyncEngine(model=model)
            assert engine is not None

    def test_get_supported_visemes(self, lip_sync_engine):
        visemes = lip_sync_engine.get_supported_visemes()
        assert visemes is not None
        assert isinstance(visemes, list)
        assert len(visemes) > 0

    def test_estimate_processing_time(self, lip_sync_engine):
        time_est = lip_sync_engine.estimate_processing_time(10.0)
        assert time_est is not None
        assert time_est > 0

    def test_phonemes_to_visemes(self, lip_sync_engine, sample_phonemes):
        visemes = lip_sync_engine.phonemes_to_visemes(sample_phonemes, fps=30.0)
        assert visemes is not None
        assert isinstance(visemes, list)

    def test_preview_viseme(self, lip_sync_engine):
        visemes = lip_sync_engine.get_supported_visemes()
        if visemes:
            preview = lip_sync_engine.preview_viseme(visemes[0])
            assert preview is not None
            assert isinstance(preview, dict)
        else:
            pytest.skip("无可用 viseme")

    def test_export_animation_data(self, lip_sync_engine, sample_phonemes):
        visemes = lip_sync_engine.phonemes_to_visemes(sample_phonemes, fps=30.0)
        if visemes:
            with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
                path = f.name
            try:
                result = lip_sync_engine.export_animation_data(visemes, path)
                assert isinstance(result, bool)
            finally:
                if os.path.exists(path):
                    os.remove(path)
        else:
            pytest.skip("无 viseme 数据可导出")


# ============================================================================
# SceneAdapter Tests
# ============================================================================

class TestSceneAdapter:
    """SceneAdapter 测试"""

    def test_init(self):
        adapter = SceneAdapter()
        assert adapter is not None

    def test_get_lighting_preset(self, scene_adapter):
        for preset in LightingPreset:
            config = scene_adapter.get_lighting_preset(preset)
            assert config is not None
            assert isinstance(config, LightingConfig)

    def test_create_scene_from_template(self, scene_adapter):
        for st in [SceneType.PRODUCT_SHOWCASE, SceneType.LIVE_STREAMING, SceneType.NEWS_BROADCAST]:
            config = scene_adapter.create_scene_from_template(
                scene_type=st,
                name=f"test_{st.name}"
            )
            assert config is not None
            assert isinstance(config, SceneConfig)

    def test_create_scene_with_customizations(self, scene_adapter):
        config = scene_adapter.create_scene_from_template(
            scene_type=SceneType.E_COMMERCE,
            name="自定义场景",
            customizations={"background_color": "#FF0000", "avatar_scale": 1.5}
        )
        assert config is not None

    def test_suggest_scene_for_content(self, scene_adapter):
        suggestions = scene_adapter.suggest_scene_for_content(
            content_description="产品展示视频，需要展示口红颜色细节"
        )
        assert suggestions is not None
        assert isinstance(suggestions, list)

    def test_suggest_scene_with_platform(self, scene_adapter):
        suggestions = scene_adapter.suggest_scene_for_content(
            content_description="直播带货",
            target_platform="抖音"
        )
        assert isinstance(suggestions, list)

    def test_get_all_scenes(self, scene_adapter):
        scenes = scene_adapter.get_all_scenes()
        assert scenes is not None
        assert isinstance(scenes, list)

    def test_get_scenes_by_type(self, scene_adapter):
        scene_adapter.create_scene_from_template(SceneType.PRODUCT_SHOWCASE, "getbytype_test")
        scenes = scene_adapter.get_scenes_by_type(SceneType.PRODUCT_SHOWCASE)
        assert isinstance(scenes, list)

    def test_adapt_avatar_to_scene(self, scene_adapter, sample_scene_config):
        result = scene_adapter.adapt_avatar_to_scene(
            avatar_id="test_avatar",
            scene_id="test_scene_001",
            content_type="product_show"
        )
        assert result is not None
        assert isinstance(result, dict)
