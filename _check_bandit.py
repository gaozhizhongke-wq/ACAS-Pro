import json
d=json.load(open("bandit_report.json",encoding="utf-8-sig"))
high=[i for i in d["results"] if i["issue_severity"]=="HIGH"]
print(f"HIGH issues: {len(high)}")
for i in high:
    print(f'  {i["issue_confidence"]} | {i["issue_text"][:80]} | {i["filename"].split("acas_pro/")[-1]}:{i["line_number"]}')
medium=[i for i in d["results"] if i["issue_severity"]=="MEDIUM"]
print(f"\nMEDIUM issues: {len(medium)}")
