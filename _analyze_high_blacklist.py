import json

d = json.load(open("bandit_report2.json", encoding="utf-8-sig"))
bl = [i for i in d["results"] if i["test_name"] == "blacklist"]
print(f"Blacklist issues: {len(bl)}")
print("="*90)
for i in bl:
    text = i["issue_text"][:80]
    fname = i["filename"].replace("\\", "/").split("acas_pro/")[-1]
    line = i["line_number"]
    print(f"  [{i['issue_confidence']:6s}] {text:80s} | {fname}:{line}")
print()
hp = [i for i in d["results"] if i["issue_severity"] == "HIGH"]
print(f"ALL HIGH issues: {len(hp)}")
for i in hp:
    fname = i["filename"].replace("\\", "/").split("acas_pro/")[-1]
    print(f"  [{i['issue_confidence']:6s}] {i['test_name']:40s} | {fname}:{i['line_number']}")
    print(f"    {i['issue_text'][:80]}")
