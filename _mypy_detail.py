#!/usr/bin/env python3
"""Get detailed error lines for top files."""
import pathlib

text = pathlib.Path("mypy_full.txt").read_text(encoding="utf-8")
lines = text.splitlines()

errors = []
for line in lines:
    if ": error:" not in line:
        continue
    parts = line.split(":")
    if len(parts) < 4:
        continue
    fname = parts[0].replace("\\", "/")
    if "acas_pro/" in fname:
        fname = fname.split("acas_pro/")[-1]
    try:
        lineno = int(parts[1])
    except:  # noqa: E722
        continue
    rest = ":".join(parts[3:]).strip()
    code = ""
    msg = rest
    if "[" in rest and "]" in rest:
        code = rest.split("[")[1].split("]")[0].strip()
        msg = rest.split("]", 1)[1].strip()
    errors.append({"file": fname, "line": lineno, "code": code, "msg": msg})

TARGET_FILES = [
    "web/health.py",
    "core/security.py",
    "core/database.py",
    "db/models.py",
    "video/video_maker.py",
    "analytics/data_monitor.py",
    "platforms/account_manager.py",
    "analytics/festival_calendar.py",
    "publisher/publish_manager.py",
    "ecommerce/platform_api_base.py",
    "llm/tools.py",
    "llm/conversation.py",
    "llm/gemini_engine.py",
    "core/config.py",
    "core/logging.py",
    "ecommerce/shop_manager.py",
    "avatar/scene_adapter.py",
    "sentiment/news_engine.py",
    "content/trend_monitor.py",
]

for target in TARGET_FILES:
    file_errors = [e for e in errors if e["file"] == target]
    if not file_errors:
        continue
    print(f"\n=== {target} ({len(file_errors)} errors) ===")
    for e in file_errors[:15]:
        print(f"  L{e['line']:4d} [{e['code']:22s}] {e['msg'][:65]}")
    if len(file_errors) > 15:
        print(f"  ... +{len(file_errors)-15} more")
