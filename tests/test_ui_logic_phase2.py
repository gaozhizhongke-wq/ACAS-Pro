#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Phase 2 UI Logic Tests
Customer, Campaign, Report modules
"""

import pytest
from datetime import datetime, timedelta

from acas_pro.ui.logic import (
    CustomerLogic, Customer, CustomerStatus, CustomerSource, CustomerSegment,
    CampaignLogic, Campaign, CampaignStatus, CampaignType,
    ReportLogic, Report, ReportType, ReportFormat
)


class TestCustomerLogic:
    """Customer logic tests"""
    
    @pytest.fixture
    def customers(self):
        return CustomerLogic()
    
    def test_create_customer(self, customers):
        """Test customer creation"""
        customer = customers.create_customer(
            name="John Doe",
            email="john@example.com",
            phone="1234567890",
            source=CustomerSource.ORGANIC,
            tags=["vip", "referral"]
        )
        
        assert customer.name == "John Doe"
        assert customer.email == "john@example.com"
        assert customer.status == CustomerStatus.NEW
        assert len(customer.tags) == 2
    
    def test_find_by_email(self, customers):
        """Test find by email"""
        customers.create_customer("Test", "test@example.com")
        
        found = customers.find_by_email("test@example.com")
        
        assert found is not None
        assert found.name == "Test"
    
    def test_update_purchase_history_vip(self, customers):
        """Test VIP status upgrade"""
        customer = customers.create_customer("Big Spender", "big@example.com")
        
        customers.update_purchase_history(customer.id, 15000)
        
        assert customer.status == CustomerStatus.VIP
        assert customer.total_spent == 15000
    
    def test_list_by_status(self, customers):
        """Test filter by status"""
        c1 = customers.create_customer("Active", "a@example.com")
        customers.update_purchase_history(c1.id, 100)
        
        customers.create_customer("New", "n@example.com")
        
        active = customers.list_customers(status=CustomerStatus.ACTIVE)
        
        assert len(active) == 1
    
    def test_create_segment(self, customers):
        """Test segment creation"""
        segment = customers.create_segment(
            name="High Value",
            criteria={"min_spent": 1000}
        )
        
        assert segment.name == "High Value"
        assert segment.criteria["min_spent"] == 1000
    
    def test_get_customer_stats(self, customers):
        """Test stats calculation"""
        c1 = customers.create_customer("C1", "c1@example.com")
        customers.update_purchase_history(c1.id, 500)
        
        c2 = customers.create_customer("C2", "c2@example.com")
        customers.update_purchase_history(c2.id, 15000)  # VIP threshold is 10000
        
        stats = customers.get_customer_stats()
        
        assert stats["total"] == 2
        assert stats["vip_count"] == 1  # Only c2 is VIP
    
    def test_get_churned_customers(self, customers):
        """Test churn detection"""
        customer = customers.create_customer("Old", "old@example.com")
        customer.last_purchase = datetime.now() - timedelta(days=100)
        
        churned = customers.get_churned_customers(days=90)
        
        assert len(churned) == 1


class TestCampaignLogic:
    """Campaign logic tests"""
    
    @pytest.fixture
    def campaigns(self):
        return CampaignLogic()
    
    def test_create_campaign(self, campaigns):
        """Test campaign creation"""
        campaign = campaigns.create_campaign(
            name="Summer Sale",
            campaign_type=CampaignType.EMAIL,
            subject="50% Off Everything!",
            content="<h1>Sale!</h1>",
            target_audience={"segment": "all"}
        )
        
        assert campaign.name == "Summer Sale"
        assert campaign.type == CampaignType.EMAIL
        assert campaign.status == CampaignStatus.DRAFT
    
    def test_schedule_campaign(self, campaigns):
        """Test scheduling"""
        campaign = campaigns.create_campaign(
            "Test", CampaignType.SMS, "Hi", "Hello", {}
        )
        
        schedule_time = datetime.now() + timedelta(days=1)
        result = campaigns.schedule_campaign(campaign.id, schedule_time)
        
        assert result is True
        assert campaign.status == CampaignStatus.SCHEDULED
    
    def test_launch_campaign(self, campaigns):
        """Test launch"""
        campaign = campaigns.create_campaign(
            "Test", CampaignType.SMS, "Hi", "Hello", {}
        )
        
        result = campaigns.launch_campaign(campaign.id)
        
        assert result is True
        assert campaign.status == CampaignStatus.RUNNING
        assert campaign.started_at is not None
    
    def test_pause_resume_campaign(self, campaigns):
        """Test pause and resume"""
        campaign = campaigns.create_campaign(
            "Test", CampaignType.SMS, "Hi", "Hello", {}
        )
        campaigns.launch_campaign(campaign.id)
        
        campaigns.pause_campaign(campaign.id)
        assert campaign.status == CampaignStatus.PAUSED
        
        campaigns.resume_campaign(campaign.id)
        assert campaign.status == CampaignStatus.RUNNING
    
    def test_update_stats(self, campaigns):
        """Test stats update"""
        campaign = campaigns.create_campaign(
            "Test", CampaignType.EMAIL, "Hi", "Hello", {}
        )
        
        campaigns.update_stats(campaign.id, sent=1000, opened=300, clicked=50)
        
        assert campaign.sent_count == 1000
        assert campaign.open_count == 300
        assert campaign.click_count == 50
    
    def test_get_performance_metrics(self, campaigns):
        """Test metrics calculation"""
        campaign = campaigns.create_campaign(
            "Test", CampaignType.EMAIL, "Hi", "Hello", {}
        )
        campaigns.update_stats(campaign.id, sent=1000, opened=300, clicked=50)
        
        metrics = campaigns.get_performance_metrics(campaign.id)
        
        assert metrics["open_rate"] == 30.0
        assert metrics["click_rate"] == 5.0
        assert abs(metrics["ctr"] - 16.67) < 0.1  # 50/300 * 100
    
    def test_duplicate_campaign(self, campaigns):
        """Test duplication"""
        original = campaigns.create_campaign(
            "Original", CampaignType.EMAIL, "Subject", "Content", {"seg": "vip"}
        )
        
        copy = campaigns.duplicate_campaign(original.id)
        
        assert copy is not None
        assert copy.name == "Original (Copy)"
        assert copy.type == original.type


class TestReportLogic:
    """Report logic tests"""
    
    @pytest.fixture
    def reports(self):
        return ReportLogic()
    
    def test_generate_sales_report(self, reports):
        """Test sales report"""
        start = datetime.now() - timedelta(days=30)
        end = datetime.now()
        
        report = reports.generate_sales_report(start, end, "Monthly Sales")
        
        assert report.type == ReportType.SALES
        assert report.name == "Monthly Sales"
        assert "total_revenue" in report.data
    
    def test_generate_customer_report(self, reports):
        """Test customer report"""
        report = reports.generate_customer_report(segment="VIP")
        
        assert report.type == ReportType.CUSTOMER
        assert report.parameters["segment"] == "VIP"
        assert "total_customers" in report.data
    
    def test_generate_campaign_report(self, reports):
        """Test campaign report"""
        report = reports.generate_campaign_report()
        
        assert report.type == ReportType.CAMPAIGN
        assert "total_campaigns" in report.data
    
    def test_export_report(self, reports):
        """Test export"""
        start = datetime.now() - timedelta(days=7)
        end = datetime.now()
        report = reports.generate_sales_report(start, end)
        
        path = reports.export_report(report.id, ReportFormat.CSV)
        
        assert path is not None
        assert path.endswith(".csv")
    
    def test_list_by_type(self, reports):
        """Test filter by type"""
        reports.generate_sales_report(datetime.now(), datetime.now())
        reports.generate_customer_report()
        
        sales_reports = reports.list_reports(report_type=ReportType.SALES)
        
        assert len(sales_reports) == 1
    
    def test_delete_report(self, reports):
        """Test deletion"""
        report = reports.generate_sales_report(datetime.now(), datetime.now())
        
        result = reports.delete_report(report.id)
        
        assert result is True
        assert reports.get_report(report.id) is None
    
    def test_get_report_summary(self, reports):
        """Test summary"""
        reports.generate_sales_report(datetime.now(), datetime.now())
        reports.generate_customer_report()
        reports.generate_campaign_report()
        
        summary = reports.get_report_summary()
        
        assert summary["total"] == 3
        assert summary["by_type"]["sales"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
