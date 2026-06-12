#!/usr/bin/env python3
text = open("mypy_result.txt", encoding="utf-8").read()
errors = [l for l in text.splitlines() if ": error:" in l and "statsmodels" not in l]  # noqa: E741

# Check what file patterns are actually in the errors
sample = errors[0] if errors else ""
print(f"Sample error: {sample[:120]}")
print(f"Total errors: {len(errors)}")

# Try matching a known file
matches = [l for l in errors if "security" in l]  # noqa: E741
print(f"Security errors: {len(matches)}")
for l in matches[:3]:  # noqa: E741
    print(f"  {l[:100]}")
