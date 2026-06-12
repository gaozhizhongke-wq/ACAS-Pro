#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for video maker module"""
from unittest.mock import patch, MagicMock
from acas_pro.video.video_maker import VideoMaker, VideoStatus, ClipType, VideoClip, VideoProject


class TestVideoStatus:
    def test_status_values(self):
        assert VideoStatus.DRAFT.value == "draft"
        assert VideoStatus.RENDERING.value == "rendering"
        assert VideoStatus.COMPLETED.value == "completed"
        assert VideoStatus.FAILED.value == "failed"


class TestClipType:
    def test_type_values(self):
        assert ClipType.VIDEO.value == "video"
        assert ClipType.IMAGE.value == "image"
        assert ClipType.TEXT.value == "text"
        assert ClipType.TRANSITION.value == "transition"
        assert ClipType.EFFECT.value == "effect"
        assert ClipType.AUDIO.value == "audio"


class TestVideoClip:
    def test_create_clip(self):
        clip = VideoClip(
            id="CLIP-001",
            clip_type=ClipType.VIDEO,
            source_path="/path/to/video.mp4",
            start_time=0.0,
            duration=5.0
        )
        assert clip.id == "CLIP-001"
        assert clip.clip_type == ClipType.VIDEO
        assert clip.source_path == "/path/to/video.mp4"
        assert clip.start_time == 0.0
        assert clip.duration == 5.0
        assert clip.position == (0.5, 0.5)


class TestVideoProject:
    def test_create_project(self):
        project = VideoProject(
            id="PROJ-001",
            name="Test Project",
            description="A test video project"
        )
        assert project.id == "PROJ-001"
        assert project.name == "Test Project"
        assert project.description == "A test video project"
        assert project.status == VideoStatus.DRAFT
        assert project.clips == []
        assert project.output_path is None


class TestVideoMakerInit:
    def test_init(self):
        with patch('acas_pro.video.video_maker.DatabaseManager'):
            maker = VideoMaker()
            assert maker.db is not None
            assert maker.output_dir is not None


class TestCreateProject:
    def test_create_project(self):
        with patch('acas_pro.video.video_maker.DatabaseManager') as mock_db:
            mock_instance = MagicMock()
            mock_db.return_value = mock_instance
            maker = VideoMaker()
            project = maker.create_project(
                name="My Video",
                target_platform="douyin",
                title="Test Title",
                script="Test script"
            )
            assert project.id.startswith("proj_")
            assert project.name == "My Video"
            assert project.title == "Test Title"
            assert project.script == "Test script"
            assert project.target_platform == "douyin"
            assert project.status == VideoStatus.DRAFT

    def test_create_project_default_platform(self):
        with patch('acas_pro.video.video_maker.DatabaseManager') as mock_db:
            mock_instance = MagicMock()
            mock_db.return_value = mock_instance
            maker = VideoMaker()
            project = maker.create_project(name="Video 1")
            assert project.target_platform == "douyin"

    def test_create_project_bilibili(self):
        with patch('acas_pro.video.video_maker.DatabaseManager') as mock_db:
            mock_instance = MagicMock()
            mock_db.return_value = mock_instance
            maker = VideoMaker()
            project = maker.create_project(name="Bilibili Video", target_platform="bilibili")
            assert project.width == 1920
            assert project.height == 1080


