#!/usr/bin/env python3
"""Run pytest and save output to file."""
import pytest
import sys
import io

# Capture output
output = io.StringIO()
sys.stdout = output
sys.stderr = output

# Run pytest
exit_code = pytest.main([
    "tests/unit/",
    "-v",
    "--tb=no",
    "-q",
    "--override-ini=addopts=",
])

# Restore stdout/stderr
sys.stdout = sys.__stdout__
sys.stderr = sys.__stderr__

# Get output
test_output = output.getvalue()

# Print output
print(test_output)

# Save to file
with open("_test_output.txt", "w", encoding="utf-8") as f:
    f.write(test_output)

# Print summary
lines = test_output.strip().split("\n")
for line in lines:
    if "passed" in line or "failed" in line or "skipped" in line:
        print(line)
        break

sys.exit(exit_code)
