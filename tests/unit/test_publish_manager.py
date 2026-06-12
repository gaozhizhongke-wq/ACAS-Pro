#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for publisher/publish_manager.py dataclasses and enums."""

from unittest.mock import MagicMock
import sys

if 'numpy' not in sys.modules:
    sys.modules['numpy'] = MagicMock()


class TestPublishStatusEnum:
    def test_values(self):
        from acas_pro.publisher.publish_manager import PublishStatus
        assert PublishStatus.PENDING.value == "pending"
        assert PublishStatus.PUBLISHED.value == "published"
        assert len(PublishStatus) >= 6

class TestContentTypeEnum:
    def test_values(self):
        from acas_pro.publisher.publish_manager import ContentType
        assert ContentType.VIDEO.value == "video"
        assert ContentType.IMAGE.value == "image"
        assert ContentType.CAROUSEL.value == "carousel"

class TestPlatformConfig:
    def test_defaults(self):
        from acas_pro.publisher.publish_manager import PlatformConfig
        pc = PlatformConfig(platform="douyin", account_id="acc1")
        assert pc.enabled == True  # noqa: E712
        assert pc.auto_publish == False  # noqa: E712
        assert pc.best_time_start == 18

class TestPublishTask:
    def test_defaults(self):
        from acas_pro.publisher.publish_manager import PublishTask, PublishStatus, ContentType
        t = PublishTask(
            id="t1", content_path="/video.mp4", content_type=ContentType.VIDEO
        )
        assert t.status == PublishStatus.PENDING
        assert t.retry_count == 0
        assert t.max_retries == 3
        assert t.platforms == []

class TestPublishManagerFeatures:
    def test_platform_features_exist(self):
        from acas_pro.publisher.publish_manager import PublishManager
        assert "douyin" in PublishManager.PLATFORM_FEATURES
        assert "bilibili" in PublishManager.PLATFORM_FEATURES
        assert "tiktok" in PublishManager.PLATFORM_FEATURES

    def test_douyin_features(self):
        from acas_pro.publisher.publish_manager import PublishManager, ContentType
        dy = PublishManager.PLATFORM_FEATURES["douyin"]
        assert dy["name"] == "抖音"
        assert dy["max_duration"] == 300
        assert ContentType.VIDEO in dy["content_types"]

    def test_bilibili_longer_duration(self):
        from acas_pro.publisher.publish_manager import PublishManager
        bili = PublishManager.PLATFORM_FEATURES["bilibili"]
        assert bili["max_duration"] == 3600

class TestPublishManagerInit:
    def test_init_with_mock_db(self):
        from acas_pro.publisher.publish_manager import PublishManager
        mock_db = MagicMock()
        # _init_database removed — schema managed by core/schema.py
        mgr = PublishManager(db=mock_db)
        assert mgr.db is mock_db
