#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - GDPR Compliance Module
Data protection and privacy controls
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('acas.gdpr')


class DataSubjectRight(Enum):
    """数据主体权利"""
    ACCESS = "access"           # 访问权
    RECTIFICATION = "rectification"  # 更正权
    ERASURE = "erasure"         # 删除权 (被遗忘权)
    RESTRICT = "restrict"       # 限制处理权
    PORTABILITY = "portability" # 数据可携带权
    OBJECT = "object"           # 反对权


class ProcessingBasis(Enum):
    """处理合法性基础"""
    CONSENT = "consent"
    CONTRACT = "contract"
    LEGAL_OBLIGATION = "legal_obligation"
    VITAL_INTERESTS = "vital_interests"
    PUBLIC_TASK = "public_task"
    LEGITIMATE_INTERESTS = "legitimate_interests"


@dataclass
class ConsentRecord:
    """同意记录"""
    user_id: str
    purpose: str
    granted: bool
    granted_at: datetime
    expires_at: Optional[datetime]
    ip_address: str
    user_agent: str
    version: str
    withdrawn_at: Optional[datetime] = None


@dataclass
class DataProcessingRecord:
    """数据处理记录 (ROPA)"""
    activity_id: str
    activity_name: str
    purposes: List[str]
    data_categories: List[str]
    data_subjects: List[str]
    recipients: List[str]
    retention_period: str
    security_measures: List[str]
    legal_basis: ProcessingBasis
    created_at: datetime
    updated_at: datetime


