import os, re, sys

issues = []
target_dirs = ['src']

patterns = [
    re.compile(r'(password|passwd|pwd)\s*=\s*[\'"][^\'"]{4,}', re.I),
    re.compile(r'(secret|api_key|apikey|token)\s*=\s*[\'"][^\'"]{8,}', re.I),
    re.compile(r'(aws_|ACCESS|SECRET|PRIVATE).*=[^=]', re.I),
]

safe_patterns = ['os.environ', 'getenv', 'config(', 'os.getenv', '#', '"""', "'''"]

for d in target_dirs:
    for root, dirs, files in os.walk(d):
        for fname in files:
            if not fname.endswith('.py'):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as fh:
                    for lineno, line in enumerate(fh, 1):
                        line_stripped = line.strip()
                        if not line_stripped or line_stripped.startswith('#'):
                            continue
                        for pat in patterns:
                            if pat.search(line):
                                if any(safe in line for safe in safe_patterns):
                                    continue
                                issues.append((fpath, lineno, line.rstrip()))
            except Exception as e:
                pass

print(f'Found {len(issues)} potential hardcoded credential lines:')
for fpath, lineno, line in issues[:50]:
    rel = os.path.relpath(fpath)
    print(f'  {rel}:{lineno}: {line[:120]}')
