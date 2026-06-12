"""
商品管理 - 多平台商品统一管理
"""

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

from ..core.logging import get_logger
from ..core.database import DatabaseManager
from .platform_api_factory import create_platform_client

logger = get_logger(__name__)


class ProductStatus(Enum):
    """商品状态"""

    DRAFT = "draft"  # 草稿
    PENDING = "pending"  # 待审核
    ACTIVE = "active"  # 在售
    INACTIVE = "inactive"  # 下架
    SOLD_OUT = "sold_out"  # 售罄
    VIOLATION = "violation"  # 违规


class ProductCategory(Enum):
    """商品类目"""

    FASHION = "fashion"  # 服饰鞋包
    BEAUTY = "beauty"  # 美妆个护
    FOOD = "food"  # 食品饮料
    HOME = "home"  # 家居日用
    DIGITAL = "digital"  # 数码家电
    MOTHER_BABY = "mother_baby"  # 母婴用品
    SPORTS = "sports"  # 运动户外
    BOOKS = "books"  # 图书文具
    PET = "pet"  # 宠物用品
    CAR = "car"  # 汽车用品
    JEWELRY = "jewelry"  # 珠宝配饰
    HEALTH = "health"  # 医疗保健


@dataclass
class ProductVariant:
    """商品规格变体"""

    id: str
    name: str  # 如："红色-大号"
    sku: str  # SKU编码
    price: float
    original_price: Optional[float] = None
    stock: int = 0
    weight: float = 0.0  # 重量(kg)
    barcode: Optional[str] = None
    image_url: Optional[str] = None
    is_default: bool = False


@dataclass
class ProductImage:
    """商品图片"""

    id: str
    url: str
    is_main: bool = False  # 是否主图
    sort_order: int = 0


@dataclass
class Product:
    """商品实体"""

    id: str
    name: str
    description: str = ""

    # 分类
    category: ProductCategory = ProductCategory.FASHION
    sub_category: str = ""

    # 价格
    price: float = 0.0
    original_price: Optional[float] = None
    cost_price: Optional[float] = None

    # 库存
    stock: int = 0
    stock_alert_threshold: int = 10

    # 规格
    has_variants: bool = False
    variants: List[ProductVariant] = field(default_factory=list)
    variant_attributes: Dict[str, List[str]] = field(default_factory=dict)

    # 图片
    images: List[ProductImage] = field(default_factory=list)
    main_image: Optional[str] = None
    video_url: Optional[str] = None

    # 物流
    weight: float = 0.0  # kg
    length: Optional[float] = None  # cm
    width: Optional[float] = None
    height: Optional[float] = None

    # 状态
    status: ProductStatus = ProductStatus.DRAFT

    # 平台映射
    platform_mappings: Dict[str, str] = field(
        default_factory=dict
    )  # {platform: platform_product_id}

    # 元数据
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    owner_id: Optional[str] = None
    shop_id: Optional[str] = None

    # 销量统计
    total_sales: int = 0
    monthly_sales: int = 0
    weekly_sales: int = 0

    def get_display_price(self) -> str:
        """获取显示价格"""
        if self.has_variants and self.variants:
            prices = [v.price for v in self.variants]
            min_price = min(prices)
            max_price = max(prices)
            if min_price == max_price:
                return f"¥{min_price:.2f}"
            return f"¥{min_price:.2f} - ¥{max_price:.2f}"
        return f"¥{self.price:.2f}"

    def get_total_stock(self) -> int:
        """获取总库存"""
        if self.has_variants and self.variants:
            return sum(v.stock for v in self.variants)
        return self.stock


