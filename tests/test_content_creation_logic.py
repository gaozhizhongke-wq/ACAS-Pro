#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Content Creation Logic Tests
"""

import pytest

from acas_pro.ui.logic.content_creation_logic import (
    ContentCreationLogic, ContentTemplate
)


class TestContentTemplate:
    def test_template_creation(self):
        template = ContentTemplate(
            id="temp001",
            name="Welcome Email",
            content_type="email",
            platform="email",
            template="Hello {name}!",
            variables=["name"]
        )
        assert template.name == "Welcome Email"
        assert template.platform == "email"


class TestContentCreationLogic:
    @pytest.fixture
    def logic(self):
        return ContentCreationLogic()

    def test_init(self, logic):
        assert logic._templates == []

    def test_get_templates_empty(self, logic):
        templates = logic.get_templates()
        assert templates == []

    def test_get_templates_by_platform(self, logic):
        logic._templates = [
            ContentTemplate("1", "T1", "email", "email", "Hello", ["name"]),
            ContentTemplate("2", "T2", "sms", "sms", "Hi", ["name"]),
        ]
        templates = logic.get_templates(platform="email")
        assert len(templates) == 1
        assert templates[0].name == "T1"

    def test_generate_content(self, logic):
        logic._templates = [
            ContentTemplate("1", "T1", "email", "email", "Hello {name}!", ["name"]),
        ]
        content = logic.generate_content("1", {"name": "John"})
        assert content == "Hello John!"

    def test_generate_content_not_found(self, logic):
        content = logic.generate_content("nonexistent", {"name": "John"})
        assert content == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
