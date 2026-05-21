#!/usr/bin/env python3
"""Check actual ACAS database state"""
import sqlite3, os, sys

db_path = os.path.join(os.path.expanduser("~"), ".acas-pro", "data", "acas.db")
if not os.path.exists(db_path):
    print(f'DB NOT FOUND at {db_path}')
    sys.exit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Count test tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'test_%'")
test_tables = [r[0] for r in cur.fetchall()]
print(f'=== TEST TABLES: {len(test_tables)} ===')
print('Sample:', test_tables[:10])

# Count all non-test, non-sqlite tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE 'test_%' ORDER BY name")
all_tables = [r[0] for r in cur.fetchall()]
print(f'\n=== ALL TABLES ({len(all_tables)}) ===')
for t in all_tables:
    try:
        cur2 = conn.cursor()
        cur2.execute(f'SELECT COUNT(*) FROM "{t}"')
        cnt = cur2.fetchone()[0]
        print(f'  {t}: {cnt} rows')
    except Exception as e:
        print(f'  {t}: ERROR - {e}')

# Check audit tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'audit%'")
audit_tables = [r[0] for r in cur.fetchall()]
print(f'\nAudit tables: {audit_tables}')
