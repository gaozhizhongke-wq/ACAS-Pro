#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Order Management Business Logic
Extracted from order pages for testability
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum


class OrderStatus(Enum):
    """Order status"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentStatus(Enum):
    """Payment status"""
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


@dataclass
class OrderItem:
    """Order line item"""
    product_id: str
    product_name: str
    quantity: int
    unit_price: float
    total_price: float


@dataclass
class Order:
    """Order data"""
    id: str
    customer_id: str
    customer_name: str
    items: List[OrderItem]
    status: OrderStatus
    payment_status: PaymentStatus
    total_amount: float
    shipping_address: str
    created_at: datetime
    updated_at: datetime
    notes: str = ""


class OrderLogic:
    """Order management business logic"""
    
    def __init__(self):
        self._orders: Dict[str, Order] = {}
    
    def create_order(self, customer_id: str, customer_name: str,
                    items: List[Dict], shipping_address: str) -> Order:
        """Create new order"""
        import uuid
        
        order_items = []
        total = 0.0
        
        for item in items:
            unit_price = item.get("unit_price", 0.0)
            quantity = item.get("quantity", 1)
            total_price = unit_price * quantity
            
            order_items.append(OrderItem(
                product_id=item.get("product_id", ""),
                product_name=item.get("product_name", ""),
                quantity=quantity,
                unit_price=unit_price,
                total_price=total_price
            ))
            total += total_price
        
        now = datetime.now()
        order = Order(
            id=str(uuid.uuid4())[:8],
            customer_id=customer_id,
            customer_name=customer_name,
            items=order_items,
            status=OrderStatus.PENDING,
            payment_status=PaymentStatus.PENDING,
            total_amount=total,
            shipping_address=shipping_address,
            created_at=now,
            updated_at=now
        )
        
        self._orders[order.id] = order
        return order
    
    def update_status(self, order_id: str, status: OrderStatus) -> bool:
        """Update order status"""
        order = self._orders.get(order_id)
        if not order:
            return False
        
        order.status = status
        order.updated_at = datetime.now()
        return True
    
    def update_payment(self, order_id: str, status: PaymentStatus) -> bool:
        """Update payment status"""
        order = self._orders.get(order_id)
        if not order:
            return False
        
        order.payment_status = status
        order.updated_at = datetime.now()
        return True
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        return self._orders.get(order_id)
    
    def list_orders(self, status: Optional[OrderStatus] = None,
                   customer_id: Optional[str] = None) -> List[Order]:
        """List orders with optional filters"""
        orders = list(self._orders.values())
        
        if status:
            orders = [o for o in orders if o.status == status]
        
        if customer_id:
            orders = [o for o in orders if o.customer_id == customer_id]
        
        # Sort by created_at desc
        orders.sort(key=lambda o: o.created_at, reverse=True)
        return orders
    
    def calculate_revenue(self, start_date: datetime, end_date: datetime) -> Dict:
        """Calculate revenue statistics"""
        orders = [
            o for o in self._orders.values()
            if start_date <= o.created_at <= end_date
            and o.payment_status == PaymentStatus.PAID
        ]
        
        total_revenue = sum(o.total_amount for o in orders)
        order_count = len(orders)
        
        return {
            "total_revenue": total_revenue,
            "order_count": order_count,
            "average_order_value": total_revenue / order_count if order_count > 0 else 0,
        }
    
    def get_status_summary(self) -> Dict[str, int]:
        """Get order count by status"""
        summary = {status.value: 0 for status in OrderStatus}
        for order in self._orders.values():
            summary[order.status.value] += 1
        return summary
