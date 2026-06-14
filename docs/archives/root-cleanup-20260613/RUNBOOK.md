# ACAS Pro - 运维手册 (Runbook)

## 快速索引

| 场景 | 命令/操作 |
|------|-----------|
| 服务健康检查 | `curl /health` |
| 查看日志 | `kubectl logs -f deployment/acas-pro-api` |
| 重启服务 | `kubectl rollout restart deployment/acas-pro-api` |
| 数据库备份 | `./backup.sh` |
| 扩容 | `kubectl scale deployment acas-pro-api --replicas=5` |

---

## 1. 部署操作

### 1.1 首次部署

```bash
# 1. 创建命名空间
kubectl apply -f k8s/namespace.yaml

# 2. 配置密钥（修改后执行）
kubectl apply -f k8s/secret.yaml

# 3. 部署数据库和缓存
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml

# 4. 等待数据库就绪
kubectl wait --for=condition=ready pod -l app=postgres --timeout=300s

# 5. 执行数据库迁移
kubectl run migrate --rm -i --restart=Never \
  --image=acas-pro:latest \
  -- alembic upgrade head

# 6. 部署应用
kubectl apply -k k8s/

# 7. 验证
kubectl get pods -n acas-pro
kubectl get svc -n acas-pro
```

### 1.2 滚动更新

```bash
# 更新镜像
kubectl set image deployment/acas-pro-api \
  api=acas-pro:v1.0.1 -n acas-pro

# 监控滚动状态
kubectl rollout status deployment/acas-pro-api -n acas-pro

# 回滚（如需要）
kubectl rollout undo deployment/acas-pro-api -n acas-pro
```

### 1.3 蓝绿部署

```bash
# 部署绿色版本
kubectl apply -f k8s/green-deployment.yaml

# 验证绿色版本健康
kubectl wait --for=condition=ready pod -l version=green --timeout=300s

# 切换流量
kubectl patch service acas-pro-api -p '{"spec":{"selector":{"version":"green"}}}'

# 保留蓝色版本（观察期后删除）
```

---

## 2. 监控告警

### 2.1 关键指标阈值

| 指标 | 警告 | 严重 | 紧急 |
|------|------|------|------|
| CPU 使用率 | >70% | >85% | >95% |
| 内存使用率 | >75% | >85% | >95% |
| P95 延迟 | >500ms | >1s | >2s |
| 错误率 | >1% | >5% | >10% |
| 磁盘使用率 | >80% | >90% | >95% |

### 2.2 告警响应

#### P1 - 服务不可用

**症状**: 健康检查失败，流量为 0

**响应**:
```bash
# 1. 检查 Pod 状态
kubectl get pods -n acas-pro

# 2. 查看事件
kubectl get events -n acas-pro --sort-by='.lastTimestamp'

# 3. 查看日志
kubectl logs -l app=acas-pro-api -n acas-pro --tail=100

# 4. 检查资源
kubectl top pods -n acas-pro

# 5. 如需要，快速扩容
kubectl scale deployment acas-pro-api --replicas=5 -n acas-pro
```

#### P2 - 性能下降

**症状**: P95 延迟 > 1s

**响应**:
```bash
# 1. 检查数据库连接池
kubectl exec -it deploy/acas-pro-api -n acas-pro -- python -c "
from sqlalchemy import create_engine
engine = create_engine('postgresql://...')
print(engine.pool.status())
"

# 2. 检查慢查询
kubectl exec -it deploy/postgres -n acas-pro -- psql -U acas_user -c "
SELECT query, mean_exec_time FROM pg_stat_statements 
ORDER BY mean_exec_time DESC LIMIT 10;
"

# 3. 检查 Redis
kubectl exec -it deploy/redis -n acas-pro -- redis-cli info stats
```

#### P3 - 数据库问题

**症状**: 连接失败，查询超时

**响应**:
```bash
# 1. 检查 PostgreSQL 状态
kubectl get pods -l app=postgres -n acas-pro

# 2. 检查连接数
kubectl exec -it deploy/postgres -n acas-pro -- psql -U acas_user -c "
SELECT count(*) FROM pg_stat_activity;
"

# 3. 终止长时间运行的查询
kubectl exec -it deploy/postgres -n acas-pro -- psql -U acas_user -c "
SELECT pg_terminate_backend(pid) FROM pg_stat_activity 
WHERE state = 'active' AND now() - query_start > interval '5 minutes';
"

# 4. 如主库故障，切换备库
# （需预先配置流复制）
```

---

## 3. 故障排查

### 3.1 Pod 崩溃循环

```bash
# 查看崩溃原因
kubectl describe pod <pod-name> -n acas-pro

# 查看前一次容器日志
kubectl logs <pod-name> -n acas-pro --previous

# 常见原因:
# - OOMKilled: 内存不足，增加 limits
# - CrashLoopBackOff: 应用启动失败，检查配置
# - ImagePullBackOff: 镜像拉取失败，检查镜像名
```

### 3.2 网络问题

```bash
# 测试服务连通性
kubectl run debug --rm -i --restart=Never --image=busybox -- \
  wget -qO- http://acas-pro-api/health

# 检查 DNS
kubectl run debug --rm -i --restart=Never --image=busybox -- \
  nslookup postgres.acas-pro.svc.cluster.local

# 检查 Ingress
kubectl get ingress -n acas-pro
kubectl describe ingress acas-pro-api -n acas-pro
```

