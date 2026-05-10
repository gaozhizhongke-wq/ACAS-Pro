#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Publish Manager
多平台内容发布管理
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from ..core.logging import get_logger
from ..core.database import DatabaseManager

logger = get_logger(__name__)


class PublishStatus(Enum):
    """发布状态"""
    PENDING = "pending"          # 待发布
    SCHEDULED = "scheduled"      # 已排期
    PUBLISHING = "publishing"    # 发布中
    PUBLISHED = "published"      # 已发布
    FAILED = "failed"            # 失败
    CANCELLED = "cancelled"      # 已取消


class ContentType(Enum):
    """内容类型"""
    VIDEO = "video"              # 视频
    IMAGE = "image"              # 图片
    TEXT = "text"                # 文字
    CAROUSEL = "carousel"        # 图文轮播


@dataclass
class PlatformConfig:
    """平台配置"""
    platform: str                # douyin/xiaohongshu/kuaishou/bilibili/tiktok
    account_id: str
    enabled: bool = True
    
    # 发布设置
    auto_publish: bool = False   # 是否自动发布
    best_time_start: int = 18    # 最佳发布时间开始（小时）
    best_time_end: int = 22      # 最佳发布时间结束（小时）
    
    # 内容适配
    title_max_length: int = 50
    desc_max_length: int = 500
    tag_max_count: int = 10


@dataclass
class PublishTask:
    """发布任务"""
    id: str
    content_path: str            # 内容文件路径
    content_type: ContentType
    
    # 内容信息
    title: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)
    cover_image: str = None
    
    # 发布配置
    platforms: List[PlatformConfig] = field(default_factory=list)
    scheduled_time: datetime = None
    
    # 状态
    status: PublishStatus = PublishStatus.PENDING
    publish_results: Dict[str, dict] = field(default_factory=dict)  # platform -> result
    
    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    published_at: datetime = None
    
    # 重试
    retry_count: int = 0
    max_retries: int = 3


