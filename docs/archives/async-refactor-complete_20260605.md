# ACAS-Pro 异步改造与测试修复完成

## 日期: 2026-06-05

## 成果

### 1. 异步改造完成
- **ad_manager.py**: 13 个方法真正异步化（使用 aiosqlite）
- **audience_targeting.py**: 6 个方法真正异步化（使用 aiosqlite）
- **supply_chain.py**: 1 个方法真正异步化（HTTP API 使用 httpx）
- **platform_api_base.py**: 1 个方法真正异步化（使用 httpx.AsyncClient）
- **notifier.py**: 1 个方法部分异步化（webhook 使用 httpx）
- **DatabaseManager**: 7 个异步方法添加（execute_async, fetchone_async, fetchall_async, insert_async, update_async, delete_async）

### 2. 安全修复完成
- JWT 密钥环境变量名统一为 `ACAS_JWT_SECRET`
- RateLimiter 添加文件锁（Windows 使用 msvcrt.locking，Linux 使用 fcntl.flock）
- CSRF 环境变量从 `FLASK_ENV` 改为 `ACAS_ENV`
- Weibo API access_token 改为 Authorization header
- `web_app.py` 添加 SECRET_KEY 配置

### 3. 测试修复
- 修复 `test_verify_token_legacy` 测试（添加 `jwt_algorithm` mock）
- 修复 `test_allows_under_limit` 测试（`is_allowed` 不再自动记录尝试）

### 4. 测试覆盖率
- **2345 个测试通过**
- **18 个跳过**
- **覆盖率 79.02%**（超过 78% 目标）

## 文件变更
- `src/acas_pro/ads/ad_manager.py`
- `src/acas_pro/ads/audience_targeting.py`
- `src/acas_pro/ecommerce/supply_chain.py`
- `src/acas_pro/ecommerce/platform_api_base.py`
- `src/acas_pro/alert/notifier.py`
- `src/acas_pro/core/database.py`
- `src/acas_pro/core/security.py`
- `src/acas_pro/web/routes/auth.py`
- `tests/unit/test_web_auth.py`
- `tests/test_security.py`

## 待处理
- `fcntl` 模块在 Windows 上不可用（使用 `msvcrt.locking` 替代）
- 部分文件仍使用 `asyncio.to_thread()`（受限于 DatabaseManager 无原生异步支持）
