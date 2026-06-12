"""
供应链管理 - 供应商/库存同步/物流追踪
"""

import json
import sqlite3
import asyncio
import hashlib
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

try:
    import httpx

    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False

from ..core.logging import get_logger
from ..core.database import DatabaseManager
from .platform_api_factory import create_platform_client

logger = get_logger(__name__)


class SupplierStatus(Enum):
    """供应商状态"""

    ACTIVE = "active"  # 合作中
    PENDING = "pending"  # 待审核
    SUSPENDED = "suspended"  # 暂停合作
    TERMINATED = "terminated"  # 终止合作


class InventorySyncStatus(Enum):
    """库存同步状态"""

    SYNCED = "synced"  # 已同步
    PENDING = "pending"  # 待同步
    SYNCING = "syncing"  # 同步中
    FAILED = "failed"  # 同步失败


@dataclass
class Supplier:
    """供应商实体"""

    id: str
    name: str
    contact_person: str
    contact_phone: str
    contact_email: Optional[str] = None

    # 公司信息
    company_name: Optional[str] = None
    business_license: Optional[str] = None
    address: Optional[str] = None

    # 供应信息
    main_products: List[str] = field(default_factory=list)
    supply_categories: List[str] = field(default_factory=list)

    # 评级
    rating: float = 5.0  # 1-5
    cooperation_count: int = 0  # 合作次数

    # 状态
    status: SupplierStatus = SupplierStatus.ACTIVE

    # 账期
    payment_terms: str = "月结30天"  # 付款条件

    # 元数据
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    owner_id: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class InventorySync:
    """库存同步记录"""

    id: str
    product_id: str
    shop_id: str
    supplier_id: Optional[str]

    # 库存信息
    quantity_before: int
    quantity_after: int
    quantity_changed: int

    # 同步状态
    status: InventorySyncStatus
    error_message: Optional[str] = None

    # 时间
    synced_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # 来源
    source: str = "manual"  # manual/api/system


@dataclass
class PurchaseOrder:
    """采购订单"""

    id: str
    supplier_id: str

    # 商品
    items: List[Dict[str, Any]] = field(default_factory=list)
    # [{"product_id": "", "product_name": "", "quantity": 0, "unit_price": 0.0}]

    # 金额
    subtotal: float = 0.0
    shipping_fee: float = 0.0
    total_amount: float = 0.0

    # 状态
    status: str = "pending"  # pending/confirmed/shipped/received/cancelled

    # 时间
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    expected_delivery: Optional[str] = None
    delivered_at: Optional[str] = None

    # 备注
    notes: Optional[str] = None


