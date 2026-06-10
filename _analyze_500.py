#!/usr/bin/env python3
text = open("mypy_result.txt", encoding="utf-8").read()
lines = text.splitlines()
errors = [l for l in lines if ": error:" in l and "statsmodels" not in l]
by_code = {}
by_file = {}
real_bugs = []
for l in errors:
    parts = l.split(":")
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
    by_code[code] = by_code.get(code, 0) + 1
    by_file.setdefault(fname, []).append(l)

print(f"TOTAL: {len(errors)}")
print()
print("By code:")
for code, count in sorted(by_code.items(), key=lambda x: -x[1])[:15]:
    print(f"  {count:4d} x [{code}]")
print()
print("Top 20 files:")
for fname, errs in sorted(by_file.items(), key=lambda x: -len(x[1]))[:20]:
    print(f"  {len(errs):4d} | {fname}")
