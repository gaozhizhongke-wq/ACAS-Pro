#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Customer Logic Tests
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock

from acas_pro.ui.logic.customer_logic import (
    CustomerLogic, Customer, CustomerSegment,
    CustomerStatus, CustomerSource
)


class TestCustomerStatus:
    """Test customer status enum"""
    
    def test_status_values(self):
        """Test status enum values"""
        assert CustomerStatus.ACTIVE.value == "active"
        assert CustomerStatus.VIP.value == "vip"
        assert CustomerStatus.NEW.value == "new"


class TestCustomerSource:
    """Test customer source enum"""
    
    def test_source_values(self):
        """Test source enum values"""
        assert CustomerSource.ORGANIC.value == "organic"
        assert CustomerSource.ADS.value == "ads"
        assert CustomerSource.REFERRAL.value == "referral"


class TestCustomer:
    """Test customer data structure"""
    
    def test_customer_creation(self):
        """Test customer creation"""
        customer = Customer(
            id="cust001",
            name="John Doe",
            email="john@example.com",
            phone="1234567890",
            status=CustomerStatus.NEW,
            source=CustomerSource.ORGANIC
        )
        assert customer.name == "John Doe"
        assert customer.email == "john@example.com"
        assert customer.total_orders == 0
        assert customer.total_spent == 0.0


