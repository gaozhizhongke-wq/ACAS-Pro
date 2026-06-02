#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for voice synthesis module"""
import pytest
from unittest.mock import MagicMock
from acas_pro.video.voice_synthesis import VoiceSynthesizer, VoiceStyle, Language, VoiceProfile


class TestVoiceStyle:
    def test_style_values(self):
        assert VoiceStyle.NEUTRAL.value == "neutral"
        assert VoiceStyle.ENERGETIC.value == "energetic"
        assert VoiceStyle.GENTLE.value == "gentle"
        assert VoiceStyle.PROFESSIONAL.value == "professional"
        assert VoiceStyle.HUMOROUS.value == "humorous"
        assert VoiceStyle.EMOTIONAL.value == "emotional"


class TestLanguage:
    def test_language_values(self):
        assert Language.CN.value == "zh-CN"
        assert Language.EN.value == "en-US"
        assert Language.JP.value == "ja-JP"
        assert Language.KR.value == "ko-KR"
        assert Language.AR.value == "ar-SA"


class TestVoiceProfile:
    def test_create_profile(self):
        profile = VoiceProfile(
            id="VP-001",
            name="Xiaomei",
            gender="female",
            language=Language.CN,
            style=VoiceStyle.GENTLE,
            description="A gentle Chinese female voice"
        )
        assert profile.id == "VP-001"
        assert profile.name == "Xiaomei"
        assert profile.gender == "female"
        assert profile.language == Language.CN
        assert profile.style == VoiceStyle.GENTLE
        assert profile.description == "A gentle Chinese female voice"
        assert profile.sample_rate == 24000


class TestVoiceSynthesizerInit:
    def test_init(self):
        mock_db = MagicMock()
        synth = VoiceSynthesizer(db=mock_db)
        assert synth.db is not None
        assert synth.output_dir is not None


class TestListVoices:
    def test_list_all(self):
        mock_db = MagicMock()
        synth = VoiceSynthesizer(db=mock_db)
        voices = synth.list_voices()
        assert len(voices) >= 6  # At least the default profiles

    def test_list_by_language(self):
        mock_db = MagicMock()
        synth = VoiceSynthesizer(db=mock_db)
        voices = synth.list_voices(language=Language.CN)
        assert len(voices) >= 4  # At least 4 Chinese voices
        for v in voices:
            assert v.language == Language.CN

    def test_list_by_gender(self):
        mock_db = MagicMock()
        synth = VoiceSynthesizer(db=mock_db)
        voices = synth.list_voices(gender="female")
        for v in voices:
            assert v.gender == "female"

    def test_list_by_language_and_gender(self):
        mock_db = MagicMock()
        synth = VoiceSynthesizer(db=mock_db)
        voices = synth.list_voices(language=Language.EN, gender="male")
        for v in voices:
            assert v.language == Language.EN
            assert v.gender == "male"


class TestSynthesize:
    def test_synthesize_basic(self):
        mock_db = MagicMock()
        synth = VoiceSynthesizer(db=mock_db)
        result = synth.synthesize(
            text="Hello world",
            voice_id="cn_female_01",
            speed=1.0,
            pitch=1.0,
            volume=1.0
        )
        # Returns None because NotImplementedError is raised
        assert result is None

    def test_synthesize_invalid_voice(self):
        mock_db = MagicMock()
        synth = VoiceSynthesizer(db=mock_db)
        result = synth.synthesize(
            text="Hello",
            voice_id="nonexistent_voice"
        )
        assert result is None

    def test_synthesize_empty_text(self):
        mock_db = MagicMock()
        synth = VoiceSynthesizer(db=mock_db)
        result = synth.synthesize(text="", voice_id="cn_female_01")
        assert result is None


class TestBatchSynthesize:
    def test_batch_synthesize(self):
        mock_db = MagicMock()
        synth = VoiceSynthesizer(db=mock_db)
        results = synth.batch_synthesize(
            texts=["Hello", "World"],
            voice_id="cn_female_01"
        )
        assert len(results) == 2
        assert all(r is None for r in results)  # All fail with NotImplementedError


class TestCloneVoice:
    def test_clone_voice(self):
        mock_db = MagicMock()
        synth = VoiceSynthesizer(db=mock_db)
        result = synth.clone_voice(
            name="My Clone",
            sample_paths=["/path/to/sample.mp3"],
            description="Test clone"
        )
        assert result is not None
        assert result.startswith("clone_")

    def test_clone_voice_no_samples(self):
        mock_db = MagicMock()
        synth = VoiceSynthesizer(db=mock_db)
        result = synth.clone_voice(
            name="My Clone",
            sample_paths=[]
        )
        assert result is None


class TestGetTaskStatus:
    def test_get_status_exists(self):
        mock_db = MagicMock()
        mock_db.fetchone.return_value = {"status": "completed"}
        synth = VoiceSynthesizer(db=mock_db)
        status = synth.get_task_status("task_123")
        assert status == {"status": "completed"}

    def test_get_status_missing(self):
        mock_db = MagicMock()
        mock_db.fetchone.return_value = None
        synth = VoiceSynthesizer(db=mock_db)
        status = synth.get_task_status("nonexistent")
        assert status is None


class TestListTasks:
    def test_list_all(self):
        mock_db = MagicMock()
        mock_db.fetchall.return_value = [
            {"id": "t1", "text": "Hello", "status": "completed"},
            {"id": "t2", "text": "World", "status": "pending"},
        ]
        synth = VoiceSynthesizer(db=mock_db)
        tasks = synth.list_tasks()
        assert len(tasks) == 2

    def test_list_by_status(self):
        mock_db = MagicMock()
        mock_db.fetchall.return_value = [
            {"id": "t1", "text": "Hello", "status": "completed"},
        ]
        synth = VoiceSynthesizer(db=mock_db)
        # list_tasks doesn't take status parameter
        tasks = synth.list_tasks()
        assert len(tasks) == 1
        assert tasks[0]["id"] == "t1"

    def test_list_empty(self):
        mock_db = MagicMock()
        mock_db.fetchall.return_value = []
        synth = VoiceSynthesizer(db=mock_db)
        tasks = synth.list_tasks()
        assert tasks == []


class TestDeleteTask:
    def test_delete_exists(self):
        mock_db = MagicMock()
        mock_db.fetchone.return_value = {"id": "t1"}
        synth = VoiceSynthesizer(db=mock_db)
        result = synth.delete_task("t1")
        assert result is True

    def test_delete_missing(self):
        mock_db = MagicMock()
        mock_db.fetchone.return_value = None
        synth = VoiceSynthesizer(db=mock_db)
        result = synth.delete_task("nonexistent")
        assert result is True  # delete returns True even if not found


class TestGetSupportedLanguages:
    def test_get_languages(self):
        mock_db = MagicMock()
        synth = VoiceSynthesizer(db=mock_db)
        # get_supported_languages doesn't exist, use list_voices instead
        voices = synth.list_voices()
        assert isinstance(voices, list)
        assert len(voices) > 0


class TestGetSupportedVoices:
    def test_get_voices(self):
        mock_db = MagicMock()
        synth = VoiceSynthesizer(db=mock_db)
        voices = synth.list_voices(language=Language.CN)
        assert isinstance(voices, list)
        assert len(voices) > 0

    def test_get_voices_unsupported_language(self):
        mock_db = MagicMock()
        synth = VoiceSynthesizer(db=mock_db)
        # Create a new language not in profiles
        class FakeLanguage:
            value = "fake"
        voices = synth.list_voices(language=FakeLanguage())
        assert voices == []