class GDPRManager:
    """
    GDPR合规管理器
    
    Features:
    - 同意管理
    - 数据主体权利
    - 处理记录 (ROPA)
    - 数据泄露通知
    - DPIA支持
    """
    
    def __init__(self):
        self.consent_records: Dict[str, List[ConsentRecord]] = {}
        self.processing_records: Dict[str, DataProcessingRecord] = {}
        self.data_requests: Dict[str, Dict] = {}
        self.breach_reports: List[Dict] = []
    
    # ============== Consent Management ==============
    
    def record_consent(self, user_id: str, purpose: str, granted: bool,
                      ip_address: str, user_agent: str, 
                      version: str = "1.0",
                      validity_days: int = 365) -> ConsentRecord:
        """
        记录用户同意
        
        Args:
            user_id: 用户ID
            purpose: 处理目的
            granted: 是否同意
            ip_address: IP地址
            user_agent: 用户代理
            version: 同意条款版本
            validity_days: 有效期天数
        """
        now = datetime.now(timezone.utc)
        
        record = ConsentRecord(
            user_id=user_id,
            purpose=purpose,
            granted=granted,
            granted_at=now,
            expires_at=now + timedelta(days=validity_days) if granted else None,
            ip_address=ip_address,
            user_agent=user_agent,
            version=version
        )
        
        if user_id not in self.consent_records:
            self.consent_records[user_id] = []
        
        self.consent_records[user_id].append(record)
        
        logger.info(f"Consent recorded for user {user_id}, purpose: {purpose}")
        
        return record
    
    def withdraw_consent(self, user_id: str, purpose: str = None) -> bool:
        """撤回同意"""
        if user_id not in self.consent_records:
            return False
        
        now = datetime.now(timezone.utc)
        withdrawn = False
        
        for record in self.consent_records[user_id]:
            if purpose and record.purpose != purpose:
                continue
            
            if record.granted and not record.withdrawn_at:
                record.withdrawn_at = now
                withdrawn = True
        
        if withdrawn:
            logger.info(f"Consent withdrawn for user {user_id}")
        
        return withdrawn
    
    def check_consent(self, user_id: str, purpose: str) -> bool:
        """检查是否拥有有效同意"""
        if user_id not in self.consent_records:
            return False
        
        now = datetime.now(timezone.utc)
        
        for record in self.consent_records[user_id]:
            if record.purpose != purpose:
                continue
            
            if not record.granted:
                continue
            
            if record.withdrawn_at:
                continue
            
            if record.expires_at and now > record.expires_at:
                continue
            
            return True
        
        return False
    
    def get_consent_history(self, user_id: str) -> List[ConsentRecord]:
        """获取同意历史"""
        return self.consent_records.get(user_id, [])
    
    # ============== Data Subject Rights ==============
    
    def request_data_export(self, user_id: str, format: str = "json") -> Dict:
        """
        数据导出请求 (可携带权)
        
        Returns:
            包含所有用户数据的字典
        """
        request_id = f"export-{user_id}-{datetime.now(timezone.utc).timestamp()}"
        
        # 收集用户数据
        export_data = {
            'request_id': request_id,
            'user_id': user_id,
            'exported_at': datetime.now(timezone.utc).isoformat(),
            'format': format,
            'data': {
                'profile': {},  # 应由具体业务填充
                'activity': [],
                'consents': [],
                'communications': []
            }
        }
        
        # 添加同意记录
        if user_id in self.consent_records:
            for record in self.consent_records[user_id]:
                export_data['data']['consents'].append({
                    'purpose': record.purpose,
                    'granted': record.granted,
                    'granted_at': record.granted_at.isoformat(),
                    'withdrawn_at': record.withdrawn_at.isoformat() if record.withdrawn_at else None
                })
        
        self.data_requests[request_id] = {
            'type': 'export',
            'user_id': user_id,
            'status': 'completed',
            'created_at': datetime.now(timezone.utc),
            'completed_at': datetime.now(timezone.utc)
        }
        
        logger.info(f"Data export completed: {request_id}")
        
        return export_data
    
    def request_data_deletion(self, user_id: str) -> Dict:
        """
        数据删除请求 (被遗忘权)
        
        Returns:
            删除报告
        """
        request_id = f"delete-{user_id}-{datetime.now(timezone.utc).timestamp()}"
        
        deletion_report = {
            'request_id': request_id,
            'user_id': user_id,
            'requested_at': datetime.now(timezone.utc).isoformat(),
            'deleted_items': [],
            'retained_items': [],
            'retention_reasons': {}
        }
        
        # 撤回所有同意
        self.withdraw_consent(user_id)
        deletion_report['deleted_items'].append('consent_records')
        
        # 标记删除请求
        self.data_requests[request_id] = {
            'type': 'deletion',
            'user_id': user_id,
            'status': 'processing',
            'created_at': datetime.now(timezone.utc)
        }
        
        logger.info(f"Data deletion requested: {request_id}")
        
        return deletion_report
    
    def request_data_rectification(self, user_id: str, 
                                   corrections: Dict[str, Any]) -> Dict:
        """数据更正请求"""
        request_id = f"rectify-{user_id}-{datetime.now(timezone.utc).timestamp()}"
        
        # 实际更正应由业务层处理
        rectification_report = {
            'request_id': request_id,
            'user_id': user_id,
            'requested_at': datetime.now(timezone.utc).isoformat(),
            'corrections': corrections,
            'status': 'pending_review'
        }
        
        self.data_requests[request_id] = {
            'type': 'rectification',
            'user_id': user_id,
            'status': 'pending',
            'created_at': datetime.now(timezone.utc)
        }
        
        logger.info(f"Data rectification requested: {request_id}")
        
        return rectification_report
    
    # ============== Records of Processing (ROPA) ==============
    
    def register_processing_activity(self, activity_id: str, activity_name: str,
                                     purposes: List[str], data_categories: List[str],
                                     data_subjects: List[str], recipients: List[str],
                                     retention_period: str, 
                                     security_measures: List[str],
                                     legal_basis: ProcessingBasis) -> DataProcessingRecord:
        """注册处理活动"""
        now = datetime.now(timezone.utc)
        
        record = DataProcessingRecord(
            activity_id=activity_id,
            activity_name=activity_name,
            purposes=purposes,
            data_categories=data_categories,
            data_subjects=data_subjects,
            recipients=recipients,
            retention_period=retention_period,
            security_measures=security_measures,
            legal_basis=legal_basis,
            created_at=now,
            updated_at=now
        )
        
        self.processing_records[activity_id] = record
        
        logger.info(f"Processing activity registered: {activity_id}")
        
        return record
    
    def get_ropa(self) -> List[DataProcessingRecord]:
        """获取所有处理记录"""
        return list(self.processing_records.values())
    
    # ============== Breach Notification ==============
    
    def report_breach(self, breach_id: str, description: str,
                     affected_users: List[str], data_categories: List[str],
                     likelihood_of_harm: str, severity: str) -> Dict:
        """
        数据泄露报告
        
        GDPR要求72小时内通知监管机构
        """
        report = {
            'breach_id': breach_id,
            'reported_at': datetime.now(timezone.utc).isoformat(),
            'description': description,
            'affected_users_count': len(affected_users),
            'affected_data_categories': data_categories,
            'likelihood_of_harm': likelihood_of_harm,
            'severity': severity,
            'notification_required': severity in ['high', 'critical'],
            'notification_deadline': (datetime.now(timezone.utc) + timedelta(hours=72)).isoformat()
        }
        
        self.breach_reports.append(report)
        
        logger.critical(f"Data breach reported: {breach_id}")
        
        return report
    
    # ============== DPIA Support ==============
    
    def assess_dpia_required(self, activity: DataProcessingRecord) -> bool:
        """评估是否需要DPIA"""
        # 高风险处理需要DPIA
        high_risk_indicators = [
            'systematic_monitoring' in activity.purposes,
            'sensitive_data' in activity.data_categories,
            'large_scale' in activity.data_subjects,
            'vulnerable_subjects' in activity.data_subjects,
            'automated_decision_making' in activity.purposes
        ]
        
        return any(high_risk_indicators)
    
    def generate_privacy_notice(self) -> str:
        """生成隐私声明"""
        notice = """
# Privacy Notice

## Data Controller
ACAS Pro

## Purposes of Processing
"""
        for record in self.processing_records.values():
            notice += f"\n### {record.activity_name}\n"
            notice += f"- Purposes: {', '.join(record.purposes)}\n"
            notice += f"- Legal Basis: {record.legal_basis.value}\n"
            notice += f"- Data Categories: {', '.join(record.data_categories)}\n"
            notice += f"- Retention: {record.retention_period}\n"
        
        notice += """
## Your Rights
- Right to access your data
- Right to rectification
- Right to erasure (right to be forgotten)
- Right to restrict processing
- Right to data portability
- Right to object

## Contact
DPO: dpo@acas-pro.com
"""
        
        return notice


