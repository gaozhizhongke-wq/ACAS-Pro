#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix encoding issues in dashboard_logic.py"""

with open('src/acas_pro/ui/logic/dashboard_logic.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix line 431 - wrong indentation and corrupted text
lines[430] = '            alert_text = "无风险"\n'

# Write back
with open('src/acas_pro/ui/logic/dashboard_logic.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Fixed line 431')
