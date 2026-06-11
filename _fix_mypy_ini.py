#!/usr/bin/env python3
"""Fix mypy.ini by adding missing 'mypy-' prefix to section names."""
import pathlib
import re

inipath = pathlib.Path(r"C:\Users\HUAWEI\.qclaw\workspace-hermes\ACAS-Pro\mypy.ini")
text = inipath.read_text(encoding="utf-8-sig")

# Find sections like [acas_pro.something] (without mypy- prefix)
# and add the prefix
pattern = r'^\[(acas_pro\..+?)\]'
replacement = r'[mypy-\1]'

new_text = re.sub(pattern, replacement, text, flags=re.MULTILINE)

if new_text != text:
    inipath.write_text(new_text, encoding="utf-8")
    # Count changes
    changes = len(re.findall(pattern, text, flags=re.MULTILINE))
    print(f"Fixed {changes} section names (added 'mypy-' prefix)")
else:
    print("No changes needed")
