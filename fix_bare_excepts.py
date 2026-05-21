#!/usr/bin/env python3
"""Fix bare except blocks that have no logger call."""
import os, glob

files = glob.glob(r'F:\自动获客系统\ACAS-Pro\src\acas_pro\**\*.py', recursive=True)
total_fixes = 0

for f in files:
    with open(f, 'r', encoding='utf-8') as fh:
        content = fh.read()
    lines = content.split('\n')
    new_lines = []
    changed = False
    
    for i, line in enumerate(lines):
        new_lines.append(line)
        stripped = line.strip()
        if 'except Exception as e:' not in stripped:
            continue
        # Check if next non-empty lines already have logger
        has_logger = False
        for j in range(i+1, min(i+6, len(lines))):
            jline = lines[j].strip()
            if jline and 'logger' in lines[j]:
                has_logger = True
                break
            if jline and 'logger' not in lines[j]:
                break
        if has_logger:
            continue
        
        indent = len(line) - len(line.lstrip())
        indent_str = ' ' * (indent + 4)
        
        if 'logger = ' in content or 'get_logger' in content or 'logging.getLogger' in content:
            logger_call = indent_str + 'logger.error(f"Unhandled exception: " + str(e))'
        else:
            logger_call = indent_str + 'import logging; logging.getLogger(__name__).error("Unhandled exception: " + str(e))'
        
        new_lines.append(logger_call)
        changed = True
        total_fixes += 1
    
    if changed:
        with open(f, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(new_lines))

print(f'Fixed {total_fixes} blocks')
