# ecommerce 模块测试：100% 覆盖 shop_api 客户端

## 目标
为 ACAS-Pro 的电商平台 API 客户端（小红书/抖音/淘宝）编写完整单元测试，覆盖所有代码分支。

## 成果
- **文件**: `tests/unit/test_ecommerce_shop_apis.py` (33KB, 87 tests)
- **覆盖率**:
  - `xiaohongshu_shop_api.py`: **100%** (原 25%)
  - `douyin_shop_api.py`: **100%** (原 31%)
  - `taobao_shop_api.py`: **100%** (原 34%)

## 覆盖范围（每个客户端 29 tests）

每类客户端的测试结构相同，覆盖以下方法：

| 方法 | 场景 |
|------|------|
| `_check_business_error` | success / auth error / API error / missing fields |
| `_build_common_params` | 参数完整性、签名生成 |
| `_request_api` | 正常调用、无biz参数、headers校验 |
| `_do_refresh_token` | 成功/空data/无data |
| `sync_orders` | 成功/日期参数/未认证/异常 |
| `sync_products` | 成功/未认证/异常 |
| `sync_inventory` | 成功/指定product_ids/未认证/异常 |
| `update_product_status` | online/offline/未认证/异常/业务失败 |
| `get_logistics_info` | 成功/空结果/未认证/异常 |
| `exchange_token` | 成功/异常 |

## 关键修复

- **Mock 策略**: 通过 `mock_request` 替换 `client.request` 方法，避免真实 HTTP 调用
- **Douyin 参数**: 使用 `params=` 而非 `data=` 传递请求体 → 断言改为 `kwargs["params"]`
- **Douyin 异常类型**: 捕获 `sqlite3.Error, ValueError, RuntimeError, json.JSONDecodeError`（非通用 `Exception`）
- **Mock 绕过校验**: `_check_business_error` 在基类 `request()` 内部，Mock 后直接返回 dict，业务失败仅返回 False 而非抛异常
