# ACAS Pro - 生产就绪检查清单

## 核心原则

**绝不降级** - 所有功能必须全功能可用，没有例外。

---

## 依赖矩阵

| 服务 | 必需 | 降级方案 | 生产要求 |
|------|------|----------|----------|
| PostgreSQL | ✅ | SQLite (仅开发) | HA主从 |
| Redis | ✅ | LRU内存 (仅开发) | Cluster模式 |
| Vault | ✅ | 本地加密 (仅开发) | HA 3节点 |
| Prometheus | ✅ | 无 | 高可用部署 |
| Nginx | ✅ | 无 | 负载均衡 |

---

## 一键部署

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 运行生产设置
python setup_production.py

# 3. 验证部署
python tests/test_production.py
```

---

## Docker Compose 全栈

```bash
# 启动所有服务
docker-compose up -d

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

---

## 服务架构

```
┌─────────────────────────────────────────────┐
│                  Nginx                       │
│           (SSL/TLS 1.3)                     │
└──────────────────┬──────────────────────────┘
                   │
    ┌──────────────┼──────────────┐
    │              │              │
┌───▼───┐    ┌────▼────┐   ┌─────▼────┐
│ API-1 │    │  API-2  │   │  API-3   │
└───┬───┘    └────┬────┘   └─────┬────┘
    │             │              │
    └─────────────┼──────────────┘
                  │
    ┌─────────────┼──────────────┐
    │             │              │
┌───▼───┐    ┌────▼────┐   ┌────▼────┐
│PostgreSQL│   │  Redis  │   │  Vault  │
│  HA      │   │ Cluster │   │   HA    │
└─────────┘    └─────────┘   └─────────┘
```

---

## 验证命令

```bash
# 测试API
curl http://localhost:8000/health

# 测试数据库
psql -h localhost -U acas -d acas_pro -c "SELECT 1"

# 测试Redis
redis-cli ping

# 测试Vault
vault status
```

---

## 生产检查项

- [ ] 所有依赖服务运行中
- [ ] SSL证书有效
- [ ] 数据库连接正常
- [ ] 缓存服务正常
- [ ] Vault已解封
- [ ] 监控告警配置
- [ ] 备份策略生效
- [ ] 日志收集正常

---

## 故障处理

| 问题 | 诊断 | 解决 |
|------|------|------|
| 服务无法启动 | `docker-compose logs` | 检查端口冲突 |
| 数据库连接失败 | 检查网络/凭证 | 验证.env配置 |
| Vault密封 | `vault status` | `vault operator unseal` |
| 性能下降 | 监控面板 | 扩容/优化查询 |

---

**状态**: 生产就绪 ✅
