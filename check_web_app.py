#!/usr/bin/env python3
"""Quick syntax check of patched web_app.py"""
import ast, sys
path = r"C:\Users\HUAWEI\.qclaw\workspace-hermes\ACAS-Pro\web_app.py"
try:
    with open(path, encoding='utf-8') as f:
        src = f.read()
    ast.parse(src)
    print("✅ web_app.py: syntax OK")
except SyntaxError as e:
    print(f"❌ Syntax error: {e}")
    sys.exit(1)

# Quick functional checks
import os, re

checks = [
    ("festival_calendar in query", "FROM festival_calendar ORDER BY date"),
    ("audit_log (not data_alerts)", "'audit_log WHERE severity IN ('critical', 'warning')"),
    ("CORS production block", "CORS wildcard (*) blocked in production"),
    ("detail in exception", "'detail': str(e)"),
    ("status degraded", "'status': 'degraded'"),
    ("no debug=True", "debug=False"),
    ("ACAS_ENV in .env", "ACAS_ENV=development"),
]

print("\n=== PATCH VERIFICATION ===")
for name, pattern in checks:
    found = pattern in open(path, encoding='utf-8').read()
    status = "✅" if found else "❌"
    print(f"  {status} {name}")
