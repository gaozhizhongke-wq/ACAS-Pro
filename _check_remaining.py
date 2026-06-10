import json
d=json.load(open("bandit_report2.json",encoding="utf-8-sig"))
med=[i for i in d["results"] if i["issue_severity"]=="MEDIUM"]
print(f"Remaining MEDIUM issues: {len(med)}")
print("="*90)
for i in med:
    conf=i["issue_confidence"]
    itype=i["test_name"]
    text=i["issue_text"][:60]
    fname=i["filename"].split("acas_pro/")[-1]
    line=i["line_number"]
    print(f"  [{conf:6s}] {itype:40s} | {text:60s} | {fname}:{line}")
