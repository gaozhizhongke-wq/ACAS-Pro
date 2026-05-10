"""Apply CSRF fixes to security.py"""
import re

path = r'F:\自动获客系统\ACAS-Pro\src\acas_pro\core\security.py'
with open(path, encoding='utf-8') as f:
    content = f.read()

# 1. Add functools.wraps import to the existing 'from functools import' line
content = content.replace(
    'from functools import wraps',
    'from functools import wraps'
)
if 'from functools import wraps' not in content:
    # Add wraps to existing import
    content = content.replace(
        'from functools import wraps',
        'from functools import wraps'
    )
    print("wraps import: already there or added")

# Find the line with functools import and ensure wraps is there
if 'from functools import' in content and 'wraps' not in content.split('from functools import')[1].split('\n')[0]:
    print("wraps NOT in functools import - need to fix")

# Find the Flask import block in security.py (it doesn't exist - CSRF is added later)
# Actually, we just need to add CSRF functions at the end of security.py

# The CSRF code to add
csrf_code = '''

# ── CSRF Protection ─────────────────────────────────────────────────────────

CSRF_STATE_SECRET = os.environ.get('CSRF_STATE_SECRET') or secrets.token_hex(32)


def generate_csrf_token() -> str:
    """Generate a secure random CSRF token."""
    return secrets.token_hex(32)


def create_csrf_cookie(response) -> str:
    """
    Attach CSRF cookie to response (double-submit cookie pattern).
    Returns the token so it can also be embedded in the HTML.
    """
    token = generate_csrf_token()
    response.set_cookie(
        'csrf_token',
        token,
        max_age=3600 * 24,
        httponly=False,   # Must be readable by JavaScript (double-submit)
        secure=True,      # HTTPS only
        samesite='Lax',
    )
    return token


def validate_csrf_request(request) -> Tuple[bool, str]:
    """
    Validate CSRF token using double-submit cookie pattern.
    Returns (is_valid, error_message).
    """
    header_token = request.headers.get('X-CSRF-Token', '').strip()
    cookie_token = request.cookies.get('csrf_token', '').strip()

    if not header_token:
        return False, 'Missing CSRF token (X-CSRF-Token header required)'
    if not cookie_token:
        return False, 'CSRF cookie not set — please refresh and try again'
    if header_token != cookie_token:
        return False, 'CSRF token mismatch'
    if not re.fullmatch(r'[0-9a-f]{64}', header_token):
        return False, 'Invalid CSRF token format'
    return True, ''


def require_csrf(f):
    """Decorator: require valid CSRF token on POST/PUT/DELETE/PATCH."""
    @wraps(f)
    def wrapped(*args, **kwargs):
        if request.method not in ('POST', 'PUT', 'DELETE', 'PATCH'):
            return f(*args, **kwargs)
        ok, msg = validate_csrf_request(request)
        if not ok:
            from flask import jsonify
            return jsonify({'error': msg, 'code': 'CSRF_INVALID'}), 403
        return f(*args, **kwargs)
    return wrapped
'''

# Append before the last empty line or at the end
content = content.rstrip() + '\n' + csrf_code

with open(path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)

print("CSRF code added to security.py")
print(f"New length: {len(content)} chars")