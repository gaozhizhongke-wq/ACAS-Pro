# ACAS-Pro 代码审查修复报告

## 任务概述
修复 ACAS-Pro 项目中的 8 个代码审查问题。

## 修复详情

### Issue 1: security.py 异常类型错误
- **文件**: `src/acas_pro/core/security.py`
- **操作**: 
  - 移除 `import sqlite3`（该文件不直接使用 sqlite3）
  - 将所有非数据库上下文的 `(sqlite3.Error, ValueError, RuntimeError, json.JSONDecodeError)` 替换为 `Exception`
  - Redis 检测块改为 `(ImportError, OSError, Exception)`
- **涉及位置**: TokenBlacklist、SessionManager、CryptoManager、RedisRateLimiter 共 15 处

### Issue 2: database.py 懒加载 `db`
- **文件**: `src/acas_pro/core/database.py`
- **操作**: 将底部的 `db = get_db()` 替换为 `__getattr__` 模式，避免模块导入时立即初始化数据库连接

### Issue 3: database.py 异常类型修复
- **文件**: `src/acas_pro/core/database.py`
- **操作**: 
  - `_init_postgres()`: 改为 `(ImportError, Exception)`
  - `__del__()`, `close()`, `transaction()`, `health_check()`: 保留 `sqlite3.Error` 但移除 `json.JSONDecodeError`，改为 `(sqlite3.Error, Exception)`
  - `reset_db()`: 同上

### Issue 4: user_service.py 异常类型 + 输入验证
- **文件**: `src/acas_pro/services/user_service.py`
- **操作**:
  - `register()`: 将冗余的异常元组（含 `Exception`）简化为 `except Exception as e:`
  - `update_profile()`: 同上
  - `register()` 新增输入长度截断验证：account(64), nickname(128), email(256), phone(32)

### Issue 5: DI 容器循环依赖检测
- **文件**: `src/acas_pro/core/di_container.py`
- **操作**: 在 `__init__` 中添加 `_resolving: set = set()`，在 `resolve()` 中添加循环检测逻辑，用 `try/finally` 确保 `_resolving` 状态正确清理

### Issue 6: RateLimiter 锁超时机制
- **文件**: `src/acas_pro/core/security.py`
- **操作**: 在 `_atomic()` 方法中，获取锁前检查锁文件是否存在且是否超过 60 秒；若是则删除（清除崩溃进程的残留锁），防止 Windows 上永久阻塞

### Issue 7: 移除 sqlite3 导入
- **文件**: `src/acas_pro/core/security.py`
- **操作**: 删除 `import sqlite3`（与 Issue 1 合并执行）

### Issue 8: 遗留 JWT 废弃警告
- **文件**: `src/acas_pro/web/routes/auth.py`
- **操作**: 在遗留 JWT 回退代码处添加 `warnings.warn(..., DeprecationWarning, stacklevel=2)`

## 测试结果

```
================ 2122 passed, 2 skipped, 21 warnings in 41.00s ================
Required test coverage of 78% reached. Total coverage: 78.88%
```

**全部通过 ✅**
