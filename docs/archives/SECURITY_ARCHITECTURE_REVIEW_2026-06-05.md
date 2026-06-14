# ACAS-Pro 安全与架构审查报告

**审查日期**: 2026-06-05  
**审查标准**: 字节跳动安全团队 + 架构评审委员会  
**审查维度**: 安全、可靠性、性能、架构、代码质量  

---

## 一、安全审查 (Security)

### 1.1 认证与授权 (Authentication & Authorization)

#### ✅ 正面发现
- **JWT 密钥管理**: `JWTManager._get_secret_key()` 强制要求环境变量 `ACAS_JWT_SECRET` 或配置 `secret_key`，不再提供随机回退，防止静默降级
- **密码策略**: `PasswordValidator` 实现了 8-128 字符长度、大小写、数字、特殊字符、常见密码检测
- **密码哈希**: `PasswordHasher` 使用 PBKDF2-SHA256 + 随机盐 + 600,000 次迭代，符合 NIST 推荐标准
- **会话管理**: `SessionManager.create_session()` 在数据库写入失败时返回 `None`（fail-fast），不返回无效 token
- **速率限制**: 注册 10 次/10 分钟，登录 20 次/10 分钟，防止暴力破解

#### 🔴 严重问题
- **JWT 密钥回退链不一致**: `config.py` 中 `SecurityConfig.__post_init__` 从 `secrets_manager.get('secret_key')` 获取，但 `secrets_manager.py` 映射的是 `ACAS_JWT_SECRET` 环境变量。如果用户设置了 `JWT_SECRET` 而不是 `ACAS_JWT_SECRET`，配置验证通过但 `JWTManager._get_secret_key()` 会失败
  - **风险**: 生产环境启动失败或认证系统不可用
  - **建议**: 统一环境变量名，或让 `JWTManager._get_secret_key()` 也检查 `JWT_SECRET`

- **LLM API Key 明文存储**: `llm.py` 的 `save_llm_config()` 将 API key 写入 `os.environ`，但环境变量在进程间共享，子进程可继承
  - **风险**: API key 泄露到日志、子进程、/proc 环境
  - **建议**: 使用内存安全存储（如 `secrets_manager`）或加密存储

- **CSRF 状态密钥随机生成**: `CSRF_STATE_SECRET` 在模块加载时通过 `secrets.token_hex(32)` 生成，每次重启变化
  - **风险**: 多实例部署时 CSRF token 验证失败（虽然实际使用 per-request token，此常量未使用）
  - **建议**: 移除未使用的 `CSRF_STATE_SECRET` 或改为环境变量强制配置

#### 🟡 中等问题
- **legacy token 回退**: `verify_token()` 在 `JWTManager.verify_token()` 失败后尝试 `jwt.decode()`，但使用相同的 `JWT_SECRET`。如果 JWT 格式被篡改（如算法改为 "none"），此回退可能被绕过
  - **风险**: 低（JWT 库已修复 "none" 算法问题）
  - **建议**: 移除 legacy 回退或严格验证算法

- **Flask SECRET_KEY 非生产环境**: `_configure_app()` 在非生产环境也要求 `SECRET_KEY`，但错误信息提示生成 48 字符 URL-safe token，而 `JWTManager` 要求 32 字符
  - **建议**: 统一密钥长度要求

### 1.2 数据安全 (Data Security)

#### ✅ 正面发现
- **SQL 注入防护**: `DatabaseManager._validate_identifier()` 白名单 + 字母数字验证
- **参数化查询**: 所有 `execute()` 调用使用 `?` 或 `%s` 占位符
- **PII 脱敏**: `PIIRedactor` 对密码、token、信用卡等字段递归脱敏
- **审计日志**: `audit_logger` 记录关键操作（登录、注册、会话创建）

#### 🔴 严重问题
- **数据库连接字符串明文**: `DATABASE_URL` 环境变量包含密码（如 `postgresql://user:password@host/db`），在日志或错误信息中可能泄露
  - **建议**: 使用 `secrets_manager` 分别存储用户名、密码、主机，拼接连接字符串

- **SQLite 数据库文件权限**: `_init_sqlite()` 创建数据库文件但未设置文件权限（默认 644）
  - **风险**: 其他用户可读取数据库文件
  - **建议**: 设置 `os.chmod(self._db_path, 0o600)`

