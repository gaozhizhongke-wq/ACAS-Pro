#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch fix: datetime.utcnow() → datetime.now(timezone.utc) in all ACAS-Pro files"""
import os, re

base = r"F:\自动获客系统\ACAS-Pro"

# Files needing fix (from grep results, deduplicated)
files = {
    r"src\acas_pro\alert\notifier.py": [56, 348],
    r"src\acas_pro\collectors\weibo_api.py": [229],
    r"src\acas_pro\core\monitoring.py": [105, 125, 283, 300],
    r"src\acas_pro\metrics\brand_reputation.py": [60, 439, 450, 461],
    r"src\acas_pro\ml\inventory_optimizer.py": [273],
    r"src\acas_pro\ml\timesfm_engine.py": [208, 327, 347],
    r"src\acas_pro\sentiment\analyzer.py": [197],
    r"src\acas_pro\sentiment\news_engine.py": [170, 176, 191, 202, 322, 329, 330],
    r"src\core\logging.py": [53, 89, 178],
    r"src\core\security.py": [113, 166, 217, 258, 277],
    r"src\ml\inventory_optimizer.py": [273],
    r"src\ml\timesfm_engine.py": [139, 261, 281],
    r"src\sentiment\analyzer.py": [197],
    r"src\sentiment\news_engine.py": [170, 176, 191, 202, 322, 329, 330],
    r"src\services\user_service.py": [77, 79, 161, 162, 176, 206, 230, 231],
}

count = 0
for rel_path, _ in files.items():
    full = os.path.join(base, rel_path)
    if not os.path.exists(full):
        print(f"SKIP (not found): {rel_path}")
        continue

    with open(full, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # Add import at top if not already present
    if 'from datetime import' in content and 'timezone' not in content.split('from datetime import')[1].split('\n')[0]:
        # Already has datetime import but no timezone
        content = re.sub(
            r'(from datetime import [^,\n]+)',
            r'\1, timezone',
            content, count=1
        )
    elif 'from datetime import' not in content and 'import datetime' not in content:
        # No datetime import at all
        content = 'from datetime import datetime, timezone\n' + content
    elif 'import datetime' in content and 'timezone' not in content:
        content = content.replace('import datetime', 'import datetime; from datetime import timezone')

    # Replace utcnow() calls
    content = content.replace('datetime.utcnow()', 'datetime.now(timezone.utc)')

    if content != original:
        with open(full, 'w', encoding='utf-8') as f:
            f.write(content)
        changed = content.count('datetime.now(timezone.utc)')
        print(f"FIXED: {rel_path} (+{changed} datetime.now(timezone.utc))")
        count += 1
    else:
        print(f"NO CHANGE: {rel_path}")

print(f"\nTotal files updated: {count}")