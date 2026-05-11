#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - SOC 2 Compliance Module
Trust Services Criteria controls
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('acas.soc2')


class TrustServiceCriteria(Enum):
    """SOC 2 Trust Services Criteria"""
    SECURITY = "CC6.1"  # 安全性
    AVAILABILITY = "A1.2"  # 可用性
    PROCESSING_INTEGRITY = "PI1.3"  # 处理完整性
    CONFIDENTIALITY = "C1.1"  # 保密性
    PRIVACY = "P1.1"  # 隐私


class ControlStatus(Enum):
    """控制状态"""
    IMPLEMENTED = "implemented"
    PARTIALLY_IMPLEMENTED = "partially_implemented"
    NOT_IMPLEMENTED = "not_implemented"
    NOT_APPLICABLE = "not_applicable"


@dataclass
class Control:
    """控制措施"""
    control_id: str
    criteria: TrustServiceCriteria
    description: str
    implementation: str
    evidence: List[str]
    status: ControlStatus
    tested_by: str
    tested_at: datetime
    findings: str
    remediation: Optional[str]


@dataclass
class AuditEvidence:
    """审计证据"""
    evidence_id: str
    control_id: str
    evidence_type: str
    description: str
    file_path: str
    collected_by: str
    collected_at: datetime
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime]


