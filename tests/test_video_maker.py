#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Video Maker Tests
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from acas_pro.video.video_maker import (
    VideoMaker, VideoProject, VideoClip,
    VideoStatus, ClipType
)


class TestVideoStatus:
    """Video status enum tests"""
    
    def test_status_values(self):
        """Test status enum values"""
        assert VideoStatus.DRAFT.value == "draft"
        assert VideoStatus.RENDERING.value == "rendering"
        assert VideoStatus.COMPLETED.value == "completed"
        assert VideoStatus.FAILED.value == "failed"


class TestClipType:
    """Clip type enum tests"""
    
    def test_clip_type_values(self):
        """Test clip type values"""
        assert ClipType.VIDEO.value == "video"
        assert ClipType.IMAGE.value == "image"
        assert ClipType.TEXT.value == "text"
        assert ClipType.TRANSITION.value == "transition"
        assert ClipType.EFFECT.value == "effect"
        assert ClipType.AUDIO.value == "audio"


class TestVideoClip:
    """Video clip tests"""
    
    def test_clip_creation(self):
        """Test clip creation"""
        clip = VideoClip(
            id="clip_001",
            clip_type=ClipType.VIDEO,
            source_path="/path/to/video.mp4",
            start_time=0.0,
            duration=5.0
        )
        
        assert clip.id == "clip_001"
        assert clip.clip_type == ClipType.VIDEO
        assert clip.scale == 1.0  # default
        assert clip.opacity == 1.0  # default


class TestVideoProject:
    """Video project tests"""
    
    def test_project_creation(self):
        """Test project creation"""
        project = VideoProject(
            id="proj_001",
            name="Test Project",
            width=1080,
            height=1920
        )
        
        assert project.id == "proj_001"
        assert project.name == "Test Project"
        assert project.status == VideoStatus.DRAFT
        assert project.fps == 30  # default
    
    def test_project_default_clips(self):
        """Test project default clips list"""
        project = VideoProject(id="proj_001", name="Test")
        
        assert project.clips == []
        assert isinstance(project.clips, list)


class TestVideoMaker:
    """Video maker tests"""
    
    @pytest.fixture
    def mock_db(self):
        mock = Mock()
        mock.execute = Mock()
        mock.fetchone = Mock(return_value=None)
        mock.fetchall = Mock(return_value=[])
        return mock
    
    @pytest.fixture
    def maker(self, mock_db):
        return VideoMaker(db=mock_db)
    
    def test_init(self, maker, mock_db):
        """Test initialization"""
        assert maker.db == mock_db
        mock_db.execute.assert_called()
    
    def test_create_project(self, maker, mock_db):
        """Test create project"""
        project = maker.create_project(
            name="Test Project",
            target_platform="douyin"
        )
        
        assert project is not None
        assert project.name == "Test Project"
        assert project.target_platform == "douyin"
        assert project.width == 1080  # from platform specs
    
    def test_create_project_custom_platform(self, maker, mock_db):
        """Test create project for different platform"""
        project = maker.create_project(
            name="Bilibili Project",
            target_platform="bilibili"
        )
        
        assert project.width == 1920  # B站横屏
        assert project.height == 1080
    
    def test_get_project_not_found(self, maker, mock_db):
        """Test get non-existent project"""
        mock_db.fetchone.return_value = None
        
        project = maker.get_project("non_existent")
        
        assert project is None
    
    def test_list_projects_empty(self, maker, mock_db):
        """Test list with no projects"""
        mock_db.fetchall.return_value = []
        
        projects = maker.list_projects()
        
        assert projects == []
    
    def test_delete_project(self, maker, mock_db):
        """Test delete project"""
        result = maker.delete_project("proj_001")
        
        assert result is True
        mock_db.execute.assert_called()
    
    def test_platform_specs_accessible(self, maker):
        """Test platform specs are accessible"""
        assert "douyin" in maker.PLATFORM_SPECS
        assert "bilibili" in maker.PLATFORM_SPECS
        assert maker.PLATFORM_SPECS["douyin"]["width"] == 1080


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
