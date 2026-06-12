#!/usr/bin/env python3
text = open("mypy_result.txt", encoding="utf-8").read()
lines = text.splitlines()
error_lines = [l for l in lines if "error:" in l and "statsmodels" not in l]  # noqa: E741
print(f"Total lines: {len(lines)}")
print(f"Error lines: {len(error_lines)}")
if error_lines:
    print("First 5 errors:")
    for l in error_lines[:5]:  # noqa: E741
        print(f"  {l[:100]}")
