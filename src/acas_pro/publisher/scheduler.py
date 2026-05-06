#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Publish Scheduler
发布任务调度器
"""

import threading
import time
from datetime import datetime, timedelta
from typing import List, Optional

from ..core.logging import get_logger
from ..publisher.publish_manager import PublishManager, PublishStatus

logger = get_logger(__name__)


class PublishScheduler:
    """
    发布任务调度器
    
    功能：
    1. 定时任务检查
    2. 最佳发布时间优化
    3. 批量任务队列管理
    4. 并发控制
    """
    
    # 各平台最佳发布时间（小时）
    BEST_PUBLISH_TIMES = {
        "douyin": [7, 12, 18, 21, 22],      # 早中晚高峰
        "xiaohongshu": [8, 12, 20, 22],      # 早中晚
        "kuaishou": [6, 12, 18, 21],         # 早中晚
        "bilibili": [12, 18, 20, 22],        # 午休+晚上
        "tiktok": [9, 12, 19, 21],           # 国际时区
        "instagram": [11, 13, 17, 19],       # 国际时区
        "youtube": [14, 16, 19],             # 下午到晚上
    }
    
    def __init__(self, publish_manager: PublishManager = None, check_interval: int = 60):
        self.publish_manager = publish_manager or PublishManager()
        self.check_interval = check_interval  # 检查间隔（秒）
        self.running = False
        self.scheduler_thread = None
        self.lock = threading.Lock()
        
    def start(self):
        """启动调度器"""
        if self.running:
            logger.warning("Scheduler already running")
            return
            
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._run, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("Publish scheduler started")
        
    def stop(self):
        """停止调度器"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
            
        logger.info("Publish scheduler stopped")
        
    def _run(self):
        """调度器主循环"""
        while self.running:
            try:
                self._check_and_publish()
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                
            time.sleep(self.check_interval)
            
    def _check_and_publish(self):
        """检查并执行待发布任务"""
        now = datetime.now()
        
        # 获取已排期的任务
        scheduled_tasks = self.publish_manager.get_scheduled_tasks()
        
        for task in scheduled_tasks:
            if not task.scheduled_time:
                continue
                
            # 检查是否到达发布时间
            if task.scheduled_time <= now:
                logger.info(f"Executing scheduled task: {task.id}")
                
                with self.lock:
                    self.publish_manager.publish(task.id, immediate=True)
                    
    def get_optimal_publish_time(
        self,
        platform: str,
        start_date: datetime = None,
        days_ahead: int = 3
    ) -> List[datetime]:
        """
        获取最佳发布时间建议
        
        Args:
            platform: 平台名称
            start_date: 开始日期（默认明天）
            days_ahead: 提前天数
            
        Returns:
            推荐发布时间列表
        """
        if start_date is None:
            start_date = datetime.now() + timedelta(days=1)
            
        best_hours = self.BEST_PUBLISH_TIMES.get(platform, [12, 18, 20])
        suggestions = []
        
        for day_offset in range(days_ahead):
            date = start_date + timedelta(days=day_offset)
            
            for hour in best_hours:
                suggestion = date.replace(hour=hour, minute=0, second=0)
                if suggestion > datetime.now():
                    suggestions.append(suggestion)
                    
        return suggestions[:10]  # 最多返回10个建议
        
    def schedule_batch(
        self,
        content_list: List[dict],
        platforms: List[str],
        start_time: datetime = None,
        interval_minutes: int = 60
    ) -> List[str]:
        """
        批量排期发布
        
        Args:
            content_list: 内容列表 [{"path": "", "title": "", ...}]
            platforms: 目标平台列表
            start_time: 开始时间（默认明天早上8点）
            interval_minutes: 内容间隔（分钟）
            
        Returns:
            创建的任务ID列表
        """
        if start_time is None:
            # 默认明天早上8点
            tomorrow = datetime.now() + timedelta(days=1)
            start_time = tomorrow.replace(hour=8, minute=0, second=0)
            
        task_ids = []
        current_time = start_time
        
        for content in content_list:
            # 创建任务
            task = self.publish_manager.create_task(
                content_path=content['path'],
                content_type=content.get('type', 'video'),
                title=content['title'],
                description=content.get('description', ''),
                tags=content.get('tags', []),
                platforms=platforms,
                scheduled_time=current_time
            )
            
            task_ids.append(task.id)
            
            # 递增时间
            current_time += timedelta(minutes=interval_minutes)
            
        logger.info(f"Scheduled {len(task_ids)} tasks starting from {start_time}")
        return task_ids
        
    def auto_optimize_schedule(
        self,
        task_ids: List[str],
        strategy: str = "balanced"
    ) -> bool:
        """
        自动优化发布时间
        
        Args:
            task_ids: 任务ID列表
            strategy: 优化策略 (balanced/spread/peak)
        """
        now = datetime.now()
        
        for i, task_id in enumerate(task_ids):
            task = self.publish_manager.get_task(task_id)
            if not task or task.status == PublishStatus.PUBLISHED:
                continue
                
            # 获取第一个平台的最佳时间
            if not task.platforms:
                continue
                
            platform = task.platforms[0].platform
            best_times = self.get_optimal_publish_time(platform, now)
            
            if not best_times:
                continue
                
            # 根据策略选择时间
            if strategy == "balanced":
                # 均衡分布
                idx = i % len(best_times)
            elif strategy == "spread":
                # 尽量分散
                idx = min(i, len(best_times) - 1)
            else:  # peak
                # 优先高峰时段
                idx = 0
                
            new_time = best_times[idx]
            self.publish_manager.schedule_task(task_id, new_time)
            
        logger.info(f"Optimized schedule for {len(task_ids)} tasks")
        return True
        
    def get_queue_status(self) -> dict:
        """获取队列状态"""
        pending = len(self.publish_manager.get_pending_tasks())
        scheduled = len(self.publish_manager.get_scheduled_tasks())
        
        return {
            "pending": pending,
            "scheduled": scheduled,
            "total": pending + scheduled,
            "scheduler_running": self.running,
            "last_check": datetime.now().isoformat(),
        }
        
    def clear_completed(self, days: int = 7) -> int:
        """清理已完成的任务"""
        from datetime import datetime, timedelta
        
        cutoff = datetime.now() - timedelta(days=days)
        
        # 获取所有已完成的任务
        completed = self.publish_manager.list_tasks(status=PublishStatus.PUBLISHED)
        
        cleared = 0
        for task in completed:
            if task.published_at and task.published_at < cutoff:
                self.publish_manager.delete_task(task.id)
                cleared += 1
                
        logger.info(f"Cleared {cleared} completed tasks")
        return cleared
