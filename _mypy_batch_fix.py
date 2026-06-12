#!/usr/bin/env python3
"""Auto-fix common mypy type error patterns across all core files."""
import pathlib
import re

CWD = pathlib.Path(r"C:\Users\HUAWEI\.qclaw\workspace-hermes\ACAS-Pro\src\acas_pro")

def fix_file(fpath: pathlib.Path) -> tuple[int, int]:
    """Fix common patterns. Returns (changes, real_bugs_fixed)."""
    try:
        text = fpath.read_text(encoding="utf-8-sig")
    except Exception:
        return 0, 0
    original = text
    changes = 0
    real_bugs = 0

    # Pattern 1: def func(...) → def func(...) -> None:
    # (functions with no return or only implicit return, missing return type)
    # Skip if already has return type annotation
    def fix_return_types(text):
        nonlocal changes, real_bugs
        lines = text.split("\n")
        new_lines = []
        for i, line in enumerate(lines):
            m = re.match(r'^(\s+def \w+\([^)]*\)):$', line)
            if m:
                # Check if next line is indented more (has body)
                if i + 1 < len(lines) and len(lines[i+1]) > len(lines[i+1].lstrip()):
                    # Check if has return type
                    if "->" not in line:
                        # Check if function body contains "return" statements
                        body_lines = []
                        for j in range(i+1, len(lines)):
                            if lines[j].strip() and not lines[j].startswith(" " * (len(m.group(1)))):
                                break
                            body_lines.append(lines[j])
                        has_return = any("return " in l and not l.strip().startswith("#") for l in body_lines)  # noqa: E741
                        has_pass = any(l.strip() == "pass" for l in body_lines)  # noqa: E741
                        if has_return and not has_pass:
                            new_line = line.replace("):", ") -> Any:")  # conservative
                            new_lines.append(new_line)
                            changes += 1
                        else:
                            new_line = line.replace("):", ") -> None:")
                            new_lines.append(new_line)
                            changes += 1
                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        return "\n".join(new_lines)

    text = fix_return_types(text)

    # Pattern 2: any -> Any, callable -> Callable[..., Any]
    text = text.replace("any]", "Any]")
    text = text.replace(": callable", ": Callable[..., Any]")

    # Pattern 3: self.db: Any = None (already typed, skip)
    # Pattern 4: variable: SomeType = None → Optional[SomeType] = None
    # (dataclass fields)
    def fix_optional_fields(text):
        nonlocal changes
        lines = text.split("\n")
        new_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            m = re.match(r'^(\s+)(\w+)\s*:\s*([\w\[\]\|,\s]+?)\s*=\s*None\s*$', line)
            if m:
                indent, name, typ = m.group(1), m.group(2), m.group(3).strip()
                if "Optional[" not in typ and "Any" not in typ and "=" not in typ:
                    # Check next line for continuation (type annotation too long)
                    if i + 1 < len(lines):
                        next_line = lines[i+1]
                        if next_line.strip().startswith("\\") or next_line.strip() == "":
                            i += 1
                            continue
                    line = f"{indent}{name}: Optional[{typ}] = None"
                    changes += 1
            new_lines.append(line)
            i += 1
        return "\n".join(new_lines)

    text = fix_optional_fields(text)

    if text != original:
        fpath.write_text(text + "\n", encoding="utf-8")
    return changes, real_bugs

# Process all core files
files = list(CWD.rglob("*.py"))
total_changes = 0
for f in sorted(files):
    # Skip UI, avatar, video (already ignored)
    rel = str(f.relative_to(CWD))
    if any(rel.startswith(p) for p in ["ui/", "avatar/", "video/", "update/"]):
        continue
    try:
        c, r = fix_file(f)
        if c > 0:
            print(f"  {rel}: {c} changes")
            total_changes += c
    except Exception as e:
        print(f"  [ERROR] {rel}: {e}")

print(f"\nTotal: {total_changes} changes")
