#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Inventory Business Logic
Extracted from InventoryPage for testability
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from datetime import datetime


@dataclass
class InventoryItem:
    """Inventory item data"""
    product_id: str
    product_name: str
    current_stock: int
    recommended_order: int
    urgency: str  # critical, high, medium, low
    days_until_stockout: int
    reorder_point: int
    confidence: float


@dataclass
class InventoryAlert:
    """Inventory alert"""
    level: str  # critical, warning, info
    message: str
    affected_products: List[str]
    timestamp: datetime


class InventoryLogic:
    """Inventory optimization business logic"""
    
    URGENCY_COLORS = {
        "critical": "#f85149",
        "high": "#d29922",
        "medium": "#58a6ff",
        "low": "#3fb950",
    }
    
    def __init__(self, optimizer_service=None) -> Any:
        self.optimizer = optimizer_service
        self._items: List[InventoryItem] = []
        self._alerts: List[InventoryAlert] = []
    
    def analyze_inventory(self, products: Optional[List[dict]] = None) -> List[InventoryItem]:
        """Analyze inventory and generate recommendations"""
        if products is None:
            products = self._fetch_default_products()
        
        items = []
        for product in products:
            item = self._analyze_product(product)
            items.append(item)
        
        # Sort by urgency
        urgency_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        items.sort(key=lambda x: urgency_order.get(x.urgency, 4))
        
        self._items = items
        self._generate_alerts()
        return items
    
    def get_alerts(self) -> List[InventoryAlert]:
        """Get current inventory alerts"""
        return self._alerts
    
    def get_critical_count(self) -> int:
        """Get count of critical items"""
        return sum(1 for item in self._items if item.urgency == "critical")
    
    def get_reorder_summary(self) -> Dict:
        """Get summary of reorder recommendations"""
        total_items = len(self._items)
        critical = sum(1 for i in self._items if i.urgency == "critical")
        high = sum(1 for i in self._items if i.urgency == "high")
        total_order_value = sum(
            i.recommended_order * 100 for i in self._items if i.recommended_order > 0
        )
        
        return {
            "total_items": total_items,
            "critical_count": critical,
            "high_count": high,
            "total_order_value": total_order_value,
            "needs_attention": critical + high > 0,
        }
    
    def export_recommendations(self) -> List[Dict]:
        """Export recommendations as dict list"""
        return [
            {
                "product_id": item.product_id,
                "product_name": item.product_name,
                "current_stock": item.current_stock,
                "recommended_order": item.recommended_order,
                "urgency": item.urgency,
                "days_until_stockout": item.days_until_stockout,
            }
            for item in self._items
        ]
    
    def _analyze_product(self, product: dict) -> InventoryItem:
        """Analyze single product"""
        stock = product.get("current_stock", 0)
        daily_sales = product.get("avg_daily_sales", 1)
        lead_time = product.get("lead_time_days", 7)
        
        # Calculate days until stockout
        days_until_stockout = int(stock / daily_sales) if daily_sales > 0 else 999
        
        # Calculate reorder point
        reorder_point = int(daily_sales * lead_time * 1.5)
        
        # Determine urgency
        if days_until_stockout <= 3:
            urgency = "critical"
        elif days_until_stockout <= 7:
            urgency = "high"
        elif days_until_stockout <= 14:
            urgency = "medium"
        else:
            urgency = "low"
        
        # Calculate recommended order
        recommended_order = 0
        if stock < reorder_point:
            recommended_order = int(daily_sales * 30)  # 30 days supply
        
        return InventoryItem(
            product_id=product.get("id", ""),
            product_name=product.get("name", ""),
            current_stock=stock,
            recommended_order=recommended_order,
            urgency=urgency,
            days_until_stockout=days_until_stockout,
            reorder_point=reorder_point,
            confidence=product.get("confidence", 0.85),
        )
    
    def _generate_alerts(self) -> Any:
        """Generate alerts from items"""
        self._alerts = []
        
        critical_items = [i for i in self._items if i.urgency == "critical"]
        if critical_items:
            self._alerts.append(InventoryAlert(
                level="critical",
                message=f"{len(critical_items)} 个产品库存严重不足",
                affected_products=[i.product_id for i in critical_items],
                timestamp=datetime.now(),
            ))
    
    def _fetch_default_products(self) -> List[dict]:
        """Fetch default/mock product data"""
        return [
            {"id": "SKU-001", "name": "Product A", "current_stock": 5, "avg_daily_sales": 2, "lead_time_days": 7},
            {"id": "SKU-002", "name": "Product B", "current_stock": 50, "avg_daily_sales": 5, "lead_time_days": 5},
            {"id": "SKU-003", "name": "Product C", "current_stock": 200, "avg_daily_sales": 10, "lead_time_days": 3},
        ]
