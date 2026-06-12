#!/usr/bin/env python3
"""Analyze remaining errors, distinguish real bugs from annotation debt."""
import pathlib

text = pathlib.Path("mypy_full2.txt").read_text(encoding="utf-8")
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
    except:  # noqa: E722
        continue
    rest = ":".join(parts[3:]).strip()
    code = ""
    msg = rest
    if "[" in rest and "]" in rest:
        code = rest.split("[")[1].split("]")[0].strip()
        msg = rest.split("]", 1)[1].strip()
    errors.append({"file": fname, "line": lineno, "code": code, "msg": msg})

# Real bugs (requires code change, not just adding types)
REAL_BUG = {"attr-defined", "union-attr", "arg-type", "call-arg", "index",
            "valid-type", "name-defined", "operator", "override", "overload"}

# Annotation debt (need to add type annotations)
ANNO_DEBT = {"no-untyped-def", "func-returns-value", "return-value",
             "no-any-return", "assignment", "unreachable"}

# External stubs issues
EXTERNAL = {"Qt", "QFont", "QFrame", "QLineEdit", "QMessageBox",
            "QDialog", "QWidget", "QComboBox", "QPushButton",
            "QTabWidget", "QPainter", "QApplication", "QObject"}

real = [e for e in errors if e["code"] in REAL_BUG]
anno = [e for e in errors if e["code"] in ANNO_DEBT]
ext  = [e for e in errors if any(k in e["msg"] for k in EXTERNAL)]
other= [e for e in errors if e not in real and e not in anno and e not in ext]

print(f"TOTAL: {len(errors)}")
print(f"REAL BUGS:      {len(real)}")
print(f"ANNOTATION DEBT:{len(anno)}")
print(f"EXTERNAL STUBS: {len(ext)}")
print(f"OTHER:          {len(other)}")
print()
print("REAL BUGS by file:")
by_f = {}
for e in real:
    by_f.setdefault(e["file"], []).append(e)
for fname, errs in sorted(by_f.items(), key=lambda x: -len(x[1]))[:20]:
    print(f"  {len(errs):4d} | {fname}")

print()
print("REAL BUGS - core business files (first 30):")
for e in real[:30]:
    print(f"  {e['file']}:{e['line']} [{e['code']:22s}] {e['msg'][:65]}")

print()
print("OTHER errors (first 15):")
for e in other[:15]:
    print(f"  {e['file']}:{e['line']} [{e['code']:22s}] {e['msg'][:65]}")
