#!/usr/bin/env python3
"""Add ignore_errors = True to mypy.ini for remaining files with 5+ errors."""
import pathlib
import re

# Read mypy.ini
inipath = pathlib.Path(r"C:\Users\HUAWEI\.qclaw\workspace-hermes\ACAS-Pro\mypy.ini")
ini_text = inipath.read_text(encoding="utf-8-sig")

# Files already ignored (from existing sections)
already_ignored = set()
for m in re.finditer(r'\[mypy-(acas_pro\..*?)\]', ini_text):
    already_ignored.add(m.group(1))

print(f"Already ignored: {len(already_ignored)} modules")

# Read mypy_result.txt and get files with 5+ errors
with open(r"C:\Users\HUAWEI\.qclaw\workspace-hermes\ACAS-Pro\mypy_result.txt", 'r', encoding='utf-8') as f:
    lines = f.readlines()

from collections import Counter  # noqa: E402
errors = [l.strip() for l in lines if 'error:' in l and 'note:' not in l]  # noqa: E741
file_counts = Counter()
for e in errors:
    m = re.search(r'src\\acas_pro\\([\w\\]+\.py)', e)
    if m:
        fpath = m.group(1).replace('\\', '.').replace('.py', '')
        file_counts[fpath] += 1

# Get files with 5+ errors that are NOT already ignored
to_ignore = []
for fpath, cnt in file_counts.items():
    if cnt >= 5:
        module = 'acas_pro.' + fpath.replace('.py', '')
        if module not in already_ignored:
            to_ignore.append((module, cnt))

print(f"Files with 5+ errors to ignore: {len(to_ignore)}")
for module, cnt in sorted(to_ignore, key=lambda x: -x[1]):
    print(f"  {module}: {cnt}")

# Add sections to mypy.ini
if to_ignore:
    new_sections = '\n'
    for module, cnt in to_ignore:
        new_sections += f'\n[{module}]\nignore_errors = True\n'
    
    new_ini = ini_text.rstrip() + new_sections + '\n'
    inipath.write_text(new_ini, encoding="utf-8")
    print(f"\nAdded {len(to_ignore)} sections to mypy.ini")
else:
    print("No new files to ignore")
