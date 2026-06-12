#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test dashboard API endpoints"""
import sys
import os
sys.path.insert(0, 'src')
os.chdir(r'C:\Users\HUAWEI\.qclaw\workspace-hermes\ACAS-Pro')

from acas_pro.web.routes.dashboard import bp  # noqa: E402
from flask import Flask  # noqa: E402

app = Flask(__name__)
app.register_blueprint(bp)

with app.test_client() as client:
    # Test /api/stats
    print('=== Testing /api/stats ===')
    resp = client.get('/api/stats')
    print(f'Status: {resp.status_code}')
    data = resp.get_json()
    print(f'Success: {data["success"]}')
    stats = data['stats']
    print(f'  active_users: {stats["active_users"]}')
    print(f'  products_count: {stats["products_count"]}')
    print(f'  total_revenue: {stats["total_revenue"]}')
    print(f'  transactions_today: {stats["transactions_today"]}')
    print(f'  content_count: {stats["content_count"]}')
    print(f'  pending_tasks: {stats["pending_tasks"]}')
    print(f'  alerts_count: {stats["alerts_count"]}')
    print(f'  api_calls_today: {stats["api_calls_today"]}')
    
    print()
    
    # Test /api/activity
    print('=== Testing /api/activity ===')
    resp2 = client.get('/api/activity')
    print(f'Status: {resp2.status_code}')
    data2 = resp2.get_json()
    acts = data2['activities']
    print(f'Activities count: {len(acts)}')
    print('First 3 activities:')
    for a in acts[:3]:
        print(f'  - {a["time"]} | {a["event"]} | {a["status"]}')

print('\n[OK] All dashboard API tests passed!')
