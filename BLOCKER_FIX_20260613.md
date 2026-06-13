# BLOCKER 修复完成报告

## 修复日期
2026-06-13

## 修复的 BLOCKER 问题

### BLOCKER-01: MD5 用于生产环境 API 签名
**状态**: ✅ 已验证（非本次修复）
**详情**: 代码审计确认所有 4 处 MD5 调用都有 `usedforsecurity=False` 标注，仅用于缓存 key 生成，不涉及安全场景。审计报告使用的是旧数据。

### BLOCKER-02: OpenAPI Spec 与 schemas.py 字段不一致
**状态**: ✅ 已修复
**文件**: `src/acas_pro/web/api_spec.py`
**修复内容**:
- RegisterRequest 字段从 `username, password, account` 改为 `account, password, nickname`
- LoginRequest 字段从 `username, password` 改为 `account, password`
- 与 `src/acas_pro/web/schemas.py` 中的实际定义保持一致

### BLOCKER-03: /api/health 健康检查发送真实 LLM API 请求
**状态**: ✅ 已修复
**文件**: `src/acas_pro/web/health.py`
**修复内容**:
- `_check_llm()` 方法不再调用 `client.chat()` 发送真实请求
- 改为仅验证 LLM 配置和客户端实例化
- 避免消耗 API 配额和误触发告警

### BLOCKER-04: Swagger UI 依赖外部 CDN
**状态**: ✅ 已修复
**文件**: `src/acas_pro/web/api_spec.py`
**修复内容**:
- 移除对外部 CDN `cdn.jsdelivr.net` 的依赖
- 替换为内联的轻量级 API 文档页面
- 通过 JavaScript 动态加载 `/api/openapi.json` 渲染端点列表

## 其他发现

### dashboard_stats blueprint 未正确注册
**文件**: `src/acas_pro/web/__init__.py`
**修复内容**: 在 `_register_blueprints()` 中添加了 `dashboard_stats` blueprint 的注册

## 测试验证

```
tests/unit/test_web_routes.py - 8 passed
```

所有相关测试通过。

## 修复文件清单

1. `src/acas_pro/web/__init__.py` - 注册 dashboard_stats blueprint
2. `src/acas_pro/web/health.py` - 移除 LLM API 调用
3. `src/acas_pro/web/api_spec.py` - 修复 OpenAPI spec + 移除外部 CDN

## 建议

1. **生产环境**: 考虑将 Swagger UI 静态文件打包到项目中，从本地服务而非内联渲染
2. **测试覆盖**: 为 dashboard_stats 的认证逻辑添加专门的单元测试
3. **健康检查**: 可考虑添加可选的"深度健康检查"端点，允许主动探测外部依赖（LLM、数据库写操作等）
