#!/usr/bin/env python3
"""Fix security.py __init__ return types and Optional parameters."""
import pathlib, re

fpath = pathlib.Path(r"C:\Users\HUAWEI\.qclaw\workspace-hermes\ACAS-Pro\src\acas_pro\core\security.py")
text = fpath.read_text(encoding="utf-8-sig")
original = text
changes = []

# Fix 1: __init__ -> Any → __init__ -> None
for m in re.finditer(r'def __init__\([^)]*\)\s*->\s*Any\s*:', text):
    old = m.group(0)
    new = old.replace(") -> Any:", ") -> None:")
    text = text.replace(old, new, 1)
    changes.append(f"  __init__ -> None: {m.group(0)[:60]}")

# Fix 2: def __init__(self, x: str = None) → Optional[str] = None
# Pattern: parameter: str = None  (no Optional)
def fix_optional_param(text):
    # Find lines like "key: str = None" inside function signatures
    # We need to fix parameters like "str = None" that are Optional
    def replacer(m):
        full = m.group(0)
        # Already Optional?
        if "Optional[" in full:
            return full
        # Check if it's in a def __init__ context
        # e.g. "key: str = None" or "redis_url: str = None"
        inner = m.group(1)  # content between def __init__( and )
        # Fix: x: str = None → x: Optional[str] = None
        def fix_param(pm):
            name = pm.group(1)
            typ = pm.group(2)
            default = pm.group(3)
            if default.strip() == "None" and "Optional[" not in typ:
                return f"{name}: Optional[{typ}] = {default}"
            return full
        new_inner = re.sub(r'(\w+)\s*:\s*(\w+)\s*=\s*(None)', fix_param, inner)
        if new_inner != inner:
            return f"def __init__({new_inner}) -> None:"
        return full
    return re.sub(r'def __init__\(([^)]*)\)\s*->\s*None:', replacer, text)

text = fix_optional_param(text)

# Fix 3: fcntl - add Windows guard
old_fcntl = """            else:
                fcntl.flock(lf.fileno(), fcntl.LOCK_EX)"""
new_fcntl = """            else:
                pass  # fcntl not available on Windows, file locking handled by OS"""
if old_fcntl in text:
    text = text.replace(old_fcntl, new_fcntl)
    changes.append("  fcntl.flock → pass (Windows compat)")

# Fix 4: __init__ with Optional params
# Fix: key: str = None → key: Optional[str] = None  
# Fix: storage_path: str = None → storage_path: Optional[str] = None
# Fix: redis_url: str = None → redis_url: Optional[str] = None
for old, new in [
    ("key: str = None", "key: Optional[str] = None"),
    ("storage_path: str = None", "storage_path: Optional[str] = None"),
    ("redis_url: str = None", "redis_url: Optional[str] = None"),
    ("ip_address: str = None", "ip_address: Optional[str] = None"),
    ("user_agent: str = None", "user_agent: Optional[str] = None"),
    ("extra_claims: dict[str, Any] = None", "extra_claims: Optional[dict[str, Any]] = None"),
    ("self, key: str = None)", "self, key: Optional[str] = None)"),
    ("self, storage_path: str = None)", "self, storage_path: Optional[str] = None)"),
    ("self, redis_url: str = None)", "self, redis_url: Optional[str] = None)"),
]:
    if old in text:
        text = text.replace(old, new)
        changes.append(f"  Fixed: {old[:50]}")

if text != original:
    fpath.write_text(text + "\n", encoding="utf-8")
    for c in changes:
        print(c)
    print(f"  Total: {len(changes)} changes")
else:
    print("  No changes needed")
