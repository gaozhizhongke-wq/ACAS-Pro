"""Binary search for polluter of test_user_service_full.py"""
import subprocess, sys

test_files = [
    "test_e2e_playwright/test_dashboard_e2e.py",
    "test_account_manager.py",
    "test_ads_modules.py",
    "test_all_modules.py",
    "test_all_remaining_modules.py",
    "test_analytics_core.py",
    "test_api.py",
    "test_auth.py",
    "test_business_coverage.py",
    "test_business_logic.py",
    "test_comprehensive_mock.py",
    "test_conversation.py",
    "test_core_0pct.py",
    "test_core_coverage.py",
    "test_coverage_boost.py",
    "test_coverage_boost_v2.py",
    "test_database.py",
    "test_deep_coverage.py",
    "test_diag.py",
    "test_diag2.py",
    "test_e2e.py",
    "test_extreme_coverage.py",
    "test_festival_calendar.py",
    "test_final_all.py",
    "test_final_comprehensive.py",
    "test_final_coverage.py",
    "test_final_mock.py",
    "test_final_mock_all.py",
    "test_full_coverage.py",
    "test_functional_coverage.py",
    "test_import_coverage.py",
    "test_inventory_optimizer.py",
    "test_llm_engines.py",
    "test_llm_tools_focused.py",
    "test_llm_tools_new.py",
    "test_logic_and_analytics.py",
    "test_mass_coverage.py",
    "test_massive_coverage.py",
    "test_massive_mock.py",
    "test_method_calls.py",
    "test_method_coverage.py",
    "test_mock_coverage.py",
    "test_mock_imports.py",
    "test_more_coverage.py",
    "test_more_methods.py",
    "test_more_mock.py",
    "test_product_manager.py",
    "test_security.py",
    "test_services.py",
    "test_settlement_engine.py",
    "test_translator.py",
    "test_ui_coverage.py",
    "test_ui_pages_enhanced.py",
    "test_ui_pages_methods.py",
    "test_ui_pages_mock.py",
    "test_ui_pyside6_all.py",
    "test_ui_web_coverage.py",
    "test_user_service_full.py",
    "test_v2_modules.py",
    "test_web_modules.py",
    "test_zero_pct_modules.py",
]

def run_test(files):
    args = files[:]
    cmd = [sys.executable, "-m", "pytest"] + args + ["--tb=no", "-q", "--no-cov"]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=r"F:\自动获客系统\ACAS-Pro")
    return "33 failed" in r.stdout or "35 failed" in r.stdout or r.returncode != 0

def bisect(candidates, target_file):
    lo, hi = 0, len(candidates)
    while lo < hi:
        mid = (lo + hi) // 2
        subset = [f"tests/{f}" for f in candidates[:mid] if f != target_file] + [f"tests/{target_file}"]
        print(f"  Testing with {mid} files before target...")
        if run_test(subset):
            print(f"  FAILS -> polluter in first {mid} files")
            hi = mid
        else:
            print(f"  PASSES -> polluter in remaining {len(candidates)-mid} files")
            lo = mid + 1
    return candidates[lo-1] if lo > 0 else None

# Full set check
full = [f"tests/{f}" for f in test_files]
print("Checking full set...")
if not run_test(full):
    print("ERROR: Full set passes!")
    sys.exit(1)
print("Full set fails. Starting bisect...")

polluter = bisect(test_files, "test_user_service_full.py")
print(f"\nPOLLUTER: {polluter}")
