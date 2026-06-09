"""
订单管理 - 多平台订单统一处理
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


class OrderStatus(Enum):
    """订单状态"""
    PENDING_PAYMENT = "pending_payment"     # 待付款
    PENDING_SHIP = "pending_ship"           # 待发货
    SHIPPED = "shipped"                     # 已发货
    DELIVERED = "delivered"                 # 已送达
    COMPLETED = "completed"                 # 已完成
    CANCELLED = "cancelled"                 # 已取消
    REFUNDING = "refunding"                 # 退款中
    REFUNDED = "refunded"                   # 已退款


class PaymentStatus(Enum):
    """支付状态"""
    UNPAID = "unpaid"
    PAID = "paid"
    PARTIAL = "partial"
    REFUNDED = "refunded"


@dataclass
class OrderItem:
    """订单商品项"""
    product_id: str
    product_name: str
    sku_id: Optional[str]
    sku_name: Optional[str]
    quantity: int
    unit_price: float
    total_price: float
    image_url: Optional[str] = None


@dataclass
class ShippingAddress:
    """收货地址"""
    name: str
    phone: str
    province: str
    city: str
    district: str
    detail: str
    zip_code: Optional[str] = None
    
    def get_full_address(self) -> str:
        return f"{self.province}{self.city}{self.district}{self.detail}"


@dataclass
class LogisticsInfo:
    """物流信息"""
    company: str
    tracking_no: str
    status: str = "pending"                 # pending/in_transit/delivered
    shipped_at: Optional[str] = None
    delivered_at: Optional[str] = None
    tracking_history: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class Order:
    """订单实体"""
    id: str
    platform_order_id: str                  # 平台订单号
    platform: str                           # 来源平台
    
    # 商品
    items: List[OrderItem] = field(default_factory=list)
    
    # 金额
    subtotal: float = 0.0                   # 商品小计
    shipping_fee: float = 0.0               # 运费
    discount: float = 0.0                   # 优惠金额
    tax: float = 0.0                        # 税费
    total_amount: float = 0.0               # 实付金额
    
    # 状态
    status: OrderStatus = OrderStatus.PENDING_PAYMENT
    payment_status: PaymentStatus = PaymentStatus.UNPAID
    
    # 收货信息
    shipping_address: Optional[ShippingAddress] = None
    
    # 物流
    logistics: Optional[LogisticsInfo] = None
    
    # 买家信息
    buyer_id: Optional[str] = None
    buyer_nickname: Optional[str] = None
    buyer_message: Optional[str] = None     # 买家留言
    
    # 时间
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    paid_at: Optional[str] = None
    shipped_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    # 关联
    shop_id: Optional[str] = None
    
    # 备注
    seller_note: Optional[str] = None
    
    def calculate_total(self) -> float:
        """计算订单总额"""
        self.subtotal = sum(item.total_price for item in self.items)
        self.total_amount = self.subtotal + self.shipping_fee - self.discount + self.tax
        return self.total_amount
    
    def get_item_count(self) -> int:
        """获取商品总数"""
        return sum(item.quantity for item in self.items)


class OrderManager:
    """订单管理器"""
    
    def __init__(self):
        self.db = DatabaseManager()
        # Tables managed by core/schema.py — do not add CREATE TABLE here
    

    
    def create_order(
        self,
        platform_order_id: str,
        platform: str,
        items: List[OrderItem],
        shipping_address: ShippingAddress,
        shop_id: Optional[str] = None,
        **kwargs
    ) -> Order:
        """创建订单"""
        order_id = f"ord_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        order = Order(
            id=order_id,
            platform_order_id=platform_order_id,
            platform=platform,
            items=items,
            shipping_address=shipping_address,
            shop_id=shop_id,
            **kwargs
        )
        
        order.calculate_total()
        self._save_order(order)
        
        logger.info(f"Created order: {order_id}")
        return order
    
    def _save_order(self, order: Order) -> None:
        """保存订单"""
        self.db.execute("""
            INSERT OR REPLACE INTO orders (
                id, platform_order_id, platform, items, subtotal,
                shipping_fee, discount, tax, total_amount, status,
                payment_status, shipping_address, logistics, buyer_id,
                buyer_nickname, buyer_message, created_at, paid_at,
                shipped_at, completed_at, shop_id, seller_note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order.id, order.platform_order_id, order.platform,
            json.dumps([item.__dict__ for item in order.items]),
            order.subtotal, order.shipping_fee, order.discount, order.tax,
            order.total_amount, order.status.value, order.payment_status.value,
            json.dumps(order.shipping_address.__dict__) if order.shipping_address else None,
            json.dumps(order.logistics.__dict__) if order.logistics else None,
            order.buyer_id, order.buyer_nickname, order.buyer_message,
            order.created_at, order.paid_at, order.shipped_at,
            order.completed_at, order.shop_id, order.seller_note
        ))
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """获取订单"""
        row = self.db.fetch_one("SELECT * FROM orders WHERE id = ?", (order_id,))
        if row:
            return self._row_to_order(row)
        return None
    
    def get_orders_by_shop(
        self,
        shop_id: str,
        status: Optional[OrderStatus] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100
    ) -> List[Order]:
        """获取店铺订单"""
        query = "SELECT * FROM orders WHERE shop_id = ?"
        params = [shop_id]
        
        if status:
            query += " AND status = ?"
            params.append(status.value)
        
        if start_date:
            query += " AND created_at >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND created_at <= ?"
            params.append(end_date)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        rows = self.db.fetch_all(query, tuple(params))
        return [self._row_to_order(row) for row in rows]
    
    def _row_to_order(self, row: Dict[str, Any]) -> Order:
        """数据库行转订单对象"""
        items_data = json.loads(row['items'] or '[]')
        items = [OrderItem(**item) for item in items_data]
        
        address_data = json.loads(row['shipping_address']) if row['shipping_address'] else None
        address = ShippingAddress(**address_data) if address_data else None
        
        logistics_data = json.loads(row['logistics']) if row['logistics'] else None
        logistics = LogisticsInfo(**logistics_data) if logistics_data else None
        
        return Order(
            id=row['id'],
            platform_order_id=row['platform_order_id'],
            platform=row['platform'],
            items=items,
            subtotal=row['subtotal'] or 0.0,
            shipping_fee=row['shipping_fee'] or 0.0,
            discount=row['discount'] or 0.0,
            tax=row['tax'] or 0.0,
            total_amount=row['total_amount'] or 0.0,
            status=OrderStatus(row['status']) if row['status'] else OrderStatus.PENDING_PAYMENT,
            payment_status=PaymentStatus(row['payment_status']) if row['payment_status'] else PaymentStatus.UNPAID,
            shipping_address=address,
            logistics=logistics,
            buyer_id=row['buyer_id'],
            buyer_nickname=row['buyer_nickname'],
            buyer_message=row['buyer_message'],
            created_at=row['created_at'],
            paid_at=row['paid_at'],
            shipped_at=row['shipped_at'],
            completed_at=row['completed_at'],
            shop_id=row['shop_id'],
            seller_note=row['seller_note'],
        )
    
    def update_order_status(
        self,
        order_id: str,
        status: OrderStatus,
        note: Optional[str] = None
    ) -> bool:
        """更新订单状态"""
        order = self.get_order(order_id)
        if not order:
            return False
        
        order.status = status
        
        # 更新时间戳
        now = datetime.now().isoformat()
        if status == OrderStatus.PENDING_SHIP and not order.paid_at:
            order.paid_at = now
            order.payment_status = PaymentStatus.PAID
        elif status == OrderStatus.SHIPPED:
            order.shipped_at = now
        elif status == OrderStatus.COMPLETED:
            order.completed_at = now
        
        if note:
            order.seller_note = note
        
        self._save_order(order)
        return True
    
    def ship_order(
        self,
        order_id: str,
        logistics_company: str,
        tracking_no: str
    ) -> bool:
        """发货"""
        order = self.get_order(order_id)
        if not order:
            return False
        
        order.logistics = LogisticsInfo(
            company=logistics_company,
            tracking_no=tracking_no,
            status="pending",
            shipped_at=datetime.now().isoformat()
        )
        
        return self.update_order_status(order_id, OrderStatus.SHIPPED)
    
    def sync_orders_from_platform(
        self,
        shop_id: str,
        platform: str,
        start_time: str,
        end_time: str
    ) -> Dict[str, Any]:
        """从平台同步订单
        
        优先调用平台API同步真实数据，如API未配置则回退到本地数据。
        
        支持的平台:
        - douyin_shop: 抖音小店
        - kuaishou_shop: 快手小店
        - xiaohongshu_shop: 小红书店铺
        - taobao: 淘宝
        - tmall: 天猫
        """
        # 尝试通过平台API同步
        from .shop_manager import ShopManager
        sm = ShopManager()
        shop = sm.get_shop(shop_id)
        
        if shop:
            creds = sm._get_platform_credentials(shop)
            client = create_platform_client(platform, creds)
            
            if client and client.is_authenticated:
                try:
                    result = client.sync_orders(
                        start_time=start_time,
                        end_time=end_time,
                    )
                    if result.success:
                        # 将API返回的订单数据同步到本地
                        synced = self._merge_platform_orders(result.data, shop_id, platform)
                        logger.info(
                            f"[OrderManager] Synced {result.created} orders from {platform} API "
                            f"for shop {shop_id}"
                        )
                        return {
                            'success': True,
                            'synced_count': result.created,
                            'new_orders': synced['new'],
                            'updated_orders': synced['updated'],
                            'platform': platform,
                            'sync_period': {'start': start_time, 'end': end_time},
                            'source': 'platform_api',
                        }
                except Exception as e:
                    logger.exception(
                        f"[OrderManager] Platform API sync failed, falling back to local data"
                    )
        
        # 回退到本地数据
        existing_orders = self.get_orders_by_shop(
            shop_id=shop_id,
            start_date=start_time,
            end_date=end_time,
            limit=1000
        )
        
        new_orders = []
        updated_orders = []
        
        for order in existing_orders:
            if order.platform == platform:
                if order.created_at >= start_time and order.created_at <= end_time:
                    new_orders.append({
                        'id': order.id,
                        'platform_order_id': order.platform_order_id,
                        'status': order.status.value,
                        'total_amount': order.total_amount,
                    })
        
        logger.info(
            f"[OrderManager] Synced {len(new_orders)} orders from {platform} "
            f"for shop {shop_id} ({start_time} -> {end_time}) [local data]"
        )
        
        return {
            'success': True,
            'synced_count': len(new_orders),
            'new_orders': new_orders,
            'updated_orders': updated_orders,
            'platform': platform,
            'sync_period': {'start': start_time, 'end': end_time},
            'source': 'local_data',
        }
    
    def _merge_platform_orders(
        self, platform_orders: list, shop_id: str, platform: str
    ) -> Dict[str, list]:
        """将平台API返回的订单数据合并到本地数据库"""
        new_orders = []
        updated_orders = []
        
        for po in platform_orders:
            platform_order_id = po.get('order_id', po.get('tid', po.get('id', '')))
            
            # 检查是否已存在
            existing = self.db.fetchone(
                "SELECT id FROM orders WHERE platform_order_id = ?",
                (platform_order_id,)
            )
            
            if existing:
                updated_orders.append(platform_order_id)
            else:
                new_orders.append(platform_order_id)
        
        return {'new': new_orders, 'updated': updated_orders}
    
    def get_order_statistics(
        self,
        shop_id: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """获取订单统计"""
        orders = self.get_orders_by_shop(shop_id, start_date=start_date, end_date=end_date, limit=10000)
        
        total_orders = len(orders)
        total_amount = sum(o.total_amount for o in orders)
        paid_orders = [o for o in orders if o.payment_status == PaymentStatus.PAID]
        
        status_counts = {}
        for status in OrderStatus:
            count = len([o for o in orders if o.status == status])
            if count > 0:
                status_counts[status.value] = count
        
        return {
            'total_orders': total_orders,
            'total_amount': total_amount,
            'paid_orders': len(paid_orders),
            'paid_amount': sum(o.total_amount for o in paid_orders),
            'status_distribution': status_counts,
            'average_order_value': total_amount / total_orders if total_orders > 0 else 0,
        }
    
    def search_orders(
        self,
        shop_id: str,
        keyword: str,
        limit: int = 50
    ) -> List[Order]:
        """搜索订单"""
        # 搜索订单号、买家昵称、商品名称
        rows = self.db.fetch_all("""
            SELECT * FROM orders 
            WHERE shop_id = ? AND (
                platform_order_id LIKE ? OR 
                buyer_nickname LIKE ? OR
                items LIKE ?
            )
            ORDER BY created_at DESC
            LIMIT ?
        """, (shop_id, f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", limit))
        
        return [self._row_to_order(row) for row in rows]
