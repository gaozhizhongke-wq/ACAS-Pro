#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Video and Voice Module Tests
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from acas_pro.video.voice_synthesis import (
    VoiceSynthesizer, VoiceProfile, VoiceStyle, Language
)


class TestVoiceStyle:
    """Voice style enum tests"""
    
    def test_voice_style_values(self):
        """Test voice style enum values"""
        assert VoiceStyle.NEUTRAL.value == "neutral"
        assert VoiceStyle.ENERGETIC.value == "energetic"
        assert VoiceStyle.GENTLE.value == "gentle"
        assert VoiceStyle.PROFESSIONAL.value == "professional"
        assert VoiceStyle.HUMOROUS.value == "humorous"
        assert VoiceStyle.EMOTIONAL.value == "emotional"


class TestLanguage:
    """Language enum tests"""
    
    def test_language_codes(self):
        """Test language codes"""
        assert Language.CN.value == "zh-CN"
        assert Language.EN.value == "en-US"
        assert Language.JP.value == "ja-JP"
        assert Language.KR.value == "ko-KR"
        assert Language.AR.value == "ar-SA"


class TestVoiceProfile:
    """Voice profile tests"""
    
    def test_profile_creation(self):
        """Test profile creation"""
        profile = VoiceProfile(
            id="test_voice",
            name="Test Voice",
            gender="female",
            language=Language.CN,
            style=VoiceStyle.GENTLE,
            description="Test description"
        )
        
        assert profile.id == "test_voice"
        assert profile.name == "Test Voice"
        assert profile.gender == "female"
        assert profile.sample_rate == 24000  # default


class TestVoiceSynthesizer:
    """Voice synthesizer tests"""
    
    @pytest.fixture
    def mock_db(self):
        mock = Mock()
        mock.execute = Mock()
        mock.fetchone = Mock(return_value=None)
        mock.fetchall = Mock(return_value=[])
        return mock
    
    @pytest.fixture
    def synthesizer(self, mock_db):
        return VoiceSynthesizer(db=mock_db, output_dir="/tmp/test_audio")
    
    def test_init(self, synthesizer, mock_db):
        """Test initialization"""
        assert synthesizer.db == mock_db
        assert synthesizer.output_dir == "/tmp/test_audio"
    
    def test_list_voices_all(self, synthesizer):
        """Test list all voices"""
        voices = synthesizer.list_voices()
        
        assert len(voices) == 7  # 7 preset profiles
        assert all(isinstance(p, VoiceProfile) for p in voices)
    
    def test_list_voices_by_language(self, synthesizer):
        """Test filter by language"""
        voices = synthesizer.list_voices(language=Language.CN)
        
        assert len(voices) == 4  # 4 Chinese voices
        assert all(v.language == Language.CN for v in voices)
    
    def test_list_voices_by_gender(self, synthesizer):
        """Test filter by gender"""
        voices = synthesizer.list_voices(gender="female")
        
        assert len(voices) == 4  # 4 female voices
        assert all(v.gender == "female" for v in voices)
    
    def test_list_voices_combined_filter(self, synthesizer):
        """Test combined filters"""
        voices = synthesizer.list_voices(language=Language.CN, gender="female")
        
        assert len(voices) == 2  # 2 Chinese female voices
    
    def test_synthesize_success(self, synthesizer, mock_db, tmp_path):
        """Test successful synthesis"""
        mock_db.fetchone.return_value = None
        
        with patch('builtins.open', create=True):
            result = synthesizer.synthesize("Hello world")
        
        assert result is not None
        assert result.endswith(".mp3")
        mock_db.execute.assert_called()
    
    def test_batch_synthesize(self, synthesizer, mock_db, tmp_path):
        """Test batch synthesis"""
        mock_db.fetchone.return_value = None
        texts = ["Text 1", "Text 2", "Text 3"]
        
        with patch('builtins.open', create=True):
            results = synthesizer.batch_synthesize(texts)
        
        assert len(results) == 3
    
    def test_clone_voice_success(self, synthesizer, mock_db, tmp_path):
        """Test voice cloning"""
        # Create a dummy file
        sample_file = tmp_path / "sample.wav"
        sample_file.write_bytes(b"dummy audio data")
        
        result = synthesizer.clone_voice("New Voice", [str(sample_file)])
        
        assert result is not None
        assert result.startswith("clone_")
    
    def test_clone_voice_no_samples(self, synthesizer):
        """Test clone with no samples"""
        result = synthesizer.clone_voice("New Voice", [])
        
        assert result is None
    
    def test_mix_with_music_voice_not_found(self, synthesizer):
        """Test mix with non-existent voice file"""
        result = synthesizer.mix_with_music("/non/existent.mp3", "/music.mp3")
        
        assert result is None
    
    def test_get_task_status_found(self, synthesizer, mock_db):
        """Test get existing task"""
        mock_db.fetchone.return_value = {
            "id": "task_123",
            "status": "completed",
            "output_path": "/tmp/output.wav"
        }
        
        status = synthesizer.get_task_status("task_123")
        
        assert status is not None
        assert status["status"] == "completed"
    
    def test_get_task_status_not_found(self, synthesizer, mock_db):
        """Test get non-existent task"""
        mock_db.fetchone.return_value = None
        
        status = synthesizer.get_task_status("non_existent")
        
        assert status is None
    
    def test_list_tasks(self, synthesizer, mock_db):
        """Test list tasks"""
        mock_db.fetchall.return_value = [
            {"id": "task_1", "status": "completed"},
            {"id": "task_2", "status": "pending"}
        ]
        
        tasks = synthesizer.list_tasks(limit=10)
        
        assert len(tasks) == 2
        assert tasks[0]["id"] == "task_1"
    
    def test_delete_task(self, synthesizer, mock_db, tmp_path):
        """Test delete task"""
        output_file = tmp_path / "output.mp3"
        output_file.write_bytes(b"mp3 data")
        
        mock_db.fetchone.return_value = {
            "id": "task_123",
            "output_path": str(output_file)
        }
        
        result = synthesizer.delete_task("task_123")
        
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
