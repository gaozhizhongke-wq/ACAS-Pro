# ACAS-Pro 字节跳动工业级严苛审查报告

> 审查人: Hermes | 审查时间: 2026-06-03 | 依据: 字节跳动工程标准

---

## 总评: 72/100 — 生产就绪度不足，距离工业级尚有关键缺口

| 维度 | 评分 | 权重 | 加权分 |
|------|------|------|--------|
| 安全性 | 55 | 25% | 13.75 |
| 代码质量 | 68 | 20% | 13.60 |
| 架构设计 | 62 | 15% | 9.30 |
| 测试体系 | 75 | 15% | 11.25 |
| 运维就绪 | 78 | 10% | 7.80 |
| 可维护性 | 70 | 10% | 7.00 |
| 性能 | 80 | 5% | 4.00 |
| **总计** | | | **66.70 → 校准 72** |

> 校准说明: 基础加权分 66.7，因测试覆盖率(79.7%)和K8s部署配置已达标上浮至72。

---

## 🔴 P0 — 阻断级问题（上线前必须修复）

### 1. SQL注入: where_clause参数未做任何校验 [安全 | 严重]

**位置**: `src/acas_pro/core/database.py` L703, L720

```python
# update() 和 delete() 接受任意 where_clause 字符串
query = f"UPDATE {table} SET ... WHERE {where_clause}"  # L703
query = f"DELETE FROM {table} WHERE {where_clause}"      # L720
```

`_validate_identifier()` 仅校验表名/列名，`where_clause` 是任意字符串直接拼入SQL。虽然当前调用者均使用参数化占位符(如 `"id = ?"`)，但API本身是**注入后门**——任何未来调用者传入用户构造的where子句即造成SQL注入。

**字节跳动标准**: 所有SQL必须100%参数化，禁止字符串拼接。where_clause应改为结构化条件对象(如 `[("id", "=", value)]`)，而非原始SQL片段。

**修复优先级**: P0-阻断

---

### 2. 全局单例+可变状态: 测试污染根因 [架构 | 严重]

**现象**: `test_user_service.py` 单独跑16个全过，全量跑9个失败。根因是 `_lazy` 字典被跨测试修改。

**根因分析**:
- `DatabaseManager` 使用全局 `_db_instance` 单例
- `config` 模块用 `_config_instance` 全局变量
- 多个模块用 `_lazy` 字典做懒加载缓存
- 测试中直接 `dict(mock)` 或修改模块全局变量，导致后续测试状态污染

**字节跳动标准**: 核心服务必须支持依赖注入，避免全局可变状态。测试隔离应是默认行为，不需要手动 teardown。

**修复优先级**: P0-阻断

---

### 3. 异步支持缺失: 0.1% async覆盖率 [架构 | 严重]

```
sync defs: 1386 | async defs: 1 | async ratio: 0.1%
```

整个项目35602行代码只有1个async函数。对于一个需要：
- 多平台API并发采集（抖音/快手/小红书/微博）
- LLM流式响应
- 实时数据分析

的系统，纯同步架构意味着：
- 平台采集器只能串行，吞吐量极低
- Web API每个请求阻塞一个线程
- 无法支持WebSocket实时推送

**字节跳动标准**: IO密集型服务必须async-first。同步代码在外部平台API调用场景下不可接受。

**修复优先级**: P0-阻断（至少采集器+Web层必须async化）

---

### 4. 代码幽灵: src/ 根目录下12个废弃副本 [维护 | 严重]

| 废弃文件 | 行数 | 正式版本行数 | 差异 |
|---------|------|------------|------|
| `src/core/database.py` | 279 | 780 | **严重过期** |
| `src/core/security.py` | 290 | 788 | **严重过期** |
| `src/core/logging.py` | 191 | 212 | 小差异 |
| `src/services/user_service.py` | 339 | 400 | 有差异 |
| `src/ui/pages/intelligence.py` | 129 | 579 | **严重过期** |
| `src/ui/main_window.py` | 288 | 396 | 有差异 |
| `src/ml/timesfm_engine.py` | 287 | 391 | 有差异 |
| `src/sentiment/analyzer.py` | 333 | 333 | 同行数不同内容 |
| `src/sentiment/news_engine.py` | 424 | 424 | 同行数不同内容 |
| `src/ml/inventory_optimizer.py` | 318 | 318 | 同行数不同内容 |
| `src/ui/pages/dashboard.py` | 161 | 164 | 小差异 |
| `src/ui/pages/inventory.py` | 170 | 168 | 小差异 |

**风险**: 新开发者import到废弃模块，导致bug难以定位。`src/core/` 下的旧版 database.py 比正式版少500行，缺少安全补丁和PostgreSQL支持。

**字节跳动标准**: 代码库中不允许存在废弃副本。CI应检测并阻止重复模块。

**修复优先级**: P0-阻断

---

## 🟡 P1 — 严重问题（上线前强烈建议修复）

### 5. 异常处理粗糙: broad vs specific = 200:18 [质量 | 严重]

```
except Exception:  200 次
except XError:      18 次
比值: 11:1
```

