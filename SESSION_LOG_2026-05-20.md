ACAS-Pro 测试覆盖率优化工作记录（2026-05-20 会话）

## 会话目标
继续提升 ACAS-Pro 项目测试覆盖率，目标 60%+。

## 当前状态
- 稳定测试集：685 passed, 1 failed (test_security.py::TestRateLimiter::test_allows_under_limit), 17 skipped
- 覆盖率：44% (14462 总语句，8153 未覆盖)
- 完整套件：2372 passed, 158 failed, 49 skipped

## 本次会话尝试
1. 修复 test_security.py 中 RateLimiter 测试（反复尝试 edit 未成功匹配文本）
2. 安装 numpy (2.4.6) 成功
3. 创建 test_inventory_optimizer.py 和 test_timesfm_engine.py（部分失败，字段名不匹配）
4. 多次尝试运行完整测试套件，均遇到大量失败（user_service, web_llm 等模块）
5. 尝试修复 test_security.py 中 patch 导入问题

## 问题记录
- test_security.py 的 edit 操作反复失败（文本匹配问题，可能是 CRLF/LF 差异）
- 完整套件运行时 user_service 和 web_llm 模块大量失败（mock 配置问题）
- inventory_optimizer 字段名不匹配（recommended_order_qty vs recommended_order_quantity）
- timesfm_engine 的 ForecastResult 字段不匹配

## 待办
- [ ] 修复 test_security.py 中 RateLimiter 测试
- [ ] 修复 inventory_optimizer 和 timesfm_engine 测试字段名
- [ ] 解决 user_service 和 web_llm 模块的 mock 问题
- [ ] 重新达到 60% 覆盖率
