"""
电商整合模块 - 店铺/商品/订单/供应链统一管理
"""

from .shop_manager import ShopManager, Shop, ShopPlatform
from .product_manager import ProductManager, Product, ProductCategory
from .order_manager import OrderManager, Order, OrderStatus
from .supply_chain import SupplyChainManager, Supplier, InventorySync

__all__ = [
    'ShopManager',
    'Shop',
    'ShopPlatform',
    'ProductManager',
    'Product',
    'ProductCategory',
    'OrderManager',
    'Order',
    'OrderStatus',
    'SupplyChainManager',
    'Supplier',
    'InventorySync',
]
