#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Trend Monitor
多平台热点监测系统
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import queue

from ..core.logging import get_logger
from ..core.database import DatabaseManager

logger = get_logger(__name__)


class Platform(Enum):
    """支持的平台"""
    DOUYIN = "douyin"      # 抖音
    XIAOHONGSHU = "xhs"    # 小红书
    KUAISHOU = "kuaishou"  # 快手
    BILIBILI = "bilibili"  # B站
    TIKTOK = "tiktok"      # TikTok
    INSTAGRAM = "instagram" # Instagram
    YOUTUBE = "youtube"    # YouTube


@dataclass
class TrendItem:
    """热点内容项"""
    id: str
    platform: Platform
    title: str
    author: str
    url: str
    views: int
    likes: int
    comments: int
    shares: int
    publish_time: datetime
    tags: List[str]
    content_type: str  # video, image, text
    thumbnail_url: Optional[str] = None
    audio_url: Optional[str] = None
    
    # 评估指标
    viral_score: float = 0.0  # 爆款潜力指数 0-100
    efficiency_score: float = 0.0  # 效率指标
    relevance_score: float = 0.0  # 适配度指标
    
    # 解析数据
    key_frames: List[str] = None  # 关键帧
    transcript: str = ""  # 语音转文字
    visual_tags: List[str] = None  # 视觉标签
    
    def __post_init__(self):
        if self.key_frames is None:
            self.key_frames = []
        if self.visual_tags is None:
            self.visual_tags = []


@dataclass
class TrendReport:
    """热点监测报告"""
    timestamp: datetime
    platform: Platform
    total_items: int
    top_items: List[TrendItem]
    trending_tags: List[Dict]
    category_distribution: Dict[str, int]


