#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Product Management Business Logic
Extracted from product pages for testability
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum


class ProductStatus(Enum):
    """Product status"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"
    OUT_OF_STOCK = "out_of_stock"
    DISCONTINUED = "discontinued"


@dataclass
class Product:
    """Product data"""

    id: str
    name: str
    description: str
    price: float
    cost: float
    stock_quantity: int
    status: ProductStatus
    category: str
    tags: List[str]
    created_at: datetime
    updated_at: datetime


class ProductLogic:
    """Product management business logic"""

    def __init__(self) -> None:
        self._products: Dict[str, Product] = {}

    def create_product(
        self,
        name: str,
        description: str,
        price: float,
        cost: float = 0.0,
        stock: int = 0,
        category: str = "",
        tags: List[str] = None,
    ) -> Product:
        """Create new product"""
        import uuid

        now = datetime.now()
        product = Product(
            id=str(uuid.uuid4())[:8],
            name=name,
            description=description,
            price=price,
            cost=cost,
            stock_quantity=stock,
            status=ProductStatus.ACTIVE if stock > 0 else ProductStatus.OUT_OF_STOCK,
            category=category,
            tags=tags or [],
            created_at=now,
            updated_at=now,
        )

        self._products[product.id] = product
        return product

    def update_product(self, product_id: str, **kwargs) -> bool:
        """Update product fields"""
        product = self._products.get(product_id)
        if not product:
            return False

        for key, value in kwargs.items():
            if hasattr(product, key):
                setattr(product, key, value)

        product.updated_at = datetime.now()
        return True

    def get_product(self, product_id: str) -> Optional[Product]:
        """Get product by ID"""
        return self._products.get(product_id)

    def list_products(
        self,
        category: Optional[str] = None,
        status: Optional[ProductStatus] = None,
        search: Optional[str] = None,
    ) -> List[Product]:
        """List products with filters"""
        products = list(self._products.values())

        if category:
            products = [p for p in products if p.category == category]

        if status:
            products = [p for p in products if p.status == status]

        if search:
            search_lower = search.lower()
            products = [
                p
                for p in products
                if search_lower in p.name.lower()
                or search_lower in p.description.lower()
            ]

        return products

    def update_stock(self, product_id: str, quantity: int) -> bool:
        """Update product stock"""
        product = self._products.get(product_id)
        if not product:
            return False

        product.stock_quantity = quantity

        # Auto-update status based on stock
        if quantity <= 0:
            product.status = ProductStatus.OUT_OF_STOCK
        elif product.status == ProductStatus.OUT_OF_STOCK:
            product.status = ProductStatus.ACTIVE

        product.updated_at = datetime.now()
        return True

    def calculate_profit_margin(self, product_id: str) -> float:
        """Calculate profit margin percentage"""
        product = self._products.get(product_id)
        if not product or product.price == 0:
            return 0.0

        return ((product.price - product.cost) / product.price) * 100

    def get_low_stock_products(self, threshold: int = 10) -> List[Product]:
        """Get products with low stock"""
        return [
            p
            for p in self._products.values()
            if p.stock_quantity <= threshold and p.status != ProductStatus.DISCONTINUED
        ]

    def get_category_summary(self) -> Dict[str, int]:
        """Get product count by category"""
        summary = {}
        for product in self._products.values():
            summary[product.category] = summary.get(product.category, 0) + 1
        return summary
