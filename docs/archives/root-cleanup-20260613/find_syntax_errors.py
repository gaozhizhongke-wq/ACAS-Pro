#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import ast

filename = 'src/acas_pro/ui/logic/content_logic.py'
with open(filename, 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

errors = []
i = 0
while i < len(lines):
    try:
        ast.parse(''.join(lines[:i+1]))
        i += 1
    except SyntaxError as e:
        errors.append({'line': i+1, 'error': str(e), 'content': repr(lines[i][:100])})
        i += 1

print(f'Found {len(errors)} potential issues:')
for err in errors:
    print(f"Line {err['line']}: {err['content']}")
