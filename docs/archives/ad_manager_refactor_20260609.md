# AdManager 重构：DatabaseManager 集成

## 目标
将 `ad_manager.py` 从直接 sqlite3 操作重构为使用 `DatabaseManager` 单例，解决审计中的 A1+P1 问题。

## 主要改动

### 1. ad_manager.py 完整重写
- **移除** 直接 `sqlite3`/`aiosqlite` 连接管理（每次操作新建连接的反模式）
- **改用** `DatabaseManager` 单例（通过懒加载 property），所有 DB 操作走 `db.insert/update/delete/fetch_one/fetchall/execute`
- **异步方法** 委托给 `db.insert_async/update_async/delete_async/fetchall_async/execute_one_async`
- **移除** `__del__` 中的 f-string 错误
- **移除** `_init_database` 的连接泄漏问题
- **保留** 完整数据模型（AdPlatform/CampaignStatus/BudgetType/AdCreative/AdSet/AdCampaign/AdAccount）
- **新增** `_row_to_account`/`_row_to_campaign` 辅助函数处理 DB 行到 dataclass 的转换（含 token 解密）
- **向后兼容** `db_path` 参数（legacy，不再直接使用）和 `close()` 方法（no-op）
- **SQL 注入防护** 参数化查询，days 参数类型校验

### 2. database.py 白名单更新
在 `_VALID_IDENTIFIERS` 中添加广告模块相关的表名和列名：
- 表: `ad_accounts`, `ad_campaigns`, `ad_records`
- 列: `adset_id`, `adsets_data`, `impression_url`, `click_url`, `tracking_url`, `conversion_goal`, `budget_type`, `budget_amount`, `conversion_rate`, `cost_per_conversion`, `daily_budget_limit`, `total_spend_7d`, `total_spend_30d`, `total_impressions`, `total_clicks`, `total_conversions`, `total_spend`, `access_token`, `refresh_token`, `token_expires_at`

## 测试结果
- 36/36 测试通过（`test_ads_modules.py`）
- 覆盖率不足报错（7% < 78%）是预期的，仅此文件覆盖

## 已知遗留
- `audience_targeting.py` 仍使用直接 sqlite3（ResourceWarning 来源），未在本次重构范围
- `DatabaseManager` 单例模式意味着测试共享同一个 DB 实例，`db_path` 参数仅为 API 兼容保留
