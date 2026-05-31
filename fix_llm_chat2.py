#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix all mojibake-corrupted string literals in llm_chat_fixed.py.
The file has corrupted Chinese characters that break string closing quotes.
We fix by reading the file as bytes, finding the corrupted patterns, and patching them.
"""

import os
import re

target = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       'src', 'acas_pro', 'ui', 'pages', 'llm_chat_fixed.py')

# Read raw bytes
with open(target, 'rb') as f:
    raw = f.read()

print(f"File size: {len(raw)} bytes")

# Decode with errors='replace' to find mojibake positions
text = raw.decode('utf-8', errors='replace')

lines = text.split('\n')
print(f"Total lines: {len(lines)}")

# Find all lines with U+FFFD replacement character (the �)
bad_lines = []
for i, line in enumerate(lines):
    if '\ufffd' in line:
        bad_lines.append((i+1, line[:100]))

print(f"\nLines with mojibake ({len(bad_lines)}):")
for lineno, content in bad_lines:
    print(f"  Line {lineno}: {repr(content[:80])}")

# Now fix: the pattern is that Chinese text like "未连接" got corrupted
# and the closing quote is missing (the �? ate it).
# Strategy: for each bad line, if it contains an unclosed QLabel( or QPushButton( call,
# rebuild the line with proper closing.

# Actually, simpler: just fix known patterns
fixes = {
    # line_no (1-indexed): new_line
    415: '        self.status_label = QLabel("未连接")',
    425: '        new_chat_btn = QPushButton("新对话")',
}

# Apply fixes
new_lines = list(lines)  # lines from split('\n')
for lineno, new_content in fixes.items():
    idx = lineno - 1  # 0-indexed
    if idx < len(new_lines):
        old = new_lines[idx]
        new_lines[idx] = new_content
        print(f"\nFixed line {lineno}:")
        print(f"  OLD: {repr(old[:80])}")
        print(f"  NEW: {repr(new_content)}")

# Write back
new_text = '\n'.join(new_lines)
with open(target, 'w', encoding='utf-8') as f:
    f.write(new_text)

print("\nFile saved. Running syntax check...")

import py_compile, sys
try:
    py_compile.compile(target, doraise=True)
    print("Syntax check: PASSED")
except py_compile.PyCompileError as e:
    print(f"Syntax check FAILED: {e}")
    # If there are more errors, show all bad lines
    sys.exit(1)
