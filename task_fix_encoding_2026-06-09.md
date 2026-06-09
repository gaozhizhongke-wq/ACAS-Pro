# 修复编码问题 - 任务记录

**开始时间**: 2026-06-09 00:50 GMT+8

## 目标
修复以下文件的 UTF-8 编码问题：
1. `src/acas_pro/ui/logic/dashboard_logic.py.bak`
2. `src/acas_pro/ui/logic/content_logic.py.bak`
3. `src/acas_pro/ui/logic/inventory_logic.py.bak`

## 问题
这些文件包含非 UTF-8 编码的字节序列，导致 Python 无法解析。

## 步骤
1. 读取 .bak 文件
2. 识别编码错误的行
3. 修复编码问题
4. 恢复文件
5. 运行测试验证
