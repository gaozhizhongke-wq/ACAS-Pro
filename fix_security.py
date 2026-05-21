import re

content = open('tests/test_security.py', 'r', encoding='utf-8').read()

# Find and replace the test_allows_under_limit method
old_text = """    def test_allows_under_limit(self):
        \"\"\"Test requests under limit are allowed\"\"\"
        limiter = RateLimiter()
        key = "test_key"
        
        for _ in range(4):"""

new_text = """    def test_allows_under_limit(self):
        \"\"\"Test requests under limit are allowed\"\"\"
        limiter = RateLimiter()
        key = "test_key"
        
        # First check should be allowed (no attempts yet)
        assert limiter.is_allowed(key, max_attempts=5) is True
        
        for _ in range(4):"""

content = content.replace(old_text, new_text)
open('tests/test_security.py', 'w', encoding='utf-8').write(content)
print('Done')
