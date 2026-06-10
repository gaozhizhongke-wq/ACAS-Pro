import json

d = json.load(open("bandit_report.json", encoding="utf-8-sig"))
medium = [i for i in d["results"] if i["issue_severity"] == "MEDIUM"]
print(f"MEDIUM issues: {len(medium)}")
print("="*90)
for i in medium:
    conf = i["issue_confidence"]
    itype = i["test_name"]   # e.g. "subprocess_without_shell_equals_true"
    text = i["issue_text"][:65]
    # normalize path
    fname = i["filename"].replace("\\", "/").split("acas_pro/")[-1]
    line = i["line_number"]
    print(f"  [{conf:6s}] {itype:40s} | {text:65s} | {fname}:{line}")
