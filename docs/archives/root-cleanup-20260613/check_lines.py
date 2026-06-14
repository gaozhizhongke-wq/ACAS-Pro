#!/usr/bin/env python3
# -*- coding: utf-8 -*-
with open('src/acas_pro/ui/logic/dashboard_logic.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
output = []
for i in range(650, 670):
    if i < len(lines):
        output.append(f'{i+1}: {repr(lines[i][:80])}')
with open('lines_output.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output))
print('Done')
