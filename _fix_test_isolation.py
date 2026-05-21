#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix TestRateLimiter test isolation by using temp file"""

# Read the file with BOM and CRLF preserved
with open(r'C:\Users\HUAWEI\.qclaw\workspace-hermes\ACAS-Pro\tests\test_security.py', 'rb') as f:
    raw = f.read()

# Decode with UTF-8-SIG (handles BOM)
content = raw.decode('utf-8-sig')

# Find where to insert setup_method and teardown_method
# We need to add them after the class docstring and before the first test method

class_def = 'class TestRateLimiter:\r\n    """Rate limiter tests"""\r\n'
setup_method = '''    def setup_method(self):
        """Use isolated temp file for each test"""
        import tempfile
        import os
        self._temp_dir = tempfile.mkdtemp()
        os.environ['ACAS_DATA_DIR'] = self._temp_dir
    
    def teardown_method(self):
        """Clean up temp directory"""
        import os
        import shutil
        os.environ.pop('ACAS_DATA_DIR', None)
        try:
            shutil.rmtree(self._temp_dir)
        except:
            pass
    
'''

# Insert setup_method after class definition
if class_def in content:
    # Find the position after class_def
    idx = content.find(class_def) + len(class_def)
    
    # Check if setup_method already exists
    if 'def setup_method' not in content:
        content = content[:idx] + setup_method + content[idx:]
        
        # Write back with CRLF preserved
        with open(r'C:\Users\HUAWEI\.qclaw\workspace-hermes\ACAS-Pro\tests\test_security.py', 'wb') as f:
            f.write(content.encode('utf-8-sig'))
        
        print('SUCCESS: Added setup_method and teardown_method to TestRateLimiter')
        print('Test will now use isolated temp file')
    else:
        print('setup_method already exists')
else:
    print('ERROR: Could not find class TestRateLimiter definition')
    # Debug: show what's around that area
    idx = content.find('TestRateLimiter')
    if idx >= 0:
        print(f'Found "TestRateLimiter" at index {idx}')
        print('Context:')
        print(repr(content[idx:idx+200]))
