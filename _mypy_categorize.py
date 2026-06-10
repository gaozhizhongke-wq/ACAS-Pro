#!/usr/bin/env python3
"""Categorize mypy errors."""
import subprocess, sys

result = subprocess.run(
    [sys.executable, "-m", "mypy", "src/", "--ignore-missing-imports",
     "--no-error-summary", "--show-error-codes"],
    capture_output=True, text=True, cwd="."
)

lines = (result.stdout + result.stderr).splitlines()
by_code = {}
by_file = {}
real_bugs = []
annotation_debt = []
qt_stubs = []
misc = []

QT_KEYWORDS = [
    "Qt", "QFont", "QFrame", "QLineEdit", "QMessageBox",
    "QDialog", "QWidget", "QComboBox", "QPushButton", "QTabWidget",
    "QPainter", "QAbstractItemView", "QHeaderView", "QTextCursor",
    "QTableWidget", "QSizePolicy", "QDialogButtonBox", "QLayout",
    "QGridLayout", "QScrollArea", "QtCore", "QtGui", "PyQt",
    "QApplication", "QObject", "QColor", "QIcon", "QAction",
    "QMenu", "QStyle", "QSize", "QPoint", "QRect",
]

REAL_BUG_CODES = {
    "attr-defined", "union-attr", "arg-type", "call-arg", "index",
    "valid-type", "assignment", "name-defined", "operator",
    "override", "overload", "call-overload", "dict-item",
}

ANNO_DEBT_CODES = {
    "no-untyped-def", "func-returns-value", "no-any-return",
    "return-value", "unreachable", "typevar-name", "redundant-expr",
    "truthy-function",
}

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
        lineno = 0

    rest = ":".join(parts[3:]).strip()
    code = ""
    msg = rest
    if "[" in rest and "]" in rest:
        code = rest.split("[")[1].split("]")[0].strip()
        msg = rest.split("]", 1)[1].strip()

    entry = {"file": fname, "line": lineno, "code": code, "msg": msg}

    if code in REAL_BUG_CODES:
        real_bugs.append(entry)
    elif code in ANNO_DEBT_CODES:
        annotation_debt.append(entry)
    elif any(k in msg or k in code for k in QT_KEYWORDS):
        qt_stubs.append(entry)
    else:
        misc.append(entry)

    by_code[code] = by_code.get(code, 0) + 1
    by_file.setdefault(fname, []).append(entry)

total = len(real_bugs) + len(annotation_debt) + len(qt_stubs) + len(misc)
print("CATEGORIZATION:")
print(f"  REAL BUGS (attr-defined/arg-type/etc): {len(real_bugs)}")
print(f"  ANNOTATION DEBT (no-untyped-def/etc): {len(annotation_debt)}")
print(f"  QT STUB ISSUES (PyQt stubs): {len(qt_stubs)}")
print(f"  MISC: {len(misc)}")
print(f"  TOTAL: {total}")
print()
print("By code:")
for code, count in sorted(by_code.items(), key=lambda x: -x[1])[:25]:
    print(f"  {count:4d} x {code}")
print()
print("Top files:")
file_counts = [(f, len(e)) for f, e in by_file.items()]
for fname, count in sorted(file_counts, key=lambda x: -x[1])[:15]:
    print(f"  {count:4d} | {fname}")
print()
print("REAL BUGS (first 20):")
for e in real_bugs[:20]:
    print(f"  {e['file']}:{e['line']} [{e['code']}] {e['msg'][:70]}")
print()
print("ANNOTATION DEBT (first 10):")
for e in annotation_debt[:10]:
    print(f"  {e['file']}:{e['line']} [{e['code']}] {e['msg'][:70]}")
print()
print("MISC (first 10):")
for e in misc[:10]:
    print(f"  {e['file']}:{e['line']} [{e['code']}] {e['msg'][:70]}")
