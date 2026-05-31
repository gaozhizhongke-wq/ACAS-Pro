#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Customer Management Business Logic
Extracted from customer pages for testability
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum


class CustomerStatus(Enum):
    """Customer status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    VIP = "vip"
    NEW = "new"
    CHURNED = "churned"


class CustomerSource(Enum):
    """Customer acquisition source"""
    ORGANIC = "organic"
    ADS = "ads"
    REFERRAL = "referral"
    SOCIAL = "social"
    EMAIL = "email"
    DIRECT = "direct"


@dataclass
class Customer:
    """Customer data"""
    id: str
    name: str
    email: str
    phone: str
    status: CustomerStatus
    source: CustomerSource
    tags: List[str] = field(default_factory=list)
    total_orders: int = 0
    total_spent: float = 0.0
    last_purchase: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    notes: str = ""


@dataclass
class CustomerSegment:
    """Customer segment"""
    id: str
    name: str
    criteria: Dict
    customer_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)


class CustomerLogic:
    """Customer management business logic"""
    
    def __init__(self) -> Any:
        self._customers: Dict[str, Customer] = {}
        self._segments: Dict[str, CustomerSegment] = {}
    
    def create_customer(self, name: str, email: str, phone: str = "",
                       source: CustomerSource = CustomerSource.ORGANIC,
                       tags: List[str] = None) -> Customer:
        """Create new customer"""
        import uuid
        
        customer = Customer(
            id=str(uuid.uuid4())[:8],
            name=name,
            email=email,
            phone=phone,
            status=CustomerStatus.NEW,
            source=source,
            tags=tags or [],
            created_at=datetime.now()
        )
        
        self._customers[customer.id] = customer
        return customer
    
    def update_customer(self, customer_id: str, **kwargs) -> bool:
        """Update customer fields"""
        customer = self._customers.get(customer_id)
        if not customer:
            return False
        
        for key, value in kwargs.items():
            if hasattr(customer, key):
                setattr(customer, key, value)
        
        return True
    
    def get_customer(self, customer_id: str) -> Optional[Customer]:
        """Get customer by ID"""
        return self._customers.get(customer_id)
    
    def find_by_email(self, email: str) -> Optional[Customer]:
        """Find customer by email"""
        for customer in self._customers.values():
            if customer.email.lower() == email.lower():
                return customer
        return None
    
    def list_customers(self, status: Optional[CustomerStatus] = None,
                      source: Optional[CustomerSource] = None,
                      search: Optional[str] = None) -> List[Customer]:
        """List customers with filters"""
        customers = list(self._customers.values())
        
        if status:
            customers = [c for c in customers if c.status == status]
        
        if source:
            customers = [c for c in customers if c.source == source]
        
        if search:
            search_lower = search.lower()
            customers = [
                c for c in customers
                if search_lower in c.name.lower() 
                or search_lower in c.email.lower()
            ]
        
        return customers
    
    def update_purchase_history(self, customer_id: str, amount: float) -> bool:
        """Update customer purchase history"""
        customer = self._customers.get(customer_id)
        if not customer:
            return False
        
        customer.total_orders += 1
        customer.total_spent += amount
        customer.last_purchase = datetime.now()
        
        # Auto-update status based on spending
        if customer.total_spent > 10000:
            customer.status = CustomerStatus.VIP
        elif customer.status == CustomerStatus.NEW:
            customer.status = CustomerStatus.ACTIVE
        
        return True
    
    def create_segment(self, name: str, criteria: Dict) -> CustomerSegment:
        """Create customer segment"""
        import uuid
        
        segment = CustomerSegment(
            id=str(uuid.uuid4())[:8],
            name=name,
            criteria=criteria,
            created_at=datetime.now()
        )
        
        self._segments[segment.id] = segment
        return segment
    
    def get_segment_customers(self, segment_id: str) -> List[Customer]:
        """Get customers matching segment criteria"""
        segment = self._segments.get(segment_id)
        if not segment:
            return []
        
        customers = list(self._customers.values())
        criteria = segment.criteria
        
        if "min_spent" in criteria:
            customers = [c for c in customers if c.total_spent >= criteria["min_spent"]]
        
        if "min_orders" in criteria:
            customers = [c for c in customers if c.total_orders >= criteria["min_orders"]]
        
        if "status" in criteria:
            target_status = CustomerStatus(criteria["status"])
            customers = [c for c in customers if c.status == target_status]
        
        return customers
    
    def get_customer_stats(self) -> Dict:
        """Get customer statistics"""
        total = len(self._customers)
        if total == 0:
            return {"total": 0, "avg_order_value": 0, "vip_count": 0}
        
        total_spent = sum(c.total_spent for c in self._customers.values())
        total_orders = sum(c.total_orders for c in self._customers.values())
        vip_count = sum(1 for c in self._customers.values() if c.status == CustomerStatus.VIP)
        
        return {
            "total": total,
            "avg_order_value": total_spent / total_orders if total_orders > 0 else 0,
            "vip_count": vip_count,
            "vip_percentage": (vip_count / total) * 100,
            "total_revenue": total_spent
        }
    
    def get_churned_customers(self, days: int = 90) -> List[Customer]:
        """Get customers who haven't purchased in X days"""
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(days=days)
        
        return [
            c for c in self._customers.values()
            if c.last_purchase and c.last_purchase < cutoff
            and c.status != CustomerStatus.CHURNED
        ]
