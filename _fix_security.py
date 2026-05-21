#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix test_allows_under_limit in test_security.py"""

# Read the file
with open(r'C:\Users\HUAWEI\.qclaw\workspace-hermes\ACAS-Pro\tests\test_security.py', 'r', encoding='utf-8-sig') as f:
    content = f.read()

# The broken test has a missing line. Let me find and fix it.
# The current broken version has:
#     def test_allows_under_limit(self):
#         """Test requests under limit are allowed"""
#         limiter = RateLimiter()
#         key = "test_key"
#         
#         for _ in range(4):
#             limiter.record_attempt(key)
#             assert limiter.is_allowed(key, max_attempts=5) is True
#         
#         # 4th attempt should still be allowed
#         assert limiter.is_allowed(key, max_attempts=5) is True

# The correct version should have:
#     def test_allows_under_limit(self):
#         """Test requests under limit are allowed"""
#         limiter = RateLimiter()
#         key = "test_key"
#         
#         # First check should be allowed (no attempts yet)
#         assert limiter.is_allowed(key, max_attempts=5) is True
#         
#         for _ in range(4):
#             limiter.record_attempt(key)
#             assert limiter.is_allowed(key, max_attempts=5) is True
#         
#         # 4th attempt should still be allowed
#         assert limiter.is_allowed(key, max_attempts=5) is True

old = '''    def test_allows_under_limit(self):
        """Test requests under limit are allowed"""
        limiter = RateLimiter()
        key = "test_key"
        
        for _ in range(4):
            limiter.record_attempt(key)
            assert limiter.is_allowed(key, max_attempts=5) is True
        
        # 4th attempt should still be allowed
        assert limiter.is_allowed(key, max_attempts=5) is True'''

new = '''    def test_allows_under_limit(self):
        """Test requests under limit are allowed"""
        limiter = RateLimiter()
        key = "test_key"
        
        # First check should be allowed (no attempts yet)
        assert limiter.is_allowed(key, max_attempts=5) is True
        
        for _ in range(4):
            limiter.record_attempt(key)
            assert limiter.is_allowed(key, max_attempts=5) is True
        
        # 4th attempt should still be allowed
        assert limiter.is_allowed(key, max_attempts=5) is True'''

if old in content:
    content = content.replace(old, new)
    with open(r'C:\Users\HUAWEI\.qclaw\workspace-hermes\ACAS-Pro\tests\test_security.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Fixed test_allows_under_limit')
else:
    print('Text not found - trying different approach')
    # Let me search for the function
    idx = content.find('def test_allows_under_limit')
    if idx >= 0:
        print(f'Found function at index {idx}')
        # Show context
        print('Context:')
        print(repr(content[idx:idx+300]))
    else:
        print('Function not found')
