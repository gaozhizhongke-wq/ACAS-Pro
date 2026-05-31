#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check database status"""
import sys, os
sys.path.insert(0, 'src')
os.chdir(r'C:\Users\HUAWEI\.qclaw\workspace-hermes\ACAS-Pro')
from acas_pro.core.database import DatabaseManager
db = DatabaseManager()

# Count all tables
tables = db.fetchall("SELECT name FROM sqlite_master WHERE type='table'")
print('Total tables:', len(tables))

# Count test tables
test_tables = [t['name'] for t in tables if 'test_' in t['name']]
print('Test tables:', len(test_tables))

# Count core tables
core_tables = [t['name'] for t in tables if 'test_' not in t['name']]
print('Core tables:', len(core_tables))
print('Core table names:', core_tables)

# Check data counts
for table in ['products', 'transactions', 'daily_metrics', 'festival_calendar', 'platform_accounts', 'data_alerts']:
    try:
        rows = db.fetchall(f'SELECT COUNT(*) as cnt FROM {table}')
        print(f'{table}: {rows[0]["cnt"]} rows')
    except:
        print(f'{table}: ERROR')
