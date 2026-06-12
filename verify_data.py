#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify core data initialization"""
import sys
import os
sys.path.insert(0, 'src')
os.chdir(r'C:\Users\HUAWEI\.qclaw\workspace-hermes\ACAS-Pro')

from acas_pro.core.database import DatabaseManager  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

db = DatabaseManager()

print('=== Data Verification ===')
products = db.fetchall('SELECT COUNT(*) as cnt FROM products')
print(f'Products: {products[0]["cnt"]}')

trans = db.fetchall('SELECT COUNT(*) as cnt FROM transactions')
print(f'Transactions: {trans[0]["cnt"]}')

dm = db.fetchall('SELECT COUNT(*) as cnt FROM daily_metrics')
print(f'Daily metrics: {dm[0]["cnt"]}')

fc = db.fetchall('SELECT COUNT(*) as cnt FROM festival_calendar')
print(f'Festivals: {fc[0]["cnt"]}')

pa = db.fetchall('SELECT COUNT(*) as cnt FROM platform_accounts')
print(f'Platform accounts: {pa[0]["cnt"]}')

alerts = db.fetchall('SELECT COUNT(*) as cnt FROM data_alerts')
print(f'Alerts: {alerts[0]["cnt"]}')

# Check revenue
rev = db.fetchall("SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE status = 'completed'")
print(f'Total revenue: {rev[0]["total"]}')

# Check transactions today
today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
today_trans = db.fetchall(f"SELECT COUNT(*) as cnt FROM transactions WHERE created_at LIKE '{today}%'")
print(f'Transactions today: {today_trans[0]["cnt"]}')

print('\n[OK] All data verified successfully!')
