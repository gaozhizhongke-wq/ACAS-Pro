#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - More UI Logic Tests
Tests for video and analytics logic
"""

import pytest
from datetime import datetime, timedelta

from acas_pro.ui.logic import (
    VideoLogic, VideoProject, VideoFormat, VideoQuality,
    AnalyticsLogic, MetricData, MetricType, TimeRange
)


class TestVideoLogic:
    """Video logic tests"""
    
    @pytest.fixture
    def video(self):
        return VideoLogic()
    
    def test_create_project(self, video):
        """Test project creation"""
        project = video.create_project(
            name="Test Video",
            duration=60,
            format=VideoFormat.MP4,
            quality=VideoQuality.FHD_1080P
        )
        
        assert project.name == "Test Video"
        assert project.duration == 60
        assert project.format == VideoFormat.MP4
        assert project.status == "draft"
    
    def test_add_scene(self, video):
        """Test adding scene"""
        project = video.create_project("Test", 60)
        result = video.add_scene(project.id, {"duration": 30, "content": "Scene 1"})
        
        assert result is True
        assert len(project.scenes) == 1
    
    def test_add_audio_track(self, video):
        """Test adding audio"""
        project = video.create_project("Test", 60)
        result = video.add_audio_track(project.id, {"type": "music", "file": "bgm.mp3"})
        
        assert result is True
        assert len(project.audio_tracks) == 1
    
    def test_estimate_render_time(self, video):
        """Test render time estimation"""
        project = video.create_project("Test", 60)
        video.add_scene(project.id, {"duration": 30})
        
        time = video.estimate_render_time(project.id)
        assert time > 0
    
    def test_get_quality_settings(self, video):
        """Test quality settings"""
        settings = video.get_quality_settings(VideoQuality.FHD_1080P)
        
        assert settings["width"] == 1920
        assert settings["height"] == 1080
    
    def test_validate_project_empty(self, video):
        """Test validation of empty project"""
        project = video.create_project("Test", 60)
        issues = video.validate_project(project.id)
        
        assert "No scenes added" in issues
    
    def test_validate_project_duration_mismatch(self, video):
        """Test validation with duration mismatch"""
        project = video.create_project("Test", 60)
        video.add_scene(project.id, {"duration": 30})  # Only 30s, project is 60s
        
        issues = video.validate_project(project.id)
        assert any("don't match" in i for i in issues)
    
    def test_export_project_config(self, video):
        """Test project export"""
        project = video.create_project("Test", 60)
        video.add_scene(project.id, {"duration": 60})
        
        config = video.export_project_config(project.id)
        
        assert config["name"] == "Test"
        assert config["duration"] == 60
        assert "settings" in config


class TestAnalyticsLogic:
    """Analytics logic tests"""
    
    @pytest.fixture
    def analytics(self):
        return AnalyticsLogic()
    
    def test_get_time_range_today(self, analytics):
        """Test today range"""
        start, end = analytics.get_time_range(TimeRange.TODAY)
        
        assert start.date() == datetime.now().date()
        assert end.date() == datetime.now().date()
    
    def test_get_time_range_7d(self, analytics):
        """Test 7 days range"""
        start, end = analytics.get_time_range(TimeRange.LAST_7_DAYS)
        
        assert (end - start).days == 7
    
    def test_get_time_range_30d(self, analytics):
        """Test 30 days range"""
        start, end = analytics.get_time_range(TimeRange.LAST_30_DAYS)
        
        assert (end - start).days == 30
    
    def test_aggregate_metrics(self, analytics):
        """Test metric aggregation"""
        data = [
            MetricData(datetime(2026, 1, 1, 10), 100, "douyin", MetricType.VIEWS),
            MetricData(datetime(2026, 1, 1, 11), 200, "douyin", MetricType.VIEWS),
            MetricData(datetime(2026, 1, 2, 10), 150, "douyin", MetricType.VIEWS),
        ]
        
        result = analytics.aggregate_metrics(data, "day")
        
        assert "2026-01-01" in result
        assert "2026-01-02" in result
        assert result["2026-01-01"][0].value == 300  # 100 + 200
    
    def test_calculate_growth_rate(self, analytics):
        """Test growth rate calculation"""
        assert analytics.calculate_growth_rate(110, 100) == 10.0
        assert analytics.calculate_growth_rate(90, 100) == -10.0
        assert analytics.calculate_growth_rate(100, 0) == 100.0
    
    def test_calculate_engagement_rate(self, analytics):
        """Test engagement rate"""
        assert analytics.calculate_engagement_rate(50, 1000) == 5.0
        assert analytics.calculate_engagement_rate(0, 1000) == 0.0
        assert analytics.calculate_engagement_rate(50, 0) == 0.0
    
    def test_generate_summary(self, analytics):
        """Test summary generation"""
        data = [
            MetricData(datetime.now(), 100, "douyin", MetricType.VIEWS),
            MetricData(datetime.now(), 200, "douyin", MetricType.VIEWS),
            MetricData(datetime.now(), 300, "douyin", MetricType.VIEWS),
        ]
        
        summary = analytics.generate_summary(data)
        
        assert summary["total"] == 600
        assert summary["average"] == 200
        assert summary["max"] == 300
        assert summary["min"] == 100
    
    def test_compare_periods(self, analytics):
        """Test period comparison"""
        current = [MetricData(datetime.now(), 100, "d", MetricType.VIEWS)]
        previous = [MetricData(datetime.now(), 80, "d", MetricType.VIEWS)]
        
        result = analytics.compare_periods(current, previous)
        
        assert result["growth_rate"] == 25.0
        assert result["current_total"] == 100
        assert result["previous_total"] == 80
    
    def test_detect_anomalies(self, analytics):
        """Test anomaly detection"""
        data = [
            MetricData(datetime.now(), 100, "d", MetricType.VIEWS),
            MetricData(datetime.now(), 105, "d", MetricType.VIEWS),
            MetricData(datetime.now(), 98, "d", MetricType.VIEWS),
            MetricData(datetime.now(), 1000, "d", MetricType.VIEWS),  # Anomaly
        ]
        
        anomalies = analytics.detect_anomalies(data, threshold=1.5)
        
        assert len(anomalies) == 1
        assert anomalies[0].value == 1000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
