import json

d = json.load(open("bandit_report2.json", encoding="utf-8-sig"))
low = [i for i in d["results"] if i["issue_severity"] == "LOW"]
non_blacklist = [i for i in low if i["test_name"] != "blacklist"]
print(f"LOW non-blacklist issues: {len(non_blacklist)}")
print("="*90)
for i in non_blacklist:
    conf = i["issue_confidence"]
    itype = i["test_name"]
    text = i["issue_text"][:65]
    fname = i["filename"].replace("\\", "/").split("acas_pro/")[-1]
    line = i["line_number"]
    print(f"  [{conf:6s}] {itype:45s} | {text:65s} | {fname}:{line}")
print()
blacklist = [i for i in low if i["test_name"] == "blacklist"]
print(f"LOW blacklist issues: {len(blacklist)}")
by_file = {}
for i in blacklist:
    fname = i["filename"].replace("\\", "/").split("acas_pro/")[-1]
    by_file.setdefault(fname, []).append(i["line_number"])
for fname, lines in sorted(by_file.items()):
    print(f"  {fname}: lines {lines}")
