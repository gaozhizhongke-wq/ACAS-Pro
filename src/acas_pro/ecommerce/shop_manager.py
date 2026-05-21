"""
店铺管理 - 多平台店铺统一管理
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

from ..core.config import config
from ..core.logging import get_logger
from ..core.database import DatabaseManager

logger = get_logger(__name__)


class ShopPlatform(Enum):
    """电商平台"""
    DOUYIN_SHOP = "douyin_shop"           # 抖音小店
    KUAISHOU_SHOP = "kuaishou_shop"       # 快手小店
    TAOBAO = "taobao"                      # 淘宝
    TMALL = "tmall"                        # 天猫
    JD = "jd"                              # 京东
    PDD = "pdd"                            # 拼多多
    XIAOHONGSHU_SHOP = "xiaohongshu_shop" # 小红书店铺
    WECHAT_SHOP = "wechat_shop"           # 微信小商店


class ShopStatus(Enum):
    """店铺状态"""
    ACTIVE = "active"                      # 营业中
    PAUSED = "paused"                      # 暂停营业
    SUSPENDED = "suspended"                # 平台封禁
    PENDING = "pending"                    # 待审核
    CLOSED = "closed"                      # 已关闭


@dataclass
class ShopCredentials:
    """店铺凭证"""
    app_key: Optional[str] = None
    app_secret: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: Optional[str] = None
    
    def is_expired(self) -> bool:
        """检查token是否过期"""
        if not self.expires_at:
            return True
        try:
            expiry = datetime.fromisoformat(self.expires_at)
            return datetime.now() > expiry
        except Exception as e:
            logger.warning(f"Failed to parse expiry date: {e}")
            return True


@dataclass
class ShopStats:
    """店铺统计数据"""
    total_products: int = 0
    total_orders_today: int = 0
    total_orders_month: int = 0
    revenue_today: float = 0.0
    revenue_month: float = 0.0
    visitors_today: int = 0
    conversion_rate: float = 0.0
    rating: float = 5.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_products': self.total_products,
            'total_orders_today': self.total_orders_today,
            'total_orders_month': self.total_orders_month,
            'revenue_today': self.revenue_today,
            'revenue_month': self.revenue_month,
            'visitors_today': self.visitors_today,
            'conversion_rate': self.conversion_rate,
            'rating': self.rating,
        }


@dataclass
class Shop:
    """店铺实体"""
    id: str
    name: str
    platform: ShopPlatform
    status: ShopStatus
    
    # 店铺信息
    shop_id_on_platform: str = ""           # 平台侧店铺ID
    shop_url: Optional[str] = None
    logo_url: Optional[str] = None
    description: str = ""
    
    # 联系信息
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    
    # 经营信息
    main_category: str = ""                 # 主营类目
    business_license: Optional[str] = None  # 营业执照号
    
    # 凭证（加密存储）
    credentials: ShopCredentials = field(default_factory=ShopCredentials)
    
    # 统计数据
    stats: ShopStats = field(default_factory=ShopStats)
    
    # 设置
    auto_sync: bool = True                  # 自动同步
    sync_interval: int = 15                 # 同步间隔（分钟）
    
    # 元数据
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    owner_id: Optional[str] = None
    last_sync_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'platform': self.platform.value,
            'status': self.status.value,
            'shop_id_on_platform': self.shop_id_on_platform,
            'shop_url': self.shop_url,
            'logo_url': self.logo_url,
            'description': self.description,
            'contact_name': self.contact_name,
            'contact_phone': self.contact_phone,
            'contact_email': self.contact_email,
            'main_category': self.main_category,
            'business_license': self.business_license,
            'auto_sync': self.auto_sync,
            'sync_interval': self.sync_interval,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'owner_id': self.owner_id,
            'last_sync_at': self.last_sync_at,
            'stats': self.stats.to_dict(),
        }


class ShopManager:
    """店铺管理器"""
    
    # 平台配置
    PLATFORM_CONFIG = {
        ShopPlatform.DOUYIN_SHOP: {
            'name': '抖音小店',
            'api_base': 'https://openapi-fxg.jinritemai.com',
            'auth_url': 'https://fxg.jinritemai.com/open/authorize',
            'scopes': ['product', 'order', 'logistics', 'aftersale'],
        },
        ShopPlatform.KUAISHOU_SHOP: {
            'name': '快手小店',
            'api_base': 'https://openapi.kwaixiaodian.com',
            'auth_url': 'https://s.kwaixiaodian.com/authorize',
            'scopes': ['item', 'trade', 'logistics'],
        },
        ShopPlatform.TAOBAO: {
            'name': '淘宝',
            'api_base': 'https://eco.taobao.com/router/rest',
            'auth_url': 'https://oauth.taobao.com/authorize',
            'scopes': ['item', 'trade', 'user'],
        },
        ShopPlatform.TMALL: {
            'name': '天猫',
            'api_base': 'https://eco.taobao.com/router/rest',
            'auth_url': 'https://oauth.taobao.com/authorize',
            'scopes': ['item', 'trade', 'user'],
        },
        ShopPlatform.JD: {
            'name': '京东',
            'api_base': 'https://api.jd.com/routerjson',
            'auth_url': 'https://oauth.jd.com/oauth/authorize',
            'scopes': ['read', 'write'],
        },
        ShopPlatform.PDD: {
            'name': '拼多多',
            'api_base': 'https://gw-api.pinduoduo.com/api/router',
            'auth_url': 'https://fuwu.pinduoduo.com/service-market/auth',
            'scopes': ['pdd_goods', 'pdd_order', 'pdd_logistics'],
        },
        ShopPlatform.XIAOHONGSHU_SHOP: {
            'name': '小红书店铺',
            'api_base': 'https://ark.xiaohongshu.com/api',
            'auth_url': 'https://ark.xiaohongshu.com/authorize',
            'scopes': ['products', 'orders', 'logistics'],
        },
        ShopPlatform.WECHAT_SHOP: {
            'name': '微信小商店',
            'api_base': 'https://api.weixin.qq.com/shop',
            'auth_url': 'https://mp.weixin.qq.com/cgi-bin/componentloginpage',
            'scopes': ['product', 'order', 'delivery'],
        },
    }
    
    def __init__(self):
        self.db = DatabaseManager()
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表"""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS shops (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                platform TEXT NOT NULL,
                status TEXT NOT NULL,
                shop_id_on_platform TEXT,
                shop_url TEXT,
                logo_url TEXT,
                description TEXT,
                contact_name TEXT,
                contact_phone TEXT,
                contact_email TEXT,
                main_category TEXT,
                business_license TEXT,
                credentials TEXT,
                auto_sync INTEGER DEFAULT 1,
                sync_interval INTEGER DEFAULT 15,
                created_at TEXT,
                updated_at TEXT,
                owner_id TEXT,
                last_sync_at TEXT
            )
        """)
        
        # 店铺统计表
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS shop_stats (
                shop_id TEXT PRIMARY KEY,
                total_products INTEGER DEFAULT 0,
                total_orders_today INTEGER DEFAULT 0,
                total_orders_month INTEGER DEFAULT 0,
                revenue_today REAL DEFAULT 0.0,
                revenue_month REAL DEFAULT 0.0,
                visitors_today INTEGER DEFAULT 0,
                conversion_rate REAL DEFAULT 0.0,
                rating REAL DEFAULT 5.0,
                updated_at TEXT,
                FOREIGN KEY (shop_id) REFERENCES shops(id)
            )
        """)
    
    def create_shop(
        self,
        name: str,
        platform: ShopPlatform,
        shop_id_on_platform: str,
        credentials: Dict[str, str],
        owner_id: Optional[str] = None,
        **kwargs
    ) -> Optional[Shop]:
        """创建店铺"""
        shop_id = f"shop_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        shop = Shop(
            id=shop_id,
            name=name,
            platform=platform,
            status=ShopStatus.PENDING,
            shop_id_on_platform=shop_id_on_platform,
            owner_id=owner_id,
            credentials=ShopCredentials(**credentials),
            **kwargs
        )
        
        # 保存到数据库
        self._save_shop(shop)
        
        # 初始化统计
        self._init_shop_stats(shop_id)
        
        logger.info(f"Created shop: {shop_id} ({name})")
        return shop
    
    def _save_shop(self, shop: Shop):
        """保存店铺"""
        self.db.execute("""
            INSERT OR REPLACE INTO shops (
                id, name, platform, status, shop_id_on_platform,
                shop_url, logo_url, description, contact_name,
                contact_phone, contact_email, main_category,
                business_license, credentials, auto_sync,
                sync_interval, created_at, updated_at, owner_id, last_sync_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            shop.id, shop.name, shop.platform.value, shop.status.value,
            shop.shop_id_on_platform, shop.shop_url, shop.logo_url,
            shop.description, shop.contact_name, shop.contact_phone,
            shop.contact_email, shop.main_category, shop.business_license,
            json.dumps(shop.credentials.__dict__),
            int(shop.auto_sync), shop.sync_interval,
            shop.created_at, shop.updated_at, shop.owner_id, shop.last_sync_at
        ))
    
    def _init_shop_stats(self, shop_id: str):
        """初始化店铺统计"""
        self.db.execute("""
            INSERT OR IGNORE INTO shop_stats (
                shop_id, updated_at
            ) VALUES (?, ?)
        """, (shop_id, datetime.now().isoformat()))
    
    def get_shop(self, shop_id: str) -> Optional[Shop]:
        """获取店铺"""
        row = self.db.fetch_one("SELECT * FROM shops WHERE id = ?", (shop_id,))
        if row:
            return self._row_to_shop(row)
        return None
    
    def get_shops_by_owner(self, owner_id: str) -> List[Shop]:
        """获取用户的所有店铺"""
        rows = self.db.fetchall(
            "SELECT * FROM shops WHERE owner_id = ? ORDER BY created_at DESC",
            (owner_id,)
        )
        return [self._row_to_shop(row) for row in rows]
    
    def get_shops_by_platform(self, platform: ShopPlatform) -> List[Shop]:
        """按平台获取店铺"""
        rows = self.db.fetchall(
            "SELECT * FROM shops WHERE platform = ?",
            (platform.value,)
        )
        return [self._row_to_shop(row) for row in rows]
    
    def _row_to_shop(self, row: Dict[str, Any]) -> Shop:
        """数据库行转店铺对象"""
        creds_data = json.loads(row['credentials'] or '{}')
        
        # 获取统计
        stats_row = self.db.fetchone(
            "SELECT * FROM shop_stats WHERE shop_id = ?",
            (row['id'],)
        )
        stats = ShopStats(**stats_row) if stats_row else ShopStats()
        
        return Shop(
            id=row['id'],
            name=row['name'],
            platform=ShopPlatform(row['platform']),
            status=ShopStatus(row['status']),
            shop_id_on_platform=row['shop_id_on_platform'],
            shop_url=row['shop_url'],
            logo_url=row['logo_url'],
            description=row['description'] or "",
            contact_name=row['contact_name'],
            contact_phone=row['contact_phone'],
            contact_email=row['contact_email'],
            main_category=row['main_category'] or "",
            business_license=row['business_license'],
            credentials=ShopCredentials(**creds_data),
            stats=stats,
            auto_sync=bool(row['auto_sync']),
            sync_interval=row['sync_interval'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            owner_id=row['owner_id'],
            last_sync_at=row['last_sync_at'],
        )
    
    def update_shop(self, shop_id: str, updates: Dict[str, Any]) -> bool:
        """更新店铺"""
        shop = self.get_shop(shop_id)
        if not shop:
            return False
        
        for key, value in updates.items():
            if hasattr(shop, key):
                setattr(shop, key, value)
        
        shop.updated_at = datetime.now().isoformat()
        self._save_shop(shop)
        
        return True
    
    def delete_shop(self, shop_id: str) -> bool:
        """删除店铺"""
        self.db.execute("DELETE FROM shop_stats WHERE shop_id = ?", (shop_id,))
        self.db.execute("DELETE FROM shops WHERE id = ?", (shop_id,))
        logger.info(f"Deleted shop: {shop_id}")
        return True
    
    def get_authorization_url(self, platform: ShopPlatform, redirect_uri: str) -> str:
        """获取平台授权URL"""
        config = self.PLATFORM_CONFIG.get(platform, {})
        auth_url = config.get('auth_url', '')
        
        # 构建授权URL（各平台参数不同，这里简化）
        params = {
            'response_type': 'code',
            'redirect_uri': redirect_uri,
            'scope': ','.join(config.get('scopes', [])),
        }
        
        # 实际实现需要根据各平台OAuth文档
        return auth_url
    
    def handle_authorization_callback(
        self,
        platform: ShopPlatform,
        code: str,
        state: str
    ) -> Dict[str, Any]:
        """处理授权回调"""
        # TODO: 实现各平台的token交换
        # 1. 用code换取access_token
        # 2. 获取店铺信息
        # 3. 保存凭证
        
        return {
            'success': True,
            'message': '授权成功',
            'shop_info': {},
        }
    
    def sync_shop_data(self, shop_id: str) -> bool:
        """同步店铺数据"""
        shop = self.get_shop(shop_id)
        if not shop:
            return False
        
        # TODO: 调用各平台API同步数据
        raise NotImplementedError("Stub: 调用各平台API同步数据")
        # 1. 同步商品列表
        # 2. 同步订单数据
        # 3. 同步统计数据
        
        shop.last_sync_at = datetime.now().isoformat()
        self._save_shop(shop)
        
        logger.info(f"Synced shop data: {shop_id}")
        return True
    
    def get_shop_analytics(
        self,
        shop_id: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """获取店铺分析数据"""
        # TODO: 从平台API获取详细分析数据
        
        return {
            'shop_id': shop_id,
            'period': {'start': start_date, 'end': end_date},
            'overview': {
                'total_orders': 0,
                'total_revenue': 0.0,
                'total_visitors': 0,
                'conversion_rate': 0.0,
            },
            'daily_stats': [],
            'top_products': [],
            'traffic_sources': [],
        }
    
    def get_platform_list(self) -> List[Dict[str, Any]]:
        """获取支持的平台列表"""
        return [
            {
                'id': platform.value,
                'name': config['name'],
                'auth_url': config['auth_url'],
            }
            for platform, config in self.PLATFORM_CONFIG.items()
        ]
    
    def batch_sync(self, owner_id: str) -> Dict[str, Any]:
        """批量同步用户所有店铺"""
        shops = self.get_shops_by_owner(owner_id)
        
        results = {
            'total': len(shops),
            'success': 0,
            'failed': 0,
            'details': [],
        }
        
        for shop in shops:
            if shop.auto_sync:
                try:
                    self.sync_shop_data(shop.id)
                    results['success'] += 1
                    results['details'].append({
                        'shop_id': shop.id,
                        'name': shop.name,
                        'status': 'success',
                    })
                except Exception as e:
                    logger.error(f"Unhandled exception: " + str(e))
                    results['failed'] += 1
                    results['details'].append({
                        'shop_id': shop.id,
                        'name': shop.name,
                        'status': 'failed',
                        'error': str(e),
                    })
        
        return results
