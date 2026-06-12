#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Fix content_logic.py
with open('src/acas_pro/ui/logic/content_logic.py.bak', 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

# Fix line 180 (index 179): missing closing quote and parenthesis
content = content.replace(
    '        return "18-35岁年轻用�?\'\n',
    '        return "18-35岁年轻用户"\n'
)

with open('src/acas_pro/ui/logic/content_logic.py', 'w', encoding='utf-8') as f:
    f.write(content)

# Fix inventory_logic.py
with open('src/acas_pro/ui/logic/inventory_logic.py.bak', 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

# Fix line 153 (index 152): unterminated f-string
content = content.replace(
    '                message=f"{len(critical_items)} 个产品库存严重不�?,',
    '                message=f"{len(critical_items)} 个产品库存严重不足",'
)

with open('src/acas_pro/ui/logic/inventory_logic.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed both files')
