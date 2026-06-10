#!/usr/bin/env python3
"""Analyze real bugs and group by file."""
import pathlib

text = pathlib.Path("mypy_full.txt").read_text(encoding="utf-8")
lines = text.splitlines()

errors = []
for line in lines:
    if ": error:" not in line:
        continue
    parts = line.split(":")
    if len(parts) < 4:
        continue
    fname = parts[0].replace("\\", "/")
    if "acas_pro/" in fname:
        fname = fname.split("acas_pro/")[-1]
    try:
        lineno = int(parts[1])
    except:
        continue
    rest = ":".join(parts[3:]).strip()
    code = ""
    msg = rest
    if "[" in rest and "]" in rest:
        code = rest.split("[")[1].split("]")[0].strip()
        msg = rest.split("]", 1)[1].strip()

    errors.append({"file": fname, "line": lineno, "code": code, "msg": msg})

REAL_CODES = {
    "attr-defined", "union-attr", "arg-type", "call-arg", "index",
    "valid-type", "assignment", "name-defined", "operator",
    "override", "overload", "call-overload", "dict-item",
}

real = [e for e in errors if e["code"] in REAL_CODES]

print(f"Real bugs: {len(real)}")
print()

# Group by file
by_file = {}
for e in real:
    by_file.setdefault(e["file"], []).append(e)

for fname, errs in sorted(by_file.items(), key=lambda x: -len(x[1]))[:30]:
    codes = {}
    for e in errs:
        codes[e["code"]] = codes.get(e["code"], 0) + 1
    code_str = ", ".join(f"{c}={n}" for c, n in sorted(codes.items(), key=lambda x: -x[1]))
    print(f"{fname}: {len(errs)} errors [{code_str}]")
    for e in errs[:3]:
        print(f"  L{e['line']:4d} [{e['code']:20s}] {e['msg'][:60]}")
    if len(errs) > 3:
        print(f"  ... and {len(errs)-3} more")
