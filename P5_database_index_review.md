# P5 数据库索引审查报告

生成时间：2026-06-11 05:20 GMT+8
审查范围：`src/acas_pro/db/models.py` 所有模型

## 📊 总览

| 模型 | 表名 | 已有索引 | 缺失索引 | 优先级 |
|------|-------|----------|----------|--------|
| User | users | account | email, phone, role, status, created_at | 中 |
| SocialAccount | social_accounts | platform | user_id (FK), platform_account_id, status, created_at | 高 |
| Product | products | 无 | category, status, platform, shop_id, created_at, sales_count | 高 |
| Order | orders | platform_order_id | user_id (FK), product_id (FK), status, payment_status, created_at | 高 |
| ContentPost | content_posts | platform | account_id (FK), status, scheduled_at, published_at, created_at | 中 |
| TrendData | trend_data | platform, keyword | recorded_at, search_volume, growth_rate, composite(platform,keyword,recorded_at) | 中 |
| InventoryItem | inventory | 无 | product_id (FK), warehouse_id, quantity, updated_at | 中 |
| VideoProject | video_projects | 无 | status, target_platform, created_at, updated_at | 低 |
| VoiceTask | voice_tasks | 无 | voice_id, status, created_at, completed_at | 低 |
| AuditLog | audit_logs | 无 | user_id, action, resource_type, resource_id, status, created_at, composite(user_id,action,created_at) | 高 |

## 🔴 高优先级（建议立即添加）

#### 1. ForeignKey 缺少索引（影响 JOIN 性能）
- `social_accounts.user_id`
- `orders.user_id`
- `orders.product_id`
- `content_posts.account_id`
- `inventory.product_id`

#### 2. 高频查询字段缺少索引
- `products.status`（商品状态查询）
- `products.platform`（平台筛选）
- `orders.status`（订单状态查询）
- `orders.payment_status`（支付状态查询）
- `audit_logs.user_id`（审计查询）
- `audit_logs.action`（审计查询）

## 🟡 中优先级（建议近期添加）

- `users.role`（权限查询）
- `users.status`（用户状态查询）
- `users.created_at`（时间范围查询）
- `social_accounts.status`（账号状态查询）
- `trend_data.recorded_at`（趋势时间查询）
- `inventory.warehouse_id`（仓库筛选）
- `inventory.quantity`（库存预警）

## 🟢 低优先级（可选）

- `products.sales_count`（销量排序）
- `video_projects.status`（项目状态查询）
- `voice_tasks.status`（任务状态查询）
- `audit_logs.created_at`（审计时间查询）

## 🔧 修复示例

### 1. 添加单列索引
```python
# 在 Column 定义中添加 index=True
user_id = Column(String(36), ForeignKey('users.id'), index=True, nullable=False)
```

### 2. 添加复合索引
```python
class TrendData(Base):
    __tablename__ = 'trend_data'
    # ... columns ...
    
    __table_args__ = (
        Index('idx_platform_keyword_recorded', 'platform', 'keyword', 'recorded_at'),
    )
```

### 3. 添加审计表复合索引
```python
class AuditLog(Base):
    __tablename__ = 'audit_logs'
    # ... columns ...
    
    __table_args__ = (
        Index('idx_user_action_time', 'user_id', 'action', 'created_at'),
        Index('idx_resource_time', 'resource_type', 'resource_id', 'created_at'),
    )
```

## 📝 建议行动

1. **立即**：为所有 ForeignKey 添加索引（5 个字段）
2. **近期**：为高频查询字段添加索引（8 个字段）
3. **可选**：添加复合索引（3 个索引）
4. **测试**：在测试环境验证索引效果（EXPLAIN QUERY PLAN）
5. **监控**：生产环境监控慢查询日志

## ⚠ 注意事项

1. **SQLite**：添加索引会锁表，建议在维护窗口执行
2. **PostgreSQL**：支持 CONCURRENTLY 选项，不锁表
3. **MySQL**：添加索引会锁表，建议使用 pt-online-schema-change
4. **索引数量**：单表索引建议不超过 5-7 个（影响写入性能）

---
生成自 P5 数据库索引审查任务
