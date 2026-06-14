#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix syntax errors in llm_chat_fixed.py caused by mojibake (encoding corruption)."""

import os
import py_compile

target = os.path.join(os.path.dirname(__file__), 'src', 'acas_pro', 'ui', 'pages', 'llm_chat_fixed.py')

with open(target, 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

print(f"File has {len(lines)} lines")

# Show lines 410-428 (0-indexed = 411-429 1-indexed) with repr
for i in range(410, min(429, len(lines))):
    print(f"{i+1}: {repr(lines[i].rstrip())}")

# Fix line 415 (0-indexed = 414): QLabel("未连�?")  -> QLabel("未连接")
if len(lines) > 414:
    line415 = lines[414]
    if '?' in line415 or '\ufffd' in line415:
        # The string is corrupted: the closing " is missing / replaced by mojibake
        # Rebuild the line: '        self.status_label = QLabel("未连接")\n'
        lines[414] = '        self.status_label = QLabel("未连接")\n'
        print("Fixed line 415")

# Fix line 425 (0-indexed = 424): QPushButton("新对�?") -> QPushButton("新对话")
if len(lines) > 424:
    line425 = lines[424]
    if '?' in line425 or '\ufffd' in line425:
        lines[424] = '        new_chat_btn = QPushButton("新对话")\n'
        print("Fixed line 425")

# Write back
with open(target, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("File fixed and saved.")

# Verify syntax
try:
    py_compile.compile(target, doraise=True)
    print("Syntax check: PASSED")
except py_compile.PyCompileError as e:
    print(f"Syntax check FAILED: {e}")
