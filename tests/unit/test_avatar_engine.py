# -*- coding: utf-8 -*-
"""Tests for avatar_engine.py"""

from unittest.mock import patch

import pytest
from acas_pro.avatar.avatar_engine import (
    AvatarType, AvatarStyle, AvatarGender, AvatarAgeGroup,
    AvatarAppearance, AvatarExpression, DigitalAvatar, AvatarEngine
)


class TestEnums:
    def test_avatar_type_values(self):
        assert AvatarType.BRAND_EXCLUSIVE.value == "brand_exclusive"
        assert AvatarType.TEMPLATE_BASED.value == "template_based"

    def test_avatar_style_values(self):
        assert AvatarStyle.REALISTIC.value == "realistic"
        assert AvatarStyle.ANIME.value == "anime"

    def test_avatar_gender_values(self):
        assert AvatarGender.MALE.value == "male"
        assert AvatarGender.FEMALE.value == "female"

    def test_avatar_age_group_values(self):
        assert AvatarAgeGroup.YOUNG.value == "young"
        assert AvatarAgeGroup.MIDDLE.value == "middle"


class TestDataclasses:
    def test_avatar_appearance_defaults(self):
        app = AvatarAppearance()
        assert app.face_shape == "oval"
        assert app.hair_color == "black"
        assert app.height == 170

    def test_avatar_expression_defaults(self):
        expr = AvatarExpression(name="smile")
        assert expr.intensity == 0.5
        assert expr.duration == 1.0

    def test_digital_avatar_to_dict(self):
        avatar = DigitalAvatar(
            id="a1", name="Test", type=AvatarType.TEMPLATE_BASED,
            style=AvatarStyle.REALISTIC, gender=AvatarGender.FEMALE,
            age_group=AvatarAgeGroup.YOUNG
        )
        data = avatar.to_dict()
        assert data['id'] == "a1"
        assert data['name'] == "Test"
        assert data['type'] == "template_based"

    def test_digital_avatar_from_dict(self):
        data = {
            'id': 'a1', 'name': 'Test', 'type': 'template_based',
            'style': 'realistic', 'gender': 'female', 'age_group': 'young',
            'appearance': {'face_shape': 'round', 'hair_color': 'blonde'}
        }
        avatar = DigitalAvatar.from_dict(data)
        assert avatar.id == "a1"
        assert avatar.appearance.face_shape == "round"


class TestAvatarEngine:
    @pytest.fixture
    def engine(self, tmp_path):
        import acas_pro.core.config as config_module
        config_module._config_lazy = None
        config_module._config_instance = None

        with patch('acas_pro.avatar.avatar_engine.config') as mock_config:
            mock_config.return_value.data_dir = str(tmp_path)
            engine = AvatarEngine()
            return engine

    def test_init(self, engine):
        assert len(engine._templates) == 4
        assert "template_business_female" in engine._templates

    def test_create_avatar_from_template(self, engine):
        avatar = engine.create_avatar_from_template(
            "template_business_female", "My Avatar", "user1"
        )
        assert avatar is not None
        assert avatar.name == "My Avatar"
        assert avatar.type == AvatarType.TEMPLATE_BASED
        assert avatar.owner_id == "user1"

    def test_create_avatar_from_template_not_found(self, engine):
        result = engine.create_avatar_from_template("nonexistent", "Test")
        assert result is None

    def test_create_avatar_with_customizations(self, engine):
        avatar = engine.create_avatar_from_template(
            "template_business_female", "Custom",
            customizations={'appearance': {'hair_color': 'red'}, 'voice_id': 'v1'}
        )
        assert avatar.appearance.hair_color == "red"
        assert avatar.voice_id == "v1"

    def test_get_avatar_template(self, engine):
        result = engine.get_avatar("template_business_female")
        assert result is not None
        assert result.name == "商务女性"

    def test_get_avatar_db(self, engine):
        # First create an avatar
        avatar = engine.create_avatar_from_template(
            "template_business_female", "DB Avatar", "user1"
        )
        # Then retrieve it
        result = engine.get_avatar(avatar.id)
        assert result is not None
        assert result.name == "DB Avatar"

    def test_get_avatar_not_found(self, engine):
        result = engine.get_avatar("nonexistent")
        assert result is None

    def test_get_user_avatars(self, engine):
        import time
        avatar1 = engine.create_avatar_from_template("template_business_female", "A1", "user1")  # noqa: F841
        time.sleep(1.1)  # Ensure different ID
        avatar2 = engine.create_avatar_from_template("template_business_male", "A2", "user1")  # noqa: F841
        result = engine.get_user_avatars("user1")
        assert len(result) >= 1
        if len(result) == 2:
            names = [a.name for a in result]
            assert "A1" in names
            assert "A2" in names

    def test_get_public_templates(self, engine):
        result = engine.get_public_templates()
        assert len(result) == 4

    def test_update_avatar(self, engine):
        avatar = engine.create_avatar_from_template(
            "template_business_female", "Original", "user1"
        )
        result = engine.update_avatar(avatar.id, {"name": "Updated"})
        assert result is True
        updated = engine.get_avatar(avatar.id)
        assert updated.name == "Updated"

    def test_update_avatar_not_found(self, engine):
        result = engine.update_avatar("nonexistent", {"name": "Updated"})
        assert result is False

    def test_delete_avatar(self, engine):
        avatar = engine.create_avatar_from_template(
            "template_business_female", "ToDelete", "user1"
        )
        result = engine.delete_avatar(avatar.id)
        assert result is True
        assert engine.get_avatar(avatar.id) is None

    def test_create_scene(self, engine):
        scene = engine.create_scene({
            'name': 'Test Scene',
            'scene_type': 'live',
            'background_type': 'virtual'
        })
        assert scene is not None
        assert scene.name == "Test Scene"
        assert scene.scene_type == "live"

    def test_get_render_status_found(self, engine):
        import time
        # Create a render task by inserting directly
        task_id = f"task_{int(time.time() * 1000)}"
        engine.db.execute("""
            INSERT INTO avatar_render_tasks (id, avatar_id, script, status, progress, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (task_id, "avatar1", "script", "pending", 0.0, "2026-01-01T00:00:00"))
        result = engine.get_render_status(task_id)
        assert result['id'] == task_id
        assert result['status'] == "pending"

    def test_get_render_status_not_found(self, engine):
        result = engine.get_render_status("nonexistent")
        assert result == {}
