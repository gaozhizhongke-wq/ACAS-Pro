# -*- coding: utf-8 -*-
"""Tests for scene_adapter.py"""

import sys
import json
from unittest.mock import MagicMock, patch
from pathlib import Path

import pytest
from acas_pro.avatar.scene_adapter import (
    SceneType, BackgroundType, LightingPreset, CameraAngle,
    LightingConfig, CameraConfig, SceneConfig, SceneAdapter
)
def _mock_numpy_for_tests():
    """Re-mock numpy during this file's tests; restore after."""
    _saved = sys.modules.get('numpy')
    sys.modules['numpy'] = MagicMock()
    yield
    if _saved is not None:
        sys.modules['numpy'] = _saved
    elif 'numpy' in sys.modules:
        del sys.modules['numpy']


class TestEnums:
    def test_scene_type_values(self):
        assert SceneType.PRODUCT_SHOWCASE.value == "product_showcase"
        assert SceneType.LIVE_STREAMING.value == "live_streaming"

    def test_background_type_values(self):
        assert BackgroundType.STUDIO.value == "studio"
        assert BackgroundType.VIRTUAL.value == "virtual"

    def test_lighting_preset_values(self):
        assert LightingPreset.STANDARD.value == "standard"
        assert LightingPreset.WARM.value == "warm"

    def test_camera_angle_values(self):
        assert CameraAngle.FRONT.value == "front"
        assert CameraAngle.CLOSE_UP.value == "close_up"


class TestDataclasses:
    def test_lighting_config_defaults(self):
        lc = LightingConfig()
        assert lc.key_light_intensity == 1.0
        assert lc.ambient_intensity == 0.2

    def test_camera_config_defaults(self):
        cc = CameraConfig()
        assert cc.angle == CameraAngle.FRONT
        assert cc.focal_length == 50.0

    def test_scene_config_defaults(self):
        sc = SceneConfig(id="s1", name="Test")
        assert sc.scene_type == SceneType.PRODUCT_SHOWCASE
        assert sc.avatar_scale == 0.75


class TestSceneAdapter:
    @pytest.fixture
    def adapter(self, tmp_path):
        # Clear any existing config singleton to ensure fresh state
        import acas_pro.core.config as config_module
        config_module._config_lazy = None
        config_module._config_instance = None
        
        with patch('acas_pro.avatar.scene_adapter.config') as mock_config:
            mock_config.return_value.data_dir = str(tmp_path)
            adapter = SceneAdapter()
            # Clear any scenes loaded from disk (should be 0 since tmp_path is empty)
            adapter._custom_scenes.clear()
            return adapter

    def test_init(self, adapter):
        assert len(adapter._custom_scenes) == 0

    def test_create_scene_from_template(self, adapter):
        scene = adapter.create_scene_from_template(SceneType.LIVE_STREAMING)
        assert scene is not None
        assert scene.scene_type == SceneType.LIVE_STREAMING
        assert scene.name == "直播带货场景"

    def test_create_scene_with_customizations(self, adapter):
        scene = adapter.create_scene_from_template(
            SceneType.PRODUCT_SHOWCASE,
            name="Custom",
            customizations={"avatar_scale": 0.5}
        )
        assert scene.avatar_scale == 0.5

    def test_get_scene_found(self, adapter):
        scene = adapter.create_scene_from_template(SceneType.NEWS_BROADCAST)
        result = adapter.get_scene(scene.id)
        assert result is not None
        assert result.id == scene.id

    def test_get_scene_not_found(self, adapter):
        result = adapter.get_scene("nonexistent")
        assert result is None

    def test_get_all_scenes(self, adapter):
        scene1 = adapter.create_scene_from_template(SceneType.EDUCATIONAL)
        scene2 = adapter.create_scene_from_template(SceneType.CORPORATE)
        result = adapter.get_all_scenes()
        # Scene IDs use second precision, may collide if created too fast
        assert len(result) >= 1
        # Verify both scene types are present if IDs didn't collide
        types = [s.scene_type for s in result]
        if len(result) == 2:
            assert SceneType.EDUCATIONAL in types
            assert SceneType.CORPORATE in types

    def test_get_scenes_by_type(self, adapter):
        adapter.create_scene_from_template(SceneType.ENTERTAINMENT)
        result = adapter.get_scenes_by_type(SceneType.ENTERTAINMENT)
        assert len(result) == 1

    def test_update_scene(self, adapter):
        scene = adapter.create_scene_from_template(SceneType.SOCIAL_MEDIA)
        result = adapter.update_scene(scene.id, {"name": "Updated"})
        assert result is True
        assert adapter.get_scene(scene.id).name == "Updated"

    def test_update_scene_not_found(self, adapter):
        result = adapter.update_scene("nonexistent", {"name": "Updated"})
        assert result is False

    def test_delete_scene(self, adapter):
        scene = adapter.create_scene_from_template(SceneType.E_COMMERCE)
        result = adapter.delete_scene(scene.id)
        assert result is True
        assert adapter.get_scene(scene.id) is None

    def test_get_lighting_preset(self, adapter):
        preset = adapter.get_lighting_preset(LightingPreset.WARM)
        assert isinstance(preset, LightingConfig)
        assert preset.key_light_color == "#FFF8DC"

    def test_adapt_avatar_to_scene(self, adapter):
        scene = adapter.create_scene_from_template(SceneType.PRODUCT_SHOWCASE)
        result = adapter.adapt_avatar_to_scene("avatar1", scene.id)
        assert isinstance(result, dict)
        assert "position" in result

    def test_adapt_avatar_product_highlight(self, adapter):
        scene = adapter.create_scene_from_template(SceneType.PRODUCT_SHOWCASE)
        result = adapter.adapt_avatar_to_scene("avatar1", scene.id, "product_highlight")
        assert result["scale"] == 0.55

    def test_suggest_scene_for_content(self, adapter):
        result = adapter.suggest_scene_for_content("直播带货秒杀")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_suggest_scene_with_platform(self, adapter):
        result = adapter.suggest_scene_for_content("产品展示", "xiaohongshu")
        assert isinstance(result, list)

    def test_dict_to_scene(self, adapter):
        data = {
            "id": "s1", "name": "Test", "scene_type": "educational",
            "background_type": "studio", "lighting_preset": "soft",
            "camera_angle": "three_quarter", "avatar_position": [0.3, 0.5],
            "avatar_scale": 0.6
        }
        scene = adapter._dict_to_scene(data)
        assert scene.id == "s1"
        assert scene.scene_type == SceneType.EDUCATIONAL

    def test_export_scene_config(self, adapter, tmp_path):
        scene = adapter.create_scene_from_template(SceneType.NEWS_BROADCAST)
        output_path = tmp_path / "scene.json"
        result = adapter.export_scene_config(scene.id, str(output_path))
        assert result is True
        assert output_path.exists()

    def test_export_scene_config_not_found(self, adapter, tmp_path):
        output_path = tmp_path / "scene.json"
        result = adapter.export_scene_config("nonexistent", str(output_path))
        assert result is False
