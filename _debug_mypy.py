import subprocess
import sys

result = subprocess.run(
    [sys.executable, "-m", "mypy", "src/", "--ignore-missing-imports",
     "--no-error-summary", "--show-error-codes"],
    capture_output=True, text=True, cwd=".",
    encoding="utf-8", errors="replace"
)

# Check what we got
out = result.stdout
err = result.stderr
print(f"stdout length: {len(out)}")
print(f"stderr length: {len(err)}")
print(f"stdout first 300: {out[:300]}")
print(f"stderr first 300: {err[:300]}")
