"""
人群定向管理模块
支持多维度人群定向和Lookalike扩展
"""

import json
import sqlite3
from datetime import datetime
import asyncio
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum

try:
    import aiosqlite
    _HAS_AIOSQLITE = True
except ImportError:
    _HAS_AIOSQLITE = False

from ..core.config import config
from ..core.logging import logger


class AudienceType(Enum):
    """人群类型"""
    CUSTOM = "custom"                  # 自定义人群
    LOOKALIKE = "lookalike"            # 相似人群
    INTEREST = "interest"              # 兴趣人群
    BEHAVIOR = "behavior"              # 行为人群
    RETARGETING = "retargeting"        # 再营销人群


class Gender(Enum):
    """性别"""
    ALL = "all"
    MALE = "male"
    FEMALE = "female"


@dataclass
class AgeRange:
    """年龄范围"""
    min_age: int = 18
    max_age: int = 65
    
    def to_dict(self) -> Dict[str, int]:
        return {'min_age': self.min_age, 'max_age': self.max_age}


@dataclass
class GeoTargeting:
    """地域定向"""
    provinces: List[str] = None        # 省份列表
    cities: List[str] = None           # 城市列表
    exclude_regions: List[str] = None  # 排除地区
    radius_targeting: Optional[Dict[str, Any]] = None  # 半径定向
    
    def __post_init__(self) -> None:
        if self.provinces is None:
            self.provinces = []
        if self.cities is None:
            self.cities = []
        if self.exclude_regions is None:
            self.exclude_regions = []


@dataclass
class DeviceTargeting:
    """设备定向"""
    device_types: List[str] = None     # mobile, tablet, desktop
    os_types: List[str] = None         # ios, android, windows
    network_types: List[str] = None    # wifi, 4g, 5g
    brands: List[str] = None           # 手机品牌
    price_ranges: List[str] = None     # 手机价位段
    
    def __post_init__(self) -> None:
        if self.device_types is None:
            self.device_types = ['mobile']
        if self.os_types is None:
            self.os_types = []
        if self.network_types is None:
            self.network_types = []
        if self.brands is None:
            self.brands = []
        if self.price_ranges is None:
            self.price_ranges = []


@dataclass
class AudienceSegment:
    """人群包"""
    id: str
    name: str
    type: AudienceType
    
    # 基础属性
    gender: Gender = Gender.ALL
    age_range: AgeRange = None
    geo_targeting: GeoTargeting = None
    device_targeting: DeviceTargeting = None
    
    # 高级定向
    interests: List[str] = None        # 兴趣标签
    behaviors: List[str] = None        # 行为标签
    custom_tags: List[str] = None      # 自定义标签
    
    # Lookalike设置
    source_audience_id: Optional[str] = None  # 源人群ID
    lookalike_ratio: Optional[float] = None   # 相似度比例
    
    # 预估规模
    estimated_size: int = 0
    estimated_daily_impressions: int = 0
    
    # 状态
    status: str = "active"             # active, paused, expired
    
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def __post_init__(self) -> None:
        if self.age_range is None:
            self.age_range = AgeRange()
        if self.geo_targeting is None:
            self.geo_targeting = GeoTargeting()
        if self.device_targeting is None:
            self.device_targeting = DeviceTargeting()
        if self.interests is None:
            self.interests = []
        if self.behaviors is None:
            self.behaviors = []
        if self.custom_tags is None:
            self.custom_tags = []
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['type'] = self.type.value
        data['gender'] = self.gender.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AudienceSegment':
        data['type'] = AudienceType(data['type'])
        data['gender'] = Gender(data['gender'])
        data['age_range'] = AgeRange(**data.get('age_range', {}))
        data['geo_targeting'] = GeoTargeting(**data.get('geo_targeting', {}))
        data['device_targeting'] = DeviceTargeting(**data.get('device_targeting', {}))
        return cls(**data)


