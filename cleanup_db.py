#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - 数据库清理脚本
清理所有测试残留表，保留核心业务表
"""

import sys
import os

sys.path.insert(0, 'src')
os.chdir(r'C:\Users\HUAWEI\.qclaw\workspace-hermes\ACAS-Pro')

from acas_pro.core.database import DatabaseManager

db = DatabaseManager()

# 获取所有表
tables = db.fetchall("SELECT name FROM sqlite_master WHERE type='table'")
all_tables = [t['name'] for t in tables]

# 核心业务表（保留）
core_tables = {
    'users', 'payment_methods', 'transactions', 'audit_log', 
    'products', 'sales_data', 'news_cache', 'sessions',
    'trend_items', 'generated_scripts', 'platform_accounts',
    'account_stats', 'account_login_logs', 'festivals',
    'marketing_plans', 'video_projects', 'video_materials',
    'voice_tasks', 'voice_clones', 'publish_tasks',
    'ad_accounts', 'ad_campaigns', 'ad_records',
    'audience_segments', 'digital_avatars', 'avatar_scenes',
    'avatar_render_tasks', 'shops', 'shop_stats', 'orders',
    'suppliers', 'inventory_syncs', 'purchase_orders',
    'settlements', 'settlement_details', 'wallets',
    'metrics_data', 'daily_metrics', 'data_alerts',
    'inventory', 'accounts', 'campaigns', 'festival_calendar',
    'content_templates', 'chat_history', 'audit_logs', 'ads', 'publications'
}

# 系统表（保留）
system_tables = {'sqlite_sequence'}

# 需要删除的测试表
test_tables = [t for t in all_tables if t not in core_tables and t not in system_tables]

print(f"Found {len(test_tables)} test tables to clean...")

# 删除测试表
for table in test_tables:
    try:
        db.execute(f"DROP TABLE IF EXISTS {table}")
        print(f"  [OK] Dropped table: {table}")
    except Exception as e:
        print(f"  [FAIL] Failed to drop {table}: {e}")

# 清理索引
indexes = db.fetchall("SELECT name FROM sqlite_master WHERE type='index'")
for idx in indexes:
    name = idx['name']
    if name.startswith('sqlite_autoindex_'):
        continue  # 保留系统自动索引
    # 检查索引对应的表是否还存在
    info = db.fetchone("SELECT tbl_name FROM sqlite_master WHERE type='index' AND name = ?", (name,))
    if info and info['tbl_name'] in test_tables:
        try:
            db.execute(f"DROP INDEX IF EXISTS {name}")
            print(f"  [OK] Dropped index: {name}")
        except Exception as e:
            print(f"  [FAIL] Failed to drop index {name}: {e}")

print(f"\nCleaned {len(test_tables)} test tables")

# 验证清理结果
tables_after = db.fetchall("SELECT name FROM sqlite_master WHERE type='table'")
remaining = [t['name'] for t in tables_after]
print(f"\nRemaining tables: {len(remaining)}")
print(f"Tables: {sorted(remaining)}")

# 检查是否还有test_开头的表
still_test = [t for t in remaining if t.startswith('test_')]
if still_test:
    print(f"\n[!] Still has test tables: {still_test}")
else:
    print("\n[OK] All test tables cleaned")