### 3.3 存储问题

```bash
# 检查 PVC 状态
kubectl get pvc -n acas-pro

# 检查存储使用情况
kubectl exec -it deploy/postgres -n acas-pro -- df -h

# 扩展存储（如支持）
kubectl patch pvc postgres-data -p '{"spec":{"resources":{"requests":{"storage":"20Gi"}}}}' -n acas-pro
```

---

## 4. 数据管理

### 4.1 数据库备份

```bash
# 手动备份
./backup.sh

# 验证备份
ls -la backups/
sha256sum -c backups/acas_*.sha256

# 恢复备份
pg_restore -h localhost -U acas_user -d acas_pro backups/acas_20240101_120000.sqlc
```

### 4.2 数据迁移

```bash
# 生成迁移脚本
alembic revision --autogenerate -m "add_new_table"

# 审查迁移脚本
cat migrations/versions/xxx_add_new_table.py

# 执行迁移
alembic upgrade head

# 回滚（如需要）
alembic downgrade -1
```

---

## 5. 安全操作

### 5.1 轮换密钥

```bash
# 1. 生成新密钥
NEW_JWT_SECRET=$(openssl rand -base64 32)

# 2. 更新 Secret
kubectl patch secret acas-pro-secrets -n acas-pro \
  --type='json' \
  -p='[{"op": "replace", "path": "/data/JWT_SECRET", "value":"'$(echo -n $NEW_JWT_SECRET | base64)'"}]'

# 3. 滚动重启
kubectl rollout restart deployment/acas-pro-api -n acas-pro

# 4. 通知用户重新登录
```

### 5.2 封锁可疑 IP

```bash
# 添加网络策略
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: block-suspicious
  namespace: acas-pro
spec:
  podSelector:
    matchLabels:
      app: acas-pro-api
  policyTypes:
    - Ingress
  ingress:
    - from:
        - ipBlock:
            cidr: 10.0.0.0/8  # 只允许内网
      ports:
        - protocol: TCP
          port: 8000
EOF
```

---

## 6. 性能调优

### 6.1 数据库优化

```sql
-- 查看慢查询
SELECT query, calls, mean_time, total_time 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;

-- 添加索引（如需要）
CREATE INDEX CONCURRENTLY idx_forecasts_product_date 
ON forecasts(product_id, created_at);

-- 分析表
ANALYZE forecasts;

-- 清理死元组
VACUUM ANALYZE forecasts;
```

### 6.2 应用优化

```bash
# 调整 Worker 数量
# 公式: workers = 2 * CPU核心数 + 1
kubectl set env deployment/acas-pro-api WORKERS=5 -n acas-pro

# 调整连接池
kubectl set env deployment/acas-pro-api DB_POOL_SIZE=20 -n acas-pro

# 启用 Gunicorn 配置
cat > gunicorn.conf.py << 'EOF'
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
keepalive = 5
timeout = 60
graceful_timeout = 30
max_requests = 1000
max_requests_jitter = 50
EOF
```

---

## 7. 灾难恢复

### 7.1 完全故障恢复

```bash
# 1. 确认故障范围
kubectl get pods -n acas-pro --all-namespaces

# 2. 从备份恢复数据库
# （在新集群上执行）
pg_restore -h new-postgres -U acas_user -d acas_pro latest_backup.sqlc

# 3. 重新部署应用
kubectl apply -k k8s/

# 4. 验证数据完整性
kubectl exec -it deploy/acas-pro-api -n acas-pro -- python -c "
from src.acas_pro.core.database import get_db
db = next(get_db())
count = db.execute('SELECT COUNT(*) FROM users').scalar()
print(f'Users: {count}')
"

# 5. 切换 DNS/负载均衡
```

### 7.2 数据损坏恢复

```bash
# 1. 停止写入
kubectl scale deployment acas-pro-api --replicas=0 -n acas-pro

# 2. 确定损坏时间点
# 查看日志找到最后正常时间

# 3. 恢复到时间点（PITR）
# 需预先配置 WAL 归档
pg_basebackup -h backup-server -D /var/lib/postgresql/data -X stream

# 4. 验证数据
# 5. 恢复服务
kubectl scale deployment acas-pro-api --replicas=3 -n acas-pro
```

---

## 8. 联系信息

| 角色 | 联系方式 | 响应时间 |
|------|----------|----------|
| 值班工程师 | oncall@acas-pro.com | 5分钟 |
| 技术负责人 | tech-lead@acas-pro.com | 15分钟 |
| 安全团队 | security@acas-pro.com | 30分钟 |

---

## 附录

### A. 常用命令速查

```bash
# 查看所有资源
kubectl get all -n acas-pro

# 进入 Pod 调试
kubectl exec -it <pod-name> -n acas-pro -- /bin/sh

# 端口转发
kubectl port-forward svc/acas-pro-api 8000:80 -n acas-pro

# 查看资源使用
kubectl top nodes
kubectl top pods -n acas-pro

# 导出日志
kubectl logs -l app=acas-pro-api -n acas-pro --since=24h > logs.txt
```

### B. 升级检查清单

- [ ] 备份数据库
- [ ] 在 staging 环境验证
- [ ] 更新 CHANGELOG
- [ ] 通知用户维护窗口
- [ ] 准备回滚方案
- [ ] 监控升级过程
- [ ] 验证功能正常
- [ ] 发送升级完成通知
