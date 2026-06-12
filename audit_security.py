import os
import re

issues = {'fstring_sql': [], 'eval_exec': [], 'pickle_load': [], 'assert_prod': [], 'shell_inject': []}

for root, dirs, files in os.walk('src'):
    for fname in files:
        if not fname.endswith('.py'):
            continue
        fpath = os.path.join(root, fname)
        in_multiline_string = False
        try:
            with open(fpath, 'r', encoding='utf-8', errors='ignore') as fh:
                for lineno, line in enumerate(fh, 1):
                    s = line.strip()
                    if not s or s.startswith('#'):
                        continue
                    # f-string SQL in execute
                    if re.search(r'\.execute\s*\(\s*f["\']', line) or \
                       re.search(r'execute\s*\(\s*f["\']', line):
                        issues['fstring_sql'].append((fpath, lineno, line.rstrip()))
                    # eval / exec
                    if re.search(r'(^|\s)(eval|exec)\s*\(', line) and 'JsonResponse' not in line:
                        issues['eval_exec'].append((fpath, lineno, line.rstrip()))
                    # pickle
                    if 'pickle.loads(' in line or 'pickle.load(' in line:
                        issues['pickle_load'].append((fpath, lineno, line.rstrip()))
                    # assert in non-test code (can be disabled with -O)
                    if re.match(r'^\s*assert\b', line) and 'test' not in fpath.lower():
                        issues['assert_prod'].append((fpath, lineno, line.rstrip()))
                    # shell injection risk
                    if re.search(r'os\.system\s*\(|subprocess\.call\s*\([^)]*shell\s*=\s*True', line):
                        issues['shell_inject'].append((fpath, lineno, line.rstrip()))
        except Exception:
            pass

total = sum(len(v) for v in issues.values())
print('=== SECURITY AUDIT RESULT ===')
print(f'Total issues found: {total}\n')
for cat, items in issues.items():
    if items:
        print(f'--- {cat} ({len(items)}) ---')
        for fpath, lineno, line in items[:10]:
            rel = os.path.relpath(fpath)
            print(f'  {rel}:{lineno}: {line[:120]}')
        print()