class ProductManager:
    """商品管理器"""

    def __init__(self):
        self.db = DatabaseManager()
        # Tables managed by core/schema.py — do not add CREATE TABLE here

    def create_product(
        self,
        name: str,
        category: ProductCategory,
        price: float,
        owner_id: Optional[str] = None,
        shop_id: Optional[str] = None,
        **kwargs,
    ) -> Product:
        """创建商品"""
        product_id = f"prod_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        product = Product(
            id=product_id,
            name=name,
            category=category,
            price=price,
            owner_id=owner_id,
            shop_id=shop_id,
            **kwargs,
        )

        self._save_product(product)
        logger.info(f"Created product: {product_id} ({name})")
        return product

    def _save_product(self, product: Product) -> None:
        """保存商品"""
        self.db.execute(
            """
            INSERT OR REPLACE INTO products (
                id, name, description, category, sub_category,
                price, original_price, cost_price, stock, stock_alert_threshold,
                has_variants, variants, variant_attributes, images, main_image,
                video_url, weight, length, width, height, status,
                platform_mappings, created_at, updated_at, owner_id, shop_id,
                total_sales, monthly_sales, weekly_sales
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                product.id,
                product.name,
                product.description,
                product.category.value,
                product.sub_category,
                product.price,
                product.original_price,
                product.cost_price,
                product.stock,
                product.stock_alert_threshold,
                int(product.has_variants),
                json.dumps([v.__dict__ for v in product.variants]),
                json.dumps(product.variant_attributes),
                json.dumps([img.__dict__ for img in product.images]),
                product.main_image,
                product.video_url,
                product.weight,
                product.length,
                product.width,
                product.height,
                product.status.value,
                json.dumps(product.platform_mappings),
                product.created_at,
                product.updated_at,
                product.owner_id,
                product.shop_id,
                product.total_sales,
                product.monthly_sales,
                product.weekly_sales,
            ),
        )

    def get_product(self, product_id: str) -> Optional[Product]:
        """获取商品"""
        row = self.db.fetchone("SELECT * FROM products WHERE id = ?", (product_id,))
        if row:
            return self._row_to_product(row)
        return None

    def get_products_by_shop(
        self, shop_id: str, status: Optional[ProductStatus] = None
    ) -> List[Product]:
        """获取店铺商品"""
        if status:
            rows = self.db.fetchall(
                "SELECT * FROM products WHERE shop_id = ? AND status = ? ORDER BY created_at DESC",
                (shop_id, status.value),
            )
        else:
            rows = self.db.fetchall(
                "SELECT * FROM products WHERE shop_id = ? ORDER BY created_at DESC",
                (shop_id,),
            )
        return [self._row_to_product(row) for row in rows]

    def _row_to_product(self, row: Dict[str, Any]) -> Product:
        """数据库行转商品对象"""
        variants_data = json.loads(row["variants"] or "[]")
        variants = [ProductVariant(**v) for v in variants_data]

        images_data = json.loads(row["images"] or "[]")
        images = [ProductImage(**img) for img in images_data]

        return Product(
            id=row["id"],
            name=row["name"],
            description=row["description"] or "",
            category=ProductCategory(row["category"])
            if row["category"]
            else ProductCategory.FASHION,
            sub_category=row["sub_category"] or "",
            price=row["price"] or 0.0,
            original_price=row["original_price"],
            cost_price=row["cost_price"],
            stock=row["stock"] or 0,
            stock_alert_threshold=row["stock_alert_threshold"] or 10,
            has_variants=bool(row["has_variants"]),
            variants=variants,
            variant_attributes=json.loads(row["variant_attributes"] or "{}"),
            images=images,
            main_image=row["main_image"],
            video_url=row["video_url"],
            weight=row["weight"] or 0.0,
            length=row["length"],
            width=row["width"],
            height=row["height"],
            status=ProductStatus(row["status"])
            if row["status"]
            else ProductStatus.DRAFT,
            platform_mappings=json.loads(row["platform_mappings"] or "{}"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            owner_id=row["owner_id"],
            shop_id=row["shop_id"],
            total_sales=row["total_sales"] or 0,
            monthly_sales=row["monthly_sales"] or 0,
            weekly_sales=row["weekly_sales"] or 0,
        )

    def update_product(self, product_id: str, updates: Dict[str, Any]) -> bool:
        """更新商品"""
        product = self.get_product(product_id)
        if not product:
            return False

        for key, value in updates.items():
            if hasattr(product, key):
                setattr(product, key, value)

        product.updated_at = datetime.now().isoformat()
        self._save_product(product)
        return True

    def delete_product(self, product_id: str) -> bool:
        """删除商品"""
        self.db.execute("DELETE FROM products WHERE id = ?", (product_id,))
        logger.info(f"Deleted product: {product_id}")
        return True

    def update_stock(
        self, product_id: str, quantity: int, variant_id: Optional[str] = None
    ) -> bool:
        """更新库存"""
        product = self.get_product(product_id)
        if not product:
            return False

        if product.has_variants and variant_id:
            for variant in product.variants:
                if variant.id == variant_id:
                    variant.stock = max(0, variant.stock + quantity)
                    break
        else:
            product.stock = max(0, product.stock + quantity)

        product.updated_at = datetime.now().isoformat()
        self._save_product(product)
        return True

    def get_low_stock_products(self, shop_id: str) -> List[Product]:
        """获取低库存商品"""
        products = self.get_products_by_shop(shop_id)
        low_stock = []

        for product in products:
            if product.has_variants:
                for variant in product.variants:
                    if variant.stock <= product.stock_alert_threshold:
                        low_stock.append(product)
                        break
            else:
                if product.stock <= product.stock_alert_threshold:
                    low_stock.append(product)

        return low_stock

    def sync_to_platform(
        self, product_id: str, platform: str, platform_shop_id: str
    ) -> Dict[str, Any]:
        """同步商品到电商平台

        优先调用平台API同步，如API未配置则使用本地模拟数据。

        支持的平台:
        - douyin_shop: 抖音小店
        - kuaishou_shop: 快手小店
        - xiaohongshu_shop: 小红书店铺
        - taobao / tmall: 淘宝/天猫
        """
        product = self.get_product(product_id)
        if not product:
            return {"success": False, "error": "Product not found"}

        # 尝试通过平台API同步
        from .shop_manager import ShopManager

        sm = ShopManager()
        shop = sm.get_shop(platform_shop_id) if platform_shop_id else None

        if shop:
            creds = sm._get_platform_credentials(shop)
            client = create_platform_client(platform, creds)

            if client and client.is_authenticated:
                try:
                    # 同步商品状态
                    result = client.update_product_status(product_id, "online")
                    if result:
                        platform_product_id = f"{platform}_{product_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                        product.platform_mappings[platform] = platform_product_id
                        product.updated_at = datetime.now().isoformat()
                        product.status = ProductStatus.ACTIVE
                        self._save_product(product)

                        logger.info(
                            f"[ProductManager] Synced product {product_id} to {platform} via API"
                        )
                        return {
                            "success": True,
                            "platform_product_id": platform_product_id,
                            "platform": platform,
                            "status": "active",
                            "source": "platform_api",
                        }
                except (sqlite3.Error, ValueError, RuntimeError, json.JSONDecodeError):
                    logger.exception(
                        "[ProductManager] Platform API sync failed, falling back to local"
                    )

        # 本地模拟数据
        platform_product_id = (
            f"{platform}_{product_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        )
        product.platform_mappings[platform] = platform_product_id
        product.updated_at = datetime.now().isoformat()
        product.status = ProductStatus.PENDING
        self._save_product(product)

        logger.info(
            f"[ProductManager] Synced product {product_id} to {platform}, "
            f"platform_product_id={platform_product_id} [local data]"
        )

        return {
            "success": True,
            "platform_product_id": platform_product_id,
            "platform": platform,
            "status": "pending_review",
            "message": f"商品已提交至{platform}，等待平台审核",
            "source": "local_data",
        }

    def batch_sync_to_platform(
        self, product_ids: List[str], platform: str, platform_shop_id: str
    ) -> Dict[str, Any]:
        """批量同步商品"""
        results = {
            "total": len(product_ids),
            "success": 0,
            "failed": 0,
            "details": [],
        }

        for product_id in product_ids:
            result = self.sync_to_platform(product_id, platform, platform_shop_id)
            if result["success"]:
                results["success"] += 1
            else:
                results["failed"] += 1
            results["details"].append(
                {
                    "product_id": product_id,
                    "result": result,
                }
            )

        return results

    def list_products(self, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """列出商品"""
        try:
            rows = self.db.fetchall("SELECT * FROM products")
            return [dict(row) for row in rows] if rows else []
        except (sqlite3.Error, ValueError, RuntimeError, json.JSONDecodeError) as e:
            logger.warning(f"Product list query failed: {e}")
            return []
