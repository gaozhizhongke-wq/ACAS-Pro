#!/usr/bin/env python3
import sqlite3, os
conn = sqlite3.connect(os.path.expanduser('~') + '/.acas-pro/data/acas.db')
cur = conn.cursor()
cur.execute("SELECT DISTINCT severity FROM audit_log LIMIT 20")
print('severity values:', [r[0] for r in cur.fetchall()])
cur.execute("SELECT COUNT(*) FROM audit_log WHERE severity IN ('high', 'critical', 'error')")
print('matching rows:', cur.fetchone()[0])
cur.execute("SELECT COUNT(*) FROM audit_log")
print('total rows:', cur.fetchone()[0])
