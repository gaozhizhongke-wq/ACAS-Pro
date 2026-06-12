# ACAS-Pro 安全修复 & 代码清理 (2026-06-11)

## 已修复

### 1. LEGACY_CSP 移除 unsafe-inline/unsafe-eval
- **文件**: `core/security_headers.py`
- **变更**: LEGACY_CSP 中移除 `'unsafe-inline'` 和 `'unsafe-eval'` 指令
- **附加**: 当 `use_nonce=False` 时添加 deprecation warning 日志

### 2. Orphaned docstring 清理
- **文件**: `ecommerce/shop_manager.py`
- **变更**: 删除 `_refresh_shop_stats` 方法中遗留的 `_save_shop` docstring 和 18 行死代码块（重复的 UPDATE 逻辑）

### 3. `config.production` → `config.is_production()` 修复
- **根本原因**: `is_production` 是方法不是属性；`environment` 是 Enum 不是字符串
- **文件**: `web/__init__.py`（3 处）、`core/security.py`（1 处）
- **影响**: 修复后 CSRF 生产环境强制检查、HTTPS 警告、CORS 配置才能正确判断环境

## 测试结果
- `tests/unit/test_security_headers.py`: 21 passed
- `tests/unit/test_shop_manager.py`: 28 passed
- 总计 49 passed, 0 failed

## 已修复 #4: `_cfg()` 函数被 shadow 问题
- **文件**: `core/security.py`
- **原因**: 行 1011 的 `_cfg = get_config()` 遮蔽了行 41 的 `_cfg()` 函数，导致行 701 的 `CryptoManager.__init__` 等多处调用 `_cfg()` 失败
- **修复**: 移除行 1011 的 `from .config import get_config; _cfg = get_config()`，改为直接调用已有函数 `_cfg()`
