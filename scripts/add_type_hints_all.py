#!/usr/bin/env python3
"""批量添加类型注解脚本 - 针对 ACAS-Pro 所有模块"""
import ast
from pathlib import Path
from typing import List, Tuple

def find_untyped_functions(file_path: str) -> List[Tuple[int, str, str]]:
    """查找缺少类型注解的函数"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []
    
    untyped = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # 检查是否有返回类型注解
            has_return_annotation = node.returns is not None
            # 检查参数是否有类型注解
            has_param_annotations = any(
                arg.annotation is not None 
                for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs
            )
            # 忽略 __init__ (返回 None 是标准)
            if node.name == '__init__':
                continue
            
            if not has_return_annotation and not has_param_annotations:
                # 获取函数签名行
                line_num = node.lineno
                untyped.append((line_num, node.name, 'missing_all'))
            elif not has_return_annotation:
                line_num = node.lineno
                untyped.append((line_num, node.name, 'missing_return'))
    
    return untyped

def process_file(file_path: str) -> int:
    """处理单个文件，添加类型注解"""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    untyped = find_untyped_functions(file_path)
    if not untyped:
        return 0
    
    modified = 0
    # 从后往前修改，避免行号偏移
    for line_num, func_name, missing_type in sorted(untyped, reverse=True):
        line_idx = line_num - 1
        if line_idx >= len(lines):
            continue
        
        line = lines[line_idx]
        # 简单的模式匹配来添加 -> None
        if missing_type in ('missing_all', 'missing_return'):
            # 查找 def 语句的结尾
            if '(' in line and ')' in line:
                # 尝试在 ) 后面添加 -> None
                # 处理多行函数定义
                if line.rstrip().endswith(':'):
                    # 单行定义
                    new_line = line.rstrip()[:-1] + ' -> None:'
                    lines[line_idx] = new_line + '\n'
                    modified += 1
    
    if modified > 0:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
    
    return modified

def main():
    """主函数"""
    src_dir = Path('src/acas_pro')
    
    total_modified = 0
    files_processed = 0
    
    # 处理所有模块
    for py_file in src_dir.rglob('*.py'):
        if py_file.name.endswith('_test.py') or py_file.name.startswith('test_'):
            continue
        
        modified = process_file(str(py_file))
        if modified > 0:
            total_modified += modified
            files_processed += 1
            print(f"Modified {py_file}: {modified} functions")
    
    print(f"\nTotal: {total_modified} functions modified in {files_processed} files")

if __name__ == '__main__':
    main()
