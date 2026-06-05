# ACAS Pro 安全修复 — 2026-06-04

## 目标
根据安全审查报告，一次性修复以下 CRITICAL/HIGH 问题。

## 已修复的问题

### 1. ✅ RateLimiter 竞态条件 (HIGH → CRITICAL)
**文件**: `core/security.py` — `RateLimiter` 类
- 添加 `fcntl.flock` 文件锁（`_atomic()` contextmanager），所有操作（is_allowed/record_attempt/reset）在同一把锁内完成读-改-写，彻底消除竞态
- 新增 `MAX_ENTRIES_PER_KEY = 100` 限制每个 key 的条目数，防止无限增长
- 从 `__init__` 中删除 `import fcntl, from contextlib import contextmanager`

### 2. ✅ SessionManager.create_session 数据库写入失败仍返回 token (HIGH)
**文件**: `core/security.py`
- 数据库 INSERT 失败时直接 `return None`，不继续执行后续代码
- 修复前：失败后继续执行 audit_logger.log，再返回 token，导致 DB 无记录但 Token 已发出

### 3. ✅ AuditLogger 表名错误 (HIGH)
**文件**: `core/logging.py`
- `audit_log` → `audit_logs`（与 database.py schema 一致）

### 4. ✅ database.py _VALID_IDENTIFIERS 缺少 session/audit 标识符 (MEDIUM)
**文件**: `core/database.py`
- 添加: `'sessions', 'audit_log', 'event_type', 'ip_address', 'severity'`

### 5. ✅ CSRF 测试模式环境变量混淆 (MEDIUM)
**文件**: `core/security.py`
- `FLASK_ENV == 'testing'` → `ACAS_ENV == 'testing'`
- Cookie secure 标志: `not os.environ.get('FLASK_ENV') == 'testing'` → `os.environ.get('ACAS_ENV') != 'testing'`

### 6. ✅ Weibo API access_token 在 URL 参数中暴露 (MEDIUM)
**文件**: `collectors/weibo_api.py`
- 从 `params={"access_token": ...}` 中移除 access_token
- 改为在 HTTP 请求时通过 `headers={"Authorization": f"Bearer {self.access_token}"}` 传递

### 7. ✅ JWT 密钥随机回退（已在之前修复）
**文件**: `core/security.py`
- `JWTManager._get_secret_key()` 无密钥时直接 `raise ValueError`，无任何随机回退
- 配置层 `_validate_production_secrets()` 已在生产模式检查 `secret_key`

### 8. ✅ JWT 密钥环境变量名称不一致 (MEDIUM)
**文件**: `core/config.py`, `web/routes/auth.py`
- `_validate_production_secrets()`: `JWT_SECRET` → `ACAS_JWT_SECRET`（与 security.py 保持一致）
- `auth.py` legacy token fallback: 改用 `JWTManager._get_secret_key()` 获取密钥（确保 env 优先级正确）

### 9. ✅ web_app.py SECRET_KEY 未设置 (HIGH)
**文件**: `web_app.py`
- 老入口文件直接 `app = Flask(__name__)` 但没有设置 `app.secret_key`
- 添加从 `SECRET_KEY` 环境变量或 `config().security.secret_key` 读取
- 生产环境缺失直接 `raise ValueError`，非生产环境也不允许弱密钥

### 10. ✅ wsgi.py FLASK_ENV 环境变量 (MEDIUM)
**文件**: `wsgi.py`
- `os.environ.get('FLASK_ENV')` → `os.environ.get('ACAS_ENV')`（与项目统一环境变量保持一致）

### 11. ✅ CSRF_STATE_SECRET 随机回退 (LOW)
**文件**: `core/security.py`
- `os.environ.get('CSRF_STATE_SECRET') or secrets.token_hex(32)` 每次重启生成不同值
- 改为：未设置时记录警告而非静默随机回退
- 当前 CSRF 机制是 per-request token（generate_csrf_token），不依赖此常量

### 12. ✅ 测试中 FLASK_ENV → ACAS_ENV (LOW)
**文件**: `tests/e2e_playwright/conftest.py`, `tests/unit/test_security.py`
- 所有测试代码中的 `FLASK_ENV` 替换为 `ACAS_ENV`

## 未处理（后续可做）
- LLM API Key 通过 URL 参数传输（已确认为 Bearer/x-api-key header ✅）
- 异步改造半完成状态
- fcntl 模块在 Windows 上不可用 → ✅ 已修复（msvcrt 平台兼容）

## 已确认正常的项
- ✅ `audit_logs` 表在 database.py L340/L505 已正确创建
- ✅ `logging.py` INSERT 语句与表结构一致（6 列: timestamp, event_type, user_id, ip_address, details, severity）
- ✅ LLM API Key 在 llm_client.py 中已使用 `Authorization: Bearer` / `x-api-key` header
- ✅ `secrets_manager.py` 中 `_SECRET_ENV_MAP` 已正确映射 `jwt_secret → ACAS_JWT_SECRET`

## 文件变更摘要
| 文件 | 变更 |
|------|------|
| `core/security.py` | RateLimiter 原子化 + SessionManager fail-fast + CSRF 环境变量 |
| `core/logging.py` | 表名 audit_logs |
| `core/database.py` | _VALID_IDENTIFIERS 补充 sessions/audit 字段 |
| `collectors/weibo_api.py` | access_token → Authorization header |
| `core/config.py` | JWT_SECRET → ACAS_JWT_SECRET 环境变量名 |
| `web/routes/auth.py` | legacy fallback 改用 JWTManager._get_secret_key() |
| `web_app.py` | 添加 SECRET_KEY 配置（生产必须设置） |
| `wsgi.py` | FLASK_ENV → ACAS_ENV |
| `core/security.py` (二次) | CSRF_STATE_SECRET 移除随机回退 |
| `tests/e2e_playwright/conftest.py` | FLASK_ENV → ACAS_ENV |
| `tests/unit/test_security.py` | FLASK_ENV → ACAS_ENV |