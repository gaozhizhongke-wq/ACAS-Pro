import os, re

patterns = [
    r'(password|passwd|pwd|secret|api_key|apikey|token|credential)\s*[=:]\s*[\'"]\S+',
    r'(mysql|postgres|redis)://\S+:\S+@',
]

found = []
for root, dirs, files in os.walk('src/acas_pro'):
    dirs[:] = [d for d in dirs if d not in ('__pycache__', '.git')]
    for f in files:
        if not f.endswith('.py'): continue
        fp = os.path.join(root, f)
        with open(fp, encoding='utf-8', errors='ignore') as fh:
            for i, line in enumerate(fh, 1):
                stripped = line.strip()
                if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
                    continue
                for p in patterns:
                    if re.search(p, line, re.I):
                        found.append(f'{fp}:{i}: {stripped[:120]}')
                        break

for f in found:
    print(f)
print(f'\nTotal: {len(found)} lines')
