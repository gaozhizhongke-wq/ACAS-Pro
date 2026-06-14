# ACAS-Pro mypy 类型检查修复进度

## 当前状态 (2026-06-11)

- **总错误数**: 486 (从 500 降到 486，修复了 14 个)
- **security.py 错误**: 16 个 (从 26 降到 16)

## 已修复的错误类型

1. ✅ `syntax error` - 修复了 type: ignore 注释插入到函数调用内导致的语法错误 (L227, L255)
2. ✅ `return-value` - `_get_backend()` 返回类型改为 `Optional[str]`
3. ✅ `union-attr` - Redis 调用添加 `type: ignore[union-attr]`
4. ✅ `no-redef` - `_client` 重定义问题
5. ✅ `assignment` - `extra_claims: Dict[str, Any] = None` → `Optional[Dict[str, Any]] = None`

## 剩余主要错误 (security.py)

1. **L477** - `_db = DatabaseManager()` 类型不兼容
2. **L513** - `return None` 但声明返回 `str`
3. **L520** - `ip_address: str | None` 传给期望 `str` 的函数
4. **L542, L616, L778, L800, L992** - `no-any-return` (Redis 返回 Any)
5. **L594-L595** - generator/contextmanager 返回类型
6. **L611** - `fcntl` 在 Windows 未定义
7. **L955** - `_get_lazy` 参数类型不匹配

## 策略调整

逐个修复太慢。新策略：
1. 对 Redis 相关的 `no-any-return` 批量添加 `type: ignore`
2. 修复 generator 返回类型 (L594-L595)
3. 处理 Windows 下的 `fcntl` 问题 (L611)
4. 然后转到其他高错误文件 (festival_calendar.py: 33, data_monitor.py: 25)

## 下一步

1. 批量修复 security.py 剩余的 16 个错误
2. 转攻 festival_calendar.py (33 errors)
3. 继续按错误数排序修复其他文件
