#!/usr/bin/env python3
# -*- coding: utf-8 -*-
with open('src/acas_pro/ui/logic/dashboard_logic.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix line 697 - add indentation
lines[696] = '        arrow = "↑" if percent > 0 else "↓" if percent < 0 else "→"'

with open('src/acas_pro/ui/logic/dashboard_logic.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Fixed line 697')
