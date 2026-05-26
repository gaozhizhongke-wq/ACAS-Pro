#!/usr/bin/env python3
"""Test imports for modules that tests are trying to import."""

import sys
import os
import traceback

# Add src directory to path so acas_pro can be found
src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
sys.path.insert(0, src_path)

modules_to_test = [
    "acas_pro.alert.notifier",
    "acas_pro.advanced_analytics.smart_decider",
    "acas_pro.platforms.douyin",
    "acas_pro.platforms.xiaohongshu",
    "acas_pro.platforms.kuaishou",
    "acas_pro.platforms.bilibili",
    "acas_pro.publisher.blockchain_publisher",
    "acas_pro.publisher.scheduler",
    "acas_pro.ml.timesfm",
    "acas_pro.ml.timesfm_v2",
]

print("Testing module imports...")
print("=" * 60)

results = []
for module_name in modules_to_test:
    try:
        __import__(module_name)
        results.append((module_name, "OK", ""))
        print(f"  [OK] {module_name}")
    except ImportError as e:
        results.append((module_name, "IMPORT ERROR", str(e)))
        print(f"  [FAIL] {module_name}: {e}")
    except Exception as e:
        results.append((module_name, "ERROR", str(e)))
        print(f"  [ERROR] {module_name}: {e}")

print("=" * 60)
print(f"\nSummary: {sum(1 for r in results if r[1] == 'OK')} OK, "
      f"{sum(1 for r in results if r[1] != 'OK')} failed")

# Also check if __init__.py files exist
print("\nChecking __init__.py files...")
init_files = [
    "src/acas_pro/alert/__init__.py",
    "src/acas_pro/advanced_analytics/__init__.py",
    "src/acas_pro/publisher/__init__.py",
    "src/acas_pro/ml/__init__.py",
    "src/acas_pro/platforms/__init__.py",
]

import os
for init_file in init_files:
    if os.path.exists(init_file):
        print(f"  [OK] {init_file} exists")
    else:
        print(f"  [FAIL] {init_file} MISSING")
