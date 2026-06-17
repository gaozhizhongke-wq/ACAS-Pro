#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Tamper-Proof Audit Logger
Enterprise-grade immutable audit trail
"""

import os
import json
import hashlib
import hmac
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('acas.audit')


class AuditEventType(Enum):
    """审计事件类型"""
    # 认证事件
    AUTH_LOGIN = "auth:login"
    AUTH_LOGOUT = "auth:logout"
    AUTH_FAILED = "auth:failed"
    AUTH_MFA = "auth:mfa"
    AUTH_TOKEN_REFRESH = "auth:token_refresh"
    
    # 用户管理
    USER_CREATE = "user:create"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_PASSWORD_CHANGE = "user:password_change"
    USER_ROLE_CHANGE = "user:role_change"
    
    # 数据访问
    DATA_READ = "data:read"
    DATA_CREATE = "data:create"
    DATA_UPDATE = "data:update"
    DATA_DELETE = "data:delete"
    DATA_EXPORT = "data:export"
    
    # 配置变更
    CONFIG_READ = "config:read"
    CONFIG_WRITE = "config:write"
    CONFIG_DELETE = "config:delete"
    
    # 系统管理
    SYSTEM_START = "system:start"
    SYSTEM_STOP = "system:stop"
    SYSTEM_BACKUP = "system:backup"
    SYSTEM_RESTORE = "system:restore"
    
    # 安全事件
    SECURITY_VIOLATION = "security:violation"
    SECURITY_ALERT = "security:alert"
    PERMISSION_DENIED = "security:permission_denied"


@dataclass
class AuditEvent:
    """审计事件"""
    event_id: str
    timestamp: datetime
    event_type: AuditEventType
    user_id: str
    user_email: str
    ip_address: str
    user_agent: str
    resource_type: str
    resource_id: str
    action: str
    status: str  # success, failed, denied
    details: Dict[str, Any]
    previous_hash: str
    current_hash: str


class ImmutableAuditLogger:
    """
    不可篡改审计日志器
    
    Features:
    - 哈希链防篡改
    - HMAC签名
    - 实时告警
    - 合规导出
    """
    
    def __init__(self, log_dir: str = "logs/audit"):
        self.log_dir = log_dir
        self.current_log_file = None
        self.last_hash = "0" * 64
        self.lock = threading.Lock()
        
        # HMAC密钥 (应从Vault获取)
        self.hmac_key = os.environ.get('AUDIT_HMAC_KEY', 'default-key-change-in-production')
        
        # 初始化日志目录
        os.makedirs(log_dir, exist_ok=True)
        
        # 加载最后一个哈希
        self._load_last_hash()
        
        # 告警回调
        self.alert_handlers: List[callable] = []
    
    def _load_last_hash(self):
        """加载最后一个事件的哈希"""
        log_files = sorted([f for f in os.listdir(self.log_dir) if f.endswith('.log')])
        
        if log_files:
            # 读取最后一个文件的最后一条记录
            last_file = os.path.join(self.log_dir, log_files[-1])
            try:
                with open(last_file, 'r') as f:
                    lines = f.readlines()
                    if lines:
                        last_event = json.loads(lines[-1])
                        self.last_hash = last_event.get('current_hash', self.last_hash)
            except Exception as e:
                logger.error(f"Failed to load last hash: {e}")
    
    def _get_current_log_file(self) -> str:
        """获取当前日志文件 (按小时轮转)"""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H")
        return os.path.join(self.log_dir, f"audit-{timestamp}.log")
    
    def _calculate_hash(self, event_data: Dict[str, Any]) -> str:
        """计算事件哈希"""
        # 包含前一个哈希，形成哈希链
        data_string = json.dumps(event_data, sort_keys=True) + self.last_hash
        return hashlib.sha256(data_string.encode()).hexdigest()
    
    def _calculate_hmac(self, event_data: Dict[str, Any]) -> str:
        """计算HMAC签名"""
        data_string = json.dumps(event_data, sort_keys=True)
        return hmac.new(
            self.hmac_key.encode(),
            data_string.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def _verify_integrity(self, event: Dict[str, Any]) -> bool:
        """验证单个事件的完整性"""
        stored_hash = event.get('current_hash')
        stored_hmac = event.get('hmac')
        
        # 重建事件数据 (排除hash和hmac字段)
        event_data = {k: v for k, v in event.items() if k not in ['current_hash', 'hmac']}
        
        # 验证哈希
        calculated_hash = self._calculate_hash(event_data)
        if calculated_hash != stored_hash:
            return False
        
        # 验证HMAC
        calculated_hmac = self._calculate_hmac(event_data)
        return hmac.compare_digest(calculated_hmac, stored_hmac)
    
    def log(self, event_type: AuditEventType, user_id: str, user_email: str,
            ip_address: str, user_agent: str, resource_type: str, resource_id: str,
            action: str, status: str, details: Dict[str, Any] = None) -> AuditEvent:
        """
        记录审计事件
        
        Args:
            event_type: 事件类型
            user_id: 用户ID
            user_email: 用户邮箱
            ip_address: IP地址
            user_agent: 用户代理
            resource_type: 资源类型
            resource_id: 资源ID
            action: 操作
            status: 状态 (success/failed/denied)
            details: 详细信息
        """
        with self.lock:
            event_id = f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}-{user_id[:8]}"
            
            # 构建事件数据
            event_data = {
                'event_id': event_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'event_type': event_type.value,
                'user_id': user_id,
                'user_email': user_email,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'resource_type': resource_type,
                'resource_id': resource_id,
                'action': action,
                'status': status,
                'details': details or {},
                'previous_hash': self.last_hash
            }
            
            # 计算当前哈希
            current_hash = self._calculate_hash(event_data)
            event_data['current_hash'] = current_hash
            
            # 计算HMAC
            event_data['hmac'] = self._calculate_hmac(event_data)
            
            # 写入日志文件
            log_file = self._get_current_log_file()
            with open(log_file, 'a') as f:
                f.write(json.dumps(event_data) + '\n')
            
            # 更新最后一个哈希
            self.last_hash = current_hash
            
            # 创建事件对象
            event = AuditEvent(
                event_id=event_id,
                timestamp=datetime.now(timezone.utc),
                event_type=event_type,
                user_id=user_id,
                user_email=user_email,
                ip_address=ip_address,
                user_agent=user_agent,
                resource_type=resource_type,
                resource_id=resource_id,
                action=action,
                status=status,
                details=details or {},
                previous_hash=event_data['previous_hash'],
                current_hash=current_hash
            )
            
            # 检查是否需要告警
            self._check_alerts(event)
            
            return event
    
    def _check_alerts(self, event: AuditEvent):
        """检查是否需要触发告警"""
        alert_conditions = [
            # 多次登录失败
            (event.event_type == AuditEventType.AUTH_FAILED and self._count_recent_failures(event.user_id) >= 5),
            # 权限被拒绝
            (event.event_type == AuditEventType.PERMISSION_DENIED),
            # 安全配置变更
            (event.event_type in [AuditEventType.CONFIG_WRITE, AuditEventType.CONFIG_DELETE] and 
             'security' in event.resource_type.lower()),
            # 数据导出
            (event.event_type == AuditEventType.DATA_EXPORT and event.details.get('record_count', 0) > 1000),
        ]
        
        if any(alert_conditions):
            self._trigger_alert(event)
    
    def _count_recent_failures(self, user_id: str, minutes: int = 5) -> int:
        """统计最近登录失败次数"""
        # 简化实现，实际应该查询日志
        return 0
    
    def _trigger_alert(self, event: AuditEvent):
        """触发告警"""
        alert = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'severity': 'high' if event.event_type == AuditEventType.SECURITY_VIOLATION else 'medium',
            'event_id': event.event_id,
            'event_type': event.event_type.value,
            'user_id': event.user_id,
            'description': f"Security alert: {event.event_type.value} by {event.user_email}"
        }
        
        # 写入告警日志
        with open(os.path.join(self.log_dir, 'alerts.log'), 'a') as f:
            f.write(json.dumps(alert) + '\n')
        
        # 调用告警处理器
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Alert handler failed: {e}")
    
    def verify_log_integrity(self, log_file: str = None) -> Dict[str, Any]:
        """
        验证日志完整性
        
        Returns:
            验证结果
        """
        if log_file is None:
            log_file = self._get_current_log_file()
        
        if not os.path.exists(log_file):
            return {'valid': True, 'message': 'Log file not found', 'tampered_events': []}
        
        tampered_events = []
        previous_hash = "0" * 64
        
        with open(log_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    event = json.loads(line)
                    
                    # 验证哈希链
                    if event.get('previous_hash') != previous_hash:
                        tampered_events.append({
                            'line': line_num,
                            'event_id': event.get('event_id'),
                            'issue': 'hash_chain_broken',
                            'expected_previous': previous_hash,
                            'actual_previous': event.get('previous_hash')
                        })
                        continue
                    
                    # 验证事件完整性
                    if not self._verify_integrity(event):
                        tampered_events.append({
                            'line': line_num,
                            'event_id': event.get('event_id'),
                            'issue': 'integrity_check_failed'
                        })
                        continue
                    
                    previous_hash = event.get('current_hash')
                    
                except json.JSONDecodeError:
                    tampered_events.append({
                        'line': line_num,
                        'issue': 'invalid_json'
                    })
        
        return {
            'valid': len(tampered_events) == 0,
            'total_events': line_num if 'line_num' in locals() else 0,
            'tampered_events': tampered_events,
            'message': 'Log integrity verified' if len(tampered_events) == 0 else f"{len(tampered_events)} events tampered"
        }
    
    def query_events(self, start_time: datetime = None, end_time: datetime = None,
                    event_types: List[AuditEventType] = None, user_id: str = None,
                    resource_type: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """查询审计事件"""
        events = []
        
        # 获取所有日志文件
        log_files = sorted([f for f in os.listdir(self.log_dir) if f.startswith('audit-') and f.endswith('.log')])
        
        for log_file in log_files:
            file_path = os.path.join(self.log_dir, log_file)
            
            with open(file_path, 'r') as f:
                for line in f:
                    try:
                        event = json.loads(line)
                        
                        # 时间过滤
                        event_time = datetime.fromisoformat(event['timestamp'])
                        if start_time and event_time < start_time:
                            continue
                        if end_time and event_time > end_time:
                            continue
                        
                        # 事件类型过滤
                        if event_types and event['event_type'] not in [et.value for et in event_types]:
                            continue
                        
                        # 用户过滤
                        if user_id and event['user_id'] != user_id:
                            continue
                        
                        # 资源类型过滤
                        if resource_type and event['resource_type'] != resource_type:
                            continue
                        
                        events.append(event)
                        
                        if len(events) >= limit:
                            return events
                            
                    except (json.JSONDecodeError, KeyError):
                        continue
        
        return events
    
    def export_for_compliance(self, output_file: str, start_date: datetime, end_date: datetime):
        """导出合规报告"""
        events = self.query_events(start_time=start_date, end_time=end_date, limit=100000)
        
        # 生成完整性证明
        integrity_report = self.verify_log_integrity()
        
        report = {
            'export_metadata': {
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'date_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'total_events': len(events),
                'integrity_status': integrity_report
            },
            'events': events
        }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Compliance export completed: {output_file}")


# 全局实例
_audit_logger: Optional[ImmutableAuditLogger] = None

def get_audit_logger() -> ImmutableAuditLogger:
    """获取审计日志器"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = ImmutableAuditLogger()
    return _audit_logger


