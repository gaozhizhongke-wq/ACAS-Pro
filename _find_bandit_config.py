#!/usr/bin/env python3
import pathlib

# Search bandit package for skips/nosec config handling
d = pathlib.Path(r"C:\Users\HUAWEI\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\bandit")
found = {}
for f in d.rglob("*.py"):
    if "test" in str(f):
        continue
    try:
        content = f.read_text(encoding="utf-8", errors="ignore")
        for keyword in ["skips", "nosec", "skip_list", "b_id_list"]:
            if keyword in content.lower():
                # Find surrounding context
                lines = content.split("\n")
                for i, line in enumerate(lines):
                    if keyword.lower() in line.lower() and "#" not in line[:5]:
                        indent = len(line) - len(line.lstrip())
                        key = f.name + f":{i+1}"
                        if key not in found:
                            found[key] = line.strip()
    except:  # noqa: E722
        pass

print("Config-related lines found in bandit:")
for k, v in sorted(found.items()):
    print(f"  {k}: {v}")
