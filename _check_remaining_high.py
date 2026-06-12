#!/usr/bin/env python3
import subprocess
import json
import sys
result = subprocess.run(
    [sys.executable, "-m", "bandit", "-r", "src/", "-ll", "--skip", "B608,B311", "-f", "json", "-q"],
    capture_output=True, text=True, cwd="."
)
d = json.loads(result.stdout)
r = d.get("results", [])
high = [i for i in r if i["issue_severity"] == "HIGH"]
med = [i for i in r if i["issue_severity"] == "MEDIUM"]
low = [i for i in r if i["issue_severity"] == "LOW"]
print(f"HIGH: {len(high)}  MEDIUM: {len(med)}  LOW: {len(low)}")
for i in high:
    fname = i["filename"].replace("\\", "/").split("acas_pro/")[-1]
    print(f"  HIGH | {i['test_name']:35s} | {fname}:{i['line_number']}")
    print(f"       | {i['issue_text'][:80]}")
for i in med:
    fname = i["filename"].replace("\\", "/").split("acas_pro/")[-1]
    print(f"  MED | {i['test_name']:35s} | {fname}:{i['line_number']}")
    print(f"       | {i['issue_text'][:80]}")
