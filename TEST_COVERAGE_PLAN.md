# ACAS-Pro 测试覆盖率提升计划 (目标: 60% → 80%)

## 当前状态
- 当前覆盖率: ~3% (测试与实现 API 不匹配导致大量失败)
- 测试文件数: 70+
- 主要问题: 测试使用的 API 与当前实现不一致

## 已完成的修复

### 1. config.environment 修复 ✅
**文件**: `src/core/config.py`
**修改**: `__post_init__` 中确保 ACAS_ENV 环境变量始终优先于配置文件中的值
```python
# ACAS_ENV always takes precedence over any other configuration
env = os.environ.get('ACAS_ENV', '').lower()
if env:
    try:
        self.environment = Environment(env)
        logger.info(f"Environment set from ACAS_ENV: {self.environment.value}")
    except ValueError:
        logger.warning(f"Invalid ACAS_ENV value: {env}, keeping current: {self.environment.value}")
```

### 2. create_app() 调用 validate() ✅
**文件**: `src/acas_pro/web/__init__.py`
**修改**: 在 Flask app 创建时强制调用 config.validate()
```python
def create_app():
    app = Flask(__name__)
    
    # Validate configuration before starting
    is_valid, errors = config.validate()
    if not is_valid:
        for error in errors:
            logger.error(f"Configuration validation failed: {error}")
        raise ValueError(f"Invalid configuration: {', '.join(errors)}")
    
    # ... rest of the function
```

### 3. datetime.utcnow() 迁移 ✅
**文件**: `api_server.py`, `api_server_v2.py`, `enterprise_security_core.py`, `llm_api_v2.py`, `logger.py`, `middleware.py`, `monitoring/logger.py`
**修改**: 所有 `datetime.utcnow()` → `datetime.now(timezone.utc)`

## 测试覆盖率提升计划

### Phase 1: 修复现有测试 API 兼容性 (预计提升到 40%)

#### 1.1 test_auth.py 修复
**问题**: 
- `PasswordValidator.validate()` 返回 tuple `(bool, str)`，测试期望 `.is_valid` 属性
- `RateLimiter.is_allowed()` 参数名不匹配 (`max_requests` vs `max_attempts`)
- `JWTManager()` 不接受参数，测试传了参数

**修复方案**:
```python
# 修改测试以匹配实际 API
result = password_validator.validate("password123")
assert result[0] == True  # 而不是 result.is_valid

# 或者修改 PasswordValidator 返回一个对象
@dataclass
class ValidationResult:
    is_valid: bool
    message: str
```

#### 1.2 test_database.py 修复
**问题**: `DatabaseManager` 是单例模式，测试尝试直接实例化

**修复方案**:
```python
# 修改测试使用 get_instance() 或直接调用类方法
from acas_pro.core.database import DatabaseManager
db = DatabaseManager()  # 单例自动返回实例
```

### Phase 2: 添加核心模块单元测试 (预计提升到 60%)

#### 2.1 config 模块测试
```python
# tests/test_config.py
class TestAppConfig:
    def test_acas_env_override(self):
        """测试 ACAS_ENV 环境变量覆盖配置文件"""
        os.environ['ACAS_ENV'] = 'production'
        config = AppConfig(environment=Environment.DEVELOPMENT)
        assert config.environment == Environment.PRODUCTION
    
    def test_validate_production_requires_secret_key(self):
        """测试生产环境必须设置 SECRET_KEY"""
        config = AppConfig(environment=Environment.PRODUCTION)
        config.security.secret_key = ""
        is_valid, errors = config.validate()
        assert not is_valid
        assert any("SECRET_KEY" in e for e in errors)
```

#### 2.2 security 模块测试
```python
# tests/test_security.py
class TestCryptoManager:
    def test_encrypt_decrypt(self):
        """测试加密解密往返"""
        cm = CryptoManager()
        plaintext = "sensitive data"
        encrypted = cm.encrypt(plaintext)
        decrypted = cm.decrypt(encrypted)
        assert decrypted == plaintext
    
    def test_password_hashing(self):
        """测试密码哈希"""
        ph = PasswordHasher()
        password = "MyP@ssw0rd!"
        hashed = ph.hash(password)
        assert ph.verify(password, hashed)
        assert not ph.verify("wrong", hashed)
```

#### 2.3 web 模块测试
```python
# tests/test_web.py
class TestCreateApp:
    def test_create_app_validates_config(self):
        """测试 create_app 调用 validate()"""
        with pytest.raises(ValueError) as exc_info:
            # 设置无效配置
            os.environ['ACAS_ENV'] = 'production'
            config.security.secret_key = ""
            create_app()
        assert "SECRET_KEY" in str(exc_info.value)
```

### Phase 3: 添加集成测试 (预计提升到 80%)

#### 3.1 API 端点测试
```python
# tests/test_api_integration.py
class TestAuthEndpoints:
    def test_register_login_flow(self, client):
        """测试注册登录完整流程"""
        # Register
        resp = client.post('/api/auth/register', json={
            'account': 'testuser',
            'password': 'Test@123456',
            'nickname': 'Test User'
        })
        assert resp.status_code == 200
        
        # Login
        resp = client.post('/api/auth/login', json={
            'account': 'testuser',
            'password': 'Test@123456'
        })
        assert resp.status_code == 200
        assert 'token' in resp.json
```

#### 3.2 数据库集成测试
```python
# tests/test_database_integration.py
class TestDatabaseOperations:
    def test_crud_operations(self, db):
        """测试增删改查"""
        # Create
        db.execute("INSERT INTO users (account) VALUES (?)", ("test",))
        
        # Read
        result = db.fetchone("SELECT * FROM users WHERE account = ?", ("test",))
        assert result['account'] == 'test'
        
        # Update
        db.execute("UPDATE users SET nickname = ? WHERE account = ?", ("Test", "test"))
        
        # Delete
        db.execute("DELETE FROM users WHERE account = ?", ("test",))
```

### Phase 4: 补充边缘情况测试 (预计提升到 85%+)

- 错误处理路径
- 并发访问
- 资源清理
- 配置边界值

## 执行建议

1. **立即执行**: Phase 1 修复现有测试，使其能正常运行
2. **本周内**: Phase 2 添加核心模块单元测试
3. **下周**: Phase 3 添加集成测试
4. **持续**: Phase 4 边缘情况测试

## 关键文件

| 模块 | 当前覆盖率 | 目标 | 优先级 |
|------|-----------|------|--------|
| config.py | 0% | 90% | P0 |
| security.py | 5% | 85% | P0 |
| database.py | 2% | 80% | P0 |
| web/__init__.py | 0% | 75% | P1 |
| web/routes/*.py | 0% | 70% | P1 |
| ml/*.py | 0% | 60% | P2 |
| ui/*.py | 0% | 50% | P3 |
