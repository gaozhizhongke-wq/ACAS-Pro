import sys, os
sys.path.insert(0, 'src')
os.chdir(r'C:\Users\HUAWEI\.qclaw\workspace-hermes\ACAS-Pro')
from acas_pro.core.database import DatabaseManager
db = DatabaseManager()
print('Database type:', 'PostgreSQL' if db._is_postgres else 'SQLite')
print('DB path:', getattr(db, '_db_path', 'N/A'))

# Check if audit_logs table exists
tables = db.fetchall("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_logs'")
print('audit_logs table exists:', len(tables) > 0)

# Check if audit_log table exists
tables2 = db.fetchall("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log'")
print('audit_log table exists:', len(tables2) > 0)
