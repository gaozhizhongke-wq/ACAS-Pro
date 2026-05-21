#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for video/voice_synthesis.py module."""

import sys
import pytest
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path

from acas_pro.video.voice_synthesis import (
    VoiceStyle, Language, VoiceProfile, VoiceSynthesizer
)


class TestVoiceStyle:
    """Test VoiceStyle enum."""
    
    def test_voice_style_values(self):
        """Test VoiceStyle enum values."""
        assert VoiceStyle.NEUTRAL.value == "neutral"
        assert VoiceStyle.ENERGETIC.value == "energetic"
        assert VoiceStyle.GENTLE.value == "gentle"
        assert VoiceStyle.PROFESSIONAL.value == "professional"
        assert VoiceStyle.HUMOROUS.value == "humorous"
        assert VoiceStyle.EMOTIONAL.value == "emotional"


class TestLanguage:
    """Test Language enum."""
    
    def test_language_values(self):
        """Test Language enum values."""
        assert Language.CN.value == "zh-CN"
        assert Language.EN.value == "en-US"
        assert Language.JP.value == "ja-JP"
        assert Language.KR.value == "ko-KR"
        assert Language.AR.value == "ar-SA"


class TestVoiceProfile:
    """Test VoiceProfile dataclass."""
    
    def test_voice_profile_creation(self):
        """Test creating a VoiceProfile."""
        profile = VoiceProfile(
            id="test_01",
            name="Test Voice",
            gender="female",
            language=Language.CN,
            style=VoiceStyle.GENTLE,
            description="Test description",
            sample_rate=24000
        )
        assert profile.id == "test_01"
        assert profile.name == "Test Voice"
        assert profile.gender == "female"
        assert profile.language == Language.CN
        assert profile.style == VoiceStyle.GENTLE
        assert profile.description == "Test description"
        assert profile.sample_rate == 24000


class TestVoiceSynthesizerInit:
    """Test VoiceSynthesizer initialization."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup mocks."""
        # Mock DatabaseManager
        mock_db = MagicMock()
        mock_db_pkg = MagicMock()
        mock_db_pkg.DatabaseManager = MagicMock(return_value=mock_db)
        sys.modules['acas_pro.core.database'] = mock_db_pkg
        
        # Mock get_logger
        mock_logger = MagicMock()
        mock_get_logger = MagicMock(return_value=mock_logger)
        mock_logging_pkg = MagicMock()
        mock_logging_pkg.get_logger = mock_get_logger
        sys.modules['acas_pro.core.logging'] = mock_logging_pkg
        
        # Mock Path.mkdir
        with patch('acas_pro.video.voice_synthesis.Path.mkdir'):
            yield
        
        # Cleanup
        if 'acas_pro.core.database' in sys.modules:
            del sys.modules['acas_pro.core.database']
        if 'acas_pro.core.logging' in sys.modules:
            del sys.modules['acas_pro.core.logging']
    
    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        with patch('acas_pro.video.voice_synthesis.Path.mkdir'):
            synth = VoiceSynthesizer()
            assert synth.db is not None
            assert 'ACAS-Audio' in synth.output_dir
    
    def test_init_with_custom_params(self):
        """Test initialization with custom parameters."""
        mock_db = MagicMock()
        with patch('acas_pro.video.voice_synthesis.Path.mkdir'):
            synth = VoiceSynthesizer(db=mock_db, output_dir='/custom/path')
            assert synth.db == mock_db
            assert synth.output_dir == '/custom/path'


class TestListVoices:
    """Test list_voices method."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup mocks."""
        mock_db = MagicMock()
        mock_db_pkg = MagicMock()
        mock_db_pkg.DatabaseManager = MagicMock(return_value=mock_db)
        sys.modules['acas_pro.core.database'] = mock_db_pkg
        
        mock_logger = MagicMock()
        mock_get_logger = MagicMock(return_value=mock_logger)
        mock_logging_pkg = MagicMock()
        mock_logging_pkg.get_logger = mock_get_logger
        sys.modules['acas_pro.core.logging'] = mock_logging_pkg
        
        with patch('acas_pro.video.voice_synthesis.Path.mkdir'):
            yield
        
        if 'acas_pro.core.database' in sys.modules:
            del sys.modules['acas_pro.core.database']
        if 'acas_pro.core.logging' in sys.modules:
            del sys.modules['acas_pro.core.logging']
    
    def test_list_voices_all(self):
        """Test listing all voices."""
        with patch('acas_pro.video.voice_synthesis.Path.mkdir'):
            synth = VoiceSynthesizer()
            voices = synth.list_voices()
            assert len(voices) == 7  # 7 preset voices
    
    def test_list_voices_by_language(self):
        """Test listing voices filtered by language."""
        with patch('acas_pro.video.voice_synthesis.Path.mkdir'):
            synth = VoiceSynthesizer()
            cn_voices = synth.list_voices(language=Language.CN)
            assert len(cn_voices) == 4  # 4 Chinese voices
    
    def test_list_voices_by_gender(self):
        """Test listing voices filtered by gender."""
        with patch('acas_pro.video.voice_synthesis.Path.mkdir'):
            synth = VoiceSynthesizer()
            female_voices = synth.list_voices(gender='female')
            assert len(female_voices) == 4  # 4 female voices


class TestBatchSynthesize:
    """Test batch_synthesize method."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup mocks."""
        mock_db = MagicMock()
        mock_db_pkg = MagicMock()
        mock_db_pkg.DatabaseManager = MagicMock(return_value=mock_db)
        sys.modules['acas_pro.core.database'] = mock_db_pkg
        
        mock_logger = MagicMock()
        mock_get_logger = MagicMock(return_value=mock_logger)
        mock_logging_pkg = MagicMock()
        mock_logging_pkg.get_logger = mock_get_logger
        sys.modules['acas_pro.core.logging'] = mock_logging_pkg
        
        with patch('acas_pro.video.voice_synthesis.Path.mkdir'):
            yield
        
        if 'acas_pro.core.database' in sys.modules:
            del sys.modules['acas_pro.core.database']
        if 'acas_pro.core.logging' in sys.modules:
            del sys.modules['acas_pro.core.logging']
    
    def test_batch_synthesize(self):
        """Test batch synthesis."""
        with patch('acas_pro.video.voice_synthesis.Path.mkdir'):
            synth = VoiceSynthesizer()
            # Mock synthesize to return a path
            with patch.object(synth, 'synthesize', return_value='/path/to/output.mp3'):
                results = synth.batch_synthesize(['text1', 'text2', 'text3'])
                assert len(results) == 3
                assert all(r == '/path/to/output.mp3' for r in results)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
