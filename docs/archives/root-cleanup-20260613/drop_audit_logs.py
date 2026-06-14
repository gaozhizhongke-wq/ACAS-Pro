#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Drop empty audit_logs table"""
import sys
import os
sys.path.insert(0, 'src')
os.chdir(r'C:\Users\HUAWEI\.qclaw\workspace-hermes\ACAS-Pro')
from acas_pro.core.database import DatabaseManager  # noqa: E402
db = DatabaseManager()

# Check if audit_logs exists and is empty
try:
    tables = db.fetchall("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_logs'")
    if tables:
        count = db.fetchall("SELECT COUNT(*) as cnt FROM audit_logs")[0]['cnt']
        if count == 0:
            db.execute("DROP TABLE audit_logs")
            print('[OK] Dropped empty audit_logs table')
        else:
            print(f'[SKIP] audit_logs has {count} rows, not dropping')
    else:
        print('[OK] audit_logs table does not exist')
except Exception as e:
    print(f'[ERROR] {e}')

# Verify remaining audit tables
tables = db.fetchall("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'audit%'")
print('Remaining audit tables:', [t['name'] for t in tables])
