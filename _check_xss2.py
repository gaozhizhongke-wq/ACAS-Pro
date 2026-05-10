import re
with open(r'F:\自动获客系统\ACAS-Pro\web_app.py', encoding='utf-8') as f:
    content = f.read()
# Find innerHTML assignments that use template literals with unescaped data
# Pattern: el.innerHTML = '...' + data.property + ...
pattern = r"\.innerHTML\s*=\s*['\"](?=.*\$\{)([^'\"]*\$\{[^}]+\}[^'\"]*)['\"]"
matches = list(re.finditer(pattern, content))
for m in matches:
    line = content[:m.start()].count('\n') + 1
    print(f'Line {line}: {m.group()[:100]}')