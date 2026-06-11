#!/usr/bin/env python3
"""Analyze remaining mypy errors by parsing mypy_result.txt."""
import re
from collections import Counter

with open(r"C:\Users\HUAWEI\.qclaw\workspace-hermes\ACAS-Pro\mypy_result.txt", 'r', encoding='utf-8') as f:
    lines = f.readlines()

errors = [l.strip() for l in lines if 'error:' in l and 'note:' not in l]
print(f'Total error lines: {len(errors)}')

if not errors:
    print("No errors found!")
    exit(0)

# Try multiple regex patterns to match file paths
patterns = [
    r'src\\acas_pro\\[\w\\\]+\.py',  # Windows backslash
    r'src/acas_pro/[\w/]+?\.py',     # Unix forward slash
    r'acas_pro\\[\w\\\]+\.py',        # Relative Windows
    r'acas_pro/[\w/]+?\.py',          # Relative Unix
]

file_counts = Counter()
for e in errors:
    matched = False
    for pattern in patterns:
        m = re.search(pattern, e)
        if m:
            fpath = m.group(0)
            # Extract just the filename (without path)
            fname = fpath.split('\\')[-1].split('/')[-1].replace('.py', '')
            file_counts[fname] += 1
            matched = True
            break
    if not matched:
        # Print first 5 unmatched errors for debugging
        if len(file_counts) < 5:
            print(f"  Unmatched: {e[:100]}")

print(f'Files with errors: {len(file_counts)}')
print()
print('All files with errors:')
for f, c in file_counts.most_common():
    print(f'  {f}: {c}')