class TrendMonitor:
    """
    多平台热点监测系统
    
    功能：
    1. 多平台API对接与数据采集
    2. 内容解析与标签化
    3. 爆款潜力评估
    4. 实时热点推送
    """
    
    def __init__(self, db: 'DatabaseManager' = None):
        self.db = db or DatabaseManager()
        self._running = False
        self._monitor_thread = None
        self._callback_queue = queue.Queue()
        self._callbacks: List[Callable] = []
        
        # 平台配置
        self.platform_configs = {
            Platform.DOUYIN: {
                "api_endpoint": "https://open.douyin.com",
                "fetch_interval": 900,  # 15分钟
                "enabled": True,
            },
            Platform.XIAOHONGSHU: {
                "api_endpoint": "https://open.xiaohongshu.com",
                "fetch_interval": 3600,  # 1小时
                "enabled": True,
            },
            Platform.KUAISHOU: {
                "api_endpoint": "https://open.kuaishou.com",
                "fetch_interval": 900,
                "enabled": True,
            },
            Platform.BILIBILI: {
                "api_endpoint": "https://open.bilibili.com",
                "fetch_interval": 3600,
                "enabled": True,
            },
            Platform.TIKTOK: {
                "api_endpoint": "https://open.tiktokapis.com",
                "fetch_interval": 1800,
                "enabled": False,  # 需要国际网络
            },
            Platform.INSTAGRAM: {
                "api_endpoint": "https://graph.instagram.com",
                "fetch_interval": 3600,
                "enabled": False,
            },
            Platform.YOUTUBE: {
                "api_endpoint": "https://www.googleapis.com/youtube/v3",
                "fetch_interval": 3600,
                "enabled": False,
            },
        }
        
        # 初始化数据表
        self._init_database()
        
    def _init_database(self):
        """初始化数据库表"""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS trend_items (
                id TEXT PRIMARY KEY,
                platform TEXT NOT NULL,
                title TEXT,
                author TEXT,
                url TEXT,
                views INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                shares INTEGER DEFAULT 0,
                publish_time TIMESTAMP,
                tags TEXT,  -- JSON array
                content_type TEXT,
                thumbnail_url TEXT,
                viral_score REAL DEFAULT 0,
                efficiency_score REAL DEFAULT 0,
                relevance_score REAL DEFAULT 0,
                transcript TEXT,
                visual_tags TEXT,  -- JSON array
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_trend_platform ON trend_items(platform)
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_trend_viral ON trend_items(viral_score DESC)
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_trend_time ON trend_items(publish_time DESC)
        """)
        
    def start_monitoring(self):
        """启动监测"""
        if self._running:
            return
            
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Trend monitoring started")
        
    def stop_monitoring(self):
        """停止监测"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        logger.info("Trend monitoring stopped")
        
    def _monitor_loop(self):
        """监测主循环"""
        last_fetch = {p: 0 for p in Platform}
        
        while self._running:
            current_time = time.time()
            
            for platform, config in self.platform_configs.items():
                if not config["enabled"]:
                    continue
                    
                if current_time - last_fetch[platform] >= config["fetch_interval"]:
                    try:
                        self._fetch_platform_data(platform)
                        last_fetch[platform] = current_time
                    except Exception as e:
                        logger.error(f"Failed to fetch {platform.value}: {e}")
                        
            # 处理回调
            self._process_callbacks()
            
            time.sleep(10)  # 10秒检查一次
            
    def _fetch_platform_data(self, platform: Platform):
        """获取平台数据"""
        logger.info(f"Fetching data from {platform.value}")
        
        # 模拟数据获取（实际实现需要对接各平台API）
        items = self._simulate_fetch(platform)
        
        # 处理和分析内容
        for item in items:
            self._analyze_content(item)
            self._save_trend_item(item)
            
        # 触发回调
        self._notify_callbacks(platform, items)
        
    def _simulate_fetch(self, platform: Platform) -> List[TrendItem]:
        """模拟数据获取（开发测试用）"""
        items = []
        
        # 模拟生成一些热点数据
        for i in range(5):
            item = TrendItem(
                id=f"{platform.value}_{int(time.time())}_{i}",
                platform=platform,
                title=f"热门内容示例 {i+1}",
                author=f"创作者{i+1}",
                url=f"https://example.com/{platform.value}/{i}",
                views=100000 + i * 50000,
                likes=5000 + i * 2000,
                comments=500 + i * 100,
                shares=200 + i * 50,
                publish_time=datetime.now() - timedelta(hours=i),
                tags=["热门", "推荐", " trending"],
                content_type="video",
            )
            items.append(item)
            
        return items
        
    def _analyze_content(self, item: TrendItem):
        """分析内容并计算评分"""
        # 计算爆款潜力指数
        engagement_rate = (item.likes + item.comments + item.shares) / max(item.views, 1)
        
        # 时间衰减因子
        hours_since_publish = (datetime.now() - item.publish_time).total_seconds() / 3600
        time_decay = max(0.1, 1 - hours_since_publish / 24)  # 24小时内衰减
        
        # 综合评分
        item.viral_score = min(100, engagement_rate * 1000 * time_decay * 100)
        item.efficiency_score = engagement_rate * 100
        
        # 模拟适配度评分（实际应基于产品匹配模型）
        item.relevance_score = 70 + (hash(item.id) % 30)
        
    def _save_trend_item(self, item: TrendItem):
        """保存热点项到数据库"""
        try:
            self.db.execute("""
                INSERT OR REPLACE INTO trend_items (
                    id, platform, title, author, url, views, likes, comments, shares,
                    publish_time, tags, content_type, thumbnail_url, viral_score,
                    efficiency_score, relevance_score, transcript, visual_tags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item.id, item.platform.value, item.title, item.author, item.url,
                item.views, item.likes, item.comments, item.shares,
                item.publish_time.isoformat(),
                json.dumps(item.tags, ensure_ascii=False),
                item.content_type, item.thumbnail_url,
                item.viral_score, item.efficiency_score, item.relevance_score,
                item.transcript,
                json.dumps(item.visual_tags, ensure_ascii=False)
            ))
        except Exception as e:
            logger.error(f"Failed to save trend item: {e}")
            
    def get_trending_items(
        self,
        platform: Optional[Platform] = None,
        min_viral_score: float = 50.0,
        limit: int = 50,
        hours: int = 24
    ) -> List[TrendItem]:
        """获取热点内容列表"""
        since = datetime.now() - timedelta(hours=hours)
        
        query = """
            SELECT * FROM trend_items 
            WHERE viral_score >= ? AND publish_time > ?
        """
        params = [min_viral_score, since.isoformat()]
        
        if platform:
            query += " AND platform = ?"
            params.append(platform.value)
            
        query += " ORDER BY viral_score DESC LIMIT ?"
        params.append(limit)
        
        rows = self.db.fetchall(query, params)
        
        items = []
        for row in rows:
            item = TrendItem(
                id=row['id'],
                platform=Platform(row['platform']),
                title=row['title'],
                author=row['author'],
                url=row['url'],
                views=row['views'],
                likes=row['likes'],
                comments=row['comments'],
                shares=row['shares'],
                publish_time=datetime.fromisoformat(row['publish_time']),
                tags=json.loads(row['tags']) if row['tags'] else [],
                content_type=row['content_type'],
                thumbnail_url=row['thumbnail_url'],
                viral_score=row['viral_score'],
                efficiency_score=row['efficiency_score'],
                relevance_score=row['relevance_score'],
                transcript=row['transcript'] or "",
                visual_tags=json.loads(row['visual_tags']) if row['visual_tags'] else [],
            )
            items.append(item)
            
        return items
        
    def get_trend_report(self, platform: Platform, hours: int = 24) -> TrendReport:
        """生成热点监测报告"""
        items = self.get_trending_items(platform=platform, hours=hours, limit=100)
        
        # 统计标签分布
        tag_counts = {}
        for item in items:
            for tag in item.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
                
        trending_tags = [
            {"tag": tag, "count": count}
            for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ]
        
        # 内容类型分布
        type_dist = {}
        for item in items:
            type_dist[item.content_type] = type_dist.get(item.content_type, 0) + 1
            
        return TrendReport(
            timestamp=datetime.now(),
            platform=platform,
            total_items=len(items),
            top_items=items[:10],
            trending_tags=trending_tags,
            category_distribution=type_dist
        )
        
    def register_callback(self, callback: Callable):
        """注册数据更新回调"""
        self._callbacks.append(callback)
        
    def _notify_callbacks(self, platform: Platform, items: List[TrendItem]):
        """通知所有回调"""
        for callback in self._callbacks:
            try:
                callback(platform, items)
            except Exception as e:
                logger.error(f"Callback error: {e}")
                
    def _process_callbacks(self):
        """处理回调队列"""
        while not self._callback_queue.empty():
            try:
                callback, args = self._callback_queue.get_nowait()
                callback(*args)
            except queue.Empty:
                break
            except Exception as e:
                logger.error(f"Process callback error: {e}")