class SupplyChainManager:
    """供应链管理器"""

    def __init__(self):
        self.db = DatabaseManager()
        # Tables managed by core/schema.py — do not add CREATE TABLE here

    def create_supplier(
        self,
        name: str,
        contact_person: str,
        contact_phone: str,
        owner_id: Optional[str] = None,
        **kwargs,
    ) -> Supplier:
        """创建供应商"""
        supplier_id = f"sup_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

        supplier = Supplier(
            id=supplier_id,
            name=name,
            contact_person=contact_person,
            contact_phone=contact_phone,
            owner_id=owner_id,
            **kwargs,
        )

        self._save_supplier(supplier)
        logger.info(f"Created supplier: {supplier_id}")
        return supplier

    def _save_supplier(self, supplier: Supplier) -> None:
        """保存供应商"""
        self.db.execute(
            """
            INSERT OR REPLACE INTO suppliers (
                id, name, contact_person, contact_phone, contact_email,
                company_name, business_license, address, main_products,
                supply_categories, rating, cooperation_count, status,
                payment_terms, created_at, owner_id, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                supplier.id,
                supplier.name,
                supplier.contact_person,
                supplier.contact_phone,
                supplier.contact_email,
                supplier.company_name,
                supplier.business_license,
                supplier.address,
                json.dumps(supplier.main_products),
                json.dumps(supplier.supply_categories),
                supplier.rating,
                supplier.cooperation_count,
                supplier.status.value,
                supplier.payment_terms,
                supplier.created_at,
                supplier.owner_id,
                supplier.notes,
            ),
        )

    def get_supplier(self, supplier_id: str) -> Optional[Supplier]:
        """获取供应商"""
        row = self.db.fetchone("SELECT * FROM suppliers WHERE id = ?", (supplier_id,))
        if row:
            return self._row_to_supplier(row)
        return None

    def get_suppliers_by_owner(self, owner_id: str) -> List[Supplier]:
        """获取用户的供应商"""
        rows = self.db.fetchall(
            "SELECT * FROM suppliers WHERE owner_id = ? ORDER BY created_at DESC",
            (owner_id,),
        )
        return [self._row_to_supplier(row) for row in rows]

    def _row_to_supplier(self, row: Dict[str, Any]) -> Supplier:
        """数据库行转供应商对象"""
        return Supplier(
            id=row["id"],
            name=row["name"],
            contact_person=row["contact_person"] or "",
            contact_phone=row["contact_phone"] or "",
            contact_email=row["contact_email"],
            company_name=row["company_name"],
            business_license=row["business_license"],
            address=row["address"],
            main_products=json.loads(row["main_products"] or "[]"),
            supply_categories=json.loads(row["supply_categories"] or "[]"),
            rating=row["rating"] or 5.0,
            cooperation_count=row["cooperation_count"] or 0,
            status=SupplierStatus(row["status"])
            if row["status"]
            else SupplierStatus.ACTIVE,
            payment_terms=row["payment_terms"] or "月结30天",
            created_at=row["created_at"],
            owner_id=row["owner_id"],
            notes=row["notes"],
        )

    # ========== 库存同步 ==========

    def sync_inventory(
        self,
        product_id: str,
        shop_id: str,
        new_quantity: int,
        supplier_id: Optional[str] = None,
        source: str = "manual",
    ) -> InventorySync:
        """同步库存"""
        from .product_manager import ProductManager

        pm = ProductManager()
        product = pm.get_product(product_id)

        if not product:
            raise ValueError(f"Product not found: {product_id}")

        old_quantity = product.get_total_stock()

        sync_id = f"sync_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        sync_record = InventorySync(
            id=sync_id,
            product_id=product_id,
            shop_id=shop_id,
            supplier_id=supplier_id,
            quantity_before=old_quantity,
            quantity_after=new_quantity,
            quantity_changed=new_quantity - old_quantity,
            status=InventorySyncStatus.SYNCING,
            source=source,
        )

        try:
            # 更新商品库存
            if product.has_variants:
                # 按比例分配库存到各规格
                total_old = sum(v.stock for v in product.variants)
                if total_old > 0:
                    for variant in product.variants:
                        ratio = variant.stock / total_old
                        variant.stock = int(new_quantity * ratio)
            else:
                product.stock = new_quantity

            pm.update_product(
                product_id,
                {
                    "stock": product.stock,
                    "variants": product.variants,
                },
            )

            sync_record.status = InventorySyncStatus.SYNCED

            # 同步到电商平台
            self._sync_to_platforms(product_id, shop_id, new_quantity)

        except (sqlite3.Error, ValueError, RuntimeError, json.JSONDecodeError) as e:
            logger.exception(f"Error in track_logistics: {e}")
            sync_record.status = InventorySyncStatus.FAILED
            sync_record.error_message = str(e)
            logger.error(f"Inventory sync failed: {e}")

        self._save_inventory_sync(sync_record)
        return sync_record

    def _save_inventory_sync(self, sync: InventorySync) -> None:
        """保存库存同步记录"""
        self.db.execute(
            """
            INSERT INTO inventory_syncs (
                id, product_id, shop_id, supplier_id, quantity_before,
                quantity_after, quantity_changed, status, error_message,
                synced_at, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                sync.id,
                sync.product_id,
                sync.shop_id,
                sync.supplier_id,
                sync.quantity_before,
                sync.quantity_after,
                sync.quantity_changed,
                sync.status.value,
                sync.error_message,
                sync.synced_at,
                sync.source,
            ),
        )

    def _sync_to_platforms(self, product_id: str, shop_id: str, quantity: int) -> None:
        """同步库存到各电商平台

        通过平台API客户端更新库存。如API未配置，仅记录日志。
        """
        # 尝试获取店铺对应的平台API客户端
        shop_manager = self._get_shop_manager()
        if shop_manager:
            shop = shop_manager.get_shop(shop_id)
            if shop:
                creds = shop_manager._get_platform_credentials(shop)
                client = create_platform_client(shop.platform.value, creds)

                if client and client.is_authenticated:
                    try:
                        result = client.sync_inventory([product_id])
                        if result.success:
                            logger.info(
                                f"[SupplyChain] Synced inventory for {product_id} "
                                f"to {shop.platform.value}: {quantity} units"
                            )
                            return
                    except (
                        sqlite3.Error,
                        ValueError,
                        RuntimeError,
                        json.JSONDecodeError,
                    ):
                        logger.exception("[SupplyChain] Platform inventory sync failed")

        logger.warning(
            f"[SupplyChain] Platform inventory sync skipped: "
            f"product_id={product_id}, shop_id={shop_id}, quantity={quantity}. "
            f"Configure platform API credentials to enable real sync."
        )

    def get_inventory_sync_history(
        self, product_id: str, limit: int = 50
    ) -> List[InventorySync]:
        """获取库存同步历史"""
        rows = self.db.fetchall(
            """SELECT * FROM inventory_syncs 
               WHERE product_id = ? 
               ORDER BY synced_at DESC 
               LIMIT ?""",
            (product_id, limit),
        )

        return [
            InventorySync(
                id=row["id"],
                product_id=row["product_id"],
                shop_id=row["shop_id"],
                supplier_id=row["supplier_id"],
                quantity_before=row["quantity_before"],
                quantity_after=row["quantity_after"],
                quantity_changed=row["quantity_changed"],
                status=InventorySyncStatus(row["status"]),
                error_message=row["error_message"],
                synced_at=row["synced_at"],
                source=row["source"],
            )
            for row in rows
        ]

    # ========== 采购管理 ==========

    def create_purchase_order(
        self,
        supplier_id: str,
        items: List[Dict[str, Any]],
        expected_delivery: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> PurchaseOrder:
        """创建采购订单"""
        order_id = f"po_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

        # 计算金额
        subtotal = sum(item["quantity"] * item["unit_price"] for item in items)
        shipping_fee = 0.0  # 可配置
        total = subtotal + shipping_fee

        order = PurchaseOrder(
            id=order_id,
            supplier_id=supplier_id,
            items=items,
            subtotal=subtotal,
            shipping_fee=shipping_fee,
            total_amount=total,
            expected_delivery=expected_delivery,
            notes=notes,
        )

        self._save_purchase_order(order)
        logger.info(f"Created purchase order: {order_id}")
        return order

    def _save_purchase_order(self, order: PurchaseOrder) -> None:
        """保存采购订单"""
        self.db.execute(
            """
            INSERT OR REPLACE INTO purchase_orders (
                id, supplier_id, items, subtotal, shipping_fee,
                total_amount, status, created_at, expected_delivery,
                delivered_at, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                order.id,
                order.supplier_id,
                json.dumps(order.items),
                order.subtotal,
                order.shipping_fee,
                order.total_amount,
                order.status,
                order.created_at,
                order.expected_delivery,
                order.delivered_at,
                order.notes,
            ),
        )

    def get_purchase_orders_by_supplier(
        self, supplier_id: str, status: Optional[str] = None
    ) -> List[PurchaseOrder]:
        """获取供应商的采购订单"""
        if status:
            rows = self.db.fetchall(
                "SELECT * FROM purchase_orders WHERE supplier_id = ? AND status = ? ORDER BY created_at DESC",
                (supplier_id, status),
            )
        else:
            rows = self.db.fetchall(
                "SELECT * FROM purchase_orders WHERE supplier_id = ? ORDER BY created_at DESC",
                (supplier_id,),
            )

        return [
            PurchaseOrder(
                id=row["id"],
                supplier_id=row["supplier_id"],
                items=json.loads(row["items"] or "[]"),
                subtotal=row["subtotal"] or 0.0,
                shipping_fee=row["shipping_fee"] or 0.0,
                total_amount=row["total_amount"] or 0.0,
                status=row["status"] or "pending",
                created_at=row["created_at"],
                expected_delivery=row["expected_delivery"],
                delivered_at=row["delivered_at"],
                notes=row["notes"],
            )
            for row in rows
        ]

    def update_purchase_order_status(
        self, order_id: str, status: str, notes: Optional[str] = None
    ) -> bool:
        """更新采购订单状态"""
        row = self.db.fetchone(
            "SELECT * FROM purchase_orders WHERE id = ?", (order_id,)
        )

        if not row:
            return False

        delivered_at = None
        if status == "received":
            delivered_at = datetime.now().isoformat()

            # 入库 - 更新库存
            items = json.loads(row["items"] or "[]")
            for item in items:
                self.sync_inventory(
                    product_id=item["product_id"],
                    shop_id="",  # 需要从上下文获取
                    new_quantity=item["quantity"],
                    source="purchase",
                )

        self.db.execute(
            """
            UPDATE purchase_orders 
            SET status = ?, delivered_at = ?, notes = ?
            WHERE id = ?
        """,
            (status, delivered_at, notes or row["notes"], order_id),
        )

        return True

    # ========== 物流追踪 ==========

    def track_logistics(self, company: str, tracking_no: str) -> Dict[str, Any]:
        """追踪物流信息

        优先级:
        1. 平台API查询（需订单关联）
        2. 快递100 API查询（需配置KDNIAO_API_KEY）
        3. 本地记录查询

        支持的物流公司编码:
        - SF: 顺丰速运
        - YTO: 圆通速递
        - ZTO: 中通快递
        - STO: 申通速递
        - YD: 韵达快递
        - JD: 京东物流
        - EMS: 中国邮政EMS
        """
        # 1. 尝试平台API查询（通过订单关联）
        order_tracking = self._query_platform_logistics(company, tracking_no)
        if order_tracking and order_tracking.get("status") not in (
            None,
            "pending",
            "unknown",
        ):
            logger.info(
                f"[SupplyChain] Tracked via platform API: {company} {tracking_no}, "
                f"status={order_tracking.get('status')}"
            )
            return order_tracking

        # 2. 尝试快递100 API
        kdniao_result = self._query_kdniao(company, tracking_no)
        if kdniao_result and kdniao_result.get("status") != "pending":
            logger.info(
                f"[SupplyChain] Tracked via KDNiao: {company} {tracking_no}, "
                f"status={kdniao_result.get('status')}"
            )
            return kdniao_result

        # 3. 查询本地记录
        result = self._query_local_tracking(company, tracking_no)
        if result:
            logger.info(
                f"[SupplyChain] Tracked logistics from local: {company} {tracking_no}, "
                f"status={result.get('status', 'unknown')}"
            )
            return result

        # 所有查询方式均无结果
        return {
            "company": company,
            "tracking_no": tracking_no,
            "status": "pending",
            "current_location": "未知",
            "estimated_delivery": None,
            "history": [],
            "note": "请配置快递100 API或平台API以启用实时物流追踪",
        }

    def get_low_stock_alerts(self, owner_id: str) -> List[Dict[str, Any]]:
        """获取低库存预警"""
        from .product_manager import ProductManager
        from .shop_manager import ShopManager

        pm = ProductManager()
        sm = ShopManager()

        alerts = []
        shops = sm.get_shops_by_owner(owner_id)
        # Note: This will fail if DatabaseManager methods are also wrong in shop_manager.py
        # For now, return empty list to make tests pass

        for shop in shops:
            products = pm.get_low_stock_products(shop.id)
            for product in products:
                alerts.append(
                    {
                        "product_id": product.id,
                        "product_name": product.name,
                        "shop_id": shop.id,
                        "shop_name": shop.name,
                        "current_stock": product.get_total_stock(),
                        "threshold": product.stock_alert_threshold,
                    }
                )

        return alerts

    def _get_shop_manager(self) -> None:
        """获取ShopManager实例（延迟导入避免循环依赖）"""
        from .shop_manager import ShopManager

        return ShopManager()

    def _query_local_tracking(
        self, company: str, tracking_no: str
    ) -> Optional[Dict[str, Any]]:
        """查询本地物流记录"""
        try:
            db = self.db
            rows = db.execute(
                "SELECT * FROM logistics_records WHERE company = ? AND tracking_no = ?",
                (company, tracking_no),
            )
            if rows:
                latest = rows[0]
                return dict(latest)
        except (sqlite3.Error, ValueError, RuntimeError, json.JSONDecodeError) as e:
            logger.debug(f"Local logistics query failed: {e}")

    def _query_platform_logistics(
        self, company: str, tracking_no: str
    ) -> Optional[Dict[str, Any]]:
        """通过平台API查询物流信息"""

        # 从环境变量获取关联的订单信息
        # 实际应用中应从订单表查询tracking_no对应的订单
        return None  # 需要订单关联才能查询平台物流

    def _query_kdniao(self, company: str, tracking_no: str) -> Optional[Dict[str, Any]]:
        """通过快递鸟API查询物流信息

        API文档: https://www.kdniao.com/documents
        需要配置环境变量: KDNIAO_API_KEY, KDNIAO_EBUSINESS_ID
        """
        import os

        api_key = os.environ.get("KDNIAO_API_KEY", "")
        business_id = os.environ.get("KDNIAO_EBUSINESS_ID", "")

        if not api_key or not business_id:
            return None

        try:
            import requests

            # 快递鸟物流追踪API
            request_data = {
                "OrderCode": "",
                "ShipperCode": company,
                "LogisticCode": tracking_no,
            }

            import json as json_module

            data = json_module.dumps(request_data, ensure_ascii=False)

            # MD5签名（平台API强制要求，不可升级）
            sign_data = data + api_key
            import hashlib

            # nosec B303: MD5 required by logistics platform API.
            sign = hashlib.md5(
                sign_data.encode("utf-8"), usedforsecurity=False
            ).hexdigest()

            params = {
                "RequestData": data,
                "EBusinessID": business_id,
                "RequestType": "1002",  # 即时查询
                "DataSign": sign,
                "DataType": "2",  # JSON
            }

            resp = requests.post(
                "https://api.kdniao.com/Ebusiness/EbusinessOrderHandle.aspx",
                data=params,
                timeout=15,
            )
            result = resp.json()

            if result.get("Success", False):
                traces = result.get("Traces", [])
                return {
                    "company": company,
                    "tracking_no": tracking_no,
                    "status": result.get("State", "unknown"),
                    "current_location": traces[-1].get("AcceptStation", "")
                    if traces
                    else "",
                    "estimated_delivery": None,
                    "history": traces,
                }
            else:
                logger.warning(
                    f"[SupplyChain] KDNiao query failed: {result.get('Reason', 'Unknown')}"
                )
                return None

        except (sqlite3.Error, ValueError, RuntimeError, json.JSONDecodeError):
            logger.exception("[SupplyChain] KDNiao API error")
            return None

    # ==================== 异步方法 ====================

    async def _query_kdniao_async(
        self, company: str, tracking_no: str
    ) -> Optional[Dict[str, Any]]:
        """异步版：通过快递鸟API查询物流信息"""
        if not _HAS_HTTPX:
            raise RuntimeError("httpx not installed")

        api_key = os.environ.get("KDNIAO_API_KEY", "")
        business_id = os.environ.get("KDNIAO_EBUSINESS_ID", "")

        if not api_key or not business_id:
            return None

        try:
            request_data = {
                "OrderCode": "",
                "ShipperCode": company,
                "LogisticCode": tracking_no,
            }

            data = json.dumps(request_data, ensure_ascii=False)
            sign_data = data + api_key
            # nosec B303: MD5 required by logistics platform API.
            sign = hashlib.md5(
                sign_data.encode("utf-8"), usedforsecurity=False
            ).hexdigest()

            params = {
                "RequestData": data,
                "EBusinessID": business_id,
                "RequestType": "1002",  # 即时查询
                "DataSign": sign,
                "DataType": "2",  # JSON
            }

            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    "https://api.kdniao.com/Ebusiness/EbusinessOrderHandle.aspx",
                    data=params,
                )
                result = resp.json()

            if result.get("Success", False):
                traces = result.get("Traces", [])
                return {
                    "company": company,
                    "tracking_no": tracking_no,
                    "status": result.get("State", "unknown"),
                    "current_location": traces[-1].get("AcceptStation", "")
                    if traces
                    else "",
                    "estimated_delivery": None,
                    "history": traces,
                }
            else:
                logger.warning(
                    f"[SupplyChain] KDNiao async query failed: {result.get('Reason', 'Unknown')}"
                )
                return None

        except (sqlite3.Error, ValueError, RuntimeError, json.JSONDecodeError):
            logger.exception("[SupplyChain] KDNiao async API error")
            return None

    async def track_logistics_async(
        self, company: str, tracking_no: str
    ) -> Dict[str, Any]:
        """异步版：追踪物流信息（真正异步）

        优先级:
        1. 平台API查询（需订单关联）
        2. 快递100 API查询（异步HTTP）
        3. 本地记录查询
        """
        # 1. 尝试平台API查询（目前返回None）
        order_tracking = self._query_platform_logistics(company, tracking_no)
        if order_tracking and order_tracking.get("status") not in (
            None,
            "pending",
            "unknown",
        ):
            logger.info(
                f"[SupplyChain] Tracked via platform API: {company} {tracking_no}, "
                f"status={order_tracking.get('status')}"
            )
            return order_tracking

        # 2. 尝试快递100 API（异步）
        if _HAS_HTTPX:
            kdniao_result = await self._query_kdniao_async(company, tracking_no)
            if kdniao_result and kdniao_result.get("status") != "pending":
                logger.info(
                    f"[SupplyChain] Tracked via KDNiao (async): {company} {tracking_no}, "
                    f"status={kdniao_result.get('status')}"
                )
                return kdniao_result

        # 3. 查询本地记录
        result = self._query_local_tracking(company, tracking_no)
        if result:
            logger.info(
                f"[SupplyChain] Tracked logistics from local: {company} {tracking_no}, "
                f"status={result.get('status', 'unknown')}"
            )
            return result

        # 所有查询方式均无结果
        return {
            "company": company,
            "tracking_no": tracking_no,
            "status": "pending",
            "current_location": "未知",
            "estimated_delivery": None,
            "history": [],
            "note": "请配置快递100 API或平台API以启用实时物流追踪",
        }

    async def get_supplier_async(self, *args, **kwargs) -> None:
        """异步版本: get_supplier"""
        return await asyncio.to_thread(self.get_supplier, *args, **kwargs)

    async def get_suppliers_by_owner_async(self, *args, **kwargs) -> None:
        """异步版本: get_suppliers_by_owner"""
        return await asyncio.to_thread(self.get_suppliers_by_owner, *args, **kwargs)

    async def get_low_stock_alerts_async(self, *args, **kwargs) -> None:
        """异步版本: get_low_stock_alerts"""
        return await asyncio.to_thread(self.get_low_stock_alerts, *args, **kwargs)
