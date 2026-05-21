"""Fix bare-name lazy references in user_service.py"""
import re

path = r'F:\自动获客系统\ACAS-Pro\src\acas_pro\services\user_service.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace bare names with lazy accessor calls
# Only replace when used as a standalone name (not already a function call or part of a definition)
replacements = {
    'rate_limiter.': '_get_lazy_rate_limiter().',
    'db.fetchone': '_get_lazy_db().fetchone',
    'db.fetch_all': '_get_lazy_db().fetch_all',
    'db.insert': '_get_lazy_db().insert',
    'db.update': '_get_lazy_db().update',
    'db.delete': '_get_lazy_db().delete',
    'password_validator.validate': '_get_lazy_password_validator().validate',
    'password_hasher.hash': '_get_lazy_password_hasher().hash',
    'password_hasher.verify': '_get_lazy_password_hasher().verify',
    'session_manager.': '_get_lazy_session_manager().',
}

for old, new in replacements.items():
    content = content.replace(old, new)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done replacing bare names with lazy accessors")
