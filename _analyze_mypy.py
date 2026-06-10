#!/usr/bin/env python3
"""Analyze full mypy output."""
import pathlib, re

text = pathlib.Path("mypy_full.txt").read_text(encoding="utf-8")
lines = text.splitlines()

by_code = {}
by_file = {}
errors = []

for line in lines:
    if ": error:" not in line and ": note:" not in line:
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

by_code = {}
by_file = {}
for e in errors:
    by_code[e["code"]] = by_code.get(e["code"], 0) + 1
    by_file.setdefault(e["file"], []).append(e)

print(f"Total errors: {len(errors)}")
print()
print("By code:")
for code, count in sorted(by_code.items(), key=lambda x: -x[1])[:25]:
    print(f"  {count:4d} x [{code}]")
print()
print("Top 20 files by error count:")
for fname, errs in sorted(by_file.items(), key=lambda x: -len(x[1]))[:20]:
    print(f"  {len(errs):4d} | {fname}")

# Real bugs: attr-defined, arg-type, union-attr, call-arg, index, valid-type, assignment
# Annotation debt: no-untyped-def, func-returns-value, return-value, no-any-return, unreachable
# Qt: any Qt/Qxxx in msg
REAL_BUG_CODES = {
    "attr-defined", "union-attr", "arg-type", "call-arg", "index",
    "valid-type", "assignment", "name-defined", "operator",
    "override", "overload", "call-overload",
}
ANNO_CODES = {
    "no-untyped-def", "func-returns-value", "return-value",
    "no-any-return", "unreachable",
}
real = [e for e in errors if e["code"] in REAL_BUG_CODES]
anno = [e for e in errors if e["code"] in ANNO_CODES]
qt = [e for e in errors if any(q in e["msg"] for q in ["Qt", "QFont", "QFrame", "QLineEdit", "QMessageBox",
                                                          "QDialog", "QWidget", "QComboBox", "QPushButton",
                                                          "QTabWidget", "QPainter", "QApplication", "QObject"])]

print()
print(f"REAL BUGS (attr-defined/arg-type/etc): {len(real)}")
print(f"ANNOTATION DEBT (no-untyped-def/etc): {len(anno)}")
print(f"QT STUB ISSUES: {len(qt)}")
print(f"MISC: {len(errors)-len(real)-len(anno)-len(qt)}")
print()
print("REAL BUGS (first 30):")
for e in real[:30]:
    print(f"  {e['file']}:{e['line']} [{e['code']}] {e['msg'][:70]}")
