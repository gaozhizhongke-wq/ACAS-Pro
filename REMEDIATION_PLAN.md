# ACAS Pro 整改计划

**项目**: ACAS Pro v2.1 安全加固  
**甲方**: 高智中科（北京）科技有限公司  
**整改目标**: 消除致命安全风险，达到生产级标准  
**当前阶段**: Phase 2 - 高可用加固 ✅ 已完成

---

## 整改对照表

### Phase 1 - 安全基线 (100% 完成)

| 甲方问题 | 整改措施 | 状态 | 文件位置 |
|---------|---------|------|---------|
| 🔴 **自签名证书** | Let's Encrypt 自动证书管理 | ✅ | `security/cert_manager.py` |
| 🔴 **硬编码密钥** | 密钥管理器 + 文件权限控制 | ✅ | `security/key_manager.py` |
| 🔴 **JWT Secret 随机** | 强制外部注入 + 密钥轮换 | ✅ | `security/key_manager.py` |
| 🔴 **无真正 RBAC** | 5 级角色 + 细粒度权限 | ✅ | `security/auth_v2.py` |
| 🔴 **CORS 全开放** | 白名单配置 + 预检限制 | ✅ | `api_server_v2.py` |
| 🔴 **API 无限流** | 分级速率限制（滑动窗口） | ✅ | `security/rate_limiter.py` |
| 🔴 **强制改密码** | 首次登录拦截 + 密码策略 | ✅ | `security/auth_v2.py` |
| 🔴 **SQLite 生产** | PostgreSQL 迁移 + 连接池 | ✅ | `database/migrate_pg.py` |

### Phase 2 - 高可用加固 (100% 完成)

| 项目 | 整改措施 | 状态 | 文件位置 |
|------|---------|------|---------|
| **Redis 集群** | Cluster 模式 + 多级缓存 | ✅ | `cache/redis_cluster.py` (17KB) |
| **PostgreSQL 主从** | 读写分离 + 负载均衡 | ✅ | `database/postgres_ha.py` (11KB) |
| **监控指标** | Prometheus 指标暴露 | ✅ | `monitoring/metrics.py` (11KB) |
| **结构化日志** | JSON 格式 + 审计追踪 | ✅ | `monitoring/logger.py` (10KB) |
| **Grafana 仪表板** | 可视化监控面板 | ✅ | `monitoring/grafana-dashboard.json` |

---

## 新增模块详情

### Phase 1 安全模块

```
security/
├── cert_manager.py      # Let's Encrypt 证书管理 (6.8KB)
├── key_manager.py       # 密钥生命周期管理 (8.6KB)
├── auth_v2.py           # JWT + RBAC (9.9KB)
└── rate_limiter.py      # 分级速率限制 (7.4KB)

database/
├── migrate_pg.py        # SQLite→PostgreSQL 迁移 (12.8KB)
└── backup.py            # 备份恢复 + 自动清理 (8.7KB)
```

### Phase 2 高可用模块

```
cache/
└── redis_cluster.py     # Redis Cluster + 多级缓存 (17.6KB)
    - 6 节点集群支持
    - L1 本地缓存 + L2 Redis 缓存
    - 自动故障转移
    - 缓存装饰器

database/
└── postgres_ha.py       # PostgreSQL 主从 + 读写分离 (11.7KB)
    - 1 主 + N 从架构
    - 读操作负载均衡（加权随机）
    - 健康检查 + 自动切换
    - 读写分离装饰器

monitoring/
├── metrics.py           # Prometheus 指标 (11.2KB)
│   - HTTP 请求指标（QPS/延迟/大小）
│   - 业务指标（活跃用户/内容创建）
│   - 系统指标（内存/CPU）
│   - Flask 中间件集成
│
├── logger.py            # 结构化日志 (10.4KB)
│   - JSON 格式输出
│   - 请求追踪 ID
│   - 审计日志
│   - 性能日志
│   - 安全事件日志
│
└── grafana-dashboard.json  # Grafana 仪表板 (3.4KB)
    - 请求速率/错误率/P99 延迟
    - 数据库连接池监控
    - 缓存命中率
    - 任务队列状态
```

