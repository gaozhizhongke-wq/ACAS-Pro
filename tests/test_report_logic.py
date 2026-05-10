#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Report Logic Tests
"""

import pytest
from datetime import datetime, timedelta

from acas_pro.ui.logic.report_logic import (
    ReportLogic, Report, ReportType, ReportFormat
)


class TestReportType:
    def test_type_values(self):
        assert ReportType.SALES.value == "sales"
        assert ReportType.CUSTOMER.value == "customer"
        assert ReportType.CAMPAIGN.value == "campaign"


class TestReportFormat:
    def test_format_values(self):
        assert ReportFormat.PDF.value == "pdf"
        assert ReportFormat.CSV.value == "csv"
        assert ReportFormat.JSON.value == "json"


class TestReportLogic:
    @pytest.fixture
    def logic(self):
        return ReportLogic()

    def test_init(self, logic):
        assert logic._reports == {}

    def test_generate_sales_report(self, logic):
        start = datetime.now() - timedelta(days=7)
        end = datetime.now()
        report = logic.generate_sales_report(start, end, "Weekly Sales")
        assert report.name == "Weekly Sales"
        assert report.type == ReportType.SALES
        assert "total_revenue" in report.data
        assert len(report.id) == 8

    def test_generate_customer_report(self, logic):
        report = logic.generate_customer_report(segment="VIP", name="VIP Report")
        assert report.name == "VIP Report"
        assert report.type == ReportType.CUSTOMER
        assert "total_customers" in report.data

    def test_generate_customer_report_no_segment(self, logic):
        report = logic.generate_customer_report()
        assert report.type == ReportType.CUSTOMER
        assert "customer_segments" in report.data

    def test_generate_campaign_report(self, logic):
        report = logic.generate_campaign_report(campaign_id="camp001", name="Campaign Performance")
        assert report.name == "Campaign Performance"
        assert report.type == ReportType.CAMPAIGN
        assert "total_campaigns" in report.data

    def test_get_report(self, logic):
        start = datetime.now() - timedelta(days=7)
        end = datetime.now()
        report = logic.generate_sales_report(start, end)
        fetched = logic.get_report(report.id)
        assert fetched == report

    def test_get_nonexistent_report(self, logic):
        fetched = logic.get_report("nonexistent")
        assert fetched is None

    def test_list_reports(self, logic):
        start = datetime.now() - timedelta(days=7)
        end = datetime.now()
        logic.generate_sales_report(start, end)
        logic.generate_customer_report()
        reports = logic.list_reports()
        assert len(reports) == 2

    def test_list_reports_by_type(self, logic):
        start = datetime.now() - timedelta(days=7)
        end = datetime.now()
        logic.generate_sales_report(start, end)
        logic.generate_customer_report()
        sales_reports = logic.list_reports(report_type=ReportType.SALES)
        assert len(sales_reports) == 1
        assert sales_reports[0].type == ReportType.SALES

    def test_export_report_json(self, logic):
        start = datetime.now() - timedelta(days=7)
        end = datetime.now()
        report = logic.generate_sales_report(start, end)
        path = logic.export_report(report.id, ReportFormat.JSON)
        assert path is not None
        assert path.endswith(".json")

    def test_export_report_csv(self, logic):
        start = datetime.now() - timedelta(days=7)
        end = datetime.now()
        report = logic.generate_sales_report(start, end)
        path = logic.export_report(report.id, ReportFormat.CSV)
        assert path is not None
        assert path.endswith(".csv")

    def test_export_nonexistent_report(self, logic):
        path = logic.export_report("nonexistent", ReportFormat.PDF)
        assert path is None

    def test_delete_report(self, logic):
        start = datetime.now() - timedelta(days=7)
        end = datetime.now()
        report = logic.generate_sales_report(start, end)
        result = logic.delete_report(report.id)
        assert result is True
        assert logic.get_report(report.id) is None

    def test_delete_nonexistent_report(self, logic):
        result = logic.delete_report("nonexistent")
        assert result is False

    def test_get_report_summary_empty(self, logic):
        summary = logic.get_report_summary()
        assert summary["total"] == 0

    def test_get_report_summary(self, logic):
        start = datetime.now() - timedelta(days=7)
        end = datetime.now()
        logic.generate_sales_report(start, end)
        logic.generate_sales_report(start, end)
        logic.generate_customer_report()
        summary = logic.get_report_summary()
        assert summary["total"] == 3
        assert summary["by_type"]["sales"] == 2
        assert summary["by_type"]["customer"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
