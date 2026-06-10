#!/usr/bin/env python3
"""Full project analysis for ByteDance delivery readiness."""
import json, subprocess, sys, os

# Run bandit without skip
result = subprocess.run(
    [sys.executable, "-m", "bandit", "-r", "src/", "-ll", "-f", "json", "-q"],
    capture_output=True, text=True, cwd="."
)
try:
    d = json.loads(result.stdout)
    all_results = d.get("results", [])
    high = [i for i in all_results if i["issue_severity"] == "HIGH"]
    med = [i for i in all_results if i["issue_severity"] == "MEDIUM"]
    low = [i for i in all_results if i["issue_severity"] == "LOW"]
    print(f"=== Bandit (no skips) ===")
    print(f"HIGH:   {len(high)}")
    print(f"MEDIUM: {len(med)}")
    print(f"LOW:    {len(low)}")
    print()
    if high:
        print(f"  HIGH issues:")
        for h in high:
            fname = h["filename"].replace("\\", "/").split("acas_pro/")[-1]
            print(f"    [{h['issue_confidence']:6s}] {h['test_name']:40s} | {fname}:{h['line_number']}")
            print(f"      {h['issue_text'][:80]}")
    if med:
        print(f"  MEDIUM issues:")
        for m in med:
            fname = m["filename"].replace("\\", "/").split("acas_pro/")[-1]
            print(f"    [{m['issue_confidence']:6s}] {m['test_name']:40s} | {fname}:{m['line_number']}")
except:
    print(f"JSON parse failed: {result.stdout[:200]}")
    print(f"STDERR: {result.stderr[:200]}")
