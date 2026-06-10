#!/usr/bin/env python3
import mypy.api, pathlib
r = mypy.api.run(["src/", "--ignore-missing-imports", "--no-error-summary"])
open("mypy_result.txt", "w", encoding="utf-8").write(r[0])
print(f"exit: {r[2]}")
lines = [l for l in r[0].split("\n") if "error:" in l and "statsmodels" not in l]
print(f"error lines: {len(lines)}")
if lines:
    # Count by file
    by_file = {}
    for l in lines:
        parts = l.split(":")
        if len(parts) >= 2:
            fname = parts[0].replace("\\", "/").split("acas_pro/")[-1] if "acas_pro/" in parts[0] else parts[0]
            by_file[fname] = by_file.get(fname, 0) + 1
    for fname, count in sorted(by_file.items(), key=lambda x: -x[1])[:15]:
        print(f"  {count:4d} | {fname}")
