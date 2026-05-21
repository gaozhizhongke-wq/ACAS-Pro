#!/usr/bin/env python3
"""运行覆盖率分析并保存到文件"""

import subprocess
import sys
from pathlib import Path

def main():
    # 切换工作目录
    work_dir = r"C:\Users\HUAWEI\.qclaw\workspace-hermes\ACAS-Pro"
    
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
        cwd=work_dir
    )
    
    # 保存完整输出到文件
    output_file = Path(work_dir) / "coverage_output.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("STDOUT:\n")
        f.write(result.stdout)
        f.write("\n\nSTDERR:\n")
        f.write(result.stderr)
    
    print(f"Output saved to: {output_file}", flush=True)
    
    # 解析覆盖率数据
    output = result.stdout + result.stderr
    lines = output.split("\n")
    
    # 解析覆盖率报告
    modules = []
    in_report = False
    
    for line in lines:
        if "-----------" in line or "=======" in line:
            in_report = True
            continue
        if "TOTAL" in line:
            # 解析总计行
            try:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "TOTAL":
                        total_stmts = int(parts[i+1])
                        total_miss = int(parts[i+2])
                        total_cover = int(parts[i+3].rstrip('%'))
                        print(f"\n总计: {total_stmts} 语句, {total_miss} 遗漏, {total_cover}% 覆盖率")
                        print(f"需要额外覆盖 {int(total_stmts * 0.6) - (total_stmts - total_miss)} 行达到60%\n")
                        break
            except (ValueError, IndexError) as e:
                pass
            break
        if in_report and line.strip() and not line.startswith("PASS") and not line.startswith("FAIL"):
            parts = line.split()
            if len(parts) >= 4:
                module = parts[0]
                try:
                    stmts = int(parts[1])
                    miss = int(parts[2])
                    cover_str = parts[3].rstrip('%')
                    if cover_str.isdigit():
                        cover = int(cover_str)
                        
                        # 只关注非UI模块
                        if "ui/pages" not in module and miss > 10:
                            modules.append((module, stmts, miss, cover))
                except (ValueError, IndexError):
                    pass
    
    # 按遗漏行数排序
    modules.sort(key=lambda x: x[2], reverse=True)
    
    # 保存分析结果
    analysis_file = Path(work_dir) / "coverage_analysis.txt"
    with open(analysis_file, "w", encoding="utf-8") as f:
        f.write("非UI模块覆盖率分析（按遗漏行数降序）\n")
        f.write("="*80 + "\n")
        f.write(f"{'模块':<50} {'语句':>6} {'遗漏':>6} {'覆盖率':>6}\n")
        f.write("-"*80 + "\n")
        
        for module, stmts, miss, cover in modules[:30]:
            f.write(f"{module:<50} {stmts:>6} {miss:>6} {cover:>5}%\n")
        
        f.write("\n建议优先覆盖的模块（遗漏行数>=20且非UI）:\n")
        f.write("-"*80 + "\n")
        for module, stmts, miss, cover in modules:
            if miss >= 20 and "ui" not in module.lower():
                f.write(f"  {module}: {miss} 行未覆盖 ({cover}% 覆盖率)\n")
    
    print(f"Analysis saved to: {analysis_file}", flush=True)
    
    return modules

if __name__ == "__main__":
    main()
