# -*- coding: utf-8 -*-
"""Tests for voice_synthesis.py to boost coverage."""
import pytest
from unittest.mock import patch, MagicMock
import os


class TestVoiceSynthesizer:
    """Test VoiceSynthesizer class."""

    @pytest.fixture
    def synth(self):
        from acas_pro.video.voice_synthesis import VoiceSynthesizer
        mock_db = MagicMock()
        return VoiceSynthesizer(db=mock_db, output_dir='/tmp/test_audio')

    def test_init(self, synth):
        assert synth.output_dir == '/tmp/test_audio'
        assert synth.db is not None

    def test_list_voices_all(self, synth):
        voices = synth.list_voices()
        assert len(voices) > 0
        assert all(v.id for v in voices)

    def test_list_voices_filtered(self, synth):
        from acas_pro.video.voice_synthesis import Language, VoiceStyle
        voices = synth.list_voices(language=Language.CN)
        assert all(v.language == Language.CN for v in voices)

    def test_synthesize_stub(self, synth):
        # synthesize raises NotImplementedError, so it returns None
        result = synth.synthesize("Hello world")
        assert result is None
        # Verify task was created with 'failed' status
        synth.db.execute.assert_called()

    def test_batch_synthesize(self, synth):
        results = synth.batch_synthesize(["Hello", "World"])
        assert len(results) == 2
        assert all(r is None for r in results)  # Stub returns None

    def test_clone_voice_success(self, synth):
        clone_id = synth.clone_voice("Test Voice", ["/path/to/sample.mp3"])
        assert clone_id is not None
        assert clone_id.startswith("clone_")
        # execute was called multiple times (init + clone)
        assert synth.db.execute.call_count >= 1

    def test_clone_voice_no_samples(self, synth):
        clone_id = synth.clone_voice("Test Voice", [])
        assert clone_id is None

    def test_mix_with_music_stub(self, synth):
        # mix_with_music has raise NotImplementedError but it's after os.path.exists check
        # When voice file doesn't exist, it returns None before reaching the raise
        result = synth.mix_with_music("nonexistent_voice.mp3", "music.mp3")
        assert result is None
        
        # When voice file exists, it should raise NotImplementedError
        with patch('os.path.exists', return_value=True):
            with pytest.raises(NotImplementedError):
                synth.mix_with_music("voice.mp3", "music.mp3")

    def test_get_task_status_found(self, synth):
        synth.db.fetchone.return_value = {
            'id': 'task_1', 'text': 'Hello', 'status': 'completed'
        }
        result = synth.get_task_status('task_1')
        assert result is not None
        assert result['id'] == 'task_1'

    def test_get_task_status_not_found(self, synth):
        synth.db.fetchone.return_value = None
        result = synth.get_task_status('missing')
        assert result is None

    def test_list_tasks(self, synth):
        synth.db.fetchall.return_value = [
            {'id': 'task_1', 'text': 'Hello'},
            {'id': 'task_2', 'text': 'World'},
        ]
        results = synth.list_tasks(limit=10)
        assert len(results) == 2
        assert results[0]['id'] == 'task_1'

    def test_delete_task_success(self, synth):
        synth.db.fetchone.return_value = {'id': 'task_1', 'output_path': None}
        result = synth.delete_task('task_1')
        assert result is True

    def test_delete_task_with_file(self, synth):
        with patch('os.path.exists', return_value=True):
            with patch('os.remove') as mock_remove:
                synth.db.fetchone.return_value = {'id': 'task_1', 'output_path': '/tmp/test.mp3'}
                result = synth.delete_task('task_1')
                assert result is True
                mock_remove.assert_called_once_with('/tmp/test.mp3')

    def test_delete_task_error(self, synth):
        synth.db.fetchone.side_effect = Exception('DB error')
        result = synth.delete_task('task_1')
        assert result is False

    def test_mock_synthesize(self, synth):
        with patch('builtins.open', MagicMock()):
            synth._mock_synthesize("Hello", "/tmp/test.mp3")
            # Should not raise

    def test_ensure_output_dir(self, synth):
        with patch('pathlib.Path.mkdir') as mock_mkdir:
            synth._ensure_output_dir()
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)


class TestVoiceProfile:
    """Test VoiceProfile dataclass."""

    def test_create_profile(self):
        from acas_pro.video.voice_synthesis import VoiceProfile, Language, VoiceStyle
        profile = VoiceProfile(
            id="test_01",
            name="Test",
            gender="female",
            language=Language.CN,
            style=VoiceStyle.GENTLE,
            description="Test voice"
        )
        assert profile.id == "test_01"
        assert profile.sample_rate == 24000  # default


class TestEnums:
    """Test enums."""

    def test_voice_style_values(self):
        from acas_pro.video.voice_synthesis import VoiceStyle
        assert VoiceStyle.NEUTRAL.value == "neutral"
        assert VoiceStyle.ENERGETIC.value == "energetic"

    def test_language_values(self):
        from acas_pro.video.voice_synthesis import Language
        assert Language.CN.value == "zh-CN"
        assert Language.EN.value == "en-US"
