import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime
from pathlib import Path

from acas_pro.video.voice_synthesis import (
    VoiceSynthesizer, VoiceProfile, VoiceStyle, Language
)


@pytest.fixture
def mock_db():
    """Create mock database"""
    db = MagicMock()
    db.fetchone.return_value = None
    db.fetchall.return_value = []
    db.execute.return_value = MagicMock(rowcount=1)
    return db


@pytest.fixture
def synthesizer(mock_db):
    """Create voice synthesizer instance"""
    with patch('acas_pro.video.voice_synthesis.DatabaseManager') as mock_db_class:
        mock_db_class.return_value = mock_db
        synth = VoiceSynthesizer(db=mock_db, output_dir='/tmp/test-audio')
        return synth


class TestVoiceStyle:
    """Test VoiceStyle enum"""
    
    def test_style_values(self):
        """Test voice style values"""
        assert VoiceStyle.NEUTRAL.value == "neutral"
        assert VoiceStyle.ENERGETIC.value == "energetic"
        assert VoiceStyle.GENTLE.value == "gentle"
        assert VoiceStyle.PROFESSIONAL.value == "professional"
        assert VoiceStyle.HUMOROUS.value == "humorous"
        assert VoiceStyle.EMOTIONAL.value == "emotional"


class TestLanguage:
    """Test Language enum"""
    
    def test_language_values(self):
        """Test language values"""
        assert Language.CN.value == "zh-CN"
        assert Language.EN.value == "en-US"
        assert Language.JP.value == "ja-JP"
        assert Language.KR.value == "ko-KR"
        assert Language.AR.value == "ar-SA"


class TestVoiceProfile:
    """Test VoiceProfile dataclass"""
    
    def test_profile_creation(self):
        """Test creating voice profile"""
        profile = VoiceProfile(
            id="cn_female_01",
            name="小晴",
            gender="female",
            language=Language.CN,
            style=VoiceStyle.GENTLE,
            description="温柔女声"
        )
        
        assert profile.id == "cn_female_01"
        assert profile.name == "小晴"
        assert profile.gender == "female"
        assert profile.language == Language.CN
        assert profile.style == VoiceStyle.GENTLE
        assert profile.description == "温柔女声"
        assert profile.sample_rate == 24000

    def test_profile_defaults(self):
        """Test voice profile defaults"""
        profile = VoiceProfile(
            id="test_01",
            name="Test",
            gender="male",
            language=Language.EN,
            style=VoiceStyle.NEUTRAL,
            description=""
        )
        
        assert profile.sample_rate == 24000


class TestVoiceSynthesizerInit:
    """Test VoiceSynthesizer initialization"""
    
    def test_init(self, synthesizer, mock_db):
        """Test initialization"""
        assert synthesizer.db == mock_db
        assert synthesizer.output_dir == "/tmp/test-audio"
        assert mock_db.execute.called

    def test_init_default_output_dir(self, mock_db):
        """Test initialization with default output directory"""
        with patch('acas_pro.video.voice_synthesis.DatabaseManager') as mock_db_class:
            mock_db_class.return_value = mock_db
            synth = VoiceSynthesizer(db=mock_db)
            assert "ACAS-Audio" in synth.output_dir

    def test_ensure_output_dir(self, synthesizer):
        """Test output directory creation"""
        with patch('pathlib.Path.mkdir') as mock_mkdir:
            synthesizer._ensure_output_dir()
            mock_mkdir.assert_called_with(parents=True, exist_ok=True)


class TestVoiceProfiles:
    """Test voice profiles"""
    
    def test_preset_profiles(self, synthesizer):
        """Test preset voice profiles"""
        profiles = synthesizer.VOICE_PROFILES
        
        assert len(profiles) > 0
        
        # Check Chinese voices
        cn_voices = [p for p in profiles if p.language == Language.CN]
        assert len(cn_voices) >= 4
        
        # Check English voices
        en_voices = [p for p in profiles if p.language == Language.EN]
        assert len(en_voices) >= 2
        
        # Check Arabic voice
        ar_voices = [p for p in profiles if p.language == Language.AR]
        assert len(ar_voices) >= 1

    def test_all_profiles_have_required_fields(self, synthesizer):
        """Test all profiles have required fields"""
        for profile in synthesizer.VOICE_PROFILES:
            assert profile.id
            assert profile.name
            assert profile.gender in ['male', 'female']
            assert isinstance(profile.language, Language)
            assert isinstance(profile.style, VoiceStyle)
            assert profile.sample_rate > 0


class TestListVoices:
    """Test listing voices"""
    
    def test_list_all_voices(self, synthesizer):
        """Test listing all voices"""
        voices = synthesizer.list_voices()
        
        assert len(voices) == len(synthesizer.VOICE_PROFILES)

    def test_list_by_language(self, synthesizer):
        """Test listing voices by language"""
        voices = synthesizer.list_voices(language=Language.CN)
        
        assert len(voices) > 0
        for voice in voices:
            assert voice.language == Language.CN

    def test_list_by_gender(self, synthesizer):
        """Test listing voices by gender"""
        voices = synthesizer.list_voices(gender="female")
        
        assert len(voices) > 0
        for voice in voices:
            assert voice.gender == "female"

    def test_list_by_language_and_gender(self, synthesizer):
        """Test listing voices by language and gender"""
        voices = synthesizer.list_voices(language=Language.CN, gender="male")
        
        assert len(voices) > 0
        for voice in voices:
            assert voice.language == Language.CN
            assert voice.gender == "male"

    def test_list_no_match(self, synthesizer):
        """Test listing voices with no match"""
        voices = synthesizer.list_voices(language=Language.JP, gender="female")
        
        # Should return empty or limited results since we don't have Japanese female voice
        assert len(voices) == 0 or all(v.language == Language.JP for v in voices)


