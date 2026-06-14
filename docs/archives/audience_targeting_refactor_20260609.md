# AudienceTargeting 重构为 DatabaseManager — 2026-06-09

## 目标
将 `audience_targeting.py` 从直接 sqlite3 连接迁移到使用 `DatabaseManager` 单例，消除 ResourceWarning 和资源泄漏。

## 变更

### 1. `audience_targeting.py` — 完全重写
- 移除所有直接 `sqlite3.connect()` 和 `aiosqlite.connect()` 调用
- 改用 `DatabaseManager` 的 `insert/update/delete/fetch_one/fetchall` 及异步方法
- 保留 `db_path` 和 `close()` 的向后兼容（legacy no-op）
- 添加 `_ensure_table()` 方法：通过 `ALTER TABLE ADD COLUMN` 为旧 schema 自动迁移缺失列
- 修复 `BEHAVOR_CATEGORIES` → `BEHAVIOR_CATEGORIES` 拼写错误
- 所有数据模型（AudienceSegment, AgeRange, GeoTargeting, DeviceTargeting）保持不变
- 新增 `_row_to_segment()` 辅助函数处理 DB 行到对象的映射

### 2. `database.py` — Schema 更新
- SQLite 和 PostgreSQL schema 中 `audience_segments` 表：
  - `segment_type` → `type`
  - `size` → `estimated_size`
  - 新增列：gender, age_range, geo_targeting, device_targeting, interests, behaviors, custom_tags, source_audience_id, lookalike_ratio, estimated_daily_impressions, status
- `_VALID_IDENTIFIERS` 白名单：移除 `segment_type`/`size`，新增 `type`/`estimated_size`/`source_audience_id`/`lookalike_ratio`/`estimated_daily_impressions`

### 3. `test_ads_modules.py` — 测试适配
- `ad_manager` 和 `audience_targeting` fixture 不再使用 `temp_db` 参数
- 改为在 fixture 中清理表数据（DELETE FROM）确保测试隔离
- `test_init_with_db_path` 改为仅测试构造函数不报错

## 测试结果
- 36/36 passed ✅
- Coverage 7% < 78% threshold（退出码1，非测试失败）
- 无 ResourceWarning（AudienceTargeting 部分）

## 遗留问题
- AdManager 仍有少量 ResourceWarning（来自 DatabaseManager 内部连接池，非直接 sqlite3 泄漏）
- `estimated_size` 列名与旧 `size` 列不兼容，需删除旧 DB 文件重建
