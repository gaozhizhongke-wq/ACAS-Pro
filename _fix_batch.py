#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix all failing test files at once"""

import os

ACAS = r'C:\Users\HUAWEI\.qclaw\workspace-hermes\ACAS-Pro'

# ============================================
# 1. Fix test_security_headers.py (2 failures)
# ============================================
# Problem: Flask request.is_secure needs request context
# Fix: Use patch on the module's request object

content = open(os.path.join(ACAS, 'tests', 'unit', 'test_security_headers.py'), 'r', encoding='utf-8-sig').read()

# Replace test_hsts_on_secure
old_hsts_on = '''    def test_hsts_on_secure(self):
        app = MagicMock()
        
        registered_handlers = []
        def capture_after_request(f):
            registered_handlers.append(f)
            return f
        app.after_request = capture_after_request
        
        sh = SecurityHeaders(app=app, hsts=True, hsts_max_age=31536000)
        handler = registered_handlers[0]
        
        response = MagicMock()
        response.headers = {}
        
        import acas_pro.core.security_headers as sec_mod
        orig_request = getattr(sec_mod, 'request', None)
        mock_request = MagicMock()
        mock_request.is_secure = True
        sec_mod.request = mock_request
        try:
            result = handler(response)
        finally:
            if orig_request is not None:
                sec_mod.request = orig_request
            else:
                if hasattr(sec_mod, 'request'):
                    delattr(sec_mod, 'request')
        
        assert 'Strict-Transport-Security' in result.headers
        assert '31536000' in result.headers['Strict-Transport-Security']'''

new_hsts_on = '''    def test_hsts_on_secure(self):
        from unittest.mock import patch
        app = MagicMock()
        
        registered_handlers = []
        def capture_after_request(f):
            registered_handlers.append(f)
            return f
        app.after_request = capture_after_request
        
        sh = SecurityHeaders(app=app, hsts=True, hsts_max_age=31536000)
        handler = registered_handlers[0]
        
        response = MagicMock()
        response.headers = {}
        
        mock_request = MagicMock()
        mock_request.is_secure = True
        
        with patch('acas_pro.core.security_headers.request', mock_request):
            result = handler(response)
        
        assert 'Strict-Transport-Security' in result.headers
        assert '31536000' in result.headers['Strict-Transport-Security']'''

content = content.replace(old_hsts_on, new_hsts_on)

# Replace test_hsts_off_on_insecure
old_hsts_off = '''    def test_hsts_off_on_insecure(self):
        app = MagicMock()
        
        registered_handlers = []
        def capture_after_request(f):
            registered_handlers.append(f)
            return f
        app.after_request = capture_after_request
        
        sh = SecurityHeaders(app=app, hsts=True)
        handler = registered_handlers[0]
        
        response = MagicMock()
        response.headers = {}
        
        import acas_pro.core.security_headers as sec_mod
        orig_request = getattr(sec_mod, 'request', None)
        mock_request = MagicMock()
        mock_request.is_secure = False
        sec_mod.request = mock_request
        try:
            result = handler(response)
        finally:
            if orig_request is not None:
                sec_mod.request = orig_request
            else:
                if hasattr(sec_mod, 'request'):
                    delattr(sec_mod, 'request')
        
        assert 'Strict-Transport-Security' not in result.headers'''

new_hsts_off = '''    def test_hsts_off_on_insecure(self):
        from unittest.mock import patch
        app = MagicMock()
        
        registered_handlers = []
        def capture_after_request(f):
            registered_handlers.append(f)
            return f
        app.after_request = capture_after_request
        
        sh = SecurityHeaders(app=app, hsts=True)
        handler = registered_handlers[0]
        
        response = MagicMock()
        response.headers = {}
        
        mock_request = MagicMock()
        mock_request.is_secure = False
        
        with patch('acas_pro.core.security_headers.request', mock_request):
            result = handler(response)
        
        assert 'Strict-Transport-Security' not in result.headers'''

content = content.replace(old_hsts_off, new_hsts_off)

# Also fix test_server_header_removed and test_init_app_adds_headers with same pattern
old_server = '''        import acas_pro.core.security_headers as sec_mod
        orig_request = getattr(sec_mod, 'request', None)
        mock_request = MagicMock()
        mock_request.is_secure = False
        sec_mod.request = mock_request
        try:
            result = handler(response)
        finally:
            if orig_request is not None:
                sec_mod.request = orig_request
            else:
                if hasattr(sec_mod, 'request'):
                    delattr(sec_mod, 'request)'''

# Actually let's just replace ALL occurrences of the old pattern with patch pattern
# The pattern is the same in test_init_app_adds_headers and test_server_header_removed
old_pattern = """        import acas_pro.core.security_headers as sec_mod
        orig_request = getattr(sec_mod, 'request', None)
        mock_request = MagicMock()
        mock_request.is_secure = False
        sec_mod.request = mock_request
        try:
            result = handler(response)
        finally:
            if orig_request is not None:
                sec_mod.request = orig_request
            else:
                if hasattr(sec_mod, 'request'):
                    delattr(sec_mod, 'request')"""

new_pattern = """        from unittest.mock import patch as _patch
        mock_request = MagicMock()
        mock_request.is_secure = False
        with _patch('acas_pro.core.security_headers.request', mock_request):
            result = handler(response)"""

content = content.replace(old_pattern, new_pattern)

with open(os.path.join(ACAS, 'tests', 'unit', 'test_security_headers.py'), 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed test_security_headers.py')

# ============================================
# 2. Fix test_account_manager.py (17 failures)
# ============================================
path = os.path.join(ACAS, 'tests', 'unit', 'test_account_manager.py')
if os.path.exists(path):
    content = open(path, 'r', encoding='utf-8-sig').read()
    # Let's see what's failing - read the first 50 lines
    lines = content.split('\n')
    print(f'\ntest_account_manager.py: {len(lines)} lines')
    for i, line in enumerate(lines[:30]):
        print(f'{i+1}: {line}')
else:
    print(f'\ntest_account_manager.py not found')

print('\nDone with initial fixes')
