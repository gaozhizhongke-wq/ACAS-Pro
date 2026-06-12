#!/usr/bin/env python3
"""Run bandit and save JSON report."""
import subprocess
import json
import sys

result = subprocess.run(
    [sys.executable, "-m", "bandit", "-r", "src/", "-f", "json", "-q"],
    capture_output=True, text=True, cwd="."
)
# Write stdout (JSON) to file
with open("bandit_report2.json", "w", encoding="utf-8") as f:
    f.write(result.stdout)

# Also print any errors
if result.stderr:
    print("STDERR:", result.stderr[:500])

# Check if JSON is valid
try:
    d = json.loads(result.stdout)
    print(f"bandit done: {len(d.get('results', []))} issues found")
except Exception as e:
    print(f"JSON parse error: {e}")
    print(f"stdout[:200]: {result.stdout[:200]}")
