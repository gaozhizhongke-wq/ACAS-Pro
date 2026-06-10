#!/usr/bin/env python3
import subprocess, sys

result = subprocess.run(
    [sys.executable, "-m", "mypy", "src/", "--ignore-missing-imports", "--no-error-summary"],
    capture_output=True, text=True, cwd="."
)

lines = result.stdout.split("\n") + result.stderr.split("\n")
error_types = {}
by_file = {}
for line in lines:
    if ": error:" not in line and ": note:" not in line:
        continue
    # Parse: path:line:col: error: message [code]
    parts = line.split(":")
    if len(parts) < 4:
        continue
    path = parts[0].replace("\\", "/")
    fname = "/".join(path.split("/")[-2:])
    code = ""
    msg = ":".join(parts[3:]).strip()
    if "[" in msg:
        code = msg.split("[")[1].split("]")[0].strip()
        msg = msg.split("]")[1].strip() if "]" in msg else msg
    error_types[code] = error_types.get(code, 0) + 1
    by_file.setdefault(fname, []).append((line, code))

print("=== mypy error types ===")
for code, count in sorted(error_types.items(), key=lambda x: -x[1]):
    print(f"  {count:4d} x {code}")

print("\n=== Top 20 files by error count ===")
file_counts = [(fname, len(errs)) for fname, errs in by_file.items()]
for fname, count in sorted(file_counts, key=lambda x: -x[1])[:20]:
    print(f"  {count:4d} | {fname}")

print(f"\nTotal errors: {sum(error_types.values())}")
print(f"Total files with errors: {len(by_file)}")
