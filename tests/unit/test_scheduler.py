#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for publisher/scheduler.py"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from acas_pro.publisher.scheduler import PublishScheduler
from acas_pro.publisher.publish_manager import PublishManager, PublishStatus


class TestPublishScheduler:
    def setup_method(self):
        self.scheduler = PublishScheduler()

    def test_init(self):
        assert self.scheduler is not None
        assert self.scheduler.publish_manager is not None
        assert self.scheduler.check_interval == 60
        assert self.scheduler.running is False

    def test_init_with_custom_interval(self):
        scheduler = PublishScheduler(check_interval=30)
        assert scheduler.check_interval == 30

    def test_get_optimal_publish_time(self):
        times = self.scheduler.get_optimal_publish_time("douyin")
        assert isinstance(times, list)
        assert len(times) > 0
        # Should be future times
        assert all(t > datetime.now() for t in times)

    def test_get_optimal_publish_time_xiaohongshu(self):
        times = self.scheduler.get_optimal_publish_time("xiaohongshu")
        assert isinstance(times, list)
        assert len(times) > 0

    def test_get_optimal_publish_time_unknown(self):
        times = self.scheduler.get_optimal_publish_time("unknown_platform")
        assert isinstance(times, list)
        assert len(times) > 0

    def test_get_optimal_publish_time_with_start_date(self):
        start = datetime.now() + timedelta(days=2)
        times = self.scheduler.get_optimal_publish_time("douyin", start_date=start)
        assert isinstance(times, list)
        assert len(times) > 0

    def test_get_optimal_publish_time_limited(self):
        times = self.scheduler.get_optimal_publish_time("douyin", days_ahead=1)
        assert len(times) <= 10  # Max 10 suggestions

    def test_schedule_batch(self):
        content_list = [
            {"path": "/tmp/v1.mp4", "title": "Video 1"},
            {"path": "/tmp/v2.mp4", "title": "Video 2"}
        ]
        with patch.object(self.scheduler.publish_manager, 'create_task') as mock_create:
            mock_task = MagicMock()
            mock_task.id = "task_1"
            mock_create.return_value = mock_task
            
            task_ids = self.scheduler.schedule_batch(
                content_list, ["douyin"]
            )
            assert len(task_ids) == 2

    def test_schedule_batch_with_start_time(self):
        content_list = [
            {"path": "/tmp/v1.mp4", "title": "Video 1"}
        ]
        start_time = datetime.now() + timedelta(days=1)
        with patch.object(self.scheduler.publish_manager, 'create_task') as mock_create:
            mock_task = MagicMock()
            mock_task.id = "task_1"
            mock_create.return_value = mock_task
            
            task_ids = self.scheduler.schedule_batch(
                content_list, ["douyin"], start_time=start_time
            )
            assert len(task_ids) == 1

    def test_auto_optimize_schedule(self):
        with patch.object(self.scheduler.publish_manager, 'get_task') as mock_get:
            mock_task = MagicMock()
            mock_task.status = PublishStatus.PENDING
            mock_task.platforms = [MagicMock()]
            mock_task.platforms[0].platform = "douyin"
            mock_get.return_value = mock_task
            
            with patch.object(self.scheduler.publish_manager, 'schedule_task') as mock_schedule:
                result = self.scheduler.auto_optimize_schedule(["task_1"])
                assert result is True

    def test_auto_optimize_schedule_balanced(self):
        with patch.object(self.scheduler.publish_manager, 'get_task') as mock_get:
            mock_task = MagicMock()
            mock_task.status = PublishStatus.PENDING
            mock_task.platforms = [MagicMock()]
            mock_task.platforms[0].platform = "douyin"
            mock_get.return_value = mock_task
            
            with patch.object(self.scheduler.publish_manager, 'schedule_task') as mock_schedule:
                result = self.scheduler.auto_optimize_schedule(
                    ["task_1", "task_2"], strategy="balanced"
                )
                assert result is True

    def test_auto_optimize_schedule_spread(self):
        with patch.object(self.scheduler.publish_manager, 'get_task') as mock_get:
            mock_task = MagicMock()
            mock_task.status = PublishStatus.PENDING
            mock_task.platforms = [MagicMock()]
            mock_task.platforms[0].platform = "douyin"
            mock_get.return_value = mock_task
            
            with patch.object(self.scheduler.publish_manager, 'schedule_task') as mock_schedule:
                result = self.scheduler.auto_optimize_schedule(
                    ["task_1"], strategy="spread"
                )
                assert result is True

    def test_auto_optimize_schedule_peak(self):
        with patch.object(self.scheduler.publish_manager, 'get_task') as mock_get:
            mock_task = MagicMock()
            mock_task.status = PublishStatus.PENDING
            mock_task.platforms = [MagicMock()]
            mock_task.platforms[0].platform = "douyin"
            mock_get.return_value = mock_task
            
            with patch.object(self.scheduler.publish_manager, 'schedule_task') as mock_schedule:
                result = self.scheduler.auto_optimize_schedule(
                    ["task_1"], strategy="peak"
                )
                assert result is True

    def test_auto_optimize_schedule_published(self):
        with patch.object(self.scheduler.publish_manager, 'get_task') as mock_get:
            mock_task = MagicMock()
            mock_task.status = PublishStatus.PUBLISHED
            mock_task.platforms = [MagicMock()]
            mock_task.platforms[0].platform = "douyin"
            mock_get.return_value = mock_task
            
            with patch.object(self.scheduler.publish_manager, 'schedule_task') as mock_schedule:
                result = self.scheduler.auto_optimize_schedule(["task_1"])
                assert result is True
                mock_schedule.assert_not_called()  # Should skip published tasks

    def test_auto_optimize_schedule_no_platforms(self):
        with patch.object(self.scheduler.publish_manager, 'get_task') as mock_get:
            mock_task = MagicMock()
            mock_task.status = PublishStatus.PENDING
            mock_task.platforms = []
            mock_get.return_value = mock_task
            
            with patch.object(self.scheduler.publish_manager, 'schedule_task') as mock_schedule:
                result = self.scheduler.auto_optimize_schedule(["task_1"])
                assert result is True

    def test_get_queue_status(self):
        with patch.object(self.scheduler.publish_manager, 'get_pending_tasks') as mock_pending:
            with patch.object(self.scheduler.publish_manager, 'get_scheduled_tasks') as mock_scheduled:
                mock_pending.return_value = [MagicMock(), MagicMock()]
                mock_scheduled.return_value = [MagicMock()]
                
                status = self.scheduler.get_queue_status()
                assert status["pending"] == 2
                assert status["scheduled"] == 1
                assert status["total"] == 3

    def test_best_publish_times(self):
        assert "douyin" in PublishScheduler.BEST_PUBLISH_TIMES
        assert "xiaohongshu" in PublishScheduler.BEST_PUBLISH_TIMES
        assert len(PublishScheduler.BEST_PUBLISH_TIMES["douyin"]) > 0
