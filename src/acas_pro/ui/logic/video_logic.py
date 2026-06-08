#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Video Creation Business Logic
Extracted from VideoMakerPage for testability
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from enum import Enum


class VideoFormat(Enum):
    """Video output formats"""
    MP4 = "mp4"
    MOV = "mov"
    AVI = "avi"
    WEBM = "webm"


class VideoQuality(Enum):
    """Video quality presets"""
    SD_480P = "480p"
    HD_720P = "720p"
    FHD_1080P = "1080p"
    QHD_1440P = "1440p"
    UHD_4K = "4k"


@dataclass
class VideoProject:
    """Video project data"""
    id: str
    name: str
    duration: int  # seconds
    format: VideoFormat
    quality: VideoQuality
    scenes: List[Dict]
    audio_tracks: List[Dict]
    status: str  # draft, rendering, completed


@dataclass
class RenderJob:
    """Video render job"""
    id: str
    project_id: str
    status: str  # queued, rendering, completed, failed
    progress: float  # 0-100
    output_path: str
    estimated_time: int  # seconds remaining


class VideoLogic:
    """Video creation business logic"""
    
    QUALITY_SETTINGS = {
        VideoQuality.SD_480P: {"width": 854, "height": 480, "bitrate": "2M"},
        VideoQuality.HD_720P: {"width": 1280, "height": 720, "bitrate": "5M"},
        VideoQuality.FHD_1080P: {"width": 1920, "height": 1080, "bitrate": "8M"},
        VideoQuality.QHD_1440P: {"width": 2560, "height": 1440, "bitrate": "16M"},
        VideoQuality.UHD_4K: {"width": 3840, "height": 2160, "bitrate": "35M"},
    }
    
    def __init__(self) -> Any:
        self._projects: Dict[str, VideoProject] = {}
        self._render_jobs: Dict[str, RenderJob] = {}
    
    def create_project(self, name: str, duration: int, 
                      format: VideoFormat = VideoFormat.MP4,
                      quality: VideoQuality = VideoQuality.FHD_1080P) -> VideoProject:
        """Create new video project"""
        import uuid
        project = VideoProject(
            id=str(uuid.uuid4()),
            name=name,
            duration=duration,
            format=format,
            quality=quality,
            scenes=[],
            audio_tracks=[],
            status="draft"
        )
        self._projects[project.id] = project
        return project
    
    def add_scene(self, project_id: str, scene_data: Dict) -> bool:
        """Add scene to project"""
        project = self._projects.get(project_id)
        if not project:
            return False
        
        scene_data["id"] = len(project.scenes)
        project.scenes.append(scene_data)
        return True
    
    def add_audio_track(self, project_id: str, audio_data: Dict) -> bool:
        """Add audio track to project"""
        project = self._projects.get(project_id)
        if not project:
            return False
        
        project.audio_tracks.append(audio_data)
        return True
    
    def estimate_render_time(self, project_id: str) -> int:
        """Estimate render time in seconds"""
        project = self._projects.get(project_id)
        if not project:
            return 0
        
        # Base time + per-scene time + quality multiplier
        base_time = 30
        scene_time = len(project.scenes) * 10
        
        quality_multiplier = {
            VideoQuality.SD_480P: 0.5,
            VideoQuality.HD_720P: 0.8,
            VideoQuality.FHD_1080P: 1.0,
            VideoQuality.QHD_1440P: 1.8,
            VideoQuality.UHD_4K: 3.5,
        }.get(project.quality, 1.0)
        
        return int((base_time + scene_time) * quality_multiplier)
    
    def get_quality_settings(self, quality: VideoQuality) -> Dict:
        """Get technical settings for quality level"""
        return self.QUALITY_SETTINGS.get(quality, self.QUALITY_SETTINGS[VideoQuality.FHD_1080P])
    
    def validate_project(self, project_id: str) -> List[str]:
        """Validate project and return list of issues"""
        project = self._projects.get(project_id)
        if not project:
            return ["Project not found"]
        
        issues = []
        
        if not project.scenes:
            issues.append("No scenes added")
        
        total_scene_duration = sum(s.get("duration", 0) for s in project.scenes)
        if total_scene_duration != project.duration:
            issues.append(f"Scene durations ({total_scene_duration}s) don't match project duration ({project.duration}s)")
        
        return issues
    
    def export_project_config(self, project_id: str) -> Dict:
        """Export project as configuration dict"""
        project = self._projects.get(project_id)
        if not project:
            return {}
        
        return {
            "id": project.id,
            "name": project.name,
            "duration": project.duration,
            "format": project.format.value,
            "quality": project.quality.value,
            "scene_count": len(project.scenes),
            "audio_track_count": len(project.audio_tracks),
            "settings": self.get_quality_settings(project.quality),
        }
