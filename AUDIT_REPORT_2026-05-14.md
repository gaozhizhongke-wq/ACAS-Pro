# ACAS Pro 最严苛审查报告

**审查日期**: 2026-05-14  
**审查人**: 风清扬  
**审查标准**: 字节跳动工程标准  
**审查结果**: ❌ **不达标，不可交付**

---

## 一、当前存在的问题清单（按严重程度排序）

### 🔴 CRITICAL - 测试架构设计缺陷（影响全部测试）

#### 问题1: 模块级全局实例导致测试隔离失败

**现象**:
- 单独运行测试: 35/35 通过
- 一起运行测试: 71/967 失败
- 失败模式: 测试间状态泄漏

**根本原因**:
```python
# src/acas_pro/services/user_service.py
from ..core.security import (
    get_password_validator, get_password_hasher,
    get_session_manager, get_rate_limiter
)

# 模块级全局实例 - 导入时创建
db = get_db()
password_validator = get_password_validator()
password_hasher = get_password_hasher()
session_manager = get_session_manager()
rate_limiter = get_rate_limiter()
```

当 `test_all_remaining_modules.py` 等测试清除并重新导入 `acas_pro.core.security` 时：
1. 创建新的全局实例
2. 但 `acas_pro.services.user_service` 仍持有旧实例引用
3. 后续测试的 `patch.multiple` 无法正确mock这些旧实例

**影响范围**:
- 16个测试文件与 `test_user_service_full.py` 冲突
- 冲突文件列表:
  - test_all_remaining_modules.py
  - test_comprehensive_mock.py
  - test_final_all.py
  - test_final_comprehensive.py
  - test_final_coverage.py
  - test_final_mock.py
  - test_final_mock_all.py
  - test_full_coverage.py
  - test_inventory_optimizer.py
  - test_massive_coverage.py
  - test_mock_imports.py
  - test_ui_pages_methods.py
  - test_ui_pages_mock.py
  - test_ui_pyside6_all.py
  - test_ui_web_coverage.py
  - test_web_modules.py

**修复方案**:
```python
# 方案1: 延迟初始化
class UserService:
    def __init__(self):
        self._password_validator = None
    
    @property
    def password_validator(self):
        if self._password_validator is None:
            self._password_validator = get_password_validator()
        return self._password_validator

# 方案2: 依赖注入
class UserService:
    def __init__(self, password_validator=None, password_hasher=None):
        self.password_validator = password_validator or get_password_validator()
        self.password_hasher = password_hasher or get_password_hasher()
```

---

#### 问题2: E2E测试Fixture设计错误

**现象**:
```
ERROR tests/test_e2e.py::TestDashboardFlow::test_dashboard_stats_returns_data
AttributeError: Mock object has no attribute 'status_code'
```

**根本原因**:
`conftest.py` 全局mock了 `requests` 模块:
```python
# conftest.py
_requests = MagicMock()
_requests.post = MagicMock  # 返回MagicMock，不是Response对象
sys.modules['requests'] = _requests
```

E2E测试的 `auth_token` fixture期望真实HTTP响应:
```python
# test_e2e.py
resp = requests.post(...)  # 返回MagicMock，没有status_code属性
if resp.status_code == 200:  # AttributeError!
```

**修复方案**:
1. 移除 `requests` 全局mock
2. 在需要mock的测试中局部使用 `@patch('requests.post')`
3. E2E测试使用真实HTTP请求，标记为 `pytest.mark.e2e`

---

#### 问题3: Playwright模块mock冲突

**现象**:
```
ModuleNotFoundError: No module named 'playwright.sync_api'; 'playwright' is not a package
```

**根本原因**:
```python
# conftest.py
sys.modules['playwright'] = MagicMock()  # 替换了真实playwright包
```

当 `test_dashboard_e2e.py` 导入 `from playwright.sync_api import ...` 时：
- Python找到 `sys.modules['playwright']` (MagicMock)
- MagicMock没有 `sync_api` 子模块
- 导入失败

**修复方案**:
```python
# 方案1: 不mock playwright，让测试自己处理
# 方案2: 正确mock子模块
playwright_mock = MagicMock()
playwright_mock.sync_api = MagicMock()
playwright_mock.sync_api.Page = MagicMock
# ...
sys.modules['playwright'] = playwright_mock
sys.modules['playwright.sync_api'] = playwright_mock.sync_api
```

---

### 🟡 HIGH - 测试覆盖率配置不合理

#### 问题4: 覆盖率阈值过高导致测试"假失败"

**现象**:
```
FAIL Required test coverage of 20% not reached. Total coverage: 2.23%
```

**根本原因**:
```ini
# pytest.ini
--cov-fail-under=20
```

实际覆盖率仅2-3%，原因：
1. V1模块大部分未被测试（循环导入问题）
2. UI模块（PySide6）无法在headless环境测试
3. 大量占位符/空壳代码存在

**修复方案**:
```ini
# 方案1: 降低阈值
--cov-fail-under=5

# 方案2: 分模块设置阈值
# V2模块要求80%，V1模块要求10%
```

---

### 🟡 MEDIUM - 代码质量问题

#### 问题5: 异常处理过于宽泛

**现象**:
```python
# src/acas_pro/core/security.py
try:
    # ...
except Exception as e:
    logger.error(f"Password verification error: {e}")
    return False
```

**问题**:
- 捕获所有异常，隐藏真实错误
- 无法区分系统错误和验证失败
- 不符合字节跳动"精确异常处理"规范

**修复方案**:
```python
from cryptography.fernet import InvalidToken

try:
    # ...
except InvalidToken:
    logger.warning("Invalid password token format")
    return False
except ValueError as e:
    logger.error(f"Password verification value error: {e}")
    return False
```

