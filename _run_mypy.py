#!/usr/bin/env python3
"""Run mypy and save full output."""
import subprocess, sys, pathlib

result = subprocess.run(
    [sys.executable, "-m", "mypy", "src/", "--ignore-missing-imports",
     "--no-error-summary", "--show-error-codes"],
    capture_output=True, text=True, cwd="."
)

pathlib.Path("mypy_output.txt").write_text(result.stdout + "\n=== STDERR ===\n" + result.stderr)
print(f"Written {len(result.stdout)} stdout + {len(result.stderr)} stderr chars")
print(result.stdout[:500])
