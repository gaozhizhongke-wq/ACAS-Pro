#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Festival Calendar
节日营销日历系统
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from ..core.logging import get_logger
from ..core.database import DatabaseManager

logger = get_logger(__name__)


class FestivalType(Enum):
    """节日类型"""
    TRADITIONAL = "traditional"      # 传统节日
    WESTERN = "western"              # 西方节日
    SHOPPING = "shopping"            # 购物节
    CULTURAL = "cultural"            # 文化节日
    RELIGIOUS = "religious"          # 宗教节日
    CUSTOM = "custom"                # 自定义


class MarketType(Enum):
    """市场类型"""
    DOMESTIC = "domestic"            # 国内市场
    OVERSEAS = "overseas"            # 海外市场
    NORTHWEST = "northwest"          # 中国西北
    MIDDLE_EAST = "middle_east"      # 中东
    SOUTHEAST_ASIA = "southeast_asia" # 东南亚
    GLOBAL = "global"                # 全球


@dataclass
class Festival:
    """节日"""
    id: str
    name: str
    name_en: str
    festival_type: FestivalType
    markets: List[MarketType]
    
    # 日期（支持农历和浮动日期）
    month: int
    day: int
    lunar: bool = False  # 是否农历
    floating: bool = False  # 是否浮动日期
    floating_rule: str = None  # 浮动规则描述
    
    # 营销属性
    importance: int = 3  # 重要性 1-5
    duration_days: int = 1  # 持续天数
    pre_heat_days: int = 7  # 预热天数
    
    # 内容建议
    themes: List[str] = None  # 主题建议
    keywords: List[str] = None  # 关键词
    visual_style: str = None  # 视觉风格
    content_tips: str = None  # 内容建议
    
    # 状态
    is_active: bool = True
    created_at: datetime = None
    
    def __post_init__(self):
        if self.themes is None:
            self.themes = []
        if self.keywords is None:
            self.keywords = []
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class MarketingPlan:
    """营销计划"""
    id: str
    festival_id: str
    name: str
    
    # 时间
    start_date: datetime
    end_date: datetime
    
    # 目标
    target_platforms: List[str]
    target_accounts: List[str]
    
    # 内容计划
    content_count: int
    content_types: List[str]
    
    # 预算
    budget: float
    
    # 状态
    status: str = "draft"  # draft, active, completed, cancelled
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class FestivalCalendar:
    """
    节日营销日历系统
    
    功能：
    1. 多历法节日管理（公历/农历/伊斯兰历）
    2. 节日数据库
    3. 营销计划制定
    4. 自动提醒
    5. 内容建议生成
    """
    
    # 内置节日库
    DEFAULT_FESTIVALS = [
        # 中国传统节日
        Festival(
            id="spring_festival",
            name="春节",
            name_en="Spring Festival",
            festival_type=FestivalType.TRADITIONAL,
            markets=[MarketType.DOMESTIC, MarketType.GLOBAL],
            month=1, day=1, lunar=True,
            importance=5, duration_days=7, pre_heat_days=15,
            themes=["团圆", "年货", "送礼", "健康", "新年新气象"],
            keywords=["过年", "春节", "红包", "年夜饭", "拜年"],
            visual_style="红色、金色、喜庆、传统元素",
            content_tips="强调家庭团聚、健康礼品、传统文化"
        ),
        Festival(
            id="lantern_festival",
            name="元宵节",
            name_en="Lantern Festival",
            festival_type=FestivalType.TRADITIONAL,
            markets=[MarketType.DOMESTIC],
            month=1, day=15, lunar=True,
            importance=3, duration_days=1, pre_heat_days=3,
            themes=["团圆", "灯会", "甜蜜"],
            keywords=["元宵", "汤圆", "灯会", "猜灯谜"],
            visual_style="灯笼、暖色调",
        ),
        Festival(
            id="dragon_boat",
            name="端午节",
            name_en="Dragon Boat Festival",
            festival_type=FestivalType.TRADITIONAL,
            markets=[MarketType.DOMESTIC],
            month=5, day=5, lunar=True,
            importance=3, duration_days=3, pre_heat_days=7,
            themes=["传统文化", "健康", "纪念"],
            keywords=["粽子", "龙舟", "艾草", "屈原"],
            visual_style="绿色、龙舟、传统",
        ),
        Festival(
            id="mid_autumn",
            name="中秋节",
            name_en="Mid-Autumn Festival",
            festival_type=FestivalType.TRADITIONAL,
            markets=[MarketType.DOMESTIC, MarketType.SOUTHEAST_ASIA],
            month=8, day=15, lunar=True,
            importance=4, duration_days=3, pre_heat_days=10,
            themes=["团圆", "赏月", "送礼", "思念"],
            keywords=["月饼", "月亮", "团圆", "中秋"],
            visual_style="月亮、暖色调、温馨",
        ),
        
        # 西方节日
        Festival(
            id="valentine",
            name="情人节",
            name_en="Valentine's Day",
            festival_type=FestivalType.WESTERN,
            markets=[MarketType.DOMESTIC, MarketType.GLOBAL],
            month=2, day=14,
            importance=4, duration_days=1, pre_heat_days=7,
            themes=["爱情", "浪漫", "礼物", "表白"],
            keywords=["情人节", "玫瑰", "巧克力", "约会"],
            visual_style="粉色、红色、爱心、浪漫",
        ),
        Festival(
            id="christmas",
            name="圣诞节",
            name_en="Christmas",
            festival_type=FestivalType.WESTERN,
            markets=[MarketType.GLOBAL],
            month=12, day=25,
            importance=4, duration_days=3, pre_heat_days=14,
            themes=["礼物", "家庭", "温暖", "年末"],
            keywords=["圣诞", "礼物", "圣诞老人", "年末促销"],
            visual_style="红绿配色、雪花、圣诞树",
        ),
        
        # 购物节
        Festival(
            id="singles_day",
            name="双11",
            name_en="Singles' Day",
            festival_type=FestivalType.SHOPPING,
            markets=[MarketType.DOMESTIC],
            month=11, day=11,
            importance=5, duration_days=3, pre_heat_days=21,
            themes=["促销", "囤货", "优惠", "狂欢"],
            keywords=["双11", "优惠", "折扣", "秒杀"],
            visual_style="红色、橙色、促销氛围",
            content_tips="强调优惠力度、限时抢购、囤货建议"
        ),
        Festival(
            id="618",
            name="618年中大促",
            name_en="618 Shopping Festival",
            festival_type=FestivalType.SHOPPING,
            markets=[MarketType.DOMESTIC],
            month=6, day=18,
            importance=4, duration_days=7, pre_heat_days=14,
            themes=["年中大促", "夏季", "优惠"],
            keywords=["618", "年中大促", "夏季优惠"],
            visual_style="蓝色、清凉、夏日",
        ),
        
        # 伊斯兰节日
        Festival(
            id="ramadan",
            name="斋月",
            name_en="Ramadan",
            festival_type=FestivalType.RELIGIOUS,
            markets=[MarketType.MIDDLE_EAST],
            month=9, day=1, floating=True,
            floating_rule="伊斯兰历9月",
            importance=5, duration_days=30, pre_heat_days=7,
            themes=["封斋", "祈祷", "家庭", "慈善"],
            keywords=["Ramadan", "封斋", "开斋", "健康"],
            visual_style="金色、深绿色、新月、灯笼",
            content_tips="尊重宗教习俗，强调健康、家庭、分享"
        ),
        Festival(
            id="eid_al_fitr",
            name="开斋节",
            name_en="Eid al-Fitr",
            festival_type=FestivalType.RELIGIOUS,
            markets=[MarketType.MIDDLE_EAST],
            month=10, day=1, floating=True,
            floating_rule="伊斯兰历10月1日",
            importance=5, duration_days=3, pre_heat_days=7,
            themes=["庆祝", "感恩", "分享", "礼物"],
            keywords=["Eid", "开斋", "庆祝", "礼物"],
            visual_style="金色、绿色、喜庆",
            content_tips="庆祝氛围，家庭聚会，礼品推荐"
        ),
        
        # 西北特色
        Festival(
            id="naadam",
            name="那达慕大会",
            name_en="Naadam Festival",
            festival_type=FestivalType.CULTURAL,
            markets=[MarketType.NORTHWEST],
            month=7, day=15,
            importance=3, duration_days=5, pre_heat_days=7,
            themes=["草原", "游牧", "竞技", "文化"],
            keywords=["那达慕", "草原", "蒙古", "赛马"],
            visual_style="草原、蓝天、蒙古元素",
        ),
    ]
    
    def __init__(self, db: 'DatabaseManager' = None):
        self.db = db or DatabaseManager()
        self._init_database()
        self._load_default_festivals()
        
    def _init_database(self):
        """初始化数据库表"""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS festivals (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                name_en TEXT,
                festival_type TEXT,
                markets TEXT,  -- JSON array
                month INTEGER,
                day INTEGER,
                lunar BOOLEAN DEFAULT 0,
                floating BOOLEAN DEFAULT 0,
                floating_rule TEXT,
                importance INTEGER DEFAULT 3,
                duration_days INTEGER DEFAULT 1,
                pre_heat_days INTEGER DEFAULT 7,
                themes TEXT,  -- JSON array
                keywords TEXT,  -- JSON array
                visual_style TEXT,
                content_tips TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS marketing_plans (
                id TEXT PRIMARY KEY,
                festival_id TEXT,
                name TEXT,
                start_date TIMESTAMP,
                end_date TIMESTAMP,
                target_platforms TEXT,  -- JSON array
                target_accounts TEXT,  -- JSON array
                content_count INTEGER,
                content_types TEXT,  -- JSON array
                budget REAL,
                status TEXT DEFAULT 'draft',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (festival_id) REFERENCES festivals(id)
            )
        """)
        
    def _load_default_festivals(self):
        """加载默认节日"""
        for festival in self.DEFAULT_FESTIVALS:
            self._save_festival(festival)
            
    def _save_festival(self, festival: Festival):
        """保存节日到数据库"""
        try:
            self.db.execute("""
                INSERT OR REPLACE INTO festivals (
                    id, name, name_en, festival_type, markets, month, day,
                    lunar, floating, floating_rule, importance, duration_days,
                    pre_heat_days, themes, keywords, visual_style, content_tips, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                festival.id, festival.name, festival.name_en,
                festival.festival_type.value,
                json.dumps([m.value for m in festival.markets], ensure_ascii=False),
                festival.month, festival.day,
                festival.lunar, festival.floating, festival.floating_rule,
                festival.importance, festival.duration_days, festival.pre_heat_days,
                json.dumps(festival.themes, ensure_ascii=False),
                json.dumps(festival.keywords, ensure_ascii=False),
                festival.visual_style, festival.content_tips, festival.is_active
            ))
        except Exception as e:
            logger.error(f"Failed to save festival {festival.id}: {e}")
            
    def get_festival(self, festival_id: str) -> Optional[Festival]:
        """获取节日信息"""
        row = self.db.fetchone("SELECT * FROM festivals WHERE id = ?", (festival_id,))
        if not row:
            return None
        return self._row_to_festival(row)
        
    def _row_to_festival(self, row: dict) -> Festival:
        """将数据库行转换为节日对象"""
        def _json_loads(val):
            if isinstance(val, str):
                return json.loads(val)
            return val if val is not None else []
        def _parse_dt(val):
            if isinstance(val, datetime):
                return val
            if isinstance(val, str):
                return datetime.fromisoformat(val)
            return datetime.now()
        return Festival(
            id=row['id'],
            name=row['name'],
            name_en=row['name_en'],
            festival_type=FestivalType(row['festival_type']),
            markets=[MarketType(m) for m in _json_loads(row['markets'])],
            month=row['month'],
            day=row['day'],
            lunar=bool(row['lunar']),
            floating=bool(row['floating']),
            floating_rule=row['floating_rule'],
            importance=row['importance'],
            duration_days=row['duration_days'],
            pre_heat_days=row['pre_heat_days'],
            themes=_json_loads(row['themes']),
            keywords=_json_loads(row['keywords']),
            visual_style=row['visual_style'],
            content_tips=row['content_tips'],
            is_active=bool(row['is_active']),
            created_at=_parse_dt(row['created_at'])
        )
        
    def list_festivals(
        self,
        festival_type: FestivalType = None,
        market: MarketType = None,
        active_only: bool = True
    ) -> List[Festival]:
        """列出节日"""
        query = "SELECT * FROM festivals WHERE 1=1"
        params = []
        
        if festival_type:
            query += " AND festival_type = ?"
            params.append(festival_type.value)
        if active_only:
            query += " AND is_active = 1"
            
        query += " ORDER BY month, day"
        
        rows = self.db.fetchall(query, params)
        festivals = [self._row_to_festival(row) for row in rows]
        
        # 市场筛选（在内存中处理）
        if market:
            festivals = [f for f in festivals if market in f.markets]
            
        return festivals
        
    def get_upcoming_festivals(
        self,
        days: int = 30,
        market: MarketType = None
    ) -> List[Festival]:
        """获取即将到来的节日"""
        today = datetime.now()
        end = today + timedelta(days=days)
        
        festivals = self.list_festivals(market=market)
        upcoming = []
        
        for festival in festivals:
            # 简化的日期计算（不考虑农历转换）
            festival_date = datetime(today.year, festival.month, festival.day)
            if festival_date < today:
                festival_date = datetime(today.year + 1, festival.month, festival.day)
                
            if today <= festival_date <= end:
                upcoming.append((festival_date, festival))
                
        upcoming.sort(key=lambda x: x[0])
        return [f for _, f in upcoming]
        
    def create_marketing_plan(
        self,
        festival_id: str,
        name: str,
        start_date: datetime,
        end_date: datetime,
        target_platforms: List[str],
        target_accounts: List[str],
        content_count: int = 10,
        content_types: List[str] = None,
        budget: float = 0.0
    ) -> MarketingPlan:
        """创建营销计划"""
        if content_types is None:
            content_types = ["video", "image", "text"]
            
        plan = MarketingPlan(
            id=f"plan_{int(datetime.now().timestamp())}",
            festival_id=festival_id,
            name=name,
            start_date=start_date,
            end_date=end_date,
            target_platforms=target_platforms,
            target_accounts=target_accounts,
            content_count=content_count,
            content_types=content_types,
            budget=budget,
        )
        
        self.db.execute("""
            INSERT INTO marketing_plans (
                id, festival_id, name, start_date, end_date,
                target_platforms, target_accounts, content_count,
                content_types, budget, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            plan.id, plan.festival_id, plan.name,
            start_date.isoformat(), end_date.isoformat(),
            json.dumps(target_platforms, ensure_ascii=False),
            json.dumps(target_accounts, ensure_ascii=False),
            content_count,
            json.dumps(content_types, ensure_ascii=False),
            budget, plan.status
        ))
        
        return plan
        
    def get_marketing_plans(
        self,
        status: str = None,
        festival_id: str = None
    ) -> List[MarketingPlan]:
        """获取营销计划列表"""
        query = "SELECT * FROM marketing_plans WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = ?"
            params.append(status)
        if festival_id:
            query += " AND festival_id = ?"
            params.append(festival_id)
            
        query += " ORDER BY start_date DESC"
        
        rows = self.db.fetchall(query, params)
        
        def _parse_dt(val):
            if isinstance(val, datetime):
                return val
            if isinstance(val, str):
                return datetime.fromisoformat(val)
            return datetime.now()
        
        plans = []
        for row in rows:
            plan = MarketingPlan(
                id=row['id'],
                festival_id=row['festival_id'],
                name=row['name'],
                start_date=_parse_dt(row['start_date']),
                end_date=_parse_dt(row['end_date']),
                target_platforms=json.loads(row['target_platforms']) if isinstance(row['target_platforms'], str) else row['target_platforms'],
                target_accounts=json.loads(row['target_accounts']) if isinstance(row['target_accounts'], str) else row['target_accounts'],
                content_count=row['content_count'],
                content_types=json.loads(row['content_types']) if isinstance(row['content_types'], str) else row['content_types'],
                budget=row['budget'],
                status=row['status'],
                created_at=_parse_dt(row['created_at'])
            )
            plans.append(plan)
            
        return plans
        
    def generate_content_suggestions(self, festival_id: str) -> dict:
        """生成内容建议"""
        festival = self.get_festival(festival_id)
        if not festival:
            return {}
            
        return {
            "festival_name": festival.name,
            "themes": festival.themes,
            "keywords": festival.keywords,
            "visual_style": festival.visual_style,
            "content_tips": festival.content_tips,
            "suggested_hashtags": [f"#{k}" for k in festival.keywords[:5]],
            "content_angles": [
                f"{festival.name}特辑",
                f"{festival.name}送礼指南",
                f"{festival.name}限定",
            ]
        }
