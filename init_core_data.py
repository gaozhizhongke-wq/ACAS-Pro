#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - 核心业务数据初始化
填充 products, transactions, daily_metrics, festival_calendar 等表
"""

import sys
import os
import random
from datetime import datetime, timedelta, timezone

sys.path.insert(0, 'src')
os.chdir(r'C:\Users\HUAWEI\.qclaw\workspace-hermes\ACAS-Pro')

from acas_pro.core.database import DatabaseManager
from acas_pro.core.config import config

db = DatabaseManager()

print("[1/5] Initializing products...")
# 清空并重新填充 products
sample_products = [
    ("P001", "Wireless Earbuds Pro", "Electronics", 299.00, 150, 50, "active", datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()),
    ("P002", "Smart Watch X1", "Electronics", 899.00, 80, 30, "active", datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()),
    ("P003", "Portable Charger 20000mAh", "Electronics", 129.00, 200, 80, "active", datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()),
    ("P004", "Bluetooth Speaker Mini", "Electronics", 199.00, 120, 40, "active", datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()),
    ("P005", "USB-C Hub 7-in-1", "Electronics", 259.00, 60, 20, "active", datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()),
    ("P006", "Mechanical Keyboard RGB", "Electronics", 459.00, 45, 15, "active", datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()),
    ("P007", "Wireless Mouse Ergonomic", "Electronics", 159.00, 100, 35, "active", datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()),
    ("P008", "Webcam 4K Pro", "Electronics", 599.00, 30, 10, "active", datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()),
    ("P009", "SSD External 1TB", "Electronics", 699.00, 55, 20, "active", datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()),
    ("P010", "Phone Stand Adjustable", "Accessories", 49.00, 300, 100, "active", datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()),
    ("P011", "Cable Organizer Box", "Accessories", 39.00, 250, 80, "active", datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()),
    ("P012", "Screen Cleaner Kit", "Accessories", 29.00, 400, 150, "active", datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()),
    ("P013", "Laptop Sleeve 15.6\"", "Accessories", 89.00, 180, 60, "active", datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()),
    ("P014", "Desk Lamp LED", "Home", 159.00, 70, 25, "active", datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()),
    ("P015", "Air Purifier Mini", "Home", 399.00, 40, 15, "active", datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()),
]

db.execute("DELETE FROM products")
for p in sample_products:
    db.execute("""
        INSERT INTO products (id, name, category, price, stock_quantity, reorder_point, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, p)
print(f"  [OK] Inserted {len(sample_products)} products")

print("[2/5] Initializing transactions...")
# 生成30天的交易数据
transactions = []
start_date = datetime.now(timezone.utc) - timedelta(days=30)
for i in range(200):
    day_offset = random.randint(0, 30)
    created = (start_date + timedelta(days=day_offset)).isoformat()
    amount = round(random.uniform(50, 2000), 2)
    status = random.choice(['completed', 'completed', 'completed', 'pending', 'settled'])
    user_id = f"U{random.randint(1, 100):03d}"
    trans_type = random.choice(['sale', 'refund', 'withdrawal', 'deposit'])
    transactions.append((f"T{i:06d}", user_id, amount, status, trans_type, created))

