import json
d=json.load(open("bandit_report.json",encoding="utf-8-sig"))
medium=[i for i in d["results"] if i["issue_severity"]=="MEDIUM"]
print(f"MEDIUM issues: {len(medium)}")
print("="*80)
for i in medium:
    conf = i["issue_confidence"]
    itype = i["issue_type"]
    text = i["issue_text"][:70]
    fname = i["filename"].split("acas_pro/")[-1]
    line = i["line_number"]
    print(f"  [{conf}] {itype} | {text} | {fname}:{line}")
