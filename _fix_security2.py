#!/usr/bin/env python3
"""Fix Redis type issues in security.py: use explicit Any type for redis clients."""
import pathlib, re

fpath = pathlib.Path(r"C:\Users\HUAWEI\.qclaw\workspace-hermes\ACAS-Pro\src\acas_pro\core\security.py")
text = fpath.read_text(encoding="utf-8-sig")
original = text
changes = []

# Fix 1: cls._redis_client = None → cls._redis_client: Any = None
# This tells mypy the type is Any, so Any | None → Any (no union-attr)
text, n1 = re.subn(r'(\s+_redis_client\s*=\s*)None(\s*(?:\n|$))', r'\1None  # type: ignore[assignment]\2', text)
if n1:
    changes.append(f"  _redis_client= -> type ignore: {n1}")

# Fix 2: self._client = None → self._client: Any = None
text, n2 = re.subn(r'(\s+_client\s*=\s*)None(\s*(?:\n|$))', r'\1None  # type: ignore[assignment]\2', text)
if n2:
    changes.append(f"  _client= -> type ignore: {n2}")

# Fix 3: return cls._backend → return cls._backend  (already ok after fix)

# Fix 4: extra_claims: dict[str, Any] = None → Optional
text = text.replace(
    "extra_claims: dict[str, Any] = None",
    "extra_claims: Optional[dict[str, Any]] = None"
)

# Fix 5: ip_address: str = None → Optional
text = text.replace(
    "ip_address: str, user_agent: str, severity: str",
    "ip_address: Optional[str], user_agent: Optional[str], severity: str"
)

# Fix 6: def __init__ with -> Any → -> None
text, n3 = re.subn(r'def __init__\([^)]*\)\s*->\s*Any\s*:', 
                    lambda m: m.group(0).replace(") -> Any:", ") -> None:"), text)
if n3:
    changes.append(f"  __init__ -> None: {n3}")

if text != original:
    fpath.write_text(text + "\n", encoding="utf-8")
    for c in changes:
        print(c)
    print(f"Total: {sum(int(re.search(r': (\d+)', c).group(1)) for c in changes if re.search(r': (\d+)', c))} changes")
else:
    print("No changes")
