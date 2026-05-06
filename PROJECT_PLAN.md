# ACAS Pro - 企业级交付开发计划

**目标**: 4周内达到企业级安全基线，可全球交付  
**启动日期**: 2026-05-03  
**交付日期**: 2026-05-31

---

## 阶段划分

### Phase 1: 安全基线 (Week 1-2) - 交付前提
**目标**: TLS、加密、RBAC、审计

| 模块 | 任务 | 工时 | 负责人 | 交付物 |
|------|------|------|--------|--------|
| TLS | Nginx + Let's Encrypt | 16h | DevOps | `nginx_tls.conf` |
| 加密 | Vault集成 | 24h | Backend | `vault_client.py` |
| RBAC | 权限体系 | 32h | Backend | `rbac.py` |
| 审计 | 不可篡改日志 | 20h | Backend | `audit_logger.py` |
| 认证 | JWT + MFA | 24h | Backend | `auth_service.py` |

**Week 1 里程碑**: TLS + 加密完成  
**Week 2 里程碑**: RBAC + 审计完成

---

### Phase 2: 高可用 (Week 3) - 生产前提
**目标**: 数据库、缓存、容器化

| 模块 | 任务 | 工时 | 交付物 |
|------|------|------|--------|
| 数据库 | PostgreSQL主从 | 24h | `postgres-ha.yaml` |
| 缓存 | Redis Cluster | 16h | `redis-cluster.yaml` |
| 容器 | Docker + K8s | 32h | `k8s-manifests/` |
| 网关 | Kong/API Gateway | 16h | `kong-config.yaml` |
| 监控 | Prometheus/Grafana | 16h | `monitoring-stack/` |

**Week 3 里程碑**: K8s集群可部署

---

### Phase 3: 合规认证 (Week 4) - 投标前提
**目标**: 文档、测试、认证准备

| 模块 | 任务 | 工时 | 交付物 |
|------|------|------|--------|
| 文档 | 架构/运维/安全 | 24h | `docs/` |
| 测试 | 渗透测试 | 16h | 第三方报告 |
| 合规 | GDPR/等保文档 | 16h | 合规声明 |
| 保险 | 网络安全险 | 8h | 保单 |
| 演练 | 灾备演练 | 8h | 演练报告 |

**Week 4 里程碑**: 企业级交付包

---

## 每日进度安排

### Week 1 (5/3-5/9) - TLS + 加密

#### Day 1 (5/3 Sun) - TLS基础
- [ ] 09:00-12:00 Nginx配置 + SSL证书
- [ ] 13:00-17:00 HTTPS强制跳转 + HSTS
- [ ] 18:00-20:00 证书自动续期脚本
- **交付**: `nginx_tls.conf`, `ssl_renew.sh`

#### Day 2 (5/4 Mon) - Vault集成
- [ ] 09:00-12:00 HashiCorp Vault部署
- [ ] 13:00-17:00 密钥注入 + 动态凭证
- [ ] 18:00-20:00 加密存储迁移
- **交付**: `vault_client.py`, 加密配置

#### Day 3 (5/5 Tue) - Vault生产化
- [ ] 09:00-12:00 Vault高可用配置
- [ ] 13:00-17:00 密钥轮换策略
- [ ] 18:00-20:00 灾难恢复测试
- **交付**: `vault-ha.yaml`, 密钥恢复流程

#### Day 4 (5/6 Wed) - RBAC设计
- [ ] 09:00-12:00 权限模型设计
- [ ] 13:00-17:00 角色定义 + 数据库表
- [ ] 18:00-20:00 权限中间件
- **交付**: `rbac.py`, 权限表结构

#### Day 5 (5/7 Thu) - RBAC实现
- [ ] 09:00-12:00 用户-角色-权限关联
- [ ] 13:00-17:00 API权限控制
- [ ] 18:00-20:00 前端权限组件
- **交付**: 完整RBAC系统

#### Day 6 (5/8 Fri) - 审计日志
- [ ] 09:00-12:00 审计事件定义
- [ ] 13:00-17:00 不可篡改日志实现
- [ ] 18:00-20:00 日志查询接口
- **交付**: `audit_logger.py`

#### Day 7 (5/9 Sat) - Week1收尾
- [ ] 09:00-12:00 集成测试
- [ ] 13:00-17:00 安全扫描
- [ ] 18:00-20:00 Week1交付包
- **交付**: Week1安全基线包

