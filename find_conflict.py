"""Find which test file causes test_user_service_full.py to fail"""
import subprocess
import sys
from pathlib import Path

test_dir = Path("tests")
test_files = sorted([f.name for f in test_dir.glob("test_*.py") if f.name != "test_user_service_full.py"])

print(f"Total test files to check: {len(test_files)}")
print("Testing each file combined with test_user_service_full.py...")

conflict_files = []

for test_file in test_files:
    cmd = [
        sys.executable, "-m", "pytest",
        f"tests/{test_file}", "tests/test_user_service_full.py",
        "--no-cov", "-q", "--tb=no"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if "failed" in result.stdout or result.returncode != 0:
        # Check if test_user_service_full.py specifically failed
        if "test_user_service_full.py" in result.stdout:
            conflict_files.append(test_file)
            print(f"  [FAIL] CONFLICT: {test_file}")
        else:
            print(f"  [WARN] OTHER FAIL: {test_file}")
    else:
        print(f"  [OK] OK: {test_file}")

print(f"\nConflict files found: {len(conflict_files)}")
for f in conflict_files:
    print(f"  - {f}")
