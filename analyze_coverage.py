#!/usr/bin/env python3
"""分析覆盖率报告，找出非UI模块中遗漏行数最多的模块"""

import subprocess
import sys
from pathlib import Path

def main():
    # 运行 pytest 并生成覆盖率报告
    print("Running pytest with coverage...", flush=True)
    result = subprocess.run(
        [
            ".venv/Scripts/python.exe",
            "-m", "pytest",
            "--tb=no", "-q",
            "--cov=src/acas_pro",
            "--cov-report=term-missing",
            "--no-header"
        ],
        capture_output=True,
        text=True,
        cwd=r"C:\Users\HUAWEI\.qclaw\workspace-hermes\ACAS-Pro"
    )
    
    output = result.stdout + result.stderr
    lines = output.split("\n")
    
    # 解析覆盖率报告
    modules = []
    in_report = False
    
    for line in lines:
        if "-----------" in line:
            in_report = True
            continue
        if "TOTAL" in line:
            break
        if in_report and line.strip():
            parts = line.split()
            if len(parts) >= 4:
                module = parts[0]
                try:
                    stmts = int(parts[1])
                    miss = int(parts[2])
                    cover = int(parts[3].rstrip('%'))
                    
                    # 只关注非UI模块（UI模块需要PySide6，很难测试）
                    if "ui/pages" not in module and miss > 10:
                        modules.append((module, stmts, miss, cover))
                except (ValueError, IndexError):
                    pass
    
    # 按遗漏行数排序
    modules.sort(key=lambda x: x[2], reverse=True)
    
    print("\n" + "="*80)
    print("非UI模块覆盖率分析（按遗漏行数降序）")
    print("="*80)
    print(f"{'模块':<50} {'语句':>6} {'遗漏':>6} {'覆盖率':>6}")
    print("-"*80)
    
    total_stmts = 0
    total_miss = 0
    
    for module, stmts, miss, cover in modules[:30]:  # 显示前30个
        print(f"{module:<50} {stmts:>6} {miss:>6} {cover:>5}%")
        total_stmts += stmts
        total_miss += miss
    
    print("-"*80)
    print(f"{'合计(前30个模块)':<50} {total_stmts:>6} {total_miss:>6}")
    print(f"\n需要额外覆盖 {700} 行才能达到60%覆盖率")
    
    # 建议
    print("\n建议优先覆盖的模块（遗漏行数>20且非UI）:")
    print("-"*80)
    for module, stmts, miss, cover in modules:
        if miss >= 20 and "ui" not in module.lower():
            print(f"  {module}: {miss} 行未覆盖 ({cover}% 覆盖率)")
    
    return modules

if __name__ == "__main__":
    main()
