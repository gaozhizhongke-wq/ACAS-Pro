# -*- coding: utf-8 -*-
"""Tests for video_maker exception branches."""
from unittest.mock import MagicMock


class TestVideoMakerExceptions:
    """Test video_maker exception handling."""

    def test_get_project_not_found(self):
        """Test get_project when project doesn't exist."""
        from acas_pro.video.video_maker import VideoMaker
        
        mock_db = MagicMock()
        mock_db.fetchone.return_value = None
        
        maker = VideoMaker(db=mock_db)
        result = maker.get_project("nonexistent")
        assert result is None

    def test_render_project_not_found(self):
        """Test render_project when project doesn't exist."""
        from acas_pro.video.video_maker import VideoMaker
        
        mock_db = MagicMock()
        mock_db.fetchone.return_value = None
        
        maker = VideoMaker(db=mock_db)
        result = maker.render_project("nonexistent")
        assert result is None

    def test_add_subtitles_project_not_found(self):
        """Test add_subtitles when project doesn't exist."""
        from acas_pro.video.video_maker import VideoMaker
        
        mock_db = MagicMock()
        mock_db.fetchone.return_value = None
        
        maker = VideoMaker(db=mock_db)
        result = maker.add_subtitles("nonexistent", [])
        assert result is False

    def test_list_projects_with_filters(self):
        """Test list_projects with status and platform filters."""
        from acas_pro.video.video_maker import VideoMaker, VideoStatus
        
        mock_db = MagicMock()
        mock_db.fetchall.return_value = []
        
        maker = VideoMaker(db=mock_db)
        result = maker.list_projects(
            status=VideoStatus.DRAFT,
            platform="douyin",
            limit=10
        )
        assert isinstance(result, list)
        assert len(result) == 0

    def test_list_projects_no_filters(self):
        """Test list_projects without filters."""
        from acas_pro.video.video_maker import VideoMaker
        
        mock_db = MagicMock()
        mock_db.fetchall.return_value = []
        
        maker = VideoMaker(db=mock_db)
        result = maker.list_projects()
        assert isinstance(result, list)