if __name__ == '__main__':
    # 测试
    print("="*60)
    print("ACAS Pro - Immutable Audit Logger Test")
    print("="*60)
    
    logger = ImmutableAuditLogger()
    
    # 记录测试事件
    logger.log(
        event_type=AuditEventType.AUTH_LOGIN,
        user_id='user-123',
        user_email='admin@acas.pro',
        ip_address='192.168.1.1',
        user_agent='Mozilla/5.0',
        resource_type='system',
        resource_id='login',
        action='login',
        status='success',
        details={'mfa_used': True}
    )
    
    logger.log(
        event_type=AuditEventType.USER_CREATE,
        user_id='user-123',
        user_email='admin@acas.pro',
        ip_address='192.168.1.1',
        user_agent='Mozilla/5.0',
        resource_type='user',
        resource_id='user-456',
        action='create',
        status='success',
        details={'role': 'operator'}
    )
    
    # 验证完整性
    print("\nVerifying log integrity...")
    result = logger.verify_log_integrity()
    print(f"  Valid: {result['valid']}")
    print(f"  Total events: {result['total_events']}")
    print(f"  Message: {result['message']}")
    
    # 查询事件
    print("\nQuerying events...")
    events = logger.query_events(limit=10)
    print(f"  Found {len(events)} events")
    
    print("\n" + "="*60)
    print("Audit logger test completed")
