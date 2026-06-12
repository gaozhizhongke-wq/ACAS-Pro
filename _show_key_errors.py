#!/usr/bin/env python3
text = open("mypy_result.txt", encoding="utf-8").read()
errors = [l for l in text.splitlines() if ": error:" in l and "statsmodels" not in l]  # noqa: E741

TARGET = {
    "core/security.py": 26,
    "core/database.py": 24,
    "analytics/festival_calendar.py": 33,
    "analytics/data_monitor.py": 25,
    "platforms/account_manager.py": 24,
    "web/health.py": 19,
    "llm/tools.py": 10,
    "llm/agent_engine.py": 11,
    "monitoring/metrics.py": 10,
    "core/async_utils.py": 8,
    "alert/notifier.py": 8,
    "core/security_headers.py": 8,
}

for fname, _ in sorted(TARGET.items(), key=lambda x: -x[1]):
    file_errors = [l for l in errors if fname in l]  # noqa: E741
    if not file_errors:
        continue
    print(f"\n=== {fname} ({len(file_errors)} errors) ===")
    for l in file_errors[:12]:  # noqa: E741
        parts = l.split("[")
        if len(parts) > 1:
            code = parts[-1].split("]")[0].strip()
            msg = parts[-1].split("]")[1].strip() if "]" in l else ""
        else:
            code = ""
            msg = l
        print(f"  [{code:25s}] {msg[:65]}")
    if len(file_errors) > 12:
        print(f"  ... +{len(file_errors)-12} more")
