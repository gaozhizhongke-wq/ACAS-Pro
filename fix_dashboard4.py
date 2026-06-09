#!/usr/bin/env python3
# -*- coding: utf-8 -*-
with open('src/acas_pro/ui/logic/dashboard_logic.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix line 680 - add indentation
lines[679] = '            return f"{value/10000:.1f}万"\n'

with open('src/acas_pro/ui/logic/dashboard_logic.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Fixed line 680')
