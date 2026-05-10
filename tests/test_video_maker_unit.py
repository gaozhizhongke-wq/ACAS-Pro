#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Video Maker Unit Tests (No DB)
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from acas_pro.video.video_maker import (
    VideoMaker, VideoProject, VideoClip, VideoStatus, ClipType
)


class TestVideoStatus:
    def test_status_values(self):
        assert VideoStatus.DRAFT.value == "draft"
        assert VideoStatus.RENDERING.value == "rendering"
        assert VideoStatus.COMPLETED.value == "completed"
        assert VideoStatus.FAILED.value == "failed"


class TestClipType:
    def test_clip_type_values(self):
        assert ClipType.VIDEO.value == "video"
        assert ClipType.IMAGE.value == "image"
        assert ClipType.TEXT.value == "text"
        assert ClipType.TRANSITION.value == "transition"


class TestVideoClip:
    def test_clip_creation(self):
        clip = VideoClip(
            id="clip001",
            clip_type=ClipType.VIDEO,
            source_path="/path/to/video.mp4",
            start_time=0.0,
            duration=5.0
        )
        assert clip.id == "clip001"
        assert clip.clip_type == ClipType.VIDEO
        assert clip.scale == 1.0
        assert clip.opacity == 1.0


class TestVideoProject:
    def test_project_creation(self):
        project = VideoProject(
            id="proj001",
            name="Test Project",
            title="Test Title",
            script="Test script"
        )
        assert project.name == "Test Project"
        assert project.width == 1080
        assert project.height == 1920
        assert project.fps == 30
        assert project.status == VideoStatus.DRAFT


