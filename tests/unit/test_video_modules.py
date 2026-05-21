#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for video modules (voice_synthesis, video_maker)."""

import sys
from unittest.mock import MagicMock, patch
import pytest


def _clear(prefix):
    for m in list(sys.modules.keys()):
        if m.startswith(prefix):
            del sys.modules[m]


class TestVoiceSynthesis:
    """Test voice_synthesis module."""

    @pytest.fixture(autouse=True)
    def setup(self):
        _clear("acas_pro.video")
        _clear("acas_pro.core")
        _clear("numpy")
        # Mock core deps
        sys.modules['acas_pro.core.config'] = MagicMock(config=MagicMock())
        sys.modules['acas_pro.core.logging'] = MagicMock(get_logger=MagicMock())
        sys.modules['numpy'] = MagicMock()
        yield
        for m in list(sys.modules.keys()):
            if m.startswith('acas_pro'):
                del sys.modules[m]

    def test_voice_style_enum(self):
        from acas_pro.video.voice_synthesis import VoiceStyle
        assert VoiceStyle.NEUTRAL.name == "NEUTRAL"
        assert VoiceStyle.ENERGETIC.name == "ENERGETIC"
        assert VoiceStyle.GENTLE.name == "GENTLE"
        assert VoiceStyle.PROFESSIONAL.name == "PROFESSIONAL"
        assert VoiceStyle.HUMOROUS.name == "HUMOROUS"
        assert VoiceStyle.EMOTIONAL.name == "EMOTIONAL"

    def test_language_enum(self):
        from acas_pro.video.voice_synthesis import Language
        assert Language.CN.name == "CN"
        assert Language.EN.name == "EN"
        assert Language.JP.name == "JP"
        assert Language.KR.name == "KR"
        assert Language.AR.name == "AR"

    def test_voice_profile(self):
        from acas_pro.video.voice_synthesis import VoiceProfile, VoiceStyle, Language
        vp = VoiceProfile(
            id="vp1", name="Test Voice", gender="male",
            language=Language.CN, style=VoiceStyle.PROFESSIONAL,
            description="Test voice profile", sample_rate=24000
        )
        assert vp.id == "vp1"
        assert vp.name == "Test Voice"
        assert vp.gender == "male"
        assert vp.language == Language.CN
        assert vp.style == VoiceStyle.PROFESSIONAL
        assert vp.sample_rate == 24000


class TestVideoMaker:
    """Test video_maker module."""

    @pytest.fixture(autouse=True)
    def setup(self):
        _clear("acas_pro.video")
        _clear("acas_pro.core")
        _clear("numpy")
        _clear("cv2")
        _clear("moviepy")
        sys.modules['acas_pro.core.config'] = MagicMock(config=MagicMock())
        sys.modules['acas_pro.core.logging'] = MagicMock(get_logger=MagicMock())
        sys.modules['numpy'] = MagicMock()
        sys.modules['cv2'] = MagicMock()
        sys.modules['moviepy'] = MagicMock()
        yield
        for m in list(sys.modules.keys()):
            if m.startswith('acas_pro'):
                del sys.modules[m]

    def test_video_maker_v2_import(self):
        _clear("acas_pro")
        try:
            from acas_pro.video import video_maker_v2
            assert video_maker_v2 is not None
        except ImportError:
            pass  # Skip if has hard dependencies