---

### Week 2 (5/10-5/16) - 认证 + 数据库

#### Day 8-10: JWT + MFA
- JWT实现 (access/refresh token)
- 多因素认证 (TOTP/SMS)
- 会话管理 + 登出
- **交付**: `auth_service.py`

#### Day 11-12: PostgreSQL
- 主从复制配置
- 连接池 + 读写分离
- 数据迁移脚本
- **交付**: `postgres-ha.yaml`

#### Day 13-14: Week2收尾
- 数据库加密 (TDE)
- 备份策略
- 集成测试
- **交付**: Week2数据库包

---

### Week 3 (5/17-5/23) - K8s + 监控

#### Day 15-17: K8s基础
- Deployment/Service/Ingress
- ConfigMap/Secret
- HPA自动扩缩容
- **交付**: `k8s-manifests/`

#### Day 18-19: 监控体系
- Prometheus + Grafana
- 告警规则
- 日志聚合 (Loki)
- **交付**: `monitoring-stack/`

#### Day 20-21: Week3收尾
- 混沌测试
- 压力测试
- 灾备演练
- **交付**: Week3高可用包

---

### Week 4 (5/24-5/31) - 合规 + 交付

#### Day 22-24: 文档
- 架构文档 (C4模型)
- 运维手册 (Runbook)
- 安全白皮书
- **交付**: `docs/`

#### Day 25-26: 第三方测试
- 渗透测试 (委托)
- 代码审计 (SonarQube)
- 合规检查
- **交付**: 测试报告

#### Day 27-28: 保险 + 法务
- 网络安全险购买
- 免责声明
- 合同条款
- **交付**: 保单, 法务文件

#### Day 29-31: 最终交付
- 集成测试
- 生产部署
- 客户交付
- **交付**: ACAS Pro v2.1 Enterprise

---

## 模块详细设计

### 1. TLS模块
```
组件:
- Nginx (反向代理)
- Let's Encrypt (证书)
- Certbot (自动续期)

配置:
- TLS 1.3 only
- HSTS max-age=31536000
- OCSP Stapling
- Perfect Forward Secrecy
```

### 2. Vault模块
```
组件:
- HashiCorp Vault (3节点HA)
- Kubernetes Auth
- Database Dynamic Secrets

功能:
- 密钥加密存储
- 自动轮换
- 审计日志
- 灾难恢复
```

### 3. RBAC模块
```
角色:
- super_admin: 全部权限
- admin: 用户/账号/内容管理
- operator: 日常运营
- viewer: 只读
- auditor: 审计只读

权限粒度:
- resource:action (user:read)
- 数据范围 (tenant隔离)
- 时间限制 (临时权限)
```

### 4. 审计模块
```
事件类型:
- AUTH: 登录/登出/失败
- DATA: 增删改查
- CONFIG: 配置变更
- ADMIN: 权限变更

存储:
- 只追加文件
- 哈希链防篡改
- 定期归档到对象存储
- 保留期7年
```

---

## 风险与应对

| 风险 | 概率 | 影响 | 应对 |
|------|------|------|------|
| Vault学习曲线 | 中 | 延期 | 提前准备，备用方案 |
| K8s复杂度 | 中 | 延期 | 先用Docker Compose |
| 第三方测试排期 | 高 | 延期 | 提前2周预约 |
| 保险购买周期 | 中 | 延期 | 并行启动流程 |

---

## 交付检查清单

### 技术检查
- [ ] TLS A+评分 (SSL Labs)
- [ ] 渗透测试无高危漏洞
- [ ] 性能测试 >1000 QPS
- [ ] 故障恢复 <5分钟
- [ ] 数据备份可恢复

### 合规检查
- [ ] GDPR技术措施文档
- [ ] 等保二级自评
- [ ] 数据分类分级
- [ ] 隐私影响评估

### 商务检查
- [ ] 网络安全险生效
- [ ] 免责声明签署
- [ ] SLA协议确认
- [ ] 应急预案确认

---

## 项目看板

| 状态 | 数量 | 说明 |
|------|------|------|
| 🔴 阻塞 | 0 | 无阻塞项 |
| 🟡 进行中 | 0 | 待启动 |
| 🟢 已完成 | 0 | 待完成 |
| ⚪ 未开始 | 31 | 全部任务 |

**当前阶段**: Week 1 Day 1  
**整体进度**: 0%  
**风险状态**: 🟢 正常