### 1.3 网络安全 (Network Security)

#### ✅ 正面发现
- **HTTPS 强制**: 生产环境检查 HTTPS（通过 nginx 反向代理）
- **CORS 白名单**: 生产环境严格验证 `Origin` 头
- **安全响应头**: `SecurityHeaders` 中间件添加 HSTS、CSP、X-Frame-Options 等

#### 🟡 中等问题
- **Weibo API access_token 传输**: 已改为 Authorization header，但 `collectors/weibo_api.py` 中仍有 URL 参数传递的代码路径（虽然已修改）
  - **建议**: 彻底移除 URL 参数传递代码

---

## 二、可靠性审查 (Reliability)

### 2.1 错误处理 (Error Handling)

#### ✅ 正面发现
- **fail-fast 模式**: `SessionManager.create_session()` 数据库失败返回 `None`，不返回无效 token
- **异常日志**: 关键操作（认证、数据库）都有详细的错误日志
- **降级策略**: PostgreSQL 失败自动降级到 SQLite（开发环境适用）

#### 🔴 严重问题
- ** broad except 过多**: 代码中大量使用 `except Exception:` 捕获所有异常
  - `auth.py`: `except Exception as e:` 捕获注册/登录验证错误，可能隐藏 SQL 注入或内存错误
  - `llm_chat()`: `except Exception as e:` 返回 500 错误，但可能隐藏 API 密钥泄露或网络错误
  - **风险**: 隐藏真正的错误，导致调试困难，可能掩盖安全漏洞
  - **建议**: 使用具体异常类型（`ValidationError`, `ConnectionError`, `TimeoutError` 等）

#### 🟡 中等问题
- **数据库连接泄漏**: `DatabaseManager._get_sqlite_connection()` 使用线程本地存储，但连接永不关闭
  - **风险**: 长时间运行后文件描述符耗尽
  - **建议**: 实现连接池或定期清理空闲连接

### 2.2 监控与告警 (Monitoring & Alerting)

#### ✅ 正面发现
- **健康检查**: `health.py` 实现数据库、LLM、配置等多维度健康检查
- **审计日志**: 关键操作记录到 `audit_logs` 表

#### 🟡 中等问题
- **缺少 metrics**: 没有 Prometheus/Grafana 指标暴露
  - **建议**: 添加 `/metrics` 端点暴露请求延迟、错误率、数据库连接数等

---

## 三、性能审查 (Performance)

### 3.1 数据库性能

#### ✅ 正面发现
- **连接池**: PostgreSQL 使用 `ThreadedConnectionPool`（min=5, max=50）
- **WAL 模式**: SQLite 使用 WAL 模式提高并发性能
- **查询超时**: PostgreSQL 设置 30 秒查询超时

#### 🔴 严重问题
- **SQLite 单线程瓶颈**: `check_same_thread=False` 允许多线程访问，但 SQLite 本身不支持高并发写入
  - **风险**: 生产环境高并发时性能急剧下降
  - **建议**: 生产环境强制使用 PostgreSQL，SQLite 仅用于开发/测试

#### 🟡 中等问题
- **缺少索引**: 部分表缺少常用查询的索引
  - `sessions(token)` 有索引，但 `users(account)` 没有唯一索引（虽然代码中标记 UNIQUE）
  - **建议**: 审查所有查询路径，添加缺失索引

### 3.2 异步性能

#### ✅ 正面发现
- **异步改造**: 13 个文件、29 个方法已完成异步化
- **HTTP 异步**: LLM 客户端、OAuth、物流追踪使用 `httpx.AsyncClient` 或 `aiohttp`

#### 🟡 中等问题
- **DatabaseManager 异步不完整**: 虽然添加了 `execute_async` 等方法，但内部仍使用 `asyncio.to_thread()` 包装同步调用
  - **风险**: 线程池耗尽时性能下降
  - **建议**: 使用 `aiosqlite` 原生异步 API

---

## 四、架构审查 (Architecture)

### 4.1 代码结构

#### ✅ 正面发现
- **模块化设计**: 核心、服务、Web、LLM 等模块分离清晰
- **配置分层**: 开发/测试/生产环境配置隔离
- **依赖注入**: `DIContainer` 支持单例/工厂/实例注册

