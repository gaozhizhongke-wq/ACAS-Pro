#!/usr/bin/env python3
"""Fix incorrectly injected logger.error calls in files that don't have module-level logger."""
import glob, re

files = glob.glob(r'F:\自动获客系统\ACAS-Pro\src\acas_pro\**\*.py', recursive=True)
total = 0

for f in files:
    with open(f, 'r', encoding='utf-8') as fh:
        content = fh.read()
    
    if 'Unhandled exception' not in content:
        continue
    
    # Check if file has module-level logger = ...
    has_module_logger = bool(re.search(r'^logger\s*=\s', content, re.MULTILINE))
    
    if has_module_logger:
        continue
    
    # Need to fix: replace 'logger.error(f"Unhandled exception: " + str(e))'
    # with 'import logging; logging.getLogger(__name__).error("Unhandled exception: " + str(e))'
    old = 'logger.error(f"Unhandled exception: " + str(e))'
    new = 'import logging; logging.getLogger(__name__).error("Unhandled exception: " + str(e))'
    
    if old in content:
        content = content.replace(old, new)
        with open(f, 'w', encoding='utf-8') as fh:
            fh.write(content)
        total += 1
        short = f.split('src\\')[-1]
        print(f'Fixed: {short}')

print(f'Total fixed: {total}')
