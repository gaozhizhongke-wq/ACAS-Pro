#!/usr/bin/env python3
import sqlite3, os
db = os.path.expanduser('~') + '/.acas-pro/data/acas.db'
conn = sqlite3.connect(db); conn.row_factory = sqlite3.Row
cur = conn.cursor()

print('=== FINAL DB STATE ===')
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
for r in cur.fetchall():
    t = r[0]
    cur.execute(f'SELECT COUNT(*) FROM "{t}"')
    cnt = cur.fetchone()[0]
    flag = ' EMPTY' if cnt == 0 else ''
    print(f'  {t}: {cnt}{flag}')

print()
print('=== KEY DATA SAMPLES ===')
cur.execute('SELECT id, name, category, price, stock_quantity FROM products LIMIT 3')
for r in cur.fetchall(): print('product:', dict(r))
cur.execute('SELECT id, type, amount, status, created_at FROM transactions LIMIT 3')
for r in cur.fetchall(): print('transaction:', dict(r))
cur.execute('SELECT id, name, date, festival_type FROM festival_calendar LIMIT 5')
for r in cur.fetchall(): print('festival:', dict(r))
cur.execute('SELECT SUM(amount) as total FROM transactions WHERE status="completed"')
print('Total completed revenue:', cur.fetchone()['total'])