class TestCustomerLogic:
    """Test customer logic"""
    
    @pytest.fixture
    def logic(self):
        return CustomerLogic()
    
    def test_init(self, logic):
        """Test initialization"""
        assert logic._customers == {}
        assert logic._segments == {}
    
    def test_create_customer(self, logic):
        """Test creating customer"""
        customer = logic.create_customer(
            name="Jane Doe",
            email="jane@example.com",
            phone="0987654321",
            source=CustomerSource.ADS,
            tags=["vip", "newsletter"]
        )
        
        assert customer.name == "Jane Doe"
        assert customer.email == "jane@example.com"
        assert customer.status == CustomerStatus.NEW
        assert len(customer.id) == 8
    
    def test_update_customer(self, logic):
        """Test updating customer"""
        customer = logic.create_customer(
            name="Test", email="test@example.com"
        )
        
        result = logic.update_customer(customer.id, name="Updated Name", phone="12345")
        
        assert result is True
        assert customer.name == "Updated Name"
        assert customer.phone == "12345"
    
    def test_update_nonexistent_customer(self, logic):
        """Test updating nonexistent customer"""
        result = logic.update_customer("nonexistent", name="Test")
        
        assert result is False
    
    def test_get_customer(self, logic):
        """Test getting customer"""
        customer = logic.create_customer(
            name="Test", email="test@example.com"
        )
        
        fetched = logic.get_customer(customer.id)
        
        assert fetched == customer
    
    def test_find_by_email(self, logic):
        """Test finding customer by email"""
        logic.create_customer(name="Test", email="test@example.com")
        
        found = logic.find_by_email("TEST@EXAMPLE.COM")
        
        assert found is not None
        assert found.email == "test@example.com"
    
    def test_find_by_email_not_found(self, logic):
        """Test finding nonexistent email"""
        found = logic.find_by_email("notfound@example.com")
        
        assert found is None
    
    def test_list_customers(self, logic):
        """Test listing customers"""
        logic.create_customer(name="Customer 1", email="c1@example.com")
        logic.create_customer(name="Customer 2", email="c2@example.com")
        
        customers = logic.list_customers()
        
        assert len(customers) == 2
    
    def test_list_customers_by_status(self, logic):
        """Test listing customers by status"""
        c1 = logic.create_customer(name="Active", email="active@example.com")
        c1.status = CustomerStatus.ACTIVE
        c2 = logic.create_customer(name="VIP", email="vip@example.com")
        c2.status = CustomerStatus.VIP
        
        vip_customers = logic.list_customers(status=CustomerStatus.VIP)
        
        assert len(vip_customers) == 1
        assert vip_customers[0].name == "VIP"
    
    def test_list_customers_by_source(self, logic):
        """Test listing customers by source"""
        logic.create_customer(name="Organic", email="o@example.com", source=CustomerSource.ORGANIC)
        logic.create_customer(name="Ads", email="a@example.com", source=CustomerSource.ADS)
        
        organic_customers = logic.list_customers(source=CustomerSource.ORGANIC)
        
        assert len(organic_customers) == 1
        assert organic_customers[0].name == "Organic"
    
    def test_list_customers_by_search(self, logic):
        """Test searching customers"""
        logic.create_customer(name="John Smith", email="john@example.com")
        logic.create_customer(name="Jane Doe", email="jane@example.com")
        
        results = logic.list_customers(search="john")
        
        assert len(results) == 1
        assert results[0].name == "John Smith"
    
    def test_update_purchase_history(self, logic):
        """Test updating purchase history"""
        customer = logic.create_customer(name="Test", email="test@example.com")
        
        result = logic.update_purchase_history(customer.id, amount=150.0)
        
        assert result is True
        assert customer.total_orders == 1
        assert customer.total_spent == 150.0
        assert customer.last_purchase is not None
    
    def test_update_purchase_history_vip_upgrade(self, logic):
        """Test VIP status upgrade"""
        customer = logic.create_customer(name="Test", email="test@example.com")
        
        logic.update_purchase_history(customer.id, amount=15000.0)
        
        assert customer.status == CustomerStatus.VIP
    
    def test_update_purchase_history_active_upgrade(self, logic):
        """Test ACTIVE status upgrade"""
        customer = logic.create_customer(name="Test", email="test@example.com")
        
        logic.update_purchase_history(customer.id, amount=100.0)
        
        assert customer.status == CustomerStatus.ACTIVE
    
    def test_create_segment(self, logic):
        """Test creating segment"""
        segment = logic.create_segment(
            name="VIP Customers",
            criteria={"min_spent": 10000}
        )
        
        assert segment.name == "VIP Customers"
        assert segment.criteria["min_spent"] == 10000
        assert len(segment.id) == 8
    
    def test_get_segment_customers(self, logic):
        """Test getting segment customers"""
        c1 = logic.create_customer(name="VIP1", email="v1@example.com")
        c1.total_spent = 15000
        c2 = logic.create_customer(name="Regular", email="r@example.com")
        c2.total_spent = 100
        
        segment = logic.create_segment(name="Big Spenders", criteria={"min_spent": 10000})
        
        customers = logic.get_segment_customers(segment.id)
        
        assert len(customers) == 1
        assert customers[0].name == "VIP1"
    
    def test_get_segment_customers_by_status(self, logic):
        """Test getting segment customers by status"""
        c1 = logic.create_customer(name="VIP", email="v@example.com")
        c1.status = CustomerStatus.VIP
        c2 = logic.create_customer(name="Active", email="a@example.com")
        c2.status = CustomerStatus.ACTIVE
        
        segment = logic.create_segment(name="VIP Only", criteria={"status": "vip"})
        
        customers = logic.get_segment_customers(segment.id)
        
        assert len(customers) == 1
        assert customers[0].name == "VIP"
    
    def test_get_segment_customers_nonexistent(self, logic):
        """Test getting customers for nonexistent segment"""
        customers = logic.get_segment_customers("nonexistent")
        
        assert customers == []
    
    def test_get_customer_stats_empty(self, logic):
        """Test stats with no customers"""
        stats = logic.get_customer_stats()
        
        assert stats["total"] == 0
        assert stats["avg_order_value"] == 0
        assert stats["vip_count"] == 0
    
    def test_get_customer_stats(self, logic):
        """Test customer stats"""
        c1 = logic.create_customer(name="C1", email="c1@example.com")
        c1.total_spent = 1000
        c1.total_orders = 10
        c1.status = CustomerStatus.VIP
        
        c2 = logic.create_customer(name="C2", email="c2@example.com")
        c2.total_spent = 500
        c2.total_orders = 5
        
        stats = logic.get_customer_stats()
        
        assert stats["total"] == 2
        assert stats["total_revenue"] == 1500
        assert stats["vip_count"] == 1
        assert stats["vip_percentage"] == 50.0
    
    def test_get_churned_customers(self, logic):
        """Test getting churned customers"""
        c1 = logic.create_customer(name="Old", email="old@example.com")
        c1.last_purchase = datetime.now() - timedelta(days=100)
        
        c2 = logic.create_customer(name="Recent", email="recent@example.com")
        c2.last_purchase = datetime.now() - timedelta(days=10)
        
        churned = logic.get_churned_customers(days=90)
        
        assert len(churned) == 1
        assert churned[0].name == "Old"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
