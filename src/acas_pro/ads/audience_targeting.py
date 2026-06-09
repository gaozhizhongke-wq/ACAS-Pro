"""
人群定向管理模块
支持多维度人群定向和Lookalike扩展
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

from ..core.database import DatabaseManager
from ..core.logging import logger


# ============================================================================
# Data Models
# ============================================================================

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
    provinces: List[str] = None
    cities: List[str] = None
    exclude_regions: List[str] = None
    radius_targeting: Optional[Dict[str, Any]] = None

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
    device_types: List[str] = None
    os_types: List[str] = None
    network_types: List[str] = None
    brands: List[str] = None
    price_ranges: List[str] = None

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

    gender: Gender = Gender.ALL
    age_range: AgeRange = None
    geo_targeting: GeoTargeting = None
    device_targeting: DeviceTargeting = None

    interests: List[str] = None
    behaviors: List[str] = None
    custom_tags: List[str] = None

    source_audience_id: Optional[str] = None
    lookalike_ratio: Optional[float] = None

    estimated_size: int = 0
    estimated_daily_impressions: int = 0

    status: str = "active"

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


# ============================================================================
# Helper: DB row → AudienceSegment
# ============================================================================

def _row_to_segment(row: Dict[str, Any]) -> AudienceSegment:
    """Convert a DatabaseManager row dict to an AudienceSegment."""
    return AudienceSegment(
        id=row['id'],
        name=row['name'],
        type=AudienceType(row['type']),
        gender=Gender(row.get('gender', 'all')),
        age_range=AgeRange(**json.loads(row['age_range'])) if row.get('age_range') else AgeRange(),
        geo_targeting=GeoTargeting(**json.loads(row['geo_targeting'])) if row.get('geo_targeting') else GeoTargeting(),
        device_targeting=DeviceTargeting(**json.loads(row['device_targeting'])) if row.get('device_targeting') else DeviceTargeting(),
        interests=json.loads(row['interests']) if row.get('interests') else [],
        behaviors=json.loads(row['behaviors']) if row.get('behaviors') else [],
        custom_tags=json.loads(row['custom_tags']) if row.get('custom_tags') else [],
        source_audience_id=row.get('source_audience_id'),
        lookalike_ratio=row.get('lookalike_ratio'),
        estimated_size=row.get('estimated_size', 0) or 0,
        estimated_daily_impressions=row.get('estimated_daily_impressions', 0) or 0,
        status=row.get('status', 'active'),
        created_at=row.get('created_at'),
        updated_at=row.get('updated_at'),
    )


# ============================================================================
# AudienceTargeting
# ============================================================================

class AudienceTargeting:
    """人群定向管理器 — backed by DatabaseManager singleton."""

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

    BEHAVIOR_CATEGORIES = {
        '购买行为': ['最近购买', '高频购买', '大额消费', '复购用户', '首单用户'],
        '互动行为': ['点赞', '评论', '分享', '收藏', '关注', '私信'],
        '浏览行为': ['深度浏览', '多次浏览', '加购未买', '对比商品', '查看评价'],
        '应用行为': ['活跃用户', '新注册用户', '流失风险', '付费用户', 'VIP用户']
    }

    def __init__(self, db: Optional[DatabaseManager] = None, db_path: Optional[str] = None):
        self._db = db  # None → lazy singleton via property
        self._db_path_override = db_path  # legacy compat
        self._logger = logger.getChild("audience_targeting")
        # Tables managed by core/schema.py — do not add CREATE/ALTER TABLE here

    # ── Lazy DatabaseManager access ─────────────────────────────────

    @property
    def db(self) -> DatabaseManager:
        if self._db is None:
            self._db = DatabaseManager()
        return self._db

    @db.setter
    def db(self, value: DatabaseManager) -> None:
        self._db = value

    # ── Legacy compat ───────────────────────────────────────────────

    @property
    def db_path(self) -> str:
        """Legacy compat — returns DatabaseManager's db_path."""
        return getattr(self.db, '_db_path', '')

    def close(self) -> None:
        """Legacy compat — no-op with DatabaseManager."""
        pass

    # ── CRUD (sync) ────────────────────────────────────────────────

    def create_segment(self, segment: AudienceSegment) -> bool:
        """创建人群包"""
        try:
            now = datetime.now().isoformat()
            self.db.insert('audience_segments', {
                'id': segment.id,
                'name': segment.name,
                'type': segment.type.value,
                'gender': segment.gender.value,
                'age_range': json.dumps(segment.age_range.to_dict()),
                'geo_targeting': json.dumps(asdict(segment.geo_targeting)),
                'device_targeting': json.dumps(asdict(segment.device_targeting)),
                'interests': json.dumps(segment.interests),
                'behaviors': json.dumps(segment.behaviors),
                'custom_tags': json.dumps(segment.custom_tags),
                'source_audience_id': segment.source_audience_id,
                'lookalike_ratio': segment.lookalike_ratio,
                'estimated_size': segment.estimated_size,
                'estimated_daily_impressions': segment.estimated_daily_impressions,
                'status': segment.status,
                'created_at': now,
                'updated_at': now,
            })
            self._logger.info(f"人群包创建成功: {segment.name}")
            return True
        except Exception as e:
            self._logger.error(f"创建人群包失败: {e}")
            return False

    def get_segment(self, segment_id: str) -> Optional[AudienceSegment]:
        """获取人群包"""
        try:
            row = self.db.fetch_one(
                "SELECT * FROM audience_segments WHERE id = ?",
                (segment_id,)
            )
            if row:
                return _row_to_segment(row)
        except Exception as e:
            self._logger.error(f"获取人群包失败: {e}")
        return None

    def get_segments(self, type: Optional[AudienceType] = None,
                     status: Optional[str] = None) -> List[AudienceSegment]:
        """获取人群包列表"""
        try:
            query = "SELECT * FROM audience_segments WHERE 1=1"
            params: list = []

            if type:
                query += " AND type = ?"
                params.append(type.value)
            if status:
                query += " AND status = ?"
                params.append(status)

            rows = self.db.fetchall(query, tuple(params) if params else None)
            return [_row_to_segment(r) for r in rows]
        except Exception as e:
            self._logger.error(f"获取人群包列表失败: {e}")
            return []

    def update_segment(self, segment_id: str, updates: Dict[str, Any]) -> bool:
        """更新人群包"""
        try:
            allowed_fields = {'name', 'status', 'estimated_size',
                              'estimated_daily_impressions'}
            data = {k: v for k, v in updates.items() if k in allowed_fields}
            if not data:
                return False
            data['updated_at'] = datetime.now().isoformat()
            self.db.update('audience_segments', data, {'id': segment_id})
            return True
        except Exception as e:
            self._logger.error(f"更新人群包失败: {e}")
            return False

    def delete_segment(self, segment_id: str) -> bool:
        """删除人群包"""
        try:
            self.db.delete('audience_segments', {'id': segment_id})
            return True
        except Exception as e:
            self._logger.error(f"删除人群包失败: {e}")
            return False

    # ── Estimation & recommendation (pure logic, no DB) ────────────

    def estimate_audience_size(self, segment: AudienceSegment) -> Dict[str, Any]:
        """预估人群规模（简化模型）"""
        base_size = 10000000

        age_coverage = (segment.age_range.max_age - segment.age_range.min_age) / 47

        if segment.geo_targeting.provinces:
            geo_coverage = len(segment.geo_targeting.provinces) / 34 * 0.8
        elif segment.geo_targeting.cities:
            geo_coverage = len(segment.geo_targeting.cities) / 300 * 0.6
        else:
            geo_coverage = 1.0

        gender_coverage = 0.5 if segment.gender != Gender.ALL else 1.0
        interest_coverage = min(1.0, len(segment.interests) * 0.1) if segment.interests else 1.0
        behavior_coverage = min(1.0, len(segment.behaviors) * 0.15) if segment.behaviors else 1.0

        estimated_size = int(
            base_size * age_coverage * geo_coverage * gender_coverage *
            interest_coverage * behavior_coverage
        )
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
        """创建相似人群包"""
        source = self.get_segment(source_segment_id)
        if not source:
            self._logger.error(f"源人群包不存在: {source_segment_id}")
            return None

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
            self._logger.info(f"相似人群包创建成功: {name}")
            return lookalike
        return None

    def get_interest_categories(self) -> Dict[str, List[str]]:
        return self.INTEREST_CATEGORIES.copy()

    def get_behavior_categories(self) -> Dict[str, List[str]]:
        return self.BEHAVIOR_CATEGORIES.copy()

    def get_recommended_targeting(self, product_category: str,
                                  target_platform: str) -> Dict[str, Any]:
        """获取推荐定向配置"""
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

    # ── Async CRUD ──────────────────────────────────────────────────

    async def create_segment_async(self, segment: AudienceSegment) -> bool:
        """创建人群包 (异步)"""
        try:
            now = datetime.now().isoformat()
            await self.db.insert_async('audience_segments', {
                'id': segment.id,
                'name': segment.name,
                'type': segment.type.value,
                'gender': segment.gender.value,
                'age_range': json.dumps(segment.age_range.to_dict()),
                'geo_targeting': json.dumps(asdict(segment.geo_targeting)),
                'device_targeting': json.dumps(asdict(segment.device_targeting)),
                'interests': json.dumps(segment.interests),
                'behaviors': json.dumps(segment.behaviors),
                'custom_tags': json.dumps(segment.custom_tags),
                'source_audience_id': segment.source_audience_id,
                'lookalike_ratio': segment.lookalike_ratio,
                'estimated_size': segment.estimated_size,
                'estimated_daily_impressions': segment.estimated_daily_impressions,
                'status': segment.status,
                'created_at': now,
                'updated_at': now,
            })
            self._logger.info(f"人群包创建成功(异步): {segment.name}")
            return True
        except Exception as e:
            self._logger.error(f"创建人群包失败(异步): {e}")
            return False

    async def get_segment_async(self, segment_id: str) -> Optional[AudienceSegment]:
        """获取人群包 (异步)"""
        try:
            row = await self.db.execute_one_async(
                "SELECT * FROM audience_segments WHERE id = ?",
                (segment_id,)
            )
            if row:
                return _row_to_segment(row)
        except Exception as e:
            self._logger.error(f"获取人群包失败(异步): {e}")
        return None

    async def get_segments_async(self, type=None, status=None) -> List[AudienceSegment]:
        """获取人群包列表 (异步)"""
        try:
            query = "SELECT * FROM audience_segments WHERE 1=1"
            params: list = []
            if type:
                query += " AND type = ?"
                params.append(type.value)
            if status:
                query += " AND status = ?"
                params.append(status)
            rows = await self.db.fetchall_async(query, tuple(params) if params else None)
            return [_row_to_segment(r) for r in rows]
        except Exception as e:
            self._logger.error(f"获取人群包列表失败(异步): {e}")
            return []

    async def update_segment_async(self, segment_id: str, updates: dict) -> bool:
        """更新人群包 (异步)"""
        try:
            allowed_fields = {'name', 'status', 'estimated_size',
                              'estimated_daily_impressions'}
            data = {k: v for k, v in updates.items() if k in allowed_fields}
            if not data:
                return False
            data['updated_at'] = datetime.now().isoformat()
            await self.db.update_async('audience_segments', data, {'id': segment_id})
            return True
        except Exception as e:
            self._logger.error(f"更新人群包失败(异步): {e}")
            return False

    async def delete_segment_async(self, segment_id: str) -> bool:
        """删除人群包 (异步)"""
        try:
            await self.db.delete_async('audience_segments', {'id': segment_id})
            return True
        except Exception as e:
            self._logger.error(f"删除人群包失败(异步): {e}")
            return False

    async def estimate_audience_size_async(self, segment: AudienceSegment) -> dict:
        """估算人群规模 (异步)"""
        return await asyncio.to_thread(self.estimate_audience_size, segment)

    async def create_lookalike_async(self, source_segment_id: str, name: str,
                                      ratio: float = 0.01) -> Optional[AudienceSegment]:
        """创建相似人群 (异步)"""
        source = await self.get_segment_async(source_segment_id)
        if not source:
            self._logger.error(f"源人群包不存在: {source_segment_id}")
            return None

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
            self._logger.info(f"相似人群包创建成功(异步): {name}")
            return lookalike
        return None