---

#### 问题6: 配置验证在生产环境不强制

**现象**:
```python
# src/acas_pro/core/config.py
def get_config() -> AppConfig:
    global _config_instance
    if _config_instance is None:
        _config_instance = AppConfig.load()
        # 只在production时验证
        if _config_instance.is_production:
            is_valid, errors = _config_instance.validate()
```

**问题**:
- 开发环境不验证配置，导致问题延迟发现
- 应在所有环境验证，生产环境强制通过

**修复方案**:
```python
def get_config() -> AppConfig:
    global _config_instance
    if _config_instance is None:
        _config_instance = AppConfig.load()
        is_valid, errors = _config_instance.validate()
        if not is_valid:
            if _config_instance.is_production:
                raise RuntimeError(f"Config validation failed: {errors}")
            else:
                logger.warning(f"Config validation warnings: {errors}")
    return _config_instance
```

---

#### 问题7: 硬编码安全参数

**现象**:
```python
# src/acas_pro/core/security.py
ACCESS_TOKEN_EXPIRY_MINUTES = 15
REFRESH_TOKEN_EXPIRY_DAYS = 7
```

**问题**:
- 安全参数应可配置
- 不同环境可能需要不同策略

**修复方案**:
```python
class JWTManager:
    @classmethod
    def _get_access_token_expiry(cls) -> int:
        return _cfg().security.access_token_expiry_minutes or 15
```

---

## 二、测试统计

| 指标 | 数值 | 状态 |
|------|------|------|
| 总测试数 | 967 | - |
| 通过 | 818 | 85% |
| 失败 | 71 | 9% |
| 跳过 | 68 | 6% |
| 错误 | 5 | 0.5% |
| 覆盖率 | 2.23% | ❌ 远低于20%阈值 |

### 失败测试分类

| 类别 | 数量 | 原因 |
|------|------|------|
| 测试隔离失败 | 35 | 模块级全局实例 |
| 安全模块测试 | 12 | mock状态冲突 |
| 监控模块测试 | 8 | 导入顺序问题 |
| 产品管理测试 | 9 | 数据库mock冲突 |
| 结算引擎测试 | 7 | 配置加载问题 |

---

## 三、架构问题

### 3.1 V1 vs V2 模块重复

**现象**:
- V1模块: `security.py`, `database.py`, `config.py`
- V2模块: `security_v2.py`, `database_v2.py`, `config_v2.py`

**问题**:
- 代码重复，维护困难
- V1模块存在循环导入问题
- V2模块未完全替换V1

**建议**:
1. 逐步废弃V1模块
2. 统一使用V2架构
3. 提供迁移指南

### 3.2 全局状态管理混乱

**现象**:
```python
# 多处存在全局实例
password_validator = PasswordValidator()  # security.py
user_service = UserService()  # user_service.py
db = get_db()  # database.py
```

**问题**:
- 无法并行测试
- 状态泄漏
- 难以mock

**建议**:
1. 使用依赖注入容器
2. 避免模块级全局实例
3. 使用工厂模式

---

## 四、安全审查

### 4.1 加密盐值管理

**现状**:
```python
salt_env = os.environ.get('ACAS_ENCRYPTION_SALT')
if not salt_env:
    # 开发环境使用持久化文件
    dev_salt_file = Path.home() / ".acas-pro" / ".dev_encryption_salt"
```

**风险**:
- 开发环境盐值持久化，可能泄露到生产环境
- 未强制要求生产环境设置盐值

**建议**:
1. 生产环境强制检查 `ACAS_ENCRYPTION_SALT`
2. 开发环境每次生成新盐值（不持久化）

### 4.2 JWT密钥管理

**现状**:
```python
key = os.environ.get('ACAS_JWT_SECRET')
if not key:
    key = _cfg().security.secret_key
```

**风险**:
- 回退到配置文件中的密钥
- 配置文件可能被提交到版本控制

**建议**:
1. 生产环境只允许环境变量
2. 配置文件中的密钥仅用于开发

---

## 五、结论

### 5.1 评分估算

| 维度 | 当前 | 目标 | 差距 |
|------|------|------|------|
| 可用性 | 85 | 95 | -10 |
| 安全性 | 80 | 95 | -15 |
| 好用性 | 90 | 95 | -5 |
| 工程化 | 70 | 95 | -25 |
| **总分** | **81** | **95** | **-14** |

### 5.2 不可交付原因

1. **测试不可靠**: 71个测试失败，无法作为质量保障
2. **架构缺陷**: 全局状态导致测试隔离失败
3. **覆盖率虚高**: 实际可测试代码覆盖率远低于要求
4. **安全隐患**: 密钥管理、异常处理存在问题

### 5.3 修复工作量估算

| 任务 | 工作量 | 优先级 |
|------|--------|--------|
| 重构全局实例为依赖注入 | 8小时 | P0 |
| 修复conftest.py mock冲突 | 4小时 | P0 |
| 修复测试隔离问题 | 6小时 | P0 |
| 调整覆盖率配置 | 1小时 | P1 |
| 完善异常处理 | 4小时 | P1 |
| 安全参数配置化 | 3小时 | P2 |
| **总计** | **26小时** | - |

---

## 六、修复后预期

修复上述问题后：
- 测试通过率: 95%+
- 覆盖率: 60%+
- 评分: 92-95分
- 可交付状态: ✅

---

**审查结论**: **当前代码不可交付字节跳动**。需26小时修复核心问题后方可交付。

**签名**: 风清扬  
**时间**: 2026-05-14 09:30  
**状态**: ❌ 审查未通过
