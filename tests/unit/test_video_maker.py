import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime
from pathlib import Path

from acas_pro.video.video_maker import (
    VideoMaker, VideoProject, VideoClip, VideoStatus, ClipType
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
def video_maker(mock_db):
    """Create video maker instance"""
    with patch('acas_pro.video.video_maker.DatabaseManager') as mock_db_class:
        mock_db_class.return_value = mock_db
        maker = VideoMaker(db=mock_db, output_dir='/tmp/test-videos')
        return maker


class TestVideoStatus:
    """Test VideoStatus enum"""
    
    def test_status_values(self):
        """Test status values"""
        assert VideoStatus.DRAFT.value == "draft"
        assert VideoStatus.RENDERING.value == "rendering"
        assert VideoStatus.COMPLETED.value == "completed"
        assert VideoStatus.FAILED.value == "failed"


class TestClipType:
    """Test ClipType enum"""
    
    def test_clip_types(self):
        """Test clip type values"""
        assert ClipType.VIDEO.value == "video"
        assert ClipType.IMAGE.value == "image"
        assert ClipType.TEXT.value == "text"
        assert ClipType.TRANSITION.value == "transition"
        assert ClipType.EFFECT.value == "effect"
        assert ClipType.AUDIO.value == "audio"


class TestVideoClip:
    """Test VideoClip dataclass"""
    
    def test_clip_creation(self):
        """Test creating a clip"""
        clip = VideoClip(
            id="clip_1",
            clip_type=ClipType.VIDEO,
            source_path="/path/to/video.mp4",
            duration=10.0
        )
        
        assert clip.id == "clip_1"
        assert clip.clip_type == ClipType.VIDEO
        assert clip.source_path == "/path/to/video.mp4"
        assert clip.duration == 10.0
        assert clip.start_time == 0.0
        assert clip.scale == 1.0
        assert clip.opacity == 1.0

    def test_clip_defaults(self):
        """Test clip defaults"""
        clip = VideoClip(
            id="clip_1",
            clip_type=ClipType.IMAGE,
            source_path="/path/to/image.jpg"
        )
        
        assert clip.duration == 5.0
        assert clip.position == (0.5, 0.5)
        assert clip.rotation == 0.0
        assert clip.text_content is None
        assert clip.text_style is None


class TestVideoProject:
    """Test VideoProject dataclass"""
    
    def test_project_creation(self):
        """Test creating a project"""
        project = VideoProject(
            id="proj_1",
            name="Test Project",
            title="Test Title",
            script="Test script"
        )
        
        assert project.id == "proj_1"
        assert project.name == "Test Project"
        assert project.width == 1080
        assert project.height == 1920
        assert project.fps == 30
        assert project.status == VideoStatus.DRAFT
        assert project.target_platform == "douyin"
        assert isinstance(project.created_at, datetime)

    def test_project_platform_specs(self):
        """Test project with different platforms"""
        platforms = ["douyin", "xiaohongshu", "kuaishou", "bilibili", "tiktok"]
        
        for platform in platforms:
            project = VideoProject(
                id=f"proj_{platform}",
                name=f"{platform} Project",
                target_platform=platform
            )
            assert project.target_platform == platform


class TestVideoMakerInit:
    """Test VideoMaker initialization"""
    
    def test_init(self, video_maker, mock_db):
        """Test initialization"""
        assert video_maker.db == mock_db
        assert video_maker.output_dir == "/tmp/test-videos"
        # Verify database initialization
        assert mock_db.execute.called

    def test_init_default_output_dir(self, mock_db):
        """Test initialization with default output directory"""
        with patch('acas_pro.video.video_maker.DatabaseManager') as mock_db_class:
            mock_db_class.return_value = mock_db
            maker = VideoMaker(db=mock_db)
            assert "ACAS-Videos" in maker.output_dir

    def test_ensure_output_dir(self, video_maker):
        """Test output directory creation"""
        with patch('pathlib.Path.mkdir') as mock_mkdir:
            video_maker._ensure_output_dir()
            mock_mkdir.assert_called_with(parents=True, exist_ok=True)


class TestPlatformSpecs:
    """Test platform specifications"""
    
    def test_douyin_specs(self, video_maker):
        """Test Douyin platform specs"""
        specs = video_maker.PLATFORM_SPECS["douyin"]
        assert specs["width"] == 1080
        assert specs["height"] == 1920
        assert specs["fps"] == 30
        assert specs["aspect_ratio"] == "9:16"
        assert specs["max_duration"] == 300

    def test_xiaohongshu_specs(self, video_maker):
        """Test Xiaohongshu platform specs"""
        specs = video_maker.PLATFORM_SPECS["xiaohongshu"]
        assert specs["width"] == 1080
        assert specs["height"] == 1440
        assert specs["aspect_ratio"] == "3:4"

    def test_bilibili_specs(self, video_maker):
        """Test Bilibili platform specs"""
        specs = video_maker.PLATFORM_SPECS["bilibili"]
        assert specs["width"] == 1920
        assert specs["height"] == 1080
        assert specs["fps"] == 60
        assert specs["aspect_ratio"] == "16:9"

    def test_all_platforms_have_required_fields(self, video_maker):
        """Test all platforms have required fields"""
        required_fields = ["name", "width", "height", "fps", "max_duration", "aspect_ratio"]
        
        for platform, specs in video_maker.PLATFORM_SPECS.items():
            for field in required_fields:
                assert field in specs, f"{platform} missing {field}"


class TestCreateProject:
    """Test project creation"""
    
    def test_create_project(self, video_maker, mock_db):
        """Test creating a project"""
        project = video_maker.create_project(
            name="Test Project",
            target_platform="douyin",
            title="Test Title",
            script="Test script"
        )
        
        assert project.name == "Test Project"
        assert project.target_platform == "douyin"
        assert project.title == "Test Title"
        assert project.script == "Test script"
        assert project.width == 1080
        assert project.height == 1920
        assert project.status == VideoStatus.DRAFT
        assert project.id.startswith("proj_")
        
        # Verify database save
        assert mock_db.execute.called

    def test_create_project_different_platform(self, video_maker, mock_db):
        """Test creating project for different platform"""
        project = video_maker.create_project(
            name="Bilibili Project",
            target_platform="bilibili"
        )
        
        assert project.width == 1920
        assert project.height == 1080
        assert project.fps == 60

    def test_create_project_default_platform(self, video_maker, mock_db):
        """Test creating project with default platform"""
        project = video_maker.create_project(name="Default Project")
        
        assert project.target_platform == "douyin"
        assert project.width == 1080
        assert project.height == 1920


class TestGetProject:
    """Test getting projects"""
    
    def test_get_project_found(self, video_maker, mock_db):
        """Test getting existing project"""
        mock_db.fetchone.return_value = {
            'id': 'proj_1',
            'name': 'Test',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'width': 1080,
            'height': 1920,
            'fps': 30,
            'duration': 0.0,
            'title': 'Title',
            'description': '',
            'script': '',
            'clips': '[]',
            'background_music': None,
            'voice_over': None,
            'status': 'draft',
            'output_path': None,
            'target_platform': 'douyin'
        }
        
        project = video_maker.get_project('proj_1')
        
        assert project is not None
        assert project.id == 'proj_1'
        assert project.name == 'Test'

    def test_get_project_not_found(self, video_maker, mock_db):
        """Test getting non-existent project"""
        mock_db.fetchone.return_value = None
        
        project = video_maker.get_project('nonexistent')
        
        assert project is None


class TestAddClip:
    """Test adding clips"""
    
    def test_add_clip_success(self, video_maker, mock_db):
        """Test adding clip to project"""
        # Setup project in DB
        mock_db.fetchone.return_value = {
            'id': 'proj_1',
            'name': 'Test',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'width': 1080,
            'height': 1920,
            'fps': 30,
            'duration': 0.0,
            'title': '',
            'description': '',
            'script': '',
            'clips': '[]',
            'background_music': None,
            'voice_over': None,
            'status': 'draft',
            'output_path': None,
            'target_platform': 'douyin'
        }
        
        clip = video_maker.add_clip(
            project_id='proj_1',
            clip_type=ClipType.VIDEO,
            source_path='/path/to/video.mp4',
            duration=10.0
        )
        
        assert clip is not None
        assert clip.clip_type == ClipType.VIDEO
        assert clip.source_path == '/path/to/video.mp4'
        assert clip.duration == 10.0
        assert clip.id.startswith('clip_')

    def test_add_clip_project_not_found(self, video_maker, mock_db):
        """Test adding clip to non-existent project"""
        mock_db.fetchone.return_value = None
        
        clip = video_maker.add_clip(
            project_id='nonexistent',
            clip_type=ClipType.VIDEO,
            source_path='/path/to/video.mp4'
        )
        
        assert clip is None

    def test_add_clip_with_kwargs(self, video_maker, mock_db):
        """Test adding clip with additional parameters"""
        mock_db.fetchone.return_value = {
            'id': 'proj_1',
            'name': 'Test',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'width': 1080,
            'height': 1920,
            'fps': 30,
            'duration': 0.0,
            'title': '',
            'description': '',
            'script': '',
            'clips': '[]',
            'background_music': None,
            'voice_over': None,
            'status': 'draft',
            'output_path': None,
            'target_platform': 'douyin'
        }
        
        clip = video_maker.add_clip(
            project_id='proj_1',
            clip_type=ClipType.TEXT,
            source_path='',
            duration=5.0,
            text_content='Hello',
            text_style={'font': 'Arial', 'size': 48}
        )
        
        assert clip is not None
        assert clip.text_content == 'Hello'
        assert clip.text_style == {'font': 'Arial', 'size': 48}


class TestAutoEdit:
    """Test auto-edit functionality"""
    
    def test_auto_edit_success(self, video_maker, mock_db):
        """Test successful auto-edit"""
        mock_db.fetchone.return_value = {
            'id': 'proj_1',
            'name': 'Test',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'width': 1080,
            'height': 1920,
            'fps': 30,
            'duration': 0.0,
            'title': '',
            'description': '',
            'script': '',
            'clips': '[]',
            'background_music': None,
            'voice_over': None,
            'status': 'draft',
            'output_path': None,
            'target_platform': 'douyin'
        }
        
        materials = [
            '/path/to/video1.mp4',
            '/path/to/image1.jpg',
            '/path/to/video2.mov'
        ]
        
        result = video_maker.auto_edit('proj_1', materials)
        
        assert result is True
        # Verify clips were added
        assert mock_db.execute.called

    def test_auto_edit_no_materials(self, video_maker, mock_db):
        """Test auto-edit with no materials"""
        mock_db.fetchone.return_value = {
            'id': 'proj_1',
            'name': 'Test',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'width': 1080,
            'height': 1920,
            'fps': 30,
            'duration': 0.0,
            'title': '',
            'description': '',
            'script': '',
            'clips': '[]',
            'background_music': None,
            'voice_over': None,
            'status': 'draft',
            'output_path': None,
            'target_platform': 'douyin'
        }
        
        result = video_maker.auto_edit('proj_1', [])
        
        assert result is False

    def test_auto_edit_project_not_found(self, video_maker, mock_db):
        """Test auto-edit with non-existent project"""
        mock_db.fetchone.return_value = None
        
        result = video_maker.auto_edit('nonexistent', ['/path/to/video.mp4'])
        
        assert result is False

    def test_auto_edit_with_music(self, video_maker, mock_db):
        """Test auto-edit with background music"""
        mock_db.fetchone.return_value = {
            'id': 'proj_1',
            'name': 'Test',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'width': 1080,
            'height': 1920,
            'fps': 30,
            'duration': 0.0,
            'title': '',
            'description': '',
            'script': '',
            'clips': '[]',
            'background_music': None,
            'voice_over': None,
            'status': 'draft',
            'output_path': None,
            'target_platform': 'douyin'
        }
        
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = True
            
            materials = ['/path/to/video1.mp4']
            result = video_maker.auto_edit('proj_1', materials, music_path='/path/to/music.mp3')
            
            assert result is True


class TestAddSubtitles:
    """Test adding subtitles"""
    
    def test_add_subtitles(self, video_maker, mock_db):
        """Test adding subtitles to project"""
        mock_db.fetchone.return_value = {
            'id': 'proj_1',
            'name': 'Test',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'width': 1080,
            'height': 1920,
            'fps': 30,
            'duration': 0.0,
            'title': '',
            'description': '',
            'script': '',
            'clips': '[]',
            'background_music': None,
            'voice_over': None,
            'status': 'draft',
            'output_path': None,
            'target_platform': 'douyin'
        }
        
        subtitles = [
            {'text': 'Hello', 'start': 0.0, 'end': 3.0},
            {'text': 'World', 'start': 3.0, 'end': 6.0}
        ]
        
        result = video_maker.add_subtitles('proj_1', subtitles)
        
        assert result is True
        # Verify clips were added
        assert mock_db.execute.called

    def test_add_subtitles_project_not_found(self, video_maker, mock_db):
        """Test adding subtitles to non-existent project"""
        mock_db.fetchone.return_value = None
        
        result = video_maker.add_subtitles('nonexistent', [])
        
        assert result is False

    def test_add_subtitles_with_style(self, video_maker, mock_db):
        """Test adding subtitles with custom style"""
        mock_db.fetchone.return_value = {
            'id': 'proj_1',
            'name': 'Test',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'width': 1080,
            'height': 1920,
            'fps': 30,
            'duration': 0.0,
            'title': '',
            'description': '',
            'script': '',
            'clips': '[]',
            'background_music': None,
            'voice_over': None,
            'status': 'draft',
            'output_path': None,
            'target_platform': 'douyin'
        }
        
        subtitles = [
            {'text': 'Styled', 'start': 0.0, 'end': 3.0, 'style': {'font': 'Arial', 'size': 64, 'color': '#FF0000'}}
        ]
        
        result = video_maker.add_subtitles('proj_1', subtitles)
        
        assert result is True


class TestRenderProject:
    """Test rendering projects"""
    
    def test_render_project(self, video_maker, mock_db):
        """Test rendering a project"""
        mock_db.fetchone.return_value = {
            'id': 'proj_1',
            'name': 'Test',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'width': 1080,
            'height': 1920,
            'fps': 30,
            'duration': 30.0,
            'title': '',
            'description': '',
            'script': '',
            'clips': '[]',
            'background_music': None,
            'voice_over': None,
            'status': 'draft',
            'output_path': None,
            'target_platform': 'douyin'
        }
        
        # Rendering is not implemented, should return None
        result = video_maker.render_project('proj_1')
        
        assert result is None
        # Verify status was updated to failed
        assert mock_db.execute.called

    def test_render_project_not_found(self, video_maker, mock_db):
        """Test rendering non-existent project"""
        mock_db.fetchone.return_value = None
        
        result = video_maker.render_project('nonexistent')
        
        assert result is None


class TestListProjects:
    """Test listing projects"""
    
    def test_list_all_projects(self, video_maker, mock_db):
        """Test listing all projects"""
        mock_db.fetchall.return_value = [
            {
                'id': 'proj_1',
                'name': 'Project 1',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'width': 1080,
                'height': 1920,
                'fps': 30,
                'duration': 30.0,
                'title': '',
                'description': '',
                'script': '',
                'clips': '[]',
                'background_music': None,
                'voice_over': None,
                'status': 'draft',
                'output_path': None,
                'target_platform': 'douyin'
            },
            {
                'id': 'proj_2',
                'name': 'Project 2',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'width': 1080,
                'height': 1920,
                'fps': 30,
                'duration': 60.0,
                'title': '',
                'description': '',
                'script': '',
                'clips': '[]',
                'background_music': None,
                'voice_over': None,
                'status': 'completed',
                'output_path': '/path/to/output.mp4',
                'target_platform': 'xiaohongshu'
            }
        ]
        
        projects = video_maker.list_projects()
        
        assert len(projects) == 2
        assert projects[0].id == 'proj_1'
        assert projects[1].id == 'proj_2'

    def test_list_projects_by_status(self, video_maker, mock_db):
        """Test listing projects by status"""
        mock_db.fetchall.return_value = [
            {
                'id': 'proj_1',
                'name': 'Project 1',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'width': 1080,
                'height': 1920,
                'fps': 30,
                'duration': 30.0,
                'title': '',
                'description': '',
                'script': '',
                'clips': '[]',
                'background_music': None,
                'voice_over': None,
                'status': 'completed',
                'output_path': '/path/to/output.mp4',
                'target_platform': 'douyin'
            }
        ]
        
        projects = video_maker.list_projects(status=VideoStatus.COMPLETED)
        
        assert len(projects) == 1
        assert projects[0].status == VideoStatus.COMPLETED

    def test_list_projects_by_platform(self, video_maker, mock_db):
        """Test listing projects by platform"""
        mock_db.fetchall.return_value = [
            {
                'id': 'proj_1',
                'name': 'Project 1',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'width': 1080,
                'height': 1920,
                'fps': 30,
                'duration': 30.0,
                'title': '',
                'description': '',
                'script': '',
                'clips': '[]',
                'background_music': None,
                'voice_over': None,
                'status': 'draft',
                'output_path': None,
                'target_platform': 'douyin'
            }
        ]
        
        projects = video_maker.list_projects(platform='douyin')
        
        assert len(projects) == 1
        assert projects[0].target_platform == 'douyin'

    def test_list_projects_empty(self, video_maker, mock_db):
        """Test listing projects when none exist"""
        mock_db.fetchall.return_value = []
        
        projects = video_maker.list_projects()
        
        assert len(projects) == 0


class TestDeleteProject:
    """Test deleting projects"""
    
    def test_delete_project(self, video_maker, mock_db):
        """Test deleting a project"""
        result = video_maker.delete_project('proj_1')
        
        assert result is True
        # Verify delete query was executed
        assert mock_db.execute.called

    def test_delete_project_error(self, video_maker, mock_db):
        """Test deleting project with error"""
        mock_db.execute.side_effect = Exception('Database error')
        
        result = video_maker.delete_project('proj_1')
        
        assert result is False


class TestDuplicateProject:
    """Test duplicating projects"""
    
    def test_duplicate_project(self, video_maker, mock_db):
        """Test duplicating a project"""
        mock_db.fetchone.return_value = {
            'id': 'proj_1',
            'name': 'Original',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'width': 1080,
            'height': 1920,
            'fps': 30,
            'duration': 30.0,
            'title': 'Title',
            'description': 'Desc',
            'script': 'Script',
            'clips': json.dumps([
                {
                    'id': 'clip_1',
                    'clip_type': 'video',
                    'source_path': '/path/to/video.mp4',
                    'start_time': 0.0,
                    'duration': 10.0,
                    'position': [0.5, 0.5],
                    'scale': 1.0,
                    'rotation': 0.0,
                    'opacity': 1.0,
                    'text_content': None,
                    'text_style': None,
                    'transition_type': None,
                    'effect_params': None,
                    'volume': 1.0,
                    'fade_in': 0.0,
                    'fade_out': 0.0
                }
            ]),
            'background_music': None,
            'voice_over': None,
            'status': 'draft',
            'output_path': None,
            'target_platform': 'douyin'
        }
        
        new_project = video_maker.duplicate_project('proj_1', 'Copy')
        
        assert new_project is not None
        assert new_project.name == 'Copy'
        assert new_project.title == 'Title'
        assert len(new_project.clips) == 1
        assert new_project.clips[0].clip_type == ClipType.VIDEO

    def test_duplicate_project_not_found(self, video_maker, mock_db):
        """Test duplicating non-existent project"""
        mock_db.fetchone.return_value = None
        
        result = video_maker.duplicate_project('nonexistent')
        
        assert result is None

    def test_duplicate_project_default_name(self, video_maker, mock_db):
        """Test duplicating project with default name"""
        mock_db.fetchone.return_value = {
            'id': 'proj_1',
            'name': 'Original',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'width': 1080,
            'height': 1920,
            'fps': 30,
            'duration': 0.0,
            'title': '',
            'description': '',
            'script': '',
            'clips': '[]',
            'background_music': None,
            'voice_over': None,
            'status': 'draft',
            'output_path': None,
            'target_platform': 'douyin'
        }
        
        new_project = video_maker.duplicate_project('proj_1')
        
        assert new_project is not None
        assert '副本' in new_project.name


class TestTransitions:
    """Test transitions"""
    
    def test_transitions_list(self, video_maker):
        """Test transitions list"""
        transitions = video_maker.TRANSITIONS
        
        assert len(transitions) > 0
        assert 'fade' in transitions
        assert 'slide_left' in transitions
        assert 'zoom_in' in transitions

    def test_all_transitions_are_strings(self, video_maker):
        """Test all transitions are strings"""
        for transition in video_maker.TRANSITIONS:
            assert isinstance(transition, str)
            assert len(transition) > 0


class TestClipConversion:
    """Test clip serialization"""
    
    def test_clip_to_dict(self, video_maker):
        """Test converting clip to dict"""
        clip = VideoClip(
            id='clip_1',
            clip_type=ClipType.VIDEO,
            source_path='/path/to/video.mp4',
            duration=10.0,
            text_content='Test',
            text_style={'font': 'Arial'}
        )
        
        data = video_maker._clip_to_dict(clip)
        
        assert data['id'] == 'clip_1'
        assert data['clip_type'] == 'video'
        assert data['source_path'] == '/path/to/video.mp4'
        assert data['duration'] == 10.0
        assert data['text_content'] == 'Test'
        assert data['text_style'] == {'font': 'Arial'}

    def test_dict_to_clip(self, video_maker):
        """Test converting dict to clip"""
        data = {
            'id': 'clip_1',
            'clip_type': 'image',
            'source_path': '/path/to/image.jpg',
            'start_time': 2.0,
            'duration': 5.0,
            'position': [0.3, 0.7],
            'scale': 1.5,
            'rotation': 45.0,
            'opacity': 0.8,
            'text_content': None,
            'text_style': None,
            'transition_type': 'fade',
            'effect_params': {'blur': 2},
            'volume': 0.5,
            'fade_in': 1.0,
            'fade_out': 1.0
        }
        
        clip = video_maker._dict_to_clip(data)
        
        assert clip.id == 'clip_1'
        assert clip.clip_type == ClipType.IMAGE
        assert clip.start_time == 2.0
        assert clip.position == (0.3, 0.7)
        assert clip.scale == 1.5
        assert clip.rotation == 45.0
        assert clip.opacity == 0.8
        assert clip.transition_type == 'fade'
        assert clip.effect_params == {'blur': 2}
        assert clip.volume == 0.5
        assert clip.fade_in == 1.0
        assert clip.fade_out == 1.0

    def test_roundtrip_conversion(self, video_maker):
        """Test roundtrip conversion"""
        original = VideoClip(
            id='clip_1',
            clip_type=ClipType.TEXT,
            source_path='',
            duration=3.0,
            text_content='Hello',
            text_style={'font': 'Arial', 'size': 48}
        )
        
        data = video_maker._clip_to_dict(original)
        restored = video_maker._dict_to_clip(data)
        
        assert restored.id == original.id
        assert restored.clip_type == original.clip_type
        assert restored.text_content == original.text_content
        assert restored.text_style == original.text_style
