#!/usr/bin/env python3
# -*- coding: utf-8 -*-
with open('src/acas_pro/ui/logic/__init__.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the file with only the working imports
new_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - UI Business Logic Layer
"""

from .dashboard_logic import DashboardLogic, KPIData, QuickAction, AlertItem
from .content_creation_logic import ContentCreationLogic, ContentTemplate
from .settings_logic import SettingsLogic, SettingItem
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
    'VideoLogic', 'VideoProject', 'RenderJob', 'VideoFormat', 'VideoQuality',
    'AnalyticsLogic', 'MetricData', 'AnalyticsReport', 'MetricType', 'TimeRange',
    'OrderLogic', 'Order', 'OrderItem', 'OrderStatus', 'PaymentStatus',
    'ProductLogic', 'Product', 'ProductStatus',
    'CustomerLogic', 'Customer', 'CustomerStatus', 'CustomerSource', 'CustomerSegment',
    'CampaignLogic', 'Campaign', 'CampaignStatus', 'CampaignType',
    'ReportLogic', 'Report', 'ReportType', 'ReportFormat'
]
'''

with open('src/acas_pro/ui/logic/__init__.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print('Simplified __init__.py')
