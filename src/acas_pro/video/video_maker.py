#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Video Maker
智能视频制作引擎
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from ..core.logging import get_logger
from ..core.database import DatabaseManager

logger = get_logger(__name__)


class VideoStatus(Enum):
    """视频状态"""
    DRAFT = "draft"              # 草稿
    RENDERING = "rendering"      # 渲染中
    COMPLETED = "completed"      # 完成
    FAILED = "failed"            # 失败


class ClipType(Enum):
    """片段类型"""
    VIDEO = "video"              # 视频片段
    IMAGE = "image"              # 图片
    TEXT = "text"                # 文字
    TRANSITION = "transition"    # 转场
    EFFECT = "effect"            # 特效
    AUDIO = "audio"              # 音频


@dataclass
class VideoClip:
    """视频片段"""
    id: str
    clip_type: ClipType
    source_path: str           # 源文件路径
    start_time: float = 0.0    # 开始时间（秒）
    duration: float = 5.0      # 时长（秒）
    
    # 视觉参数
    position: tuple = field(default_factory=lambda: (0.5, 0.5))  # 中心位置 (x, y)
    scale: float = 1.0         # 缩放
    rotation: float = 0.0      # 旋转角度
    opacity: float = 1.0       # 透明度
    
    # 文字参数
    text_content: str = None
    text_style: dict = None    # 字体/颜色/大小等
    
    # 特效参数
    transition_type: str = None  # 转场类型
    effect_params: dict = None   # 特效参数
    
    # 音频参数
    volume: float = 1.0
    fade_in: float = 0.0
    fade_out: float = 0.0


@dataclass
class VideoProject:
    """视频项目"""
    id: str
    name: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # 基础参数
    width: int = 1080
    height: int = 1920          # 默认9:16竖屏
    fps: int = 30
    duration: float = 0.0
    
    # 内容
    title: str = ""
    description: str = ""
    script: str = ""            # 文案脚本
    
    # 片段列表
    clips: List[VideoClip] = field(default_factory=list)
    
    # 音频
    background_music: str = None
    voice_over: str = None      # 配音文件
    
    # 状态
    status: VideoStatus = VideoStatus.DRAFT
    output_path: str = None
    
    # 平台适配
    target_platform: str = "douyin"  # douyin/xiaohongshu/kuaishou等