class TestGetProject:
    def test_get_exists(self):
        with patch('acas_pro.video.video_maker.DatabaseManager') as mock_db:
            mock_instance = MagicMock()
            mock_instance.fetchone.return_value = {
                'id': 'proj_123',
                'name': 'Test',
                'created_at': '2024-01-01T00:00:00',
                'updated_at': '2024-01-01T00:00:00',
                'width': 1080,
                'height': 1920,
                'fps': 30,
                'duration': 0,
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
            mock_db.return_value = mock_instance
            maker = VideoMaker()
            result = maker.get_project("proj_123")
            assert result is not None
            assert result.name == "Test"

    def test_get_missing(self):
        with patch('acas_pro.video.video_maker.DatabaseManager') as mock_db:
            mock_instance = MagicMock()
            mock_instance.fetchone.return_value = None
            mock_db.return_value = mock_instance
            maker = VideoMaker()
            result = maker.get_project("nonexistent")
            assert result is None


class TestAddClip:
    def test_add_clip(self):
        with patch('acas_pro.video.video_maker.DatabaseManager') as mock_db:
            mock_instance = MagicMock()
            mock_instance.fetchone.return_value = {
                'id': 'proj_123',
                'name': 'Test',
                'created_at': '2024-01-01T00:00:00',
                'updated_at': '2024-01-01T00:00:00',
                'width': 1080,
                'height': 1920,
                'fps': 30,
                'duration': 0,
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
            mock_db.return_value = mock_instance
            maker = VideoMaker()
            clip = maker.add_clip(
                project_id="proj_123",
                clip_type=ClipType.VIDEO,
                source_path="/path/video.mp4",
                duration=10.0
            )
            assert clip is not None
            assert clip.clip_type == ClipType.VIDEO
            assert clip.source_path == "/path/video.mp4"

    def test_add_clip_missing_project(self):
        with patch('acas_pro.video.video_maker.DatabaseManager') as mock_db:
            mock_instance = MagicMock()
            mock_instance.fetchone.return_value = None
            mock_db.return_value = mock_instance
            maker = VideoMaker()
            clip = maker.add_clip(
                project_id="nonexistent",
                clip_type=ClipType.VIDEO,
                source_path="/path/video.mp4"
            )
            assert clip is None


class TestRenderProject:
    def test_render(self):
        with patch('acas_pro.video.video_maker.DatabaseManager') as mock_db:
            mock_instance = MagicMock()
            mock_instance.fetchone.return_value = {
                'id': 'proj_123',
                'name': 'Test',
                'created_at': '2024-01-01T00:00:00',
                'updated_at': '2024-01-01T00:00:00',
                'width': 1080,
                'height': 1920,
                'fps': 30,
                'duration': 0,
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
            mock_db.return_value = mock_instance
            maker = VideoMaker()
            result = maker.render_project("proj_123")
            # Returns None because NotImplementedError is raised
            assert result is None

    def test_render_missing(self):
        with patch('acas_pro.video.video_maker.DatabaseManager') as mock_db:
            mock_instance = MagicMock()
            mock_instance.fetchone.return_value = None
            mock_db.return_value = mock_instance
            maker = VideoMaker()
            result = maker.render_project("nonexistent")
            assert result is None


class TestListProjects:
    def test_list_all(self):
        with patch('acas_pro.video.video_maker.DatabaseManager') as mock_db:
            mock_instance = MagicMock()
            mock_instance.fetchall.return_value = [
                {
                    'id': 'proj_1', 'name': 'Video 1', 'created_at': '2024-01-01T00:00:00', 'updated_at': '2024-01-01T00:00:00',
                    'width': 1080, 'height': 1920, 'fps': 30, 'duration': 0, 'title': '', 'description': '', 'script': '',
                    'clips': '[]', 'background_music': None, 'voice_over': None, 'status': 'draft', 'output_path': None, 'target_platform': 'douyin'
                },
                {
                    'id': 'proj_2', 'name': 'Video 2', 'created_at': '2024-01-01T00:00:00', 'updated_at': '2024-01-01T00:00:00',
                    'width': 1080, 'height': 1920, 'fps': 30, 'duration': 0, 'title': '', 'description': '', 'script': '',
                    'clips': '[]', 'background_music': None, 'voice_over': None, 'status': 'completed', 'output_path': None, 'target_platform': 'douyin'
                },
            ]
            mock_db.return_value = mock_instance
            maker = VideoMaker()
            projects = maker.list_projects()
            assert len(projects) == 2

    def test_list_by_status(self):
        with patch('acas_pro.video.video_maker.DatabaseManager') as mock_db:
            mock_instance = MagicMock()
            mock_instance.fetchall.return_value = [
                {
                    'id': 'proj_1', 'name': 'Completed', 'created_at': '2024-01-01T00:00:00', 'updated_at': '2024-01-01T00:00:00',
                    'width': 1080, 'height': 1920, 'fps': 30, 'duration': 0, 'title': '', 'description': '', 'script': '',
                    'clips': '[]', 'background_music': None, 'voice_over': None, 'status': 'completed', 'output_path': None, 'target_platform': 'douyin'
                },
            ]
            mock_db.return_value = mock_instance
            maker = VideoMaker()
            projects = maker.list_projects(status=VideoStatus.COMPLETED)
            assert len(projects) == 1
            assert projects[0].name == "Completed"

    def test_list_empty(self):
        with patch('acas_pro.video.video_maker.DatabaseManager') as mock_db:
            mock_instance = MagicMock()
            mock_instance.fetchall.return_value = []
            mock_db.return_value = mock_instance
            maker = VideoMaker()
            projects = maker.list_projects()
            assert projects == []


class TestDeleteProject:
    def test_delete_exists(self):
        with patch('acas_pro.video.video_maker.DatabaseManager') as mock_db:
            mock_instance = MagicMock()
            mock_db.return_value = mock_instance
            maker = VideoMaker()
            result = maker.delete_project("proj_123")
            assert result is True

    def test_delete_missing(self):
        with patch('acas_pro.video.video_maker.DatabaseManager') as mock_db:
            mock_instance = MagicMock()
            mock_instance.fetchone.return_value = None
            mock_db.return_value = mock_instance
            maker = VideoMaker()
            result = maker.delete_project("nonexistent")
            assert result is True  # delete returns True even if not found


class TestDuplicateProject:
    def test_duplicate(self):
        with patch('acas_pro.video.video_maker.DatabaseManager') as mock_db:
            mock_instance = MagicMock()
            mock_instance.fetchone.return_value = {
                'id': 'proj_123', 'name': 'Original', 'created_at': '2024-01-01T00:00:00', 'updated_at': '2024-01-01T00:00:00',
                'width': 1080, 'height': 1920, 'fps': 30, 'duration': 0, 'title': '', 'description': '', 'script': 'Script',
                'clips': '[]', 'background_music': None, 'voice_over': None, 'status': 'draft', 'output_path': None, 'target_platform': 'douyin'
            }
            mock_db.return_value = mock_instance
            maker = VideoMaker()
            new_project = maker.duplicate_project("proj_123")
            assert new_project is not None
            assert new_project.id != "proj_123"
            assert "副本" in new_project.name

    def test_duplicate_missing(self):
        with patch('acas_pro.video.video_maker.DatabaseManager') as mock_db:
            mock_instance = MagicMock()
            mock_instance.fetchone.return_value = None
            mock_db.return_value = mock_instance
            maker = VideoMaker()
            result = maker.duplicate_project("nonexistent")
            assert result is None


class TestAutoEdit:
    def test_auto_edit(self):
        with patch('acas_pro.video.video_maker.DatabaseManager') as mock_db:
            mock_instance = MagicMock()
            mock_instance.fetchone.return_value = {
                'id': 'proj_123', 'name': 'Test', 'created_at': '2024-01-01T00:00:00', 'updated_at': '2024-01-01T00:00:00',
                'width': 1080, 'height': 1920, 'fps': 30, 'duration': 0, 'title': '', 'description': '', 'script': '',
                'clips': '[]', 'background_music': None, 'voice_over': None, 'status': 'draft', 'output_path': None, 'target_platform': 'douyin'
            }
            mock_db.return_value = mock_instance
            maker = VideoMaker()
            result = maker.auto_edit(
                project_id="proj_123",
                materials=["/path/video1.mp4", "/path/image1.jpg"]
            )
            assert result is True

    def test_auto_edit_missing_project(self):
        with patch('acas_pro.video.video_maker.DatabaseManager') as mock_db:
            mock_instance = MagicMock()
            mock_instance.fetchone.return_value = None
            mock_db.return_value = mock_instance
            maker = VideoMaker()
            result = maker.auto_edit("nonexistent", ["/path/video.mp4"])
            assert result is False

    def test_auto_edit_no_materials(self):
        with patch('acas_pro.video.video_maker.DatabaseManager') as mock_db:
            mock_instance = MagicMock()
            mock_instance.fetchone.return_value = {
                'id': 'proj_123', 'name': 'Test', 'created_at': '2024-01-01T00:00:00', 'updated_at': '2024-01-01T00:00:00',
                'width': 1080, 'height': 1920, 'fps': 30, 'duration': 0, 'title': '', 'description': '', 'script': '',
                'clips': '[]', 'background_music': None, 'voice_over': None, 'status': 'draft', 'output_path': None, 'target_platform': 'douyin'
            }
            mock_db.return_value = mock_instance
            maker = VideoMaker()
            result = maker.auto_edit("proj_123", [])
            assert result is False
