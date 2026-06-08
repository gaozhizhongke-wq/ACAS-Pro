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
from .platform_api_factory import create_platform_client, PlatformCredentials

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

    def _get_db(self) -> None:
        """获取数据库连接（兼容方法）"""
        return self.db
        self._init_database()
    
    def _init_database(self) -> None:
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
    
    def _save_shop(self, shop: Shop) -> None:
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
            json.dumps(shop.credentials.__dict__) if hasattr(shop.credentials, '__dict__') else shop.credentials,
            int(shop.auto_sync), shop.sync_interval,
            shop.created_at, shop.updated_at, shop.owner_id, shop.last_sync_at
        ))
    
    def _init_shop_stats(self, shop_id: str) -> None:
        """初始化店铺统计"""
        self.db.execute("""
            INSERT OR IGNORE INTO shop_stats (
                shop_id, updated_at
            ) VALUES (?, ?)
        """, (shop_id, datetime.now().isoformat()))
    
    def get_shop(self, shop_id: str) -> Optional[Shop]:
        """获取店铺"""
        row = self.db.fetchone("SELECT * FROM shops WHERE id = ?", (shop_id,))
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
        try:
            creds_raw = row.get('credentials')
            if creds_raw is None:
                creds_data = {}
            elif isinstance(creds_raw, str):
                creds_data = json.loads(creds_raw) if creds_raw else {}
            elif isinstance(creds_raw, dict):
                creds_data = creds_raw
            else:
                creds_data = {}
        except (json.JSONDecodeError, TypeError):
            creds_data = {}
        
        # 获取统计 (过滤出 ShopStats 字段)
        stats_row = self.db.fetchone(
            "SELECT * FROM shop_stats WHERE shop_id = ?",
            (row['id'],)
        )
        if stats_row:
            # 只取 ShopStats dataclass 有的字段
            import inspect
            stats_fields = {f.name for f in __import__('dataclasses', fromlist=['fields']).fields(ShopStats)}
            filtered = {k: v for k, v in stats_row.items() if k in stats_fields}
            stats = ShopStats(**filtered)
        else:
            stats = ShopStats()
        
        # 解析 platform 和 status 枚举
        try:
            platform = ShopPlatform(row['platform'])
        except (ValueError, TypeError):
            platform = ShopPlatform.DOUYIN_SHOP  # 默认值
        
        try:
            status = ShopStatus(row['status'])
        except (ValueError, TypeError):
            status = ShopStatus.ACTIVE  # 默认值
        
        return Shop(
            id=row['id'],
            name=row['name'],
            platform=platform,
            status=status,
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
        """处理授权回调
        
        各平台OAuth流程:
        - 抖音小店: https://openapi-fxg.jinritemai.com/auth/inner/token
        - 快手小店: https://v2.kwaixiaodian.com/oauth/refreshToken
        - 小红书: https://ark.xiaohongshu.com/api/auth/token
        - 拼多多: https://gw-api.pinduoduo.com/api/router
        """
        platform_config = self.PLATFORM_CONFIG.get(platform)
        if not platform_config:
            return {
                'success': False,
                'error': f'Unsupported platform: {platform.value}',
            }
        
        # 尝试通过API客户端换取token
        creds = PlatformCredentials()
        client = create_platform_client(platform.value, creds)
        
        if client:
            # 需要先配置app_key/app_secret才能换取token
            if not client.is_configured:
                logger.warning(
                    f"[ShopManager] Platform {platform.value} API not configured. "
                    f"Set app_key/app_secret in shop credentials."
                )
                return {
                    'success': False,
                    'error': f'Platform {platform.value} API credentials not configured',
                    'required': ['app_key', 'app_secret'],
                    'auth_url': platform_config.get('auth_url', ''),
                }
            
            # 用授权码换取token
            token_result = client.exchange_token(code)
            if 'error' in token_result:
                logger.error(f"[ShopManager] Token exchange failed: {token_result['error']}")
                return {
                    'success': False,
                    'error': f'Token exchange failed: {token_result["error"]}',
                }
            
            # 创建或更新店铺
            shop_id = f"shop_{platform.value}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            logger.info(
                f"[ShopManager] OAuth success for {platform.value}, shop_id={shop_id}"
            )
            return {
                'success': True,
                'shop_id': shop_id,
                'platform': platform.value,
                'token_data': token_result,
            }
        
        # 不支持API的平台（如拼多多、京东等），返回手动配置引导
        shop_id = f"shop_{platform.value}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        return {
            'success': True,
            'message': f'请手动配置{platform_config["name"]}API凭证',
            'shop_id': shop_id,
            'platform': platform.value,
            'auth_url': platform_config.get('auth_url', ''),
            'requires_manual_config': True,
        }
    
    def sync_shop_data(self, shop_id: str) -> bool:
        """同步店铺数据
        
        同步内容包括:
        1. 商品列表 (product listing)
        2. 订单数据 (order data) 
        3. 店铺统计 (shop statistics)
        
        优先调用平台API同步，如API未配置则回退到本地数据。
        """
        shop = self.get_shop(shop_id)
        if not shop:
            return False
        
        # 尝试通过API客户端同步
        creds = self._get_platform_credentials(shop)
        client = create_platform_client(shop.platform.value, creds)
        
        if client and client.is_authenticated:
            try:
                # 同步商品
                product_result = client.sync_products()
                if product_result.success:
                    logger.info(
                        f"[ShopManager] Synced {product_result.created} products "
                        f"from {shop.platform.value}"
                    )
                
                # 同步订单
                order_result = client.sync_orders()
                if order_result.success:
                    logger.info(
                        f"[ShopManager] Synced {order_result.created} orders "
                        f"from {shop.platform.value}"
                    )
                
                # 同步库存
                inventory_result = client.sync_inventory()
                if inventory_result.success:
                    logger.info(
                        f"[ShopManager] Synced {inventory_result.total} inventory "
                        f"from {shop.platform.value}"
                    )
            except Exception as e:
                logger.exception(
                    f"[ShopManager] Platform API sync failed, falling back to local data"
                )
        elif client and client.is_configured:
            logger.warning(
                f"[ShopManager] Platform {shop.platform.value} configured but not authenticated. "
                f"Complete OAuth to enable API sync."
            )
        else:
            logger.info(
                f"[ShopManager] No API client for {shop.platform.value}, using local data"
            )
        
        # 更新同步时间戳
        shop.last_sync_at = datetime.now().isoformat()
        self._save_shop(shop)
        
        # 更新统计数据
        self._refresh_shop_stats(shop_id)
        
        logger.info(f"[ShopManager] Synced shop data: {shop_id}")
        return True
    
    def get_shop_analytics(
        self,
        shop_id: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """获取店铺分析数据
        
        数据来源:
        1. 本地订单数据库 (订单数、收入)
        2. 平台API (访客数、转化率、流量来源)
        
        当前版本基于本地数据，平台API数据需要授权后获取。
        """
        shop = self.get_shop(shop_id)
        if not shop:
            return {
                'shop_id': shop_id,
                'error': 'Shop not found',
                'period': {'start': start_date, 'end': end_date},
            }
        
        # 从订单表获取统计
        from .order_manager import OrderManager, OrderStatus, PaymentStatus
        order_mgr = OrderManager()
        orders = order_mgr.get_orders_by_shop(
            shop_id=shop_id,
            start_date=start_date,
            end_date=end_date,
            limit=10000
        )
        
        paid_orders = [o for o in orders if o.payment_status == PaymentStatus.PAID]
        total_revenue = sum(o.total_amount for o in paid_orders)
        
        # 按日分组
        daily_stats = {}
        for order in orders:
            day = order.created_at[:10]  # YYYY-MM-DD
            if day not in daily_stats:
                daily_stats[day] = {'date': day, 'orders': 0, 'revenue': 0.0}
            daily_stats[day]['orders'] += 1
            if order.payment_status == PaymentStatus.PAID:
                daily_stats[day]['revenue'] += order.total_amount
        
        return {
            'shop_id': shop_id,
            'shop_name': shop.name,
            'platform': shop.platform.value,
            'period': {'start': start_date, 'end': end_date},
            'overview': {
                'total_orders': len(orders),
                'total_revenue': total_revenue,
                'total_visitors': 0,  # 需要平台API
                'conversion_rate': 0.0,  # 需要平台API
            },
            'daily_stats': sorted(daily_stats.values(), key=lambda x: x['date']),
            'top_products': [],  # 需要商品分析
            'traffic_sources': [],  # 需要平台API
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
                    logger.exception(f"Error in batch_sync: {e}")
                    results['failed'] += 1
                    results['details'].append({
                        'shop_id': shop.id,
                        'name': shop.name,
                        'status': 'failed',
                        'error': str(e),
                    })
        
        return results
    
    def _get_platform_credentials(self, shop) -> PlatformCredentials:
        """从店铺数据中提取平台API凭证"""
        creds_data = {}
        if shop.credentials:
            try:
                if hasattr(shop.credentials, 'to_dict'):
                    creds_data = shop.credentials.to_dict()
                elif hasattr(shop.credentials, '__dict__'):
                    creds_data = vars(shop.credentials)
                elif isinstance(shop.credentials, str):
                    creds_data = json.loads(shop.credentials)
                elif isinstance(shop.credentials, dict):
                    creds_data = shop.credentials
            except (json.JSONDecodeError, TypeError):
                creds_data = {}
        
        return PlatformCredentials(
            app_key=creds_data.get('app_key', ''),
            app_secret=creds_data.get('app_secret', ''),
            access_token=creds_data.get('access_token', ''),
            refresh_token=creds_data.get('refresh_token', ''),
            token_expires_at=creds_data.get('token_expires_at', ''),
            shop_id=shop.shop_id_on_platform or '',
        )

    def _refresh_shop_stats(self, shop_id: str) -> None:
        """更新店铺统计数据"""
        try:
            db = self._get_db()
            # 统计订单数和收入
            stats = db.fetchone(
                """SELECT COUNT(*) as order_count, COALESCE(SUM(total_amount), 0) as revenue
                   FROM orders WHERE shop_id = ?""",
                (shop_id,)
            )
            if stats:
                db.execute(
                    """UPDATE shops SET order_count = ?, total_revenue = ?, updated_at = ?
                       WHERE id = ?""",
                    (stats['order_count'], stats['revenue'], datetime.now().isoformat(), shop_id)
                )
        except Exception as e:
            logger.debug(f"Shop stats refresh failed for shop {shop_id}: {e}")
        """保存店铺对象到数据库"""
        try:
            db = self._get_db()
            db.execute(
                """UPDATE shops SET name = ?, platform = ?, status = ?,
                   shop_id_on_platform = ?, credentials = ?, last_sync_at = ?,
                   updated_at = ? WHERE id = ?""",
                (
                    shop.name, shop.platform.value, shop.status.value,
                    shop.shop_id_on_platform,
                    json.dumps(shop.credentials.__dict__) if hasattr(shop.credentials, '__dict__') else shop.credentials,
                    shop.last_sync_at, datetime.now().isoformat(), shop.id
                )
            )
            return True
        except Exception as e:
            logger.warning(f"Shop save failed: {e}")
            return False
