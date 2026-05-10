#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - UI Business Logic Layer
Extracted from Qt views for testability
"""

from .dashboard_logic import DashboardLogic, KPIData, QuickAction, AlertItem
from .content_creation_logic import ContentCreationLogic, ContentTemplate
from .settings_logic import SettingsLogic, SettingItem
from .inventory_logic import InventoryLogic, InventoryItem, InventoryAlert
from .content_logic import (
    ContentCreationLogic as ContentLogic,
    TrendItem, ScriptTemplate, GeneratedScript,
    ContentStyle, Platform
)
from .video_logic import VideoLogic, VideoProject, RenderJob, VideoFormat, VideoQuality
from .analytics_logic import AnalyticsLogic, MetricData, AnalyticsReport, MetricType, TimeRange
from .order_logic import OrderLogic, Order, OrderItem, OrderStatus, PaymentStatus
from .product_logic import ProductLogic, Product, ProductStatus
from .customer_logic import CustomerLogic, Customer, CustomerStatus, CustomerSource, CustomerSegment
from .campaign_logic import CampaignLogic, Campaign, CampaignStatus, CampaignType
from .report_logic import ReportLogic, Report, ReportType, ReportFormat

__all__ = [
    'DashboardLogic', 'KPIData', 'QuickAction', 'AlertItem',
    'ContentCreationLogic', 'ContentTemplate',
    'SettingsLogic', 'SettingItem',
    'InventoryLogic', 'InventoryItem', 'InventoryAlert',
    'ContentLogic', 'TrendItem', 'ScriptTemplate', 'GeneratedScript',
    'ContentStyle', 'Platform',
    'VideoLogic', 'VideoProject', 'RenderJob', 'VideoFormat', 'VideoQuality',
    'AnalyticsLogic', 'MetricData', 'AnalyticsReport', 'MetricType', 'TimeRange',
    'OrderLogic', 'Order', 'OrderItem', 'OrderStatus', 'PaymentStatus',
    'ProductLogic', 'Product', 'ProductStatus',
    'CustomerLogic', 'Customer', 'CustomerStatus', 'CustomerSource', 'CustomerSegment',
    'CampaignLogic', 'Campaign', 'CampaignStatus', 'CampaignType',
    'ReportLogic', 'Report', 'ReportType', 'ReportFormat'
]