class VideoMaker:
    """
    智能视频制作引擎
    
    功能：
    1. 视频项目管理
    2. 智能素材混剪
    3. 节奏感知剪辑
    4. 字幕自动生成
    5. 多平台格式导出
    """
    
    # 平台规格配置
    PLATFORM_SPECS = {
        "douyin": {
            "name": "抖音",
            "width": 1080,
            "height": 1920,
            "fps": 30,
            "max_duration": 300,  # 5分钟
            "aspect_ratio": "9:16",
        },
        "xiaohongshu": {
            "name": "小红书",
            "width": 1080,
            "height": 1440,
            "fps": 30,
            "max_duration": 300,
            "aspect_ratio": "3:4",
        },
        "kuaishou": {
            "name": "快手",
            "width": 1080,
            "height": 1920,
            "fps": 30,
            "max_duration": 600,
            "aspect_ratio": "9:16",
        },
        "bilibili": {
            "name": "B站",
            "width": 1920,
            "height": 1080,
            "fps": 60,
            "max_duration": 3600,
            "aspect_ratio": "16:9",
        },
        "tiktok": {
            "name": "TikTok",
            "width": 1080,
            "height": 1920,
            "fps": 30,
            "max_duration": 600,
            "aspect_ratio": "9:16",
        },
    }
    
    # 转场效果
    TRANSITIONS = [
        "fade",           # 淡入淡出
        "slide_left",     # 左滑
        "slide_right",    # 右滑
        "zoom_in",        # 放大
        "zoom_out",       # 缩小
        "wipe",           # 擦除
        "dissolve",       # 溶解
    ]
    
    # Tables managed by core/schema.py — do not add CREATE TABLE here

    def __init__(self, db: 'DatabaseManager' = None, output_dir: str = None) -> Any:
        self.db = db or DatabaseManager()
        self.output_dir = output_dir or os.path.expanduser("~/ACAS-Videos")
        self._ensure_output_dir()
        

        
    def _ensure_output_dir(self) -> Any:
        """确保输出目录存在"""
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        
    def create_project(
        self,
        name: str,
        target_platform: str = "douyin",
        title: str = "",
        script: str = ""
    ) -> VideoProject:
        """创建视频项目"""
        specs = self.PLATFORM_SPECS.get(target_platform, self.PLATFORM_SPECS["douyin"])
        
        project = VideoProject(
            id=f"proj_{int(datetime.now().timestamp())}",
            name=name,
            width=specs["width"],
            height=specs["height"],
            fps=specs["fps"],
            title=title,
            script=script,
            target_platform=target_platform,
        )
        
        self._save_project(project)
        logger.info(f"Created video project: {project.id}")
        return project
        
    def _save_project(self, project: VideoProject) -> Any:
        """保存项目到数据库"""
        self.db.execute("""
            INSERT OR REPLACE INTO video_projects (
                id, name, created_at, updated_at, width, height, fps, duration,
                title, description, script, clips, background_music, voice_over,
                status, output_path, target_platform
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            project.id, project.name, project.created_at.isoformat(),
            project.updated_at.isoformat(), project.width, project.height,
            project.fps, project.duration, project.title, project.description,
            project.script, json.dumps([self._clip_to_dict(c) for c in project.clips]),
            project.background_music, project.voice_over, project.status.value,
            project.output_path, project.target_platform
        ))
        
    def _clip_to_dict(self, clip: VideoClip) -> dict:
        """将片段转换为字典"""
        return {
            "id": clip.id,
            "clip_type": clip.clip_type.value,
            "source_path": clip.source_path,
            "start_time": clip.start_time,
            "duration": clip.duration,
            "position": clip.position,
            "scale": clip.scale,
            "rotation": clip.rotation,
            "opacity": clip.opacity,
            "text_content": clip.text_content,
            "text_style": clip.text_style,
            "transition_type": clip.transition_type,
            "effect_params": clip.effect_params,
            "volume": clip.volume,
            "fade_in": clip.fade_in,
            "fade_out": clip.fade_out,
        }
        
    def get_project(self, project_id: str) -> Optional[VideoProject]:
        """获取项目"""
        row = self.db.fetchone("SELECT * FROM video_projects WHERE id = ?", (project_id,))
        if not row:
            return None
        return self._row_to_project(row)
        
    def _row_to_project(self, row: dict) -> VideoProject:
        """将数据库行转换为项目对象"""
        clips_data = json.loads(row['clips']) if row['clips'] else []
        clips = [self._dict_to_clip(c) for c in clips_data]
        
        return VideoProject(
            id=row['id'],
            name=row['name'],
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
            width=row['width'],
            height=row['height'],
            fps=row['fps'],
            duration=row['duration'],
            title=row['title'] or "",
            description=row['description'] or "",
            script=row['script'] or "",
            clips=clips,
            background_music=row['background_music'],
            voice_over=row['voice_over'],
            status=VideoStatus(row['status']),
            output_path=row['output_path'],
            target_platform=row['target_platform'],
        )
        
    def _dict_to_clip(self, data: dict) -> VideoClip:
        """将字典转换为片段对象"""
        return VideoClip(
            id=data['id'],
            clip_type=ClipType(data['clip_type']),
            source_path=data['source_path'],
            start_time=data.get('start_time', 0.0),
            duration=data.get('duration', 5.0),
            position=tuple(data.get('position', [0.5, 0.5])),
            scale=data.get('scale', 1.0),
            rotation=data.get('rotation', 0.0),
            opacity=data.get('opacity', 1.0),
            text_content=data.get('text_content'),
            text_style=data.get('text_style'),
            transition_type=data.get('transition_type'),
            effect_params=data.get('effect_params'),
            volume=data.get('volume', 1.0),
            fade_in=data.get('fade_in', 0.0),
            fade_out=data.get('fade_out', 0.0),
        )
        
    def add_clip(
        self,
        project_id: str,
        clip_type: ClipType,
        source_path: str,
        duration: float = 5.0,
        **kwargs
    ) -> Optional[VideoClip]:
        """添加片段到项目"""
        project = self.get_project(project_id)
        if not project:
            logger.error(f"Project not found: {project_id}")
            return None
            
        clip = VideoClip(
            id=f"clip_{len(project.clips)}_{int(datetime.now().timestamp())}",
            clip_type=clip_type,
            source_path=source_path,
            duration=duration,
            **kwargs
        )
        
        project.clips.append(clip)
        project.duration = sum(c.duration for c in project.clips)
        project.updated_at = datetime.now()
        
        self._save_project(project)
        return clip
        
    def auto_edit(
        self,
        project_id: str,
        materials: List[str],
        music_path: str = None,
        target_duration: float = 30.0
    ) -> bool:
        """
        智能自动剪辑
        
        根据素材自动进行节奏感知剪辑
        """
        project = self.get_project(project_id)
        if not project:
            return False
            
        logger.info(f"Starting auto-edit for project: {project_id}")
        
        # 计算每个素材的目标时长
        if not materials:
            logger.warning("No materials provided for auto-edit")
            return False
            
        clip_duration = target_duration / len(materials)
        clip_duration = min(clip_duration, 5.0)  # 单片段不超过5秒
        
        # 添加素材片段
        for i, material in enumerate(materials):
            # 判断素材类型
            ext = Path(material).suffix.lower()
            if ext in ['.mp4', '.mov', '.avi', '.mkv']:
                clip_type = ClipType.VIDEO
            elif ext in ['.jpg', '.jpeg', '.png', '.webp']:
                clip_type = ClipType.IMAGE
            else:
                continue
                
            # 添加转场（除了第一个）
            transition = None
            if i > 0:
                transition = self.TRANSITIONS[i % len(self.TRANSITIONS)]
                
            self.add_clip(
                project_id=project_id,
                clip_type=clip_type,
                source_path=material,
                duration=clip_duration,
                transition_type=transition
            )
            
        # 添加背景音乐
        if music_path and os.path.exists(music_path):
            project.background_music = music_path
            
        project.updated_at = datetime.now()
        self._save_project(project)
        
        logger.info(f"Auto-edit completed for project: {project_id}")
        return True
        
    def add_subtitles(
        self,
        project_id: str,
        subtitles: List[Dict[str, any]]
    ) -> Any:
        """
        添加字幕
        
        subtitles: [{"text": "字幕文字", "start": 0.0, "end": 3.0, "style": {}}]
        """
        project = self.get_project(project_id)
        if not project:
            return False
            
        for sub in subtitles:
            clip = VideoClip(
                id=f"subtitle_{int(datetime.now().timestamp() * 1000)}",
                clip_type=ClipType.TEXT,
                source_path="",
                start_time=sub.get('start', 0.0),
                duration=sub.get('end', 3.0) - sub.get('start', 0.0),
                text_content=sub.get('text', ''),
                text_style=sub.get('style', {
                    'font': 'Arial',
                    'size': 48,
                    'color': '#FFFFFF',
                    'outline': '#000000',
                })
            )
            project.clips.append(clip)
            
        self._save_project(project)
        return True
        
    def render_project(
        self,
        project_id: str,
        quality: str = "high"
    ) -> Optional[str]:
        """
        渲染视频项目
        
        quality: low/medium/high/ultra
        """
        project = self.get_project(project_id)
        if not project:
            return None
            
        # 更新状态
        project.status = VideoStatus.RENDERING
        self._save_project(project)
        
        try:
            # 生成输出路径
            output_filename = f"{project.id}_{project.name}.mp4"
            output_path = os.path.join(self.output_dir, output_filename)
            
            # TODO: 实际渲染逻辑（需要ffmpeg或moviepy）
            logger.warning("Video rendering not integrated, returning None"); return None
            # 这里模拟渲染过程
            logger.info(f"Rendering project {project_id} to {output_path}")
            
            # 模拟渲染完成
            project.output_path = output_path
            project.status = VideoStatus.COMPLETED
            project.updated_at = datetime.now()
            self._save_project(project)
            
            logger.info(f"Render completed: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Render failed: {e}")
            project.status = VideoStatus.FAILED
            self._save_project(project)
            return None
            
    def list_projects(
        self,
        status: VideoStatus = None,
        platform: str = None,
        limit: int = 50
    ) -> List[VideoProject]:
        """列出视频项目"""
        query = "SELECT * FROM video_projects WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = ?"
            params.append(status.value)
        if platform:
            query += " AND target_platform = ?"
            params.append(platform)
            
        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)
        
        rows = self.db.fetchall(query, params)
        return [self._row_to_project(row) for row in rows]
        
    def delete_project(self, project_id: str) -> bool:
        """删除项目"""
        try:
            self.db.execute("DELETE FROM video_projects WHERE id = ?", (project_id,))
            return True
        except Exception as e:
            logger.error(f"Failed to delete project: {e}")
            return False
            
    def duplicate_project(self, project_id: str, new_name: str = None) -> Optional[VideoProject]:
        """复制项目"""
        project = self.get_project(project_id)
        if not project:
            return None
            
        new_project = VideoProject(
            id=f"proj_{int(datetime.now().timestamp())}",
            name=new_name or f"{project.name} 副本",
            width=project.width,
            height=project.height,
            fps=project.fps,
            title=project.title,
            description=project.description,
            script=project.script,
            clips=[VideoClip(
                id=f"clip_{i}_{int(datetime.now().timestamp())}",
                clip_type=c.clip_type,
                source_path=c.source_path,
                start_time=c.start_time,
                duration=c.duration,
                position=c.position,
                scale=c.scale,
                rotation=c.rotation,
                opacity=c.opacity,
                text_content=c.text_content,
                text_style=c.text_style,
                transition_type=c.transition_type,
                effect_params=c.effect_params,
            ) for i, c in enumerate(project.clips)],
            target_platform=project.target_platform,
        )
        
        self._save_project(new_project)
        return new_project
