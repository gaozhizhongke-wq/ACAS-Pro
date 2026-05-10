#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Report Generation Business Logic
Extracted from report pages for testability
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import json


class ReportType(Enum):
    """Report type"""
    SALES = "sales"
    CUSTOMER = "customer"
    CAMPAIGN = "campaign"
    INVENTORY = "inventory"
    FINANCIAL = "financial"


class ReportFormat(Enum):
    """Report export format"""
    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"
    JSON = "json"


@dataclass
class Report:
    """Report data"""
    id: str
    name: str
    type: ReportType
    format: ReportFormat
    data: Dict[str, Any] = field(default_factory=dict)
    parameters: Dict = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.now)
    file_path: Optional[str] = None


class ReportLogic:
    """Report generation business logic"""
    
    def __init__(self):
        self._reports: Dict[str, Report] = {}
    
    def generate_sales_report(self, start_date: datetime, end_date: datetime,
                             name: str = "Sales Report") -> Report:
        """Generate sales report"""
        import uuid
        
        # Mock sales data
        data = {
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "total_revenue": 150000.00,
            "total_orders": 450,
            "average_order_value": 333.33,
            "top_products": [
                {"name": "Product A", "revenue": 50000},
                {"name": "Product B", "revenue": 35000},
            ],
            "daily_sales": [
                {"date": (start_date + timedelta(days=i)).isoformat(), "amount": 5000 + i * 100}
                for i in range((end_date - start_date).days + 1)
            ]
        }
        
        report = Report(
            id=str(uuid.uuid4())[:8],
            name=name,
            type=ReportType.SALES,
            format=ReportFormat.PDF,
            data=data,
            parameters={"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
            generated_at=datetime.now()
        )
        
        self._reports[report.id] = report
        return report
    
    def generate_customer_report(self, segment: Optional[str] = None,
                                name: str = "Customer Report") -> Report:
        """Generate customer analytics report"""
        import uuid
        
        data = {
            "total_customers": 1250,
            "new_customers": 150,
            "active_customers": 800,
            "churned_customers": 50,
            "customer_segments": [
                {"name": "VIP", "count": 150, "revenue": 75000},
                {"name": "Regular", "count": 650, "revenue": 65000},
                {"name": "New", "count": 450, "revenue": 10000},
            ],
            "acquisition_channels": {
                "organic": 400,
                "ads": 500,
                "referral": 200,
                "social": 150
            }
        }
        
        if segment:
            data["filtered_by_segment"] = segment
        
        report = Report(
            id=str(uuid.uuid4())[:8],
            name=name,
            type=ReportType.CUSTOMER,
            format=ReportFormat.PDF,
            data=data,
            parameters={"segment": segment},
            generated_at=datetime.now()
        )
        
        self._reports[report.id] = report
        return report
    
    def generate_campaign_report(self, campaign_id: Optional[str] = None,
                                name: str = "Campaign Report") -> Report:
        """Generate campaign performance report"""
        import uuid
        
        data = {
            "total_campaigns": 12,
            "active_campaigns": 3,
            "total_sent": 50000,
            "total_opened": 15000,
            "total_clicked": 3000,
            "average_open_rate": 30.0,
            "average_click_rate": 6.0,
            "top_performing": [
                {"name": "Summer Sale", "open_rate": 45, "click_rate": 12},
                {"name": "New Product", "open_rate": 38, "click_rate": 9},
            ]
        }
        
        report = Report(
            id=str(uuid.uuid4())[:8],
            name=name,
            type=ReportType.CAMPAIGN,
            format=ReportFormat.PDF,
            data=data,
            parameters={"campaign_id": campaign_id},
            generated_at=datetime.now()
        )
        
        self._reports[report.id] = report
        return report
    
    def get_report(self, report_id: str) -> Optional[Report]:
        """Get report by ID"""
        return self._reports.get(report_id)
    
    def list_reports(self, report_type: Optional[ReportType] = None) -> List[Report]:
        """List generated reports"""
        reports = list(self._reports.values())
        
        if report_type:
            reports = [r for r in reports if r.type == report_type]
        
        # Sort by generated_at desc
        reports.sort(key=lambda r: r.generated_at, reverse=True)
        return reports
    
    def export_report(self, report_id: str, format: ReportFormat) -> Optional[str]:
        """Export report to file"""
        report = self._reports.get(report_id)
        if not report:
            return None
        
        report.format = format
        
        if format == ReportFormat.JSON:
            file_path = f"/tmp/report_{report_id}.json"
            # In real implementation, write to file
            report.file_path = file_path
            return file_path
        elif format == ReportFormat.CSV:
            file_path = f"/tmp/report_{report_id}.csv"
            report.file_path = file_path
            return file_path
        else:
            file_path = f"/tmp/report_{report_id}.{format.value}"
            report.file_path = file_path
            return file_path
    
    def delete_report(self, report_id: str) -> bool:
        """Delete report"""
        if report_id in self._reports:
            del self._reports[report_id]
            return True
        return False
    
    def get_report_summary(self) -> Dict:
        """Get summary of all reports"""
        if not self._reports:
            return {"total": 0, "by_type": {}}
        
        by_type = {}
        for report in self._reports.values():
            type_name = report.type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1
        
        return {
            "total": len(self._reports),
            "by_type": by_type
        }
