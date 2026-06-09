#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix line 423 in dashboard_logic.py"""

with open('src/acas_pro/ui/logic/dashboard_logic.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix line 423 - wrong indentation and corrupted text
lines[422] = '            alert_text = f"{critical}个紧急 {high}个高"\n'

# Write back
with open('src/acas_pro/ui/logic/dashboard_logic.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Fixed line 423')
