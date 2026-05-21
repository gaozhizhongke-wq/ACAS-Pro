#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix TestRateLimiter in test_security.py to use isolated temp file.
Run this script to patch the file.
"""

# Read the file with BOM and CRLF preserved
with open(r'C:\Users\HUAWEI\.qclaw\workspace-hermes\ACAS-Pro\tests\test_security.py', 'rb') as f:
    raw = f.read()

# Convert to string with CRLF preserved
content = raw.decode('utf-8-sig')

# Find TestRateLimiter class and add setup_method
old_class = '''class TestRateLimiter:
    """Rate limiter tests"""'''

new_class = '''class TestRateLimiter:
    """Rate limiter tests"""
    
    def setup_method(self):
        """Use isolated temp file for each test"""
        import tempfile
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_file.close()
        import os
        os.environ['ACAS_RATE_LIMIT_PATH'] = self.temp_file.name
    
    def teardown_method(self):
        """Clean up temp file"""
        import os
        try:
            os.unlink(self.temp_file.name)
        except:
            pass
        os.environ.pop('ACAS_RATE_LIMIT_PATH', None)'''

if old_class in content:
    content = content.replace(old_class, new_class)
    with open(r'C:\Users\HUAWEI\.qclaw\workspace-hermes\ACAS-Pro\tests\test_security.py', 'w', encoding='utf-8-sig', newline='') as f:
        f.write(content)
    print('Patched TestRateLimiter with setup_method')
else:
    print('Could not find TestRateLimiter class')
    # Debug: show what's around 'TestRateLimiter'
    idx = content.find('TestRateLimiter')
    if idx >= 0:
        print(f'Found at index {idx}')
        print(repr(content[idx:idx+200]))
    else:
        print('Class not found')