#### 🔴 严重问题
- **循环依赖风险**: `config.py` → `secrets_manager.py` → `config.py`（通过 `get_config()`）
  - **风险**: 初始化顺序不确定，可能导致死锁或错误配置
  - **建议**: 重构为单向依赖，或延迟初始化

#### 🟡 中等问题
- **全局单例**: `DatabaseManager`, `config` 等使用全局单例
  - **风险**: 测试隔离困难，并发测试可能互相干扰
  - **建议**: 使用依赖注入替代全局单例

### 4.2 扩展性

#### ✅ 正面发现
- **多 LLM 提供商**: 支持 OpenAI、Anthropic、Kimi、DeepSeek 等
- **多数据库**: SQLite/PostgreSQL 自动切换

#### 🟡 中等问题
- **硬编码提供商列表**: `_PROVIDER_MAP` 在 `llm.py` 中硬编码
  - **建议**: 使用插件机制动态注册提供商

---

## 五、代码质量审查 (Code Quality)

### 5.1 类型安全

#### ✅ 正面发现
- **类型注解**: 64.6% 的函数有类型注解
- **Pydantic 验证**: API 请求使用 Pydantic v2 模型验证

#### 🔴 严重问题
- **类型注解不完整**: 35.4% 的函数缺少返回类型注解
  - **风险**: 运行时类型错误，IDE 无法提供准确提示
  - **建议**: 强制要求所有公共 API 函数添加类型注解

### 5.2 测试覆盖

#### ✅ 正面发现
- **测试数量**: 2345 个测试，覆盖率 79.02%
- **测试隔离**: `_make_isolated_app()` 实现测试隔离

#### 🟡 中等问题
- **E2E 测试跳过**: 16 个 Playwright E2E 测试因缺少浏览器跳过
  - **建议**: CI/CD 中配置 Playwright 环境
- **部分模块 0% 覆盖**: `ad_manager.py`, `audience_targeting.py` 等核心模块在覆盖率报告中显示 0%
  - **注意**: 实际有测试，但覆盖率统计可能因导入路径问题未计入

### 5.3 代码规范

#### ✅ 正面发现
- **PEP 8**: 代码格式符合 PEP 8
- **文档字符串**: 关键类和方法有文档字符串

#### 🟡 中等问题
- **TODO/FIXME**: 24 处 TODO/FIXME，部分涉及核心功能
  - `avatar_engine.py`: 7 个 TODO
  - `lip_sync.py`: 6 个 TODO
  - **建议**: 建立 TODO 追踪机制，定期清理

---

## 六、综合评分

| 维度 | 评分 | 说明 |
|------|------|------|
| 安全 | 75/100 | 基础安全机制完善，但存在密钥管理不一致、broad except 等问题 |
| 可靠性 | 70/100 | fail-fast 模式良好，但异常处理不够精细，缺少连接池清理 |
| 性能 | 65/100 | 异步改造进行中，数据库层仍为同步瓶颈 |
| 架构 | 72/100 | 模块化良好，但存在循环依赖和全局单例问题 |
| 代码质量 | 68/100 | 测试覆盖良好，但类型注解不完整，TODO 较多 |
| **综合** | **70/100** | **工业级 Beta 水平，距离生产级还需改进** |

---

## 七、优先修复项 (P0)

1. **统一 JWT 环境变量名**: `ACAS_JWT_SECRET` vs `JWT_SECRET`
2. **移除 broad except**: 使用具体异常类型
3. **LLM API Key 安全存储**: 不写入环境变量，使用加密存储
4. **SQLite 文件权限**: 设置 0o600
5. **数据库连接清理**: 实现连接池自动清理

## 八、建议修复项 (P1)

1. **添加 Prometheus metrics**
2. **完善类型注解**（目标 100%）
3. **清理 TODO/FIXME**
4. **E2E 测试环境配置**
5. **数据库索引审查**

---

**审查结论**: ACAS-Pro 具备良好的安全基础和架构设计，但在密钥管理一致性、异常处理精细化、性能优化方面存在改进空间。建议优先修复 P0 项，再逐步推进 P1 项，预计 2-4 周可达生产级标准（评分 85+）。
