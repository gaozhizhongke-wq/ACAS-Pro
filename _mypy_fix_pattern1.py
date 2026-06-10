#!/usr/bin/env python3
"""Fix common mypy type errors: dataclass Optional[] and return types."""
import pathlib, re, sys

CWD = r"C:\Users\HUAWEI\.qclaw\workspace-hermes\ACAS-Pro"
FIXES = []

def fix_file(fpath):
    text = fpath.read_text(encoding="utf-8-sig")
    original = text
    changes = 0

    lines = text.split("\n")
    new_lines = []

    for i, line in enumerate(lines):
        orig_line = line
        changed = False

        # Pattern 1: dataclass field = None without Optional
        # e.g. "    database: DatabaseConfig = None"
        # Fix: "    database: Optional[DatabaseConfig] = None"
        m = re.match(r'^(\s+)(\w+)\s*:\s*([\w\[\],\s]+?)\s*=\s*None\s*$', line)
        if m and "Optional[" not in line and ": Optional[" not in line:
            indent, name, type_hint = m.group(1), m.group(2), m.group(3)
            # Check it's not already Optional
            if "Optional" not in type_hint and "Any" not in type_hint:
                # It's a field = None, should be Optional
                line = f"{indent}{name}: Optional[{type_hint}] = None"
                changes += 1
                changed = True

        # Pattern 2: property methods without return type
        # e.g. "    @property\n    def something(self)"  - no return type
        # Already have type annotations, skip

        # Pattern 3: def without return type, has "return" in body
        # Find function def without -> and check if it has return statements
        # This is more complex - skip for now

        new_lines.append(line)

    new_text = "\n".join(new_lines)
    if new_text != original:
        fpath.write_text(new_text + "\n", encoding="utf-8")
        FIXES.append(f"  [FIXED] {fpath.name}: {changes} changes")

    return changes

# Files to fix
files = [
    "src/acas_pro/core/config.py",
    "src/acas_pro/core/logging.py",
    "src/acas_pro/platforms/account_manager.py",
    "src/acas_pro/ecommerce/shop_manager.py",
    "src/acas_pro/db/models.py",
    "src/acas_pro/content/trend_monitor.py",
    "src/acas_pro/llm/conversation.py",
    "src/acas_pro/llm/gemini_engine.py",
    "src/acas_pro/analytics/festival_calendar.py",
]

total = 0
for fpath_str in files:
    p = pathlib.Path(CWD) / fpath_str
    if not p.exists():
        print(f"  [SKIP] {fpath_str} (not found)")
        continue
    n = fix_file(p)
    total += n
    if n:
        print(f"  [FIXED] {fpath_str}: {n} changes")

print(f"\nTotal: {total} changes")