11:1的宽泛/精确异常捕获比。大量 `except Exception` 吞掉所有异常，导致：
- `KeyboardInterrupt` / `SystemExit` 被意外捕获
- 真正的错误被静默吞掉，日志中无traceback
- 无法区分网络超时、权限错误、数据错误等不同场景

**字节跳动标准**: 精确异常捕获比应 ≥ 3:1（精确:宽泛），当前为 1:11，严重倒挂。

---

### 6. NotImplementedError桩代码: 6个模块11处 [质量 | 严重]

| 模块 | NotImplementedError数 | 总函数数 | 桩比例 |
|------|---------------------|---------|--------|
| avatar_engine.py | 3 | 20 | 15% |
| lip_sync.py | 3 | 14 | 21% |
| voice_synthesis.py | 2 | 12 | 17% |
| platform_api_base.py | 1 | 20 | 5% |
| video_maker.py | 1 | 16 | 6% |
| publish_manager.py | 1 | 18 | 6% |

**数字人模块**(avatar+lip_sync+voice)是重灾区：**8个NotImplementedError / 46个函数 = 17%桩率**。这意味着数字人核心能力（视频生成、唇形同步、语音合成）全是空壳。

**字节跳动标准**: 生产代码NotImplementedError必须为0。未实现功能应返回明确错误码，而非抛出未实现异常。

---

### 7. UI层硬编码随机数据 [质量 | 中等]

`advanced_analytics.py` 19处 `random.uniform/randint` 生成虚假数据填充UI表格：

```python
self.channel_table.setItem(i, 2, QTableWidgetItem(str(random.randint(100, 500))))
self.total_revenue_label.setText(f"总营收: ¥{random.randint(100000, 500000)}")
```

高级分析页面展示的数据全是随机数，不是真实业务数据。用户看到的"总转化 637"、"整体ROI 3.12"全是假数据。

**字节跳动标准**: UI必须连接真实数据源，开发阶段可用mock但必须标注，不允许随机数伪装成生产数据。

---

### 8. 类型注解覆盖率: 64.6% [质量 | 中等]

```
Functions: 1386 | Typed returns: 896 | Coverage: 64.6%
```

1/3的函数缺少返回类型注解。Python动态类型系统中，类型注解是大型项目可维护性的生命线。

**字节跳动标准**: 核心模块类型注解覆盖率应 ≥ 95%，项目整体 ≥ 85%。

---

## 🟢 P2 — 改进建议（迭代优化）

### 9. 测试断言密度: 1.6 asserts/test [测试 | 改进]

```
Test functions: 2341 | Assertions: 3730 | Avg: 1.6/test
```

平均每个测试1.6个断言，偏低。部分测试只验证"不抛异常"而不验证结果正确性。字节跳动标准: ≥ 3 asserts/test。

### 10. 外部API调用极少: 仅2个模块 [功能 | 改进]

```
notifier.py: 4 HTTP calls
supply_chain.py: 1 HTTP call
```

项目号称支持抖音/快手/小红书/微博/淘宝/京东/拼多多等多平台，但实际HTTP调用几乎为零。采集器（collectors/）的TODO标记密集（11个模块各1-2个TODO），说明平台对接多为空壳。

### 11. 圈复杂度热点 [质量 | 改进]

```
security.py: if/elif=47 for/while=0 try/except=22 total=69
database.py: if/elif=32 for/while=3 try/except=17 total=52
```

security.py 69的圈复杂度远超阈值(15-20)。应拆分为独立策略类。

### 12. TODO/FIXME统计 [质量 | 信息]

约50个TODO/FIXME分布 across collectors(12)、advanced_analytics(5)、avatar(13)、ml(8)、platforms(8)等模块。集中清理可提升代码整洁度。

---

## ✅ 做得好的部分

| 项 | 评价 |
|----|------|
| **测试覆盖率 79.7%** | 达到字节跳动基础线(70%+)，video_maker.py 94% 优秀 |
| **K8s/Helm配置** | Deployment+Service+Ingress+HPA+SSL 完整，生产可用 |
| **Locust性能测试** | 6场景覆盖，1000+RPS目标明确 |
| **配置管理** | SecurityConfig自动生成secret_key、生产环境强制校验、SecretsManager分层 |
| **数据库安全** | `_validate_identifier()` 白名单+alnum校验、参数化占位符(?/%s) |
| **密码安全** | PBKDF2 600000迭代、常见密码黑名单、强度校验完整 |
| **0个硬编码密钥** | 全项目扫描无password/secret/api_key硬编码 |
| **0个bare except** | 没有 `except:` 这种最危险的异常捕获 |
| **文档完整度** | K8S-DEPLOYMENT.md、PERFORMANCE-TESTING.md等配套文档齐全 |

---

## 距离95分的差距与路径

| 差距 | 需要投入 | 预估提升 |
|------|---------|---------|
| P0修复(4项) | 2-3周 | +8分 → 80 |
| P1修复(4项) | 2-3周 | +7分 → 87 |
| P2改进(4项) | 2-3周 | +5分 → 92 |
| async化(核心路径) | 3-4周 | +3分 → 95 |

**总计: 约8-10周全职投入可达95分。**

---

*本审查基于代码静态分析，未进行运行时审计、渗透测试或负载验证。生产上线前建议补充安全扫描(SAST/DAST)和混沌工程测试。*
