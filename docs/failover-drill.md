# ACAS Pro - 灾备演练手册

## 演练类型

| 类型 | 频率 | 时长 | RTO 目标 |
|------|------|------|----------|
| 桌面演练 | 每季度 | 2小时 | - |
| 切换演练 | 每半年 | 4小时 | 5分钟 |
| 混沌演练 | 每月 | 8小时 | 5分钟 |
| 全链路演练 | 每年 | 2天 | 5分钟 |

---

## 演练场景

### 场景1: 主库故障

```bash
# 1. 模拟主库故障
kubectl exec -it postgres-primary-0 -- pkill -9 postgres

# 2. 观察自动切换
kubectl logs -f failover-controller-xxx

# 3. 验证备库提升
kubectl exec -it postgres-replica-0 -- psql -c "SELECT pg_is_in_recovery();"
# 应返回 f (false，表示不再是备库)

# 4. 验证应用可用
curl https://api.acas-pro.com/health

# 5. 恢复主库
kubectl delete pod postgres-primary-0
# 数据会自动从新的主库同步
```

### 场景2: 区域级故障

```bash
# 1. 模拟整个区域不可用
# 在网络层隔离主区域

# 2. 触发全局流量切换
# 更新 DNS/GLB

# 3. 启动备区域全量服务
kubectl apply -f dr/secondary-region-full.yaml

# 4. 验证业务连续性
./scripts/verify-business-continuity.sh

# 5. 故障恢复后切回
./scripts/switch-back-to-primary.sh
```

### 场景3: 数据损坏

```bash
# 1. 模拟数据损坏
kubectl exec -it postgres-primary-0 -- psql -c "
UPDATE users SET email = 'corrupted' WHERE id < 100;
"

# 2. 发现数据异常
# 通过一致性检查任务发现

# 3. 时间点恢复 (PITR)
# 恢复到损坏前5分钟
pg_restore --target-time "2026-05-02 14:55:00" ...

# 4. 验证数据完整性
./scripts/verify-data-integrity.sh
```

---

## 演练检查清单

### 演练前

- [ ] 通知相关团队
- [ ] 确认演练时间窗口
- [ ] 备份当前状态
- [ ] 准备回滚方案
- [ ] 检查监控告警

### 演练中

- [ ] 记录每个步骤时间
- [ ] 监控错误率/延迟
- [ ] 验证数据一致性
- [ ] 确认通知渠道畅通

### 演练后

- [ ] 生成演练报告
- [ ] 更新 Runbook
- [ ] 修复发现的问题
- [ ] 安排复盘会议

---

## 演练报告模板

```markdown
# 灾备演练报告 - YYYY-MM-DD

## 基本信息
- 演练类型: [切换演练/混沌演练/全链路演练]
- 演练时长: X小时X分钟
- 参与人员: [名单]

## 演练场景
[描述模拟的故障场景]

## 执行结果

| 指标 | 目标 | 实际 | 状态 |
|------|------|------|------|
| RTO | 5分钟 | X分钟 | ✓/✗ |
| RPO | 1分钟 | X分钟 | ✓/✗ |
| 数据一致性 | 100% | X% | ✓/✗ |

## 问题记录
1. [问题描述] - [严重程度] - [处理状态]

## 改进措施
1. [改进项] - [负责人] - [完成时间]

## 附件
- 监控截图
- 日志文件
- 时间线记录
```
