#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for content/script_generator.py dataclasses and enums."""

from unittest.mock import MagicMock
import sys
import pytest

if 'numpy' not in sys.modules:
    sys.modules['numpy'] = MagicMock()


class TestContentStyleEnum:
    def test_values(self):
        from acas_pro.content.script_generator import ContentStyle
        assert ContentStyle.BROADCAST.value == "broadcast"
        assert ContentStyle.DRAMA.value == "drama"
        assert ContentStyle.PROMOTION.value == "promotion"
        assert len(ContentStyle) == 6

class TestScriptGeneratorPlatformEnum:
    def test_values(self):
        from acas_pro.content.script_generator import Platform
        assert Platform.DOUYIN.value == "douyin"
        assert len(Platform) == 4

class TestScriptTemplate:
    def test_defaults(self):
        from acas_pro.content.script_generator import ScriptTemplate, ContentStyle, Platform
        t = ScriptTemplate(
            id="t1", name="口播模板", style=ContentStyle.BROADCAST,
            platform=Platform.DOUYIN, structure=["hook", "body", "cta"],
            min_length=50, max_length=500, example="试试看", tags=["带货"]
        )
        assert t.style == ContentStyle.BROADCAST
        assert len(t.structure) == 3

class TestGeneratedScript:
    def test_defaults(self):
        from acas_pro.content.script_generator import GeneratedScript, ContentStyle, Platform
        s = GeneratedScript(
            id="g1", input_text="测试", title="标题",
            content="内容", style=ContentStyle.PROMOTION,
            platform=Platform.DOUYIN, word_count=100,
            hashtags=["tag1"], hooks=["hook"],
            cta="点击购买", variations=[]
        )
        assert s.style == ContentStyle.PROMOTION
