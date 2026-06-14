#!/usr/bin/env python3
# -*- coding: utf-8 -*-
with open('src/acas_pro/ui/logic/content_logic.py', 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

# Fix line 180 - the line is missing closing quote
lines[179] = '        return "18-35岁年轻用户"\n'

with open('src/acas_pro/ui/logic/content_logic.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

# Also fix the .bak file
with open('src/acas_pro/ui/logic/content_logic.py.bak', 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

lines[179] = '        return "18-35岁年轻用户"\n'

with open('src/acas_pro/ui/logic/content_logic.py.bak', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Fixed')
