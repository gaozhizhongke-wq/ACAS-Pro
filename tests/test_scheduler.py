#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Publish Scheduler Tests
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from acas_pro.publisher.scheduler import PublishScheduler
from acas_pro.publisher.publish_manager import PublishStatus


class TestPublishScheduler:
    """Publish scheduler tests"""
    
    @pytest.fixture
    def mock_manager(self):
        mock = Mock()
        mock.get_scheduled_tasks.return_value = []
        mock.get_pending_tasks.return_value = []
        mock.create_task.return_value = Mock(id="task_001")
        mock.get_task.return_value = None
        return mock
    
    @pytest.fixture
    def scheduler(self, mock_manager):
        return PublishScheduler(publish_manager=mock_manager, check_interval=60)
    
    def test_init(self, scheduler):
        """Test initialization"""
        assert scheduler.check_interval == 60
        assert scheduler.running is False
    
    def test_best_publish_times_exist(self, scheduler):
        """Test best publish times exist"""
        assert "douyin" in scheduler.BEST_PUBLISH_TIMES
        assert "xiaohongshu" in scheduler.BEST_PUBLISH_TIMES
        assert "bilibili" in scheduler.BEST_PUBLISH_TIMES
    
    def test_get_optimal_publish_time(self, scheduler):
        """Test get optimal publish time"""
        suggestions = scheduler.get_optimal_publish_time("douyin")
        
        assert len(suggestions) > 0
        assert all(isinstance(t, datetime) for t in suggestions)
    
    def test_get_optimal_publish_time_with_start_date(self, scheduler):
        """Test get optimal publish time with start date"""
        start = datetime.now() + timedelta(days=1)
        suggestions = scheduler.get_optimal_publish_time("douyin", start_date=start, days_ahead=2)
        
        assert len(suggestions) > 0
        # Check that suggestions are in the future
        assert all(t > datetime.now() for t in suggestions)
    
    def test_schedule_batch(self, scheduler, mock_manager):
        """Test schedule batch"""
        content_list = [
            {"path": "/path/1.mp4", "title": "Video 1"},
            {"path": "/path/2.mp4", "title": "Video 2"},
        ]
        
        task_ids = scheduler.schedule_batch(
            content_list=content_list,
            platforms=["douyin"],
            start_time=datetime.now(),
            interval_minutes=60
        )
        
        assert len(task_ids) == 2
        mock_manager.create_task.assert_called()
    
    def test_schedule_batch_default_start_time(self, scheduler, mock_manager):
        """Test schedule batch with default start time"""
        content_list = [{"path": "/path/1.mp4", "title": "Video 1"}]
        
        task_ids = scheduler.schedule_batch(
            content_list=content_list,
            platforms=["douyin"]
        )
        
        assert len(task_ids) == 1
    
    def test_auto_optimize_schedule(self, scheduler, mock_manager):
        """Test auto optimize schedule"""
        mock_task = Mock()
        mock_task.status = PublishStatus.SCHEDULED
        mock_task.platforms = [Mock(platform="douyin")]
        mock_manager.get_task.return_value = mock_task
        
        result = scheduler.auto_optimize_schedule(["task_001", "task_002"])
        
        assert result is True
    
    def test_get_queue_status(self, scheduler, mock_manager):
        """Test get queue status"""
        mock_manager.get_pending_tasks.return_value = [Mock(), Mock()]
        mock_manager.get_scheduled_tasks.return_value = [Mock()]
        
        status = scheduler.get_queue_status()
        
        assert status["pending"] == 2
        assert status["scheduled"] == 1
        assert status["total"] == 3
    
    def test_clear_completed(self, scheduler, mock_manager):
        """Test clear completed tasks"""
        mock_task = Mock()
        mock_task.published_at = datetime.now() - timedelta(days=10)
        mock_manager.list_tasks.return_value = [mock_task, mock_task]
        
        cleared = scheduler.clear_completed(days=7)
        
        assert cleared == 2
        mock_manager.delete_task.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