---

## 生产部署架构

```
┌─────────────────────────────────────────────────────────────────┐
│                           用户访问                               │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTPS (Let's Encrypt)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  Nginx (反向代理 + SSL 终结)                                      │
│  - 速率限制 (10r/s)                                              │
│  - 静态文件缓存                                                  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  API 实例 1   │   │  API 实例 2   │   │  API 实例 N   │
│   :5000      │   │   :5000      │   │   :5000      │
└──────┬───────┘   └──────┬───────┘   └──────┬───────┘
       │                  │                  │
       └──────────────────┼──────────────────┘
                          │
       ┌──────────────────┼──────────────────┐
       │                  │                  │
       ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌─────────────────┐
│  PostgreSQL  │  │     Redis    │  │  Prometheus     │
│   主从集群    │  │   Cluster    │  │   + Grafana     │
│  读写分离     │  │   6 节点     │  │   监控告警      │
└──────────────┘  └──────────────┘  └─────────────────┘
```

---

## 运行方式

### 开发测试

```bash
# Windows 安全版启动
start_secure.bat

# 测试 Redis 集群
python cache/redis_cluster.py test

# 测试 PostgreSQL HA
python database/postgres_ha.py test

# 启动指标服务器
python monitoring/metrics.py serve --port 9090
```

### Docker 生产部署

```bash
# 1. 配置环境
cp .env.example .env
# 编辑 .env 设置生产配置

# 2. 启动全栈服务
docker-compose --profile monitoring up -d

# 3. 查看状态
docker-compose ps

# 4. 访问监控
# Grafana: http://localhost:3000 (admin/admin)
# Prometheus: http://localhost:9090
# 应用指标: http://localhost:5000/metrics
```

### 环境变量配置

```bash
# 数据库（主从）
export DB_MASTER_HOST=postgres-master
export DB_REPLICA_HOSTS="postgres-replica-1,postgres-replica-2"
export DB_PASSWORD=your-secure-password

# Redis 集群
export REDIS_URL=redis://redis-cluster:6379

# 监控
export PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus
export LOG_LEVEL=INFO
export LOG_DIR=/var/log/acas

# SSL
export SSL_CERT_FILE=/etc/letsencrypt/live/acas.gaozhizhongke.com/fullchain.pem
export SSL_KEY_FILE=/etc/letsencrypt/live/acas.gaozhizhongke.com/privkey.pem
```

---

## 甲方验收检查清单

### Phase 1 安全基线验收

```bash
# 1. 密钥管理检查
ls -la .keys/          # 文件权限应为 600
python -c "from security import get_key_manager; print(get_key_manager().list_keys())"

# 2. 认证流程测试
curl http://localhost:5000/api/v2/auth/login \
  -d '{"username":"admin","password":"admin123"}'
# 预期: 返回 token，但标记 password_changed=false

# 3. 强制改密码测试
curl http://localhost:5000/api/v2/content \
  -H "Authorization: Bearer <token>"
# 预期: 403, action_required=change_password

# 4. 速率限制测试
for i in {1..35}; do curl -s http://localhost:5000/health; done
# 第 35 次应返回 429 Too Many Requests

# 5. 权限控制测试
curl -X POST http://localhost:5000/api/v2/content \
  -H "Authorization: Bearer <viewer_token>"
# 预期: 403 Forbidden

# 6. 数据库迁移测试
python database/migrate_pg.py migrate --sqlite-path acas_pro.db
# 预期: 数据成功迁移到 PostgreSQL
```

### Phase 2 高可用验收