class SOC2Manager:
    """
    SOC 2合规管理器
    
    Features:
    - 控制措施管理
    - 审计证据收集
    - 例外跟踪
    - 报告生成
    """
    
    def __init__(self):
        self.controls: Dict[str, Control] = {}
        self.evidence: Dict[str, AuditEvidence] = {}
        self.exceptions: List[Dict] = []
        self.audit_logs: List[Dict] = []
        
        # 初始化标准控制
        self._init_standard_controls()
    
    def _init_standard_controls(self):
        """初始化SOC 2标准控制"""
        standard_controls = [
            # Security
            Control(
                control_id="CC6.1-001",
                criteria=TrustServiceCriteria.SECURITY,
                description="Logical access security",
                implementation="RBAC with MFA",
                evidence=["rbac_config", "mfa_logs"],
                status=ControlStatus.IMPLEMENTED,
                tested_by="Internal Audit",
                tested_at=datetime.now(timezone.utc),
                findings="No exceptions noted",
                remediation=None
            ),
            Control(
                control_id="CC6.2-001",
                criteria=TrustServiceCriteria.SECURITY,
                description="Encryption at rest and in transit",
                implementation="TLS 1.3, AES-256",
                evidence=["ssl_config", "encryption_audit"],
                status=ControlStatus.IMPLEMENTED,
                tested_by="Internal Audit",
                tested_at=datetime.now(timezone.utc),
                findings="No exceptions noted",
                remediation=None
            ),
            Control(
                control_id="CC6.3-001",
                criteria=TrustServiceCriteria.SECURITY,
                description="Access removal upon termination",
                implementation="Automated offboarding workflow",
                evidence=["offboarding_logs"],
                status=ControlStatus.IMPLEMENTED,
                tested_by="Internal Audit",
                tested_at=datetime.now(timezone.utc),
                findings="No exceptions noted",
                remediation=None
            ),
            Control(
                control_id="CC6.6-001",
                criteria=TrustServiceCriteria.SECURITY,
                description="Encryption key management",
                implementation="HashiCorp Vault",
                evidence=["vault_audit_logs", "key_rotation_records"],
                status=ControlStatus.IMPLEMENTED,
                tested_by="Internal Audit",
                tested_at=datetime.now(timezone.utc),
                findings="No exceptions noted",
                remediation=None
            ),
            
            # Availability
            Control(
                control_id="A1.2-001",
                criteria=TrustServiceCriteria.AVAILABILITY,
                description="System monitoring",
                implementation="Prometheus + Grafana",
                evidence=["monitoring_dashboards", "alert_logs"],
                status=ControlStatus.IMPLEMENTED,
                tested_by="Internal Audit",
                tested_at=datetime.now(timezone.utc),
                findings="No exceptions noted",
                remediation=None
            ),
            Control(
                control_id="A1.2-002",
                criteria=TrustServiceCriteria.AVAILABILITY,
                description="Backup and recovery",
                implementation="Daily backups, 4hr RTO",
                evidence=["backup_logs", "dr_test_results"],
                status=ControlStatus.IMPLEMENTED,
                tested_by="Internal Audit",
                tested_at=datetime.now(timezone.utc),
                findings="No exceptions noted",
                remediation=None
            ),
            
            # Confidentiality
            Control(
                control_id="C1.1-001",
                criteria=TrustServiceCriteria.CONFIDENTIALITY,
                description="Data classification",
                implementation="3-tier classification system",
                evidence=["data_classification_policy"],
                status=ControlStatus.IMPLEMENTED,
                tested_by="Internal Audit",
                tested_at=datetime.now(timezone.utc),
                findings="No exceptions noted",
                remediation=None
            ),
            Control(
                control_id="C1.2-001",
                criteria=TrustServiceCriteria.CONFIDENTIALITY,
                description="NDA agreements",
                implementation="Signed NDAs for all employees",
                evidence=["nda_records"],
                status=ControlStatus.IMPLEMENTED,
                tested_by="Internal Audit",
                tested_at=datetime.now(timezone.utc),
                findings="No exceptions noted",
                remediation=None
            ),
        ]
        
        for control in standard_controls:
            self.controls[control.control_id] = control
    
    def add_control(self, control: Control):
        """添加控制措施"""
        self.controls[control.control_id] = control
        logger.info(f"Control added: {control.control_id}")
    
    def update_control_status(self, control_id: str, 
                             status: ControlStatus,
                             findings: str = None,
                             remediation: str = None):
        """更新控制状态"""
        if control_id not in self.controls:
            raise ValueError(f"Control not found: {control_id}")
        
        control = self.controls[control_id]
        control.status = status
        
        if findings:
            control.findings = findings
        if remediation:
            control.remediation = remediation
        
        control.tested_at = datetime.now(timezone.utc)
        
        logger.info(f"Control {control_id} status updated to {status.value}")
    
    def add_evidence(self, evidence: AuditEvidence):
        """添加审计证据"""
        self.evidence[evidence.evidence_id] = evidence
        
        # 关联到控制
        if evidence.control_id in self.controls:
            control = self.controls[evidence.control_id]
            if evidence.evidence_id not in control.evidence:
                control.evidence.append(evidence.evidence_id)
        
        logger.info(f"Evidence added: {evidence.evidence_id}")
    
    def record_exception(self, control_id: str, description: str,
                        severity: str, remediation_plan: str,
                        target_date: datetime):
        """记录控制例外"""
        exception = {
            'exception_id': f"EXC-{len(self.exceptions)+1:04d}",
            'control_id': control_id,
            'description': description,
            'severity': severity,
            'remediation_plan': remediation_plan,
            'target_date': target_date.isoformat(),
            'recorded_at': datetime.now(timezone.utc).isoformat(),
            'status': 'open'
        }
        
        self.exceptions.append(exception)
        
        logger.warning(f"Exception recorded: {exception['exception_id']}")
        
        return exception
    
    def generate_control_matrix(self) -> Dict:
        """生成控制矩阵"""
        matrix = {
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'summary': {
                'total_controls': len(self.controls),
                'by_criteria': {},
                'by_status': {}
            },
            'controls': []
        }
        
        # 按标准分组
        for criteria in TrustServiceCriteria:
            criteria_controls = [
                c for c in self.controls.values() 
                if c.criteria == criteria
            ]
            matrix['summary']['by_criteria'][criteria.value] = len(criteria_controls)
        
        # 按状态分组
        for status in ControlStatus:
            status_controls = [
                c for c in self.controls.values()
                if c.status == status
            ]
            matrix['summary']['by_status'][status.value] = len(status_controls)
        
        # 控制详情
        for control in self.controls.values():
            matrix['controls'].append({
                'control_id': control.control_id,
                'criteria': control.criteria.value,
                'description': control.description,
                'status': control.status.value,
                'tested_at': control.tested_at.isoformat(),
                'findings': control.findings
            })
        
        return matrix
    
    def generate_readiness_report(self) -> Dict:
        """生成SOC 2准备度报告"""
        total = len(self.controls)
        implemented = len([c for c in self.controls.values() 
                          if c.status == ControlStatus.IMPLEMENTED])
        partial = len([c for c in self.controls.values()
                      if c.status == ControlStatus.PARTIALLY_IMPLEMENTED])
        not_impl = len([c for c in self.controls.values()
                       if c.status == ControlStatus.NOT_IMPLEMENTED])
        
        readiness_score = (implemented + partial * 0.5) / total if total > 0 else 0
        
        report = {
            'report_date': datetime.now(timezone.utc).isoformat(),
            'readiness_score': f"{readiness_score:.1%}",
            'summary': {
                'total_controls': total,
                'implemented': implemented,
                'partially_implemented': partial,
                'not_implemented': not_impl,
                'not_applicable': len([c for c in self.controls.values()
                                      if c.status == ControlStatus.NOT_APPLICABLE])
            },
            'open_exceptions': len([e for e in self.exceptions if e['status'] == 'open']),
            'recommendations': []
        }
        
        # 生成建议
        if not_impl > 0:
            report['recommendations'].append(
                f"Prioritize implementation of {not_impl} missing controls"
            )
        
        if partial > 0:
            report['recommendations'].append(
                f"Complete implementation of {partial} partially implemented controls"
            )
        
        open_exceptions = [e for e in self.exceptions if e['status'] == 'open']
        if open_exceptions:
            report['recommendations'].append(
                f"Address {len(open_exceptions)} open control exceptions"
            )
        
        return report
    
    def generate_audit_report(self, start_date: datetime, 
                             end_date: datetime) -> Dict:
        """生成审计报告"""
        report = {
            'audit_period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'scope': 'SOC 2 Type II',
            'trust_services_criteria': [c.value for c in TrustServiceCriteria],
            'executive_summary': {
                'total_controls_tested': len(self.controls),
                'controls_passed': len([c for c in self.controls.values()
                                       if c.status == ControlStatus.IMPLEMENTED]),
                'controls_failed': len([c for c in self.controls.values()
                                       if c.status == ControlStatus.NOT_IMPLEMENTED]),
                'exceptions_noted': len(self.exceptions)
            },
            'control_testing_results': [],
            'exceptions': self.exceptions,
            'management_response': ''
        }
        
        for control in self.controls.values():
            report['control_testing_results'].append({
                'control_id': control.control_id,
                'criteria': control.criteria.value,
                'description': control.description,
                'tested_by': control.tested_by,
                'tested_at': control.tested_at.isoformat(),
                'result': control.status.value,
                'findings': control.findings
            })
        
        return report


