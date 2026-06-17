# ACAS Pro - Vault 灾难恢复手册

## 灾难场景

### 场景1: Vault单节点故障
**症状**: 一个Vault pod无法访问
**影响**: 集群仍可工作，但容错降低
**RTO**: 5分钟
**RPO**: 0

```bash
# 自动处理 - K8s会重启pod
kubectl get pods -n acas-pro -l app=vault

# 手动验证
kubectl exec -it vault-1 -n acas-pro -- vault status
```

### 场景2: Vault集群多数节点故障
**症状**: 2个及以上Vault节点无法访问
**影响**: 集群不可用，无法读取密钥
**RTO**: 30分钟
**RPO**: 0 (Raft快照)

```bash
# 1. 检查节点状态
kubectl get pods -n acas-pro -l app=vault

# 2. 如果pod运行但无法加入集群
kubectl exec -it vault-0 -n acas-pro -- vault operator raft list-peers

# 3. 移除故障节点
kubectl exec -it vault-0 -n acas-pro -- \
  vault operator raft remove-peer vault-1

# 4. 重新初始化故障节点
kubectl delete pod vault-1 -n acas-pro
```

### 场景3: Vault完全不可用 (K8s集群故障)
**症状**: 整个K8s集群无法访问
**影响**: 所有服务无法获取密钥
**RTO**: 4小时
**RPO**: 1小时 (快照间隔)

```bash
# 1. 在新集群恢复Vault
kubectl apply -f vault/vault_ha.yaml

# 2. 从快照恢复数据
# 快照存储在S3: s3://acas-backup/vault/snapshots/
aws s3 cp s3://acas-backup/vault/snapshots/latest.snap /tmp/vault.snap

# 3. 恢复Raft数据
kubectl cp /tmp/vault.snap vault-0:/vault/data/raft/snapshots/
kubectl exec -it vault-0 -- vault operator raft snapshot restore /vault/data/raft/snapshots/vault.snap

# 4. 解封Vault
kubectl exec -it vault-0 -- vault operator unseal $UNSEAL_KEY_1
kubectl exec -it vault-0 -- vault operator unseal $UNSEAL_KEY_2
kubectl exec -it vault-0 -- vault operator unseal $UNSEAL_KEY_3
```

### 场景4: 密钥泄露
**症状**: 怀疑密钥被泄露
**影响**: 需要紧急轮换所有密钥
**RTO**: 1小时
**RPO**: N/A

```bash
# 1. 紧急轮换所有密钥
python vault/key_rotation.py --emergency-rotate-all

# 2. 吊销所有动态凭证
vault lease revoke -prefix database/creds/
vault lease revoke -prefix aws/creds/

# 3. 审计日志分析
vault audit-hash -audit-device-file-path=/var/log/vault/audit.log

# 4. 通知相关团队
# - 安全团队
# - 法务团队
# - 客户成功团队
```

---

## 备份策略

### 自动备份 (每小时)
```bash
# Raft快照
vault operator raft snapshot save /tmp/vault-$(date +%Y%m%d-%H%M%S).snap

# 上传到S3
aws s3 cp /tmp/vault-*.snap s3://acas-backup/vault/snapshots/

# 保留最近30个快照
aws s3 ls s3://acas-backup/vault/snapshots/ | sort | head -n -30 | xargs -I {} aws s3 rm s3://acas-backup/vault/snapshots/{}
```

### 手动备份 (变更前)
```bash
# 操作前手动快照
vault operator raft snapshot save /backup/pre-migration-$(date +%s).snap
```

---

## 恢复流程

### 准备
1. 确保有3个unseal key
2. 确保有root token
3. 确保有最新快照

### 步骤
```bash
# 1. 部署新Vault集群
kubectl apply -f vault/vault_ha.yaml

# 2. 等待pod就绪
kubectl wait --for=condition=ready pod -l app=vault --timeout=300s

# 3. 初始化 (如果是全新集群)
vault operator init -key-shares=5 -key-threshold=3
# 保存输出！

# 4. 解封
vault operator unseal <key1>
vault operator unseal <key2>
vault operator unseal <key3>

# 5. 验证
vault status
vault operator raft list-peers
```

---

## 关键联系人

| 角色 | 联系人 | 职责 |
|------|--------|------|
| 技术负责人 | [CTO] | 灾难恢复决策 |
| 安全负责人 | [CISO] | 密钥泄露处理 |
| 运维负责人 | [SRE Lead] | 集群恢复 |
| 法务负责人 | [Legal] | 合规通知 |

---

## 恢复验证清单

- [ ] Vault集群状态正常
- [ ] 所有节点已加入Raft
- [ ] 密钥可正常读取
- [ ] 动态凭证可正常生成
- [ ] 审计日志正常记录
- [ ] 应用服务正常启动
- [ ] 监控告警正常

---

## 演练计划

**频率**: 每季度一次  
**范围**: 场景3 (完全恢复)  
**参与**: SRE + 安全团队  
**记录**: 演练报告存档