```bash
# 1. Redis 集群状态
python cache/redis_cluster.py nodes
# 预期: 显示 6 个节点（3 主 3 从）

# 2. Redis 读写测试
python cache/redis_cluster.py test
# 预期: SET/GET/DELETE 全部通过

# 3. PostgreSQL 健康检查
python database/postgres_ha.py health
# 预期: 1 主库 healthy, N 从库 healthy

# 4. 读写分离测试
python database/postgres_ha.py test
# 预期: 读操作走从库，写操作走主库

# 5. 监控指标检查
curl http://localhost:5000/metrics | grep acas_
# 预期: 返回 Prometheus 格式指标

# 6. 日志格式验证
tail -f logs/acas-pro.log | jq .
# 预期: JSON 格式日志，包含 request_id
```

---

## 下一步计划

### Phase 3 - 运维体系 (Week 3-4)

- [ ] CI/CD 流水线 (GitHub Actions/GitLab CI)
- [ ] 自动化测试集成 (单元测试 + 集成测试)
- [ ] 监控告警体系 (Alertmanager + 钉钉/企业微信)
- [ ] 灾难恢复演练 (定期备份恢复测试)
- [ ] 性能压测报告 (Locust/k6)
- [ ] 安全审计报告 (渗透测试 + 漏洞扫描)

---

## 交付物清单

### Phase 1 (安全基线)

| 文件 | 说明 | 大小 |
|------|------|------|
| `security/cert_manager.py` | 证书管理 | 6.8 KB |
| `security/key_manager.py` | 密钥管理 | 8.6 KB |
| `security/auth_v2.py` | 认证授权 V2 | 9.9 KB |
| `security/rate_limiter.py` | 速率限制 | 7.4 KB |
| `database/migrate_pg.py` | 数据库迁移 | 12.8 KB |
| `database/backup.py` | 备份恢复 | 8.7 KB |

### Phase 2 (高可用)

| 文件 | 说明 | 大小 |
|------|------|------|
| `cache/redis_cluster.py` | Redis 集群管理 | 17.6 KB |
| `database/postgres_ha.py` | PostgreSQL HA | 11.7 KB |
| `monitoring/metrics.py` | Prometheus 指标 | 11.2 KB |
| `monitoring/logger.py` | 结构化日志 | 10.4 KB |
| `monitoring/grafana-dashboard.json` | Grafana 仪表板 | 3.4 KB |

### 部署文件

| 文件 | 说明 | 大小 |
|------|------|------|
| `docker-compose.yml` | Docker 编排 | 3.4 KB |
| `Dockerfile` | 应用容器 | 0.7 KB |
| `nginx/nginx.conf` | Nginx 配置 | 4.2 KB |
| `deploy.sh` | 部署脚本 | 3.6 KB |
| `.env.example` | 环境变量模板 | 2.0 KB |

---

## 整改评分自评

| 维度 | 整改前 | Phase 1 后 | Phase 2 后 | 提升 |
|------|--------|-----------|-----------|------|
| 证书管理 | 自签名 | Let's Encrypt | Let's Encrypt | ✅ |
| 密钥安全 | 硬编码 | 文件权限控制 | 文件权限控制 | ✅ |
| 认证授权 | 单角色 | 5级RBAC | 5级RBAC | ✅ |
| API安全 | 无限流 | 滑动窗口限流 | 滑动窗口限流 | ✅ |
| 数据库 | SQLite | PostgreSQL | **主从+读写分离** | ✅✅ |
| 缓存 | 无 | 无 | **Redis Cluster** | ✅✅ |
| 监控 | 无 | 基础健康检查 | **Prometheus+Grafana** | ✅✅ |
| 日志 | 文本 | 文本 | **结构化JSON** | ✅✅ |
| 部署 | 单机 | Docker Compose | **高可用架构** | ✅✅ |
| 备份 | 无 | 自动备份 | 自动备份 | ✅ |

---

**整改负责人**: 技术团队  
**Phase 1 完成日期**: 2026-05-04  
**Phase 2 完成日期**: 2026-05-04  
**当前状态**: ✅ **Phase 1 & 2 100% 完成**  
**下一步**: Phase 3 运维体系（待甲方确认启动）