# 全局实例
_gdpr_manager: Optional[GDPRManager] = None

def get_gdpr_manager() -> GDPRManager:
    """获取GDPR管理器"""
    global _gdpr_manager
    if _gdpr_manager is None:
        _gdpr_manager = GDPRManager()
    return _gdpr_manager


if __name__ == '__main__':
    # 测试
    print("="*60)
    print("ACAS Pro - GDPR Manager Test")
    print("="*60)
    
    gdpr = GDPRManager()
    
    # 注册处理活动
    print("\n[1] Registering processing activities...")
    gdpr.register_processing_activity(
        activity_id="user-management",
        activity_name="User Account Management",
        purposes=["account_creation", "authentication"],
        data_categories=["personal_identifiers", "contact_info"],
        data_subjects=["users"],
        recipients=["internal"],
        retention_period="account_lifetime",
        security_measures=["encryption", "access_control"],
        legal_basis=ProcessingBasis.CONTRACT
    )
    print("    ✓ Activity registered")
    
    # 记录同意
    print("\n[2] Recording consent...")
    consent = gdpr.record_consent(
        user_id='user-123',
        purpose='marketing',
        granted=True,
        ip_address='192.168.1.1',
        user_agent='Mozilla/5.0'
    )
    print(f"    ✓ Consent recorded: {consent.purpose}")
    
    # 检查同意
    print("\n[3] Checking consent...")
    has_consent = gdpr.check_consent('user-123', 'marketing')
    print(f"    Has consent: {has_consent}")
    
    # 数据导出
    print("\n[4] Data export...")
    export = gdpr.request_data_export('user-123')
    print(f"    Export ID: {export['request_id']}")
    
    # 隐私声明
    print("\n[5] Privacy notice...")
    notice = gdpr.generate_privacy_notice()
    print(f"    Generated: {len(notice)} chars")
    
    print("\n" + "="*60)
    print("GDPR test completed")
