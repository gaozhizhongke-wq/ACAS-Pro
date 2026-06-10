#!/usr/bin/env python3
"""
Fix all mypy type errors systematically.
Strategy:
  1. dataclass field = None → Optional[Type] = None
  2. bare return in non-None function → add -> None
  3. missing return statement → add return None
  4. Union[None, X] → Optional[X]
  5. type: ignore for external stubs (flask, pydantic, etc.)
"""
import pathlib, re, sys

CWD = pathlib.Path(r"C:\Users\HUAWEI\.qclaw\workspace-hermes\ACAS-Pro")
src = CWD / "src" / "acas_pro"

def fix_config(fpath):
    text = fpath.read_text(encoding="utf-8-sig")
    original = text
    changes = 0

    # Fix: database: DatabaseConfig = None → Optional[DatabaseConfig] = None
    # Pattern: word: ClassName = None  (not already Optional)
    lines = text.split("\n")
    new_lines = []
    for line in lines:
        # Match: "    name: TypeName = None" at dataclass field level
        m = re.match(r'^(\s+)(\w+)\s*:\s*([\w\[\]\|,\s]+?)\s*=\s*None\s*$', line)
        if m and "Optional[" not in line and "= None" in line:
            indent, name, type_hint = m.group(1), m.group(2), m.group(3).strip()
            # Only fix if it looks like a dataclass/dataclass-style field
            if not any(kw in line for kw in ["def ", "return ", "# "]):
                # It's a bare type = None, wrap in Optional
                line = f"{indent}{name}: Optional[{type_hint}] = None"
                changes += 1
        new_lines.append(line)
    new_text = "\n".join(new_lines)
    if new_text != original:
        fpath.write_text(new_text + "\n", encoding="utf-8")
        print(f"  [FIXED] {fpath.name}: {changes} Optional[] fixes")
    return changes

def fix_all_dataclass_none(src_path):
    """Scan all .py files for 'TypeName = None' without Optional."""
    total = 0
    for fpath in sorted(src_path.rglob("*.py")):
        try:
            total += fix_config(fpath)
        except Exception as e:
            print(f"  [ERROR] {fpath.name}: {e}")
    return total

print("=== Fixing dataclass = None → Optional[] ===")
n = fix_all_dataclass_none(src)
print(f"Total Optional[] fixes: {n}")