class PublishManager:
    """
    多平台内容发布管理器
    
    功能：
    1. 多平台发布任务管理
    2. 内容适配与优化
    3. 定时发布调度
    4. 发布状态追踪
    5. 失败重试机制
    """
    
    # 平台特性配置
    PLATFORM_FEATURES = {
        "douyin": {
            "name": "抖音",
            "content_types": [ContentType.VIDEO],
            "max_duration": 300,      # 5分钟
            "title_max": 55,
            "desc_max": 500,
            "tag_max": 10,
            "aspect_ratios": ["9:16"],
            "features": ["dou+"],     # 支持DOU+投放
        },
        "xiaohongshu": {
            "name": "小红书",
            "content_types": [ContentType.VIDEO, ContentType.IMAGE, ContentType.CAROUSEL],
            "max_duration": 300,
            "title_max": 20,
            "desc_max": 1000,
            "tag_max": 10,
            "aspect_ratios": ["3:4", "1:1", "4:3"],
            "features": ["notes", "tags"],
        },
        "kuaishou": {
            "name": "快手",
            "content_types": [ContentType.VIDEO],
            "max_duration": 600,      # 10分钟
            "title_max": 50,
            "desc_max": 500,
            "tag_max": 10,
            "aspect_ratios": ["9:16"],
            "features": ["promotion"],
        },
        "bilibili": {
            "name": "B站",
            "content_types": [ContentType.VIDEO],
            "max_duration": 3600,     # 1小时
            "title_max": 80,
            "desc_max": 2000,
            "tag_max": 10,
            "aspect_ratios": ["16:9"],
            "features": ["danmaku", "sections"],
        },
        "tiktok": {
            "name": "TikTok",
            "content_types": [ContentType.VIDEO],
            "max_duration": 600,
            "title_max": 100,
            "desc_max": 2200,
            "tag_max": 30,
            "aspect_ratios": ["9:16"],
            "features": ["promote"],
        },
        "instagram": {
            "name": "Instagram",
            "content_types": [ContentType.VIDEO, ContentType.IMAGE, ContentType.CAROUSEL],
            "max_duration": 60,
            "title_max": 0,           # 无标题
            "desc_max": 2200,
            "tag_max": 30,
            "aspect_ratios": ["1:1", "4:5", "9:16"],
            "features": ["reels", "stories"],
        },
        "youtube": {
            "name": "YouTube",
            "content_types": [ContentType.VIDEO],
            "max_duration": 43200,    # 12小时
            "title_max": 100,
            "desc_max": 5000,
            "tag_max": 15,
            "aspect_ratios": ["16:9"],
            "features": ["shorts", "chapters"],
        },
    }
    
    def __init__(self, db: 'DatabaseManager' = None):
        self.db = db or DatabaseManager()
        self._init_database()
        
    def _init_database(self):
        """初始化数据库表"""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS publish_tasks (
                id TEXT PRIMARY KEY,
                content_path TEXT NOT NULL,
                content_type TEXT,
                title TEXT,
                description TEXT,
                tags TEXT,  -- JSON array
                cover_image TEXT,
                platforms TEXT,  -- JSON array
                scheduled_time TIMESTAMP,
                status TEXT DEFAULT 'pending',
                publish_results TEXT,  -- JSON
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                published_at TIMESTAMP,
                retry_count INTEGER DEFAULT 0,
                max_retries INTEGER DEFAULT 3
            )
        """)
        
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS platform_accounts (
                id TEXT PRIMARY KEY,
                platform TEXT NOT NULL,
                account_id TEXT NOT NULL,
                account_name TEXT,
                access_token TEXT,
                refresh_token TEXT,
                token_expires_at TIMESTAMP,
                settings TEXT,  -- JSON
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
    def create_task(
        self,
        content_path: str,
        content_type: ContentType,
        title: str,
        description: str = "",
        tags: List[str] = None,
        platforms: List[str] = None,
        scheduled_time: datetime = None
    ) -> PublishTask:
        """创建发布任务"""
        task = PublishTask(
            id=f"pub_{int(datetime.now().timestamp())}",
            content_path=content_path,
            content_type=content_type,
            title=title,
            description=description,
            tags=tags or [],
            platforms=[PlatformConfig(platform=p, account_id="") for p in (platforms or ["douyin"])],
            scheduled_time=scheduled_time,
        )
        
        self._save_task(task)
        logger.info(f"Created publish task: {task.id}")
        return task
        
    def _save_task(self, task: PublishTask):
        """保存任务到数据库"""
        self.db.execute("""
            INSERT OR REPLACE INTO publish_tasks (
                id, content_path, content_type, title, description, tags,
                cover_image, platforms, scheduled_time, status, publish_results,
                created_at, published_at, retry_count, max_retries
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task.id, task.content_path, task.content_type.value,
            task.title, task.description,
            json.dumps(task.tags, ensure_ascii=False),
            task.cover_image,
            json.dumps([self._platform_config_to_dict(p) for p in task.platforms], ensure_ascii=False),
            task.scheduled_time.isoformat() if task.scheduled_time else None,
            task.status.value,
            json.dumps(task.publish_results, ensure_ascii=False),
            task.created_at.isoformat(),
            task.published_at.isoformat() if task.published_at else None,
            task.retry_count, task.max_retries
        ))
        
    def _platform_config_to_dict(self, config: PlatformConfig) -> dict:
        """转换平台配置为字典"""
        return {
            "platform": config.platform,
            "account_id": config.account_id,
            "enabled": config.enabled,
            "auto_publish": config.auto_publish,
            "best_time_start": config.best_time_start,
            "best_time_end": config.best_time_end,
        }
        
    def get_task(self, task_id: str) -> Optional[PublishTask]:
        """获取任务"""
        row = self.db.execute_one("SELECT * FROM publish_tasks WHERE id = ?", (task_id,))
        if not row:
            return None
        return self._row_to_task(row)
        
    def _row_to_task(self, row: dict) -> PublishTask:
        """将数据库行转换为任务对象"""
        platforms_data = json.loads(row['platforms']) if row['platforms'] else []
        platforms = [PlatformConfig(**p) for p in platforms_data]
        
        return PublishTask(
            id=row['id'],
            content_path=row['content_path'],
            content_type=ContentType(row['content_type']),
            title=row['title'] or "",
            description=row['description'] or "",
            tags=json.loads(row['tags']) if row['tags'] else [],
            cover_image=row['cover_image'],
            platforms=platforms,
            scheduled_time=datetime.fromisoformat(row['scheduled_time']) if row['scheduled_time'] else None,
            status=PublishStatus(row['status']),
            publish_results=json.loads(row['publish_results']) if row['publish_results'] else {},
            created_at=datetime.fromisoformat(row['created_at']),
            published_at=datetime.fromisoformat(row['published_time']) if row.get('published_at') else None,
            retry_count=row['retry_count'],
            max_retries=row['max_retries'],
        )
        
    def adapt_content_for_platform(
        self,
        title: str,
        description: str,
        tags: List[str],
        platform: str
    ) -> Dict[str, any]:
        """
        根据平台特性适配内容
        
        Returns:
            适配后的内容字典
        """
        features = self.PLATFORM_FEATURES.get(platform)
        if not features:
            return {"title": title, "description": description, "tags": tags}
            
        # 截断标题
        adapted_title = title[:features['title_max']] if features['title_max'] > 0 else ""
        
        # 截断描述
        adapted_desc = description[:features['desc_max']]
        
        # 限制标签数量
        adapted_tags = tags[:features['tag_max']]
        
        # 平台特定优化
        if platform == "xiaohongshu":
            # 小红书需要添加话题标签
            adapted_desc = self._add_hashtags_to_desc(adapted_desc, adapted_tags)
        elif platform == "instagram":
            # Instagram标签放在描述中
            adapted_desc = self._add_hashtags_to_desc(adapted_desc, adapted_tags)
            adapted_tags = []  # Instagram不需要单独的标签字段
            
        return {
            "title": adapted_title,
            "description": adapted_desc,
            "tags": adapted_tags,
        }
        
    def _add_hashtags_to_desc(self, desc: str, tags: List[str]) -> str:
        """将标签添加到描述中"""
        if not tags:
            return desc
        hashtags = " ".join([f"#{tag}" for tag in tags])
        return f"{desc}\n\n{hashtags}"
        
    def publish(self, task_id: str, immediate: bool = False) -> bool:
        """
        执行发布
        
        Args:
            task_id: 任务ID
            immediate: 是否立即发布（忽略排期）
        """
        task = self.get_task(task_id)
        if not task:
            logger.error(f"Task not found: {task_id}")
            return False
            
        if task.status == PublishStatus.PUBLISHED:
            logger.warning(f"Task already published: {task_id}")
            return False
            
        # 检查排期
        if not immediate and task.scheduled_time and task.scheduled_time > datetime.now():
            logger.info(f"Task scheduled for {task.scheduled_time}")
            task.status = PublishStatus.SCHEDULED
            self._save_task(task)
            return True
            
        task.status = PublishStatus.PUBLISHING
        self._save_task(task)
        
        logger.info(f"Publishing task: {task_id}")
        
        # 逐个平台发布
        for platform_config in task.platforms:
            if not platform_config.enabled:
                continue
                
            platform = platform_config.platform
            
            try:
                # 适配内容
                adapted = self.adapt_content_for_platform(
                    task.title, task.description, task.tags, platform
                )
                
                # 执行发布（模拟）
                result = self._publish_to_platform(
                    platform=platform,
                    account_id=platform_config.account_id,
                    content_path=task.content_path,
                    content_type=task.content_type,
                    title=adapted['title'],
                    description=adapted['description'],
                    tags=adapted['tags'],
                    cover_image=task.cover_image,
                )
                
                task.publish_results[platform] = {
                    "success": result['success'],
                    "platform_post_id": result.get('post_id'),
                    "url": result.get('url'),
                    "message": result.get('message'),
                    "published_at": datetime.now().isoformat(),
                }
                
            except Exception as e:
                logger.error(f"Failed to publish to {platform}: {e}")
                task.publish_results[platform] = {
                    "success": False,
                    "error": str(e),
                }
                
        # 更新任务状态
        all_success = all(r.get('success') for r in task.publish_results.values())
        task.status = PublishStatus.PUBLISHED if all_success else PublishStatus.FAILED
        task.published_at = datetime.now()
        self._save_task(task)
        
        logger.info(f"Publish task completed: {task_id}, status: {task.status.value}")
        return all_success
        
    def _publish_to_platform(
        self,
        platform: str,
        account_id: str,
        content_path: str,
        content_type: ContentType,
        title: str,
        description: str,
        tags: List[str],
        cover_image: str = None
    ) -> dict:
        """
        发布到指定平台
        
        TODO: 实际实现需要调用各平台API
        """
        logger.info(f"Publishing to {platform}: {title}")
        
        # 模拟发布成功
        # 实际实现需要：
        # 1. 获取平台access_token
        # 2. 上传媒体文件
        # 3. 创建发布请求
        # 4. 处理响应
        
        return {
            "success": True,
            "post_id": f"{platform}_{int(datetime.now().timestamp())}",
            "url": f"https://{platform}.com/p/{int(datetime.now().timestamp())}",
            "message": "Published successfully",
        }
        
    def schedule_task(self, task_id: str, scheduled_time: datetime) -> bool:
        """重新排期任务"""
        task = self.get_task(task_id)
        if not task:
            return False
            
        task.scheduled_time = scheduled_time
        task.status = PublishStatus.SCHEDULED
        self._save_task(task)
        
        logger.info(f"Task {task_id} scheduled for {scheduled_time}")
        return True
        
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = self.get_task(task_id)
        if not task or task.status == PublishStatus.PUBLISHED:
            return False
            
        task.status = PublishStatus.CANCELLED
        self._save_task(task)
        
        logger.info(f"Task cancelled: {task_id}")
        return True
        
    def retry_task(self, task_id: str) -> bool:
        """重试失败的任务"""
        task = self.get_task(task_id)
        if not task or task.status != PublishStatus.FAILED:
            return False
            
        if task.retry_count >= task.max_retries:
            logger.warning(f"Max retries reached for task: {task_id}")
            return False
            
        task.retry_count += 1
        task.status = PublishStatus.PENDING
        self._save_task(task)
        
        return self.publish(task_id)
        
    def list_tasks(
        self,
        status: PublishStatus = None,
        platform: str = None,
        limit: int = 50
    ) -> List[PublishTask]:
        """列出任务"""
        query = "SELECT * FROM publish_tasks WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = ?"
            params.append(status.value)
            
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        rows = self.db.execute(query, tuple(params))
        tasks = [self._row_to_task(row) for row in rows]
        
        # 平台筛选（在内存中处理）
        if platform:
            tasks = [
                t for t in tasks
                if any(p.platform == platform for p in t.platforms)
            ]
            
        return tasks
        
    def get_pending_tasks(self) -> List[PublishTask]:
        """获取待发布的任务（用于调度器）"""
        return self.list_tasks(status=PublishStatus.PENDING)
        
    def get_scheduled_tasks(self) -> List[PublishTask]:
        """获取已排期的任务"""
        return self.list_tasks(status=PublishStatus.SCHEDULED)
        
    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        try:
            self.db.execute("DELETE FROM publish_tasks WHERE id = ?", (task_id,))
            return True
        except Exception as e:
            logger.error(f"Failed to delete task: {e}")
            return False