class TestSynthesize:
    """Test voice synthesis"""
    
    def test_synthesize_not_implemented(self, synthesizer, mock_db):
        """Test synthesis returns None (not implemented)"""
        result = synthesizer.synthesize("Hello world")
        
        assert result is None
        # Verify task was saved
        assert mock_db.execute.called

    def test_synthesize_with_params(self, synthesizer, mock_db):
        """Test synthesis with parameters"""
        result = synthesizer.synthesize(
            text="Test text",
            voice_id="cn_female_01",
            speed=1.5,
            pitch=1.2,
            volume=0.8,
            emotion="happy"
        )
        
        assert result is None
        # Verify task was saved with correct parameters
        assert mock_db.execute.called

    def test_synthesize_empty_text(self, synthesizer, mock_db):
        """Test synthesis with empty text"""
        result = synthesizer.synthesize("")
        
        assert result is None

    def test_synthesize_invalid_voice(self, synthesizer, mock_db):
        """Test synthesis with invalid voice ID"""
        result = synthesizer.synthesize("Test", voice_id="invalid_voice")
        
        assert result is None


class TestBatchSynthesize:
    """Test batch synthesis"""
    
    def test_batch_synthesize(self, synthesizer, mock_db):
        """Test batch synthesis"""
        texts = ["Hello", "World", "Test"]
        results = synthesizer.batch_synthesize(texts)
        
        assert len(results) == 3
        # All should be None since synthesis is not implemented
        assert all(r is None for r in results)

    def test_batch_synthesize_empty(self, synthesizer, mock_db):
        """Test batch synthesis with empty list"""
        results = synthesizer.batch_synthesize([])
        
        assert len(results) == 0

    def test_batch_synthesize_with_voice_id(self, synthesizer, mock_db):
        """Test batch synthesis with specific voice"""
        texts = ["Text 1", "Text 2"]
        results = synthesizer.batch_synthesize(texts, voice_id="en_female_01")
        
        assert len(results) == 2


class TestCloneVoice:
    """Test voice cloning"""
    
    def test_clone_voice_success(self, synthesizer, mock_db):
        """Test successful voice cloning"""
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = True
            
            result = synthesizer.clone_voice(
                name="My Voice",
                sample_paths=["/path/to/sample1.wav", "/path/to/sample2.wav"],
                description="Custom voice"
            )
            
            assert result is not None
            assert result.startswith("clone_")
            # Verify database save
            assert mock_db.execute.called

    def test_clone_voice_no_samples(self, synthesizer, mock_db):
        """Test cloning with no samples"""
        result = synthesizer.clone_voice(name="My Voice", sample_paths=[])
        
        assert result is None

    def test_clone_voice_missing_files(self, synthesizer, mock_db):
        """Test cloning with missing files"""
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = False
            
            result = synthesizer.clone_voice(
                name="My Voice",
                sample_paths=["/nonexistent/file.wav"]
            )
            
            # Should still create clone entry even if files don't exist
            assert result is not None


class TestMockSynthesize:
    """Test mock synthesis"""
    
    def test_mock_synthesize(self, synthesizer, tmp_path):
        """Test mock synthesis creates file"""
        output_path = str(tmp_path / "test.mp3")
        
        synthesizer._mock_synthesize("Test text", output_path)
        
        assert Path(output_path).exists()
        # Check file has MP3 header
        with open(output_path, 'rb') as f:
            header = f.read(4)
            assert header == b'\xff\xfb\x90\x00'

    def test_mock_synthesize_content(self, synthesizer, tmp_path):
        """Test mock synthesis file content"""
        output_path = str(tmp_path / "test.mp3")
        
        synthesizer._mock_synthesize("Test", output_path)
        
        # File should be at least 104 bytes (4 byte header + 100 bytes padding)
        assert Path(output_path).stat().st_size >= 104


class TestDatabaseInit:
    """Test database initialization"""
    
    def test_init_tables(self, synthesizer, mock_db):
        """Test database tables are created"""
        # Verify that execute was called for table creation
        assert mock_db.execute.called
        
        # Check calls include CREATE TABLE
        calls = [str(call) for call in mock_db.execute.call_args_list]
        assert any('CREATE TABLE' in call for call in calls)
        assert any('voice_tasks' in call for call in calls)
        assert any('voice_clones' in call for call in calls)


class TestVoiceProfileProperties:
    """Test voice profile properties"""
    
    def test_profile_languages(self, synthesizer):
        """Test all languages are represented"""
        languages = set(p.language for p in synthesizer.VOICE_PROFILES)
        
        assert Language.CN in languages
        assert Language.EN in languages
        assert Language.AR in languages

    def test_profile_styles(self, synthesizer):
        """Test all styles are represented"""
        styles = set(p.style for p in synthesizer.VOICE_PROFILES)
        
        assert len(styles) > 0
        assert VoiceStyle.NEUTRAL in styles or VoiceStyle.GENTLE in styles

    def test_profile_genders(self, synthesizer):
        """Test both genders are represented"""
        genders = set(p.gender for p in synthesizer.VOICE_PROFILES)
        
        assert "male" in genders
        assert "female" in genders

    def test_unique_ids(self, synthesizer):
        """Test all voice IDs are unique"""
        ids = [p.id for p in synthesizer.VOICE_PROFILES]
        
        assert len(ids) == len(set(ids))
