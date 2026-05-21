import sys, os
sys.path.insert(0, 'src')
os.chdir(r'C:\Users\HUAWEI\.qclaw\workspace-hermes\ACAS-Pro')

from acas_pro.core.database import DatabaseManager

db = DatabaseManager()

# Check schema
tables = db.fetchall("SELECT name FROM sqlite_master WHERE type='table'")
print('Tables:', [t['name'] for t in tables])

# Check indexes
indexes = db.fetchall("SELECT name, tbl_name FROM sqlite_master WHERE type='index'")
print('Indexes:', [(i['name'], i['tbl_name']) for i in indexes])

# Check users
users = db.fetchall("SELECT id, account, account_type, status, role FROM users LIMIT 5")
print('Users:', users)

# Check products
products = db.fetchall("SELECT COUNT(*) as cnt FROM products")
print('Products count:', products[0]['cnt'] if products else 0)

# Check transactions
trans = db.fetchall("SELECT COUNT(*) as cnt FROM transactions")
print('Transactions count:', trans[0]['cnt'] if trans else 0)

# Check orders
orders = db.fetchall("SELECT COUNT(*) as cnt FROM orders")
print('Orders count:', orders[0]['cnt'] if orders else 0)

# Check if data_alerts table exists
try:
    alerts = db.fetchall("SELECT COUNT(*) as cnt FROM data_alerts")
    print('Alerts count:', alerts[0]['cnt'] if alerts else 0)
except Exception as e:
    print('data_alerts table missing:', e)

# Check if daily_metrics exists
try:
    dm = db.fetchall("SELECT COUNT(*) as cnt FROM daily_metrics")
    print('Daily metrics count:', dm[0]['cnt'] if dm else 0)
except Exception as e:
    print('daily_metrics table missing:', e)

# Check if platform_accounts exists
try:
    pa = db.fetchall("SELECT COUNT(*) as cnt FROM platform_accounts")
    print('Platform accounts count:', pa[0]['cnt'] if pa else 0)
except Exception as e:
    print('platform_accounts table missing:', e)

# Check if festivals table exists
try:
    f = db.fetchall("SELECT COUNT(*) as cnt FROM festivals")
    print('Festivals count:', f[0]['cnt'] if f else 0)
except Exception as e:
    print('festivals table missing:', e)

# Check if festival_calendar exists
try:
    fc = db.fetchall("SELECT COUNT(*) as cnt FROM festival_calendar")
    print('Festival calendar count:', fc[0]['cnt'] if fc else 0)
except Exception as e:
    print('festival_calendar table missing:', e)

print('\nSchema check complete')