class TestVideoMaker:
    @pytest.fixture
    def mock_db(self):
        db = Mock()
        db.execute = Mock()
        db.fetchone = Mock(return_value=None)
        db.fetchall = Mock(return_value=[])
        return db

    @pytest.fixture
    def maker(self, mock_db):
        with patch('acas_pro.video.video_maker.Path.mkdir'):
            return VideoMaker(db=mock_db, output_dir="/tmp/videos")

    def test_init(self, maker, mock_db):
        assert maker.db == mock_db
        assert maker.output_dir == "/tmp/videos"
        mock_db.execute.assert_called()

    def test_platform_specs(self, maker):
        assert "douyin" in maker.PLATFORM_SPECS
        assert "xiaohongshu" in maker.PLATFORM_SPECS
        assert "bilibili" in maker.PLATFORM_SPECS
        assert maker.PLATFORM_SPECS["douyin"]["width"] == 1080
        assert maker.PLATFORM_SPECS["bilibili"]["width"] == 1920

    def test_transitions(self, maker):
        assert "fade" in maker.TRANSITIONS
        assert "slide_left" in maker.TRANSITIONS
        assert "zoom_in" in maker.TRANSITIONS

    def test_create_project(self, maker, mock_db):
        project = maker.create_project(
            name="Test Project",
            target_platform="douyin",
            title="Test Title",
            script="Test script"
        )
        assert project.name == "Test Project"
        assert project.target_platform == "douyin"
        assert project.width == 1080
        assert project.height == 1920
        mock_db.execute.assert_called()

    def test_create_project_default_platform(self, maker, mock_db):
        project = maker.create_project(name="Test")
        assert project.target_platform == "douyin"

    def test_create_project_xiaohongshu(self, maker, mock_db):
        project = maker.create_project(name="Test", target_platform="xiaohongshu")
        assert project.height == 1440

    def test_create_project_bilibili(self, maker, mock_db):
        project = maker.create_project(name="Test", target_platform="bilibili")
        assert project.width == 1920
        assert project.height == 1080

    def test_get_project_not_found(self, maker, mock_db):
        mock_db.fetchone.return_value = None
        result = maker.get_project("nonexistent")
        assert result is None

    def test_add_clip(self, maker, mock_db):
        mock_row = {
            'id': 'proj001', 'name': 'Test', 'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(), 'width': 1080, 'height': 1920,
            'fps': 30, 'duration': 0, 'title': '', 'description': '',
            'script': '', 'clips': '[]', 'background_music': None,
            'voice_over': None, 'status': 'draft', 'output_path': None,
            'target_platform': 'douyin'
        }
        mock_db.fetchone.return_value = mock_row

        clip = maker.add_clip(
            project_id="proj001",
            clip_type=ClipType.VIDEO,
            source_path="/path/video.mp4",
            duration=5.0
        )

        assert clip is not None
        assert clip.clip_type == ClipType.VIDEO
        assert clip.source_path == "/path/video.mp4"

    def test_add_clip_project_not_found(self, maker, mock_db):
        mock_db.fetchone.return_value = None
        clip = maker.add_clip("nonexistent", ClipType.VIDEO, "/path/video.mp4")
        assert clip is None

    def test_auto_edit(self, maker, mock_db):
        mock_row = {
            'id': 'proj001', 'name': 'Test', 'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(), 'width': 1080, 'height': 1920,
            'fps': 30, 'duration': 0, 'title': '', 'description': '',
            'script': '', 'clips': '[]', 'background_music': None,
            'voice_over': None, 'status': 'draft', 'output_path': None,
            'target_platform': 'douyin'
        }
        mock_db.fetchone.return_value = mock_row

        with patch('os.path.exists', return_value=True):
            result = maker.auto_edit(
                project_id="proj001",
                materials=["/path/video1.mp4", "/path/image1.jpg"],
                target_duration=30.0
            )

        assert result is True

    def test_auto_edit_no_materials(self, maker, mock_db):
        mock_row = {
            'id': 'proj001', 'name': 'Test', 'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(), 'width': 1080, 'height': 1920,
            'fps': 30, 'duration': 0, 'title': '', 'description': '',
            'script': '', 'clips': '[]', 'background_music': None,
            'voice_over': None, 'status': 'draft', 'output_path': None,
            'target_platform': 'douyin'
        }
        mock_db.fetchone.return_value = mock_row

        result = maker.auto_edit("proj001", materials=[])
        assert result is False

    def test_auto_edit_project_not_found(self, maker, mock_db):
        mock_db.fetchone.return_value = None
        result = maker.auto_edit("nonexistent", materials=["/path/video.mp4"])
        assert result is False

    def test_add_subtitles(self, maker, mock_db):
        mock_row = {
            'id': 'proj001', 'name': 'Test', 'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(), 'width': 1080, 'height': 1920,
            'fps': 30, 'duration': 0, 'title': '', 'description': '',
            'script': '', 'clips': '[]', 'background_music': None,
            'voice_over': None, 'status': 'draft', 'output_path': None,
            'target_platform': 'douyin'
        }
        mock_db.fetchone.return_value = mock_row

        subtitles = [
            {"text": "Hello", "start": 0.0, "end": 3.0},
            {"text": "World", "start": 3.0, "end": 6.0}
        ]
        result = maker.add_subtitles("proj001", subtitles)
        assert result is True

    def test_add_subtitles_project_not_found(self, maker, mock_db):
        mock_db.fetchone.return_value = None
        result = maker.add_subtitles("nonexistent", [])
        assert result is False

    def test_render_project(self, maker, mock_db):
        mock_row = {
            'id': 'proj001', 'name': 'Test', 'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(), 'width': 1080, 'height': 1920,
            'fps': 30, 'duration': 10.0, 'title': '', 'description': '',
            'script': '', 'clips': '[]', 'background_music': None,
            'voice_over': None, 'status': 'draft', 'output_path': None,
            'target_platform': 'douyin'
        }
        mock_db.fetchone.return_value = mock_row

        output_path = maker.render_project("proj001")

        assert output_path is not None
        assert "proj001" in output_path

    def test_render_project_not_found(self, maker, mock_db):
        mock_db.fetchone.return_value = None
        result = maker.render_project("nonexistent")
        assert result is None

    def test_list_projects(self, maker, mock_db):
        mock_db.fetchall.return_value = []
        projects = maker.list_projects()
        assert projects == []

    def test_list_projects_with_filters(self, maker, mock_db):
        mock_db.fetchall.return_value = []
        projects = maker.list_projects(status=VideoStatus.DRAFT, platform="douyin")
        assert projects == []
        mock_db.fetchall.assert_called_once()

    def test_delete_project(self, maker, mock_db):
        result = maker.delete_project("proj001")
        assert result is True
        mock_db.execute.assert_called_with(
            "DELETE FROM video_projects WHERE id = ?",
            ("proj001",)
        )

    def test_delete_project_error(self, maker, mock_db):
        mock_db.execute.side_effect = Exception("DB Error")
        result = maker.delete_project("proj001")
        assert result is False

    def test_duplicate_project(self, maker, mock_db):
        mock_row = {
            'id': 'proj001', 'name': 'Original', 'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(), 'width': 1080, 'height': 1920,
            'fps': 30, 'duration': 0, 'title': 'Title', 'description': 'Desc',
            'script': 'Script', 'clips': '[]', 'background_music': None,
            'voice_over': None, 'status': 'draft', 'output_path': None,
            'target_platform': 'douyin'
        }
        mock_db.fetchone.return_value = mock_row

        new_project = maker.duplicate_project("proj001", "Copy")

        assert new_project is not None
        assert new_project.name == "Copy"
        assert new_project.width == 1080

    def test_duplicate_project_not_found(self, maker, mock_db):
        mock_db.fetchone.return_value = None
        result = maker.duplicate_project("nonexistent")
        assert result is None

    def test_clip_to_dict(self, maker):
        clip = VideoClip(
            id="clip001",
            clip_type=ClipType.VIDEO,
            source_path="/path/video.mp4",
            start_time=1.0,
            duration=5.0,
            text_content="Hello",
            transition_type="fade"
        )
        data = maker._clip_to_dict(clip)
        assert data["id"] == "clip001"
        assert data["clip_type"] == "video"
        assert data["text_content"] == "Hello"

    def test_dict_to_clip(self, maker):
        data = {
            "id": "clip001",
            "clip_type": "video",
            "source_path": "/path/video.mp4",
            "start_time": 1.0,
            "duration": 5.0,
            "position": [0.5, 0.5],
            "scale": 1.0
        }
        clip = maker._dict_to_clip(data)
        assert clip.id == "clip001"
        assert clip.clip_type == ClipType.VIDEO


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
