#!/usr/bin/env python3
import sqlite3, os
path = os.path.expanduser('~/.acas-pro/data/acas.db')
conn = sqlite3.connect(path)
cur = conn.cursor()
for t in ['data_alerts', 'festivals']:
    cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (t,))
    row = cur.fetchone()
    if row:
        print(f"=== {t} ===")
        print(row[0])
        print()
conn.close()