db.execute("DELETE FROM transactions")
for t in transactions:
    db.execute("""
        INSERT INTO transactions (id, user_id, amount, status, type, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, t)
print(f"  [OK] Inserted {len(transactions)} transactions")

print("[3/5] Initializing daily_metrics...")
# 生成90天的日度指标
daily_metrics = []
platforms = ['xiaohongshu', 'douyin', 'weibo', 'wechat', 'taobao']
for i in range(90):
    date = (datetime.now(timezone.utc) - timedelta(days=89-i)).strftime('%Y-%m-%d')
    for platform in platforms:
        revenue = round(random.uniform(1000, 15000), 2)
        orders = random.randint(10, 200)
        views = random.randint(1000, 50000)
        account_id = f"PA{random.randint(1, 4):03d}"
        daily_metrics.append((date, platform, account_id, revenue, orders, views))

db.execute("DELETE FROM daily_metrics")
for dm in daily_metrics:
    db.execute("""
        INSERT INTO daily_metrics (date, platform, account_id, revenue, orders, views)
        VALUES (?, ?, ?, ?, ?, ?)
    """, dm)
print(f"  [OK] Inserted {len(daily_metrics)} daily metrics")

print("[4/5] Initializing festival_calendar...")
# 填充节日日历
festivals_data = [
    ("FC001", "618 Shopping Festival", "shopping", "2026-06-18", "cn", "Summer shopping spree", "discounts,promotions"),
    ("FC002", "Double 11", "shopping", "2026-11-11", "cn", "Biggest shopping day", "discounts,coupons"),
    ("FC003", "Mid-Autumn Festival", "traditional", "2026-09-17", "cn", "Family reunion", "gifts,mooncakes"),
    ("FC004", "National Day", "holiday", "2026-10-01", "cn", "Golden week", "travel,sales"),
    ("FC005", "Valentine's Day", "romantic", "2026-02-14", "global", "Love celebration", "gifts,flowers"),
    ("FC006", "Mother's Day", "family", "2026-05-10", "global", "Honor mothers", "gifts,flowers"),
    ("FC007", "Father's Day", "family", "2026-06-21", "global", "Honor fathers", "gifts,tools"),
    ("FC008", "Dragon Boat Festival", "traditional", "2026-06-19", "cn", "Zongzi tradition", "food,gifts"),
    ("FC009", "New Year", "holiday", "2026-01-01", "global", "New beginning", "celebration,gifts"),
    ("FC010", "Spring Festival", "traditional", "2026-02-17", "cn", "Chinese New Year", "red envelopes,gifts"),
]

db.execute("DELETE FROM festival_calendar")
for fc in festivals_data:
    db.execute("""
        INSERT INTO festival_calendar (id, name, festival_type, date, region, description, marketing_tips)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, fc)
print(f"  [OK] Inserted {len(festivals_data)} festivals")

print("[5/5] Initializing platform_accounts...")
# 确保平台账号数据存在
accounts_data = [
    ("PA001", "xiaohongshu", "xhs_001", "ACAS_Official", "ACAS Official", "token_001", "", 125000, 342, 2500000, 85000, "active", "growth"),
    ("PA002", "douyin", "dy_001", "ACAS_Douyin", "ACAS Douyin", "token_002", "", 89000, 567, 1800000, 62000, "active", "growth"),
    ("PA003", "weibo", "wb_001", "ACAS_Weibo", "ACAS Weibo", "token_003", "", 56000, 890, 1200000, 45000, "active", "mature"),
    ("PA004", "wechat", "wx_001", "ACAS_Official", "ACAS Official", "token_004", "", 45000, 234, 800000, 32000, "active", "growth"),
]

db.execute("DELETE FROM platform_accounts")
for acc in accounts_data:
    db.execute("""
        INSERT INTO platform_accounts (id, platform, account_id, account_name, nickname, access_token, refresh_token, followers, content_count, total_views, total_likes, status, phase)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, acc)
print(f"  [OK] Inserted {len(accounts_data)} platform accounts")

# 更新 data_alerts
print("[6/6] Updating data_alerts...")
db.execute("DELETE FROM data_alerts")
alerts = [
    (1, "low_stock", None, None, None, "Product P008 stock below threshold", "warning", 0),
    (2, "revenue_drop", None, None, None, "Revenue dropped 15% compared to last week", "warning", 0),
    (3, "high_return", None, None, None, "Return rate exceeded 5% on P002", "warning", 0),
]
for alert in alerts:
    db.execute("""
        INSERT INTO data_alerts (id, alert_type, platform, account_id, content_id, message, severity, acknowledged)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, alert)
print(f"  [OK] Inserted {len(alerts)} alerts")
print(f"  [OK] Inserted {len(alerts)} alerts")

print("\n[OK] All core data initialized successfully!")
print("\nData summary:")
print(f"  - Products: {len(sample_products)}")
print(f"  - Transactions: {len(transactions)}")
print(f"  - Daily metrics: {len(daily_metrics)}")
print(f"  - Festivals: {len(festivals_data)}")
print(f"  - Platform accounts: {len(accounts_data)}")
print(f"  - Alerts: {len(alerts)}")
