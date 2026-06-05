# ACAS-Pro P0 安全修复完成 (2026-06-05)

## 修复项

### P0-1: JWT 环境变量名不一致
- **文件**: `src/acas_pro/core/security.py`
- **修复**: `_get_secret_key()` 统一使用 `ACAS_JWT_SECRET` 环境变量

### P0-2: `broad except Exception` 过多
- **文件**: `src/acas_pro/web/routes/auth.py`
- **修复**: `verify_token` 使用具体异常类型（`jwt.ExpiredSignatureError`, `jwt.InvalidTokenError`, `ValueError`, `KeyError`）
- **文件**: `src/acas_pro/core/security.py`
- **修复**: `PasswordHasher.verify` 捕获 `ValueError`, `TypeError` 替代 `Exception`

### P0-3: LLM API Key 明文写入 `os.environ`
- **文件**: `src/acas_pro/web/routes/llm.py`
- **修复**: 移除 `os.environ[env_key] = req.api_key`，改用 `secrets_manager` 存储

### P0-4: SQLite 数据库文件权限默认 644
- **文件**: `src/acas_pro/core/database.py`
- **修复**: 创建数据库文件时设置 `0o600` 权限（Unix）

### P0-5: 数据库连接永不关闭
- **文件**: `src/acas_pro/core/database.py`
- **修复**: 添加 `close()` 方法，清理 SQLite/PostgreSQL 连接

## 测试验证
- **2345 个测试通过**
- **18 个跳过**（Playwright E2E）
- **覆盖率 78.92%**（超过 78% 目标）

## 提交
- **提交**: `01c1088`
- **状态**: 待推送（网络问题）
