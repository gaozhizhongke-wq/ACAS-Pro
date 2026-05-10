import sqlite3
conn = sqlite3.connect(r'F:\自动获客系统\ACAS-Pro\data\acas.db')
c = conn.execute('SELECT name FROM sqlite_master WHERE type=? ORDER BY name', ('table',))
print('TABLES:', [r[0] for r in c.fetchall()])

# Check products table columns
try:
    c2 = conn.execute('PRAGMA table_info(products)')
    cols = [r[1] for r in c2.fetchall()]
    print('products columns:', cols)
except Exception as e:
    print('products error:', e)

# Check users
try:
    c4 = conn.execute('SELECT COUNT(*) FROM users')
    print('users count:', c4.fetchone()[0])
except Exception as e:
    print('users error:', e)

conn.close()