# 全局实例
_soc2_manager: Optional[SOC2Manager] = None

def get_soc2_manager() -> SOC2Manager:
    """获取SOC2管理器"""
    global _soc2_manager
    if _soc2_manager is None:
        _soc2_manager = SOC2Manager()
    return _soc2_manager


if __name__ == '__main__':
    # 测试
    print("="*60)
    print("ACAS Pro - SOC 2 Manager Test")
    print("="*60)
    
    soc2 = SOC2Manager()
    
    # 控制矩阵
    print("\n[1] Control matrix...")
    matrix = soc2.generate_control_matrix()
    print(f"    Total controls: {matrix['summary']['total_controls']}")
    print(f"    By criteria: {matrix['summary']['by_criteria']}")
    
    # 准备度报告
    print("\n[2] Readiness report...")
    readiness = soc2.generate_readiness_report()
    print(f"    Readiness score: {readiness['readiness_score']}")
    print(f"    Implemented: {readiness['summary']['implemented']}")
    
    # 添加例外
    print("\n[3] Recording exception...")
    exc = soc2.record_exception(
        control_id="CC6.1-001",
        description="Temporary access granted for emergency",
        severity="medium",
        remediation_plan="Revoke access and document justification",
        target_date=datetime.now(timezone.utc) + timedelta(days=7)
    )
    print(f"    Exception ID: {exc['exception_id']}")
    
    # 审计报告
    print("\n[4] Audit report...")
    audit = soc2.generate_audit_report(
        start_date=datetime.now(timezone.utc) - timedelta(days=90),
        end_date=datetime.now(timezone.utc)
    )
    print(f"    Controls tested: {audit['executive_summary']['total_controls_tested']}")
    print(f"    Controls passed: {audit['executive_summary']['controls_passed']}")
    
    print("\n" + "="*60)
    print("SOC 2 test completed")
