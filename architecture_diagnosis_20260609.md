# ACAS-Pro 生产持久化与架构一致性诊断 — 2026-06-09

## 目标
深度诊断 ACAS-Pro 的生产持久化和架构一致性问题，给出优化方案。

## 关键发现

### Schema 分散（最致命）
- `database.py` 定义 13 张核心表
- 30+ 张业务表的 CREATE TABLE 散落在 16 个模块中
- 4 张表存在重复定义冲突：orders, products, transactions, platform_accounts
- PostgreSQL 实际不可用（SQLite 专属语法散落各模块）

### 生产持久化
- SQLite 单文件，无并发写入、无灾备、无流式复制
- DatabaseManager 连接池薄弱（SQLite 只有 threading.local 单连接）
- execute() 的 SQL 方言翻译只覆盖少量场景

### 测试
- 2430 个测试收集，覆盖率 30%（目标 78%）
- 单例 DatabaseManager 导致测试间状态泄漏
- DELETE FROM 隔离不如事务回滚可靠

### 代码 Bug
- `DatabaseManager.__del__` 和 `close()` 使用未定义的 `logger` 变量

## 优化方案
- 阶段一：Schema 集中化（core/schema.py + Alembic），~12h
- 阶段二：DatabaseManager 加固（SQLAlchemy Core + 连接池），~15h  
- 阶段三：模块间一致性（BaseRepository + CI 守卫），~11h
- 总计 ~38h

## 用户决策
待定 — 用户尚未决定从哪个阶段开始执行