class AudienceTargeting:
    """人群定向管理器"""
    
    # 预定义兴趣标签库
    INTEREST_CATEGORIES = {
        '电商购物': ['淘宝', '京东', '拼多多', '网购', '优惠', '折扣', '秒杀'],
        '美妆护肤': ['护肤', '彩妆', '美妆', '口红', '面膜', '化妆'],
        '数码科技': ['手机', '电脑', '数码', '科技', '智能设备', '游戏'],
        '美食餐饮': ['美食', '餐饮', '外卖', '零食', '烘焙', '饮品'],
        '旅游出行': ['旅游', '酒店', '机票', '景点', '自驾游', '出国'],
        '母婴育儿': ['母婴', '育儿', '奶粉', '童装', '早教', '玩具'],
        '家居生活': ['家居', '装修', '家具', '家纺', '收纳', '绿植'],
        '运动健身': ['运动', '健身', '瑜伽', '跑步', '减肥', '户外'],
        '金融理财': ['理财', '基金', '股票', '保险', '信用卡', '贷款'],
        '汽车': ['汽车', '二手车', '新能源车', '保养', '车险', '驾驶']
    }
    
    # 预定义行为标签库
    BEHAVIOR_CATEGORIES = {
        '购买行为': ['最近购买', '高频购买', '大额消费', '复购用户', '首单用户'],
        '互动行为': ['点赞', '评论', '分享', '收藏', '关注', '私信'],
        '浏览行为': ['深度浏览', '多次浏览', '加购未买', '对比商品', '查看评价'],
        '应用行为': ['活跃用户', '新注册用户', '流失风险', '付费用户', 'VIP用户']
    }
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or config.database.path
        self._conn = None  # explicit single connection to avoid ResourceWarning
        self._init_database()
        self.logger = logger.getChild("audience_targeting")

    def close(self) -> None:
        """Close the managed database connection."""
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception as e:
                logger.debug("audience_targeting DB connection cleanup: {e}")
            self._conn = None

    def __del__(self) -> None:
        self.close()

    def _init_database(self) -> None:
        """初始化数据库表"""
        self._conn = sqlite3.connect(self.db_path)
        conn = self._conn
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audience_segments (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                gender TEXT DEFAULT 'all',
                age_range TEXT NOT NULL,
                geo_targeting TEXT NOT NULL,
                device_targeting TEXT NOT NULL,
                interests TEXT,
                behaviors TEXT,
                custom_tags TEXT,
                source_audience_id TEXT,
                lookalike_ratio REAL,
                estimated_size INTEGER DEFAULT 0,
                estimated_daily_impressions INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()
        self._conn = None

    def create_segment(self, segment: AudienceSegment) -> bool:
        """创建人群包"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                now = datetime.now().isoformat()
                conn.execute("""
                    INSERT INTO audience_segments
                    (id, name, type, gender, age_range, geo_targeting, device_targeting,
                     interests, behaviors, custom_tags, source_audience_id, lookalike_ratio,
                     estimated_size, estimated_daily_impressions, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    segment.id, segment.name, segment.type.value, segment.gender.value,
                    json.dumps(segment.age_range.to_dict()),
                    json.dumps(segment.geo_targeting.__dict__),
                    json.dumps(segment.device_targeting.__dict__),
                    json.dumps(segment.interests),
                    json.dumps(segment.behaviors),
                    json.dumps(segment.custom_tags),
                    segment.source_audience_id,
                    segment.lookalike_ratio,
                    segment.estimated_size,
                    segment.estimated_daily_impressions,
                    segment.status, now, now
                ))
                conn.commit()
            
            self.logger.info(f"人群包创建成功: {segment.name}")
            return True
        except Exception as e:
            self.logger.error(f"创建人群包失败: {e}")
            return False
    
    def get_segment(self, segment_id: str) -> Optional[AudienceSegment]:
        """获取人群包"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT * FROM audience_segments WHERE id = ?",
                    (segment_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    return AudienceSegment(
                        id=row[0],
                        name=row[1],
                        type=AudienceType(row[2]),
                        gender=Gender(row[3]),
                        age_range=AgeRange(**json.loads(row[4])),
                        geo_targeting=GeoTargeting(**json.loads(row[5])),
                        device_targeting=DeviceTargeting(**json.loads(row[6])),
                        interests=json.loads(row[7]) if row[7] else [],
                        behaviors=json.loads(row[8]) if row[8] else [],
                        custom_tags=json.loads(row[9]) if row[9] else [],
                        source_audience_id=row[10],
                        lookalike_ratio=row[11],
                        estimated_size=row[12],
                        estimated_daily_impressions=row[13],
                        status=row[14],
                        created_at=row[15],
                        updated_at=row[16]
                    )
        except Exception as e:
            self.logger.error(f"获取人群包失败: {e}")
        
        return None
    
    def get_segments(self, type: Optional[AudienceType] = None,
                    status: Optional[str] = None) -> List[AudienceSegment]:
        """获取人群包列表"""
        segments = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = "SELECT * FROM audience_segments WHERE 1=1"
                params = []
                
                if type:
                    query += " AND type = ?"
                    params.append(type.value)
                if status:
                    query += " AND status = ?"
                    params.append(status)
                
                cursor = conn.execute(query, params)
                
                for row in cursor.fetchall():
                    segments.append(AudienceSegment(
                        id=row[0],
                        name=row[1],
                        type=AudienceType(row[2]),
                        gender=Gender(row[3]),
                        age_range=AgeRange(**json.loads(row[4])),
                        geo_targeting=GeoTargeting(**json.loads(row[5])),
                        device_targeting=DeviceTargeting(**json.loads(row[6])),
                        interests=json.loads(row[7]) if row[7] else [],
                        behaviors=json.loads(row[8]) if row[8] else [],
                        custom_tags=json.loads(row[9]) if row[9] else [],
                        source_audience_id=row[10],
                        lookalike_ratio=row[11],
                        estimated_size=row[12],
                        estimated_daily_impressions=row[13],
                        status=row[14],
                        created_at=row[15],
                        updated_at=row[16]
                    ))
        except Exception as e:
            self.logger.error(f"获取人群包列表失败: {e}")
        
        return segments
    
    def update_segment(self, segment_id: str, updates: Dict[str, Any]) -> bool:
        """更新人群包"""
        try:
            allowed_fields = ['name', 'status', 'estimated_size', 
                            'estimated_daily_impressions']
            
            set_clause = []
            params = []
            
            for field, value in updates.items():
                if field in allowed_fields:
                    set_clause.append(f"{field} = ?")
                    params.append(value)
            
            if not set_clause:
                return False
            
            set_clause.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            params.append(segment_id)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    f"UPDATE audience_segments SET {', '.join(set_clause)} WHERE id = ?",
                    params
                )
                conn.commit()
            
            return True
        except Exception as e:
            self.logger.error(f"更新人群包失败: {e}")
            return False
    
    def delete_segment(self, segment_id: str) -> bool:
        """删除人群包"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM audience_segments WHERE id = ?", (segment_id,))
                conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"删除人群包失败: {e}")
            return False
    
    def estimate_audience_size(self, segment: AudienceSegment) -> Dict[str, Any]:
        """
        预估人群规模
        
        这是一个简化模型，实际应该调用平台API获取真实预估
        """
        # 基础人群规模（假设）
        base_size = 10000000  # 1000万基础用户
        
        # 年龄系数
        age_coverage = (segment.age_range.max_age - segment.age_range.min_age) / 47
        
        # 地域系数
        if segment.geo_targeting.provinces:
            geo_coverage = len(segment.geo_targeting.provinces) / 34 * 0.8
        elif segment.geo_targeting.cities:
            geo_coverage = len(segment.geo_targeting.cities) / 300 * 0.6
        else:
            geo_coverage = 1.0
        
        # 性别系数
        gender_coverage = 0.5 if segment.gender != Gender.ALL else 1.0
        
        # 兴趣系数
        if segment.interests:
            interest_coverage = min(1.0, len(segment.interests) * 0.1)
        else:
            interest_coverage = 1.0
        
        # 行为系数
        if segment.behaviors:
            behavior_coverage = min(1.0, len(segment.behaviors) * 0.15)
        else:
            behavior_coverage = 1.0
        
        # 计算预估规模
        estimated_size = int(
            base_size * age_coverage * geo_coverage * gender_coverage * 
            interest_coverage * behavior_coverage
        )
        
        # 日曝光预估（假设日活20%，人均曝光5次）
        estimated_daily_impressions = int(estimated_size * 0.2 * 5)
        
        return {
            'estimated_size': estimated_size,
            'estimated_daily_impressions': estimated_daily_impressions,
            'coverage_factors': {
                'age': round(age_coverage, 3),
                'geo': round(geo_coverage, 3),
                'gender': round(gender_coverage, 3),
                'interest': round(interest_coverage, 3),
                'behavior': round(behavior_coverage, 3)
            }
        }
    
    def create_lookalike(self, source_segment_id: str, name: str,
                        ratio: float = 0.01) -> Optional[AudienceSegment]:
        """
        创建相似人群包
        
        Args:
            source_segment_id: 源人群包ID
            name: 新人群包名称
            ratio: 相似度比例 (0.001-0.1)
        """
        source = self.get_segment(source_segment_id)
        if not source:
            self.logger.error(f"源人群包不存在: {source_segment_id}")
            return None
        
        # 创建Lookalike人群包
        lookalike = AudienceSegment(
            id=f"lookalike_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            name=name,
            type=AudienceType.LOOKALIKE,
            gender=source.gender,
            age_range=source.age_range,
            geo_targeting=source.geo_targeting,
            device_targeting=source.device_targeting,
            source_audience_id=source_segment_id,
            lookalike_ratio=ratio,
            estimated_size=int(source.estimated_size * (1 + ratio * 10)),
            estimated_daily_impressions=int(source.estimated_daily_impressions * (1 + ratio * 5))
        )
        
        if self.create_segment(lookalike):
            self.logger.info(f"相似人群包创建成功: {name}")
            return lookalike
        
        return None
    
    def get_interest_categories(self) -> Dict[str, List[str]]:
        """获取兴趣分类"""
        return self.INTEREST_CATEGORIES.copy()
    
    def get_behavior_categories(self) -> Dict[str, List[str]]:
        """获取行为分类"""
        return self.BEHAVIOR_CATEGORIES.copy()
    
    def get_recommended_targeting(self, product_category: str,
                                 target_platform: str) -> Dict[str, Any]:
        """
        获取推荐定向配置
        
        Args:
            product_category: 产品类目
            target_platform: 目标平台
        """
        recommendations = {
            '美妆': {
                'interests': ['美妆护肤', '电商购物'],
                'behaviors': ['最近购买', '深度浏览'],
                'gender': 'female',
                'age_range': {'min_age': 18, 'max_age': 45}
            },
            '数码': {
                'interests': ['数码科技', '电商购物'],
                'behaviors': ['对比商品', '查看评价'],
                'gender': 'all',
                'age_range': {'min_age': 18, 'max_age': 50}
            },
            '母婴': {
                'interests': ['母婴育儿', '电商购物'],
                'behaviors': ['最近购买', '复购用户'],
                'gender': 'female',
                'age_range': {'min_age': 22, 'max_age': 40}
            },
            '食品': {
                'interests': ['美食餐饮', '电商购物'],
                'behaviors': ['最近购买', '高频购买'],
                'gender': 'all',
                'age_range': {'min_age': 18, 'max_age': 60}
            },
            '服装': {
                'interests': ['电商购物', '美妆护肤'],
                'behaviors': ['加购未买', '多次浏览'],
                'gender': 'female',
                'age_range': {'min_age': 18, 'max_age': 50}
            }
        }
        
        return recommendations.get(product_category, {
            'interests': ['电商购物'],
            'behaviors': ['活跃用户'],
            'gender': 'all',
            'age_range': {'min_age': 18, 'max_age': 65}
        })
    
    # ==================== 异步方法 ====================
    
    async def create_segment_async(self, segment: 'AudienceSegment') -> bool:
        """创建人群包 (真正异步)"""
        if not _HAS_AIOSQLITE:
            raise RuntimeError("aiosqlite not installed")
        try:
            now = datetime.now().isoformat()
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute("""
                    INSERT INTO audience_segments
                    (id, name, type, gender, age_range, geo_targeting, device_targeting,
                     interests, behaviors, custom_tags, source_audience_id, lookalike_ratio,
                     estimated_size, estimated_daily_impressions, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    segment.id, segment.name, segment.type.value, segment.gender.value,
                    json.dumps(segment.age_range.to_dict()),
                    json.dumps(segment.geo_targeting.__dict__),
                    json.dumps(segment.device_targeting.__dict__),
                    json.dumps(segment.interests),
                    json.dumps(segment.behaviors),
                    json.dumps(segment.custom_tags),
                    segment.source_audience_id,
                    segment.lookalike_ratio,
                    segment.estimated_size,
                    segment.estimated_daily_impressions,
                    segment.status, now, now
                ))
                await conn.commit()
            
            self.logger.info(f"人群包创建成功(异步): {segment.name}")
            return True
        except Exception as e:
            self.logger.error(f"创建人群包失败(异步): {e}")
            return False
    
    async def get_segment_async(self, segment_id: str) -> 'Optional[AudienceSegment]':
        """获取人群包 (真正异步)"""
        if not _HAS_AIOSQLITE:
            raise RuntimeError("aiosqlite not installed")
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                cursor = await conn.execute(
                    "SELECT * FROM audience_segments WHERE id = ?",
                    (segment_id,)
                )
                row = await cursor.fetchone()
                
                if row:
                    return AudienceSegment(
                        id=row[0],
                        name=row[1],
                        type=AudienceType(row[2]),
                        gender=Gender(row[3]),
                        age_range=AgeRange(**json.loads(row[4])),
                        geo_targeting=GeoTargeting(**json.loads(row[5])),
                        device_targeting=DeviceTargeting(**json.loads(row[6])),
                        interests=json.loads(row[7]) if row[7] else [],
                        behaviors=json.loads(row[8]) if row[8] else [],
                        custom_tags=json.loads(row[9]) if row[9] else [],
                        source_audience_id=row[10],
                        lookalike_ratio=row[11],
                        estimated_size=row[12],
                        estimated_daily_impressions=row[13],
                        status=row[14],
                        created_at=row[15],
                        updated_at=row[16]
                    )
        except Exception as e:
            self.logger.error(f"获取人群包失败(异步): {e}")
        
        return None
    
    async def get_segments_async(self, type=None, status=None) -> None:
        """获取人群包列表 (真正异步)
        
        Args:
            type: 人群类型过滤 (AudienceType)
            status: 状态过滤 (active/paused/expired)
        """
        if not _HAS_AIOSQLITE:
            raise RuntimeError("aiosqlite not installed")
        segments = []
        
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                query = "SELECT * FROM audience_segments WHERE 1=1"
                params = []
                
                if type:
                    query += " AND type = ?"
                    params.append(type.value)
                if status:
                    query += " AND status = ?"
                    params.append(status)
                
                cursor = await conn.execute(query, params)
                rows = await cursor.fetchall()
                
                for row in rows:
                    segments.append(AudienceSegment(
                        id=row[0],
                        name=row[1],
                        type=AudienceType(row[2]),
                        gender=Gender(row[3]),
                        age_range=AgeRange(**json.loads(row[4])),
                        geo_targeting=GeoTargeting(**json.loads(row[5])),
                        device_targeting=DeviceTargeting(**json.loads(row[6])),
                        interests=json.loads(row[7]) if row[7] else [],
                        behaviors=json.loads(row[8]) if row[8] else [],
                        custom_tags=json.loads(row[9]) if row[9] else [],
                        source_audience_id=row[10],
                        lookalike_ratio=row[11],
                        estimated_size=row[12],
                        estimated_daily_impressions=row[13],
                        status=row[14],
                        created_at=row[15],
                        updated_at=row[16]
                    ))
        except Exception as e:
            self.logger.error(f"获取人群包列表失败(异步): {e}")
        
        return segments
    
    async def update_segment_async(self, segment_id: str, updates: dict) -> bool:
        """更新人群包 (真正异步)"""
        if not _HAS_AIOSQLITE:
            raise RuntimeError("aiosqlite not installed")
        try:
            allowed_fields = ['name', 'status', 'estimated_size', 
                            'estimated_daily_impressions']
            
            set_clause = []
            params = []
            
            for field, value in updates.items():
                if field in allowed_fields:
                    set_clause.append(f"{field} = ?")
                    params.append(value)
            
            if not set_clause:
                return False
            
            set_clause.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            params.append(segment_id)
            
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute(
                    f"UPDATE audience_segments SET {', '.join(set_clause)} WHERE id = ?",
                    params
                )
                await conn.commit()
            
            return True
        except Exception as e:
            self.logger.error(f"更新人群包失败(异步): {e}")
            return False
    
    async def delete_segment_async(self, segment_id: str) -> bool:
        """删除人群包 (真正异步)"""
        if not _HAS_AIOSQLITE:
            raise RuntimeError("aiosqlite not installed")
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute("DELETE FROM audience_segments WHERE id = ?", (segment_id,))
                await conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"删除人群包失败(异步): {e}")
            return False
    
    async def estimate_audience_size_async(self, segment: 'AudienceSegment') -> dict:
        """估算人群规模 (异步)"""
        return await asyncio.to_thread(self.estimate_audience_size, segment)
    
    async def create_lookalike_async(self, source_segment_id: str, name: str,
                                      ratio: float = 0.01):
        """创建相似人群 (真正异步)"""
        if not _HAS_AIOSQLITE:
            raise RuntimeError("aiosqlite not installed")
        
        source = await self.get_segment_async(source_segment_id)
        if not source:
            self.logger.error(f"源人群包不存在: {source_segment_id}")
            return None
        
        # 创建Lookalike人群包
        lookalike = AudienceSegment(
            id=f"lookalike_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            name=name,
            type=AudienceType.LOOKALIKE,
            gender=source.gender,
            age_range=source.age_range,
            geo_targeting=source.geo_targeting,
            device_targeting=source.device_targeting,
            source_audience_id=source_segment_id,
            lookalike_ratio=ratio,
            estimated_size=int(source.estimated_size * (1 + ratio * 10)),
            estimated_daily_impressions=int(source.estimated_daily_impressions * (1 + ratio * 5))
        )
        
        if await self.create_segment_async(lookalike):
            self.logger.info(f"相似人群包创建成功(异步): {name}")
            return lookalike
        
        return None

