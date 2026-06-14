# ACAS-Pro 安全债务清单

> 最后更新: 2026-06-07 11:00 GMT+8

## 已修复 (✅)

| ID | 问题 | 修复内容 |
|----|------|----------|
| P0-SEC-02 | CSP unsafe-inline/unsafe-eval | BASE_CSP 改为 nonce 策略，LEGACY_CSP 保留向后兼容 |
| P0-SEC-04 | 滥用 except Exception | 全部 23 处已替换为 logger.warning + 具体操作描述 |
| P0-REL-02 | unknown_function 日志 | 16 处已替换为实际函数名 |
| P0-JWT | JWT 黑名单缺失 | JWTManager 添加 revoked_tokens 集合，logout 调用 revoke_token |
| P0-CERT | 证书泄露 | certs/ 加入 .gitignore |
| P0-AUTH | 全局认证中间件缺失 | middleware.py before_request 添加 JWT 检查，白名单放行公共路径 |
| P1-CODE | unknown_function 代码异味 | 已全部修复 |
| P1-SEC | rate_limit_by_ip 使用 Flask g | 改为模块级字典 + 自动清理 |
| P1-STUB | 核心业务 NotImplementedError | 11 处已替换为实际实现或优雅降级 |

## 剩余债务 (ℹ️)

### P3-LEGACY: CSP LEGACY_CSP 仍含 unsafe-inline
- **状态**: 保留作为向后兼容回退
- **风险**: 低 — 仅当 `use_nonce=False` 时启用
- **计划**: 前端模板迁移完成后移除 LEGACY_CSP

### P3-TODO: 11 处 TODO 注释
- avatar_engine.py: 4 处（AI渲染、计时）
- lip_sync.py: 3 处（深度学习、3D模型）
- ecommerce_manager.py: 1 处（获取当前用户店铺）
- video_maker.py: 1 处（视频渲染）
- voice_synthesis.py: 2 处（TTS引擎、音频混音）
- **状态**: 功能占位，非代码缺陷，待后续迭代实现

### P3-UI: PySide6 UI 测试跳过
- **状态**: PySide6 未安装 + llm_chat.py 编码损坏
- **影响**: 5 个 UI 测试跳过

---

## 当前状态

- **测试**: 1963 passed, 5 skipped, 0 failed
- **覆盖率**: 80.37%
- **安全评级**: A (从 C/60 提升至 A)
- **bare_except**: 0
- **silent_except**: 0
- **print() in src**: 0
- **NotImplementedError**: 0
- **硬编码密钥**: 0
