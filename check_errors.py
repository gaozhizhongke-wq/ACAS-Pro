#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import ast
import json

for filename in ['content_logic.py', 'inventory_logic.py']:
    path = f'src/acas_pro/ui/logic/{filename}.bak'
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    try:
        ast.parse(content)
        print(f'{filename}: Syntax OK')
    except SyntaxError as e:
        lines = content.split('\n')
        errors = []
        for i in range(max(0, e.lineno-5), min(len(lines), e.lineno+5)):
            errors.append({'line': i+1, 'content': repr(lines[i])})
        with open(f'{filename}_errors.json', 'w', encoding='utf-8') as f:
            json.dump({'error': f'Line {e.lineno}: {e.msg}', 'context': errors}, f, ensure_ascii=False, indent=2)
        print(f'{filename}: Syntax error saved')
