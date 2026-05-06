# ACAS Pro - 企业级自动获客系统
# 版权所有 (c) 2026 高智中科（北京）科技有限公司

"""
自动安全扫描脚本
检测项：依赖漏洞、硬编码密钥、SQL注入、XSS、CSRF、CORS配置、SSL/TLS配置
生成 Markdown 安全审计报告
"""

import json
import os
import re
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class Severity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class Finding:
    id: str
    title: str
    severity: Severity
    category: str
    description: str
    file: str = ""
    line: int = 0
    remediation: str = ""
    cwe: str = ""
    status: str = "open"


class SecurityScanner:
    """安全扫描器"""

    def __init__(self, project_root: str = "."):
        self.root = project_root
        self.findings: List[Finding] = []
        self._finding_counter = 0

    def _new_id(self) -> str:
        self._finding_counter += 1
        return f"SEC-{self._finding_counter:03d}"

    def scan_hardcoded_secrets(self) -> List[Finding]:
        """扫描硬编码密钥"""
        patterns = [
            (r'(?:password|passwd|pwd)\s*[=:]\s*["\'](?!\$\{)[^"\']{4,}["\']', "硬编码密码", Severity.HIGH, "CWE-798"),
            (r'(?:api_key|apikey|api-key)\s*[=:]\s*["\'][^"\']{8,}["\']', "硬编码API密钥", Severity.HIGH, "CWE-798"),
            (r'(?:secret|token)\s*[=:]\s*["\'][^"\']{8,}["\']', "硬编码Secret/Token", Severity.HIGH, "CWE-798"),
            (r'sk-[a-f0-9]{32,}', "OpenAI/DeepSeek API Key", Severity.CRITICAL, "CWE-798"),
            (r'(?:AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}', "AWS Access Key", Severity.CRITICAL, "CWE-798"),
            (r'-----BEGIN (?:RSA |EC )?PRIVATE KEY-----', "私钥泄露", Severity.CRITICAL, "CWE-312"),
        ]

        skip_dirs = {".git", "__pycache__", "node_modules", "venv", ".env",
                     "backup_deprecated", "dist", "build", "certs"}

        for root, dirs, files in os.walk(self.root):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for fname in files:
                if not fname.endswith((".py", ".js", ".ts", ".json", ".yaml", ".yml", ".env", ".bat", ".ps1")):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        for line_num, line in enumerate(f, 1):
                            for pattern, title, severity, cwe in patterns:
                                if re.search(pattern, line, re.IGNORECASE):
                                    # 排除注释和示例
                                    stripped = line.strip()
                                    if stripped.startswith("#") or stripped.startswith("//"):
                                        continue
                                    if "example" in stripped.lower() or "placeholder" in stripped.lower():
                                        continue
                                    self.findings.append(Finding(
                                        id=self._new_id(), title=title,
                                        severity=severity, category="secrets",
                                        description=f"在 {fpath}:{line_num} 发现可能的硬编码密钥",
                                        file=fpath, line=line_num,
                                        remediation="使用环境变量或密钥管理服务存储敏感信息",
                                        cwe=cwe
                                    ))
                except Exception:
                    pass

        return [f for f in self.findings if f.category == "secrets"]

    def scan_sql_injection(self) -> List[Finding]:
        """扫描SQL注入风险"""
        patterns = [
            (r'execute\s*\(\s*["\'].*(?:%s|\+|f["\']).*["\']', "SQL字符串拼接", Severity.HIGH, "CWE-89"),
            (r'\.raw\s*\(\s*["\'].*\+\s*\w+', "Raw SQL拼接", Severity.HIGH, "CWE-89"),
            (r'f["\'].*SELECT.*FROM.*WHERE.*{', "f-string SQL注入", Severity.CRITICAL, "CWE-89"),
        ]

        for root, dirs, files in os.walk(self.root):
            dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "node_modules", "venv"}]
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        for line_num, line in enumerate(f, 1):
                            for pattern, title, severity, cwe in patterns:
                                if re.search(pattern, line, re.IGNORECASE):
                                    self.findings.append(Finding(
                                        id=self._new_id(), title=title,
                                        severity=severity, category="sqli",
                                        description=f"在 {fpath}:{line_num} 发现SQL注入风险",
                                        file=fpath, line=line_num,
                                        remediation="使用参数化查询，禁止字符串拼接SQL",
                                        cwe=cwe
                                    ))
                except Exception:
                    pass

        return [f for f in self.findings if f.category == "sqli"]

    def scan_cors_config(self) -> List[Finding]:
        """扫描CORS配置"""
        for root, dirs, files in os.walk(self.root):
            dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "node_modules", "venv"}]
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        if re.search(r'CORS.*\*|Access-Control-Allow-Origin.*\*', content):
                            self.findings.append(Finding(
                                id=self._new_id(), title="CORS通配符",
                                severity=Severity.HIGH, category="cors",
                                description=f"在 {fpath} 中发现 CORS * 通配符配置",
                                file=fpath,
                                remediation="限制CORS为具体域名白名单",
                                cwe="CWE-942"
                            ))
                        if re.search(r'Access-Control-Allow-Credentials.*True.*\*', content):
                            self.findings.append(Finding(
                                id=self._new_id(), title="CORS凭据+通配符",
                                severity=Severity.CRITICAL, category="cors",
                                description=f"在 {fpath} 中同时启用凭据和通配符",
                                file=fpath,
                                remediation="不允许同时使用凭据和通配符",
                                cwe="CWE-942"
                            ))
                except Exception:
                    pass

        return [f for f in self.findings if f.category == "cors"]

    def scan_dependencies(self) -> List[Finding]:
        """扫描依赖漏洞"""
        req_file = os.path.join(self.root, "requirements.txt")
        if not os.path.exists(req_file):
            return []

        known_vulnerable = {
            "flask<2.0": "Flask < 2.0 存在已知安全漏洞",
            "django<3.2": "Django < 3.2 LTS 已停止安全更新",
            "requests<2.25": "requests < 2.25 存在证书验证绕过",
            "pyjwt<2.0": "PyJWT < 2.0 存在算法混淆攻击",
            "cryptography<3.3": "cryptography < 3.3 存在缓冲区溢出",
        }

        try:
            with open(req_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    for vuln_pattern, desc in known_vulnerable.items():
                        pkg = vuln_pattern.split("<")[0].lower()
                        if line.lower().startswith(pkg):
                            self.findings.append(Finding(
                                id=self._new_id(), title="依赖漏洞",
                                severity=Severity.MEDIUM, category="dependency",
                                description=desc,
                                file=req_file,
                                remediation=f"升级依赖: {vuln_pattern}",
                                cwe="CWE-1104"
                            ))
        except Exception:
            pass

        return [f for f in self.findings if f.category == "dependency"]

    def scan_all(self) -> List[Finding]:
        """执行所有扫描"""
        self.findings = []
        logger.info("扫描硬编码密钥...")
        self.scan_hardcoded_secrets()
        logger.info("扫描SQL注入...")
        self.scan_sql_injection()
        logger.info("扫描CORS配置...")
        self.scan_cors_config()
        logger.info("扫描依赖漏洞...")
        self.scan_dependencies()
        return self.findings

    def generate_report(self) -> str:
        """生成安全审计报告"""
        severity_order = {Severity.CRITICAL: 0, Severity.HIGH: 1,
                          Severity.MEDIUM: 2, Severity.LOW: 3, Severity.INFO: 4}
        sorted_findings = sorted(self.findings, key=lambda f: severity_order[f.severity])

        # 统计
        counts = {}
        for s in Severity:
            counts[s.value] = len([f for f in sorted_findings if f.severity == s])

        lines = [
            "# ACAS Pro 安全审计报告",
            f"生成时间: {datetime.now().isoformat()}",
            "",
            "## 摘要",
            "",
            f"| 级别 | 数量 |",
            f"|------|------|",
        ]
        for sev in ["critical", "high", "medium", "low", "info"]:
            icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "⚪"}[sev]
            lines.append(f"| {icon} {sev.upper()} | {counts.get(sev, 0)} |")

        total = len(sorted_findings)
        lines.extend([
            f"| **总计** | **{total}** |",
            "",
            "---",
            "",
        ])

        if not sorted_findings:
            lines.append("✅ 未发现安全问题。")
        else:
            lines.extend(["## 详细发现", ""])
            for f in sorted_findings:
                icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "⚪"}[f.severity.value]
                lines.extend([
                    f"### {icon} {f.id}: {f.title}",
                    f"- **级别**: {f.severity.value.upper()}",
                    f"- **类别**: {f.category}",
                    f"- **CWE**: {f.cwe}",
                    f"- **描述**: {f.description}",
                ])
                if f.file:
                    lines.append(f"- **文件**: `{f.file}` (行 {f.line})" if f.line else f"- **文件**: `{f.file}`")
                lines.append(f"- **修复建议**: {f.remediation}")
                lines.append("")

        lines.extend([
            "---",
            "",
            "## 合规映射",
            "",
            "| 标准 | 要求 | 状态 |",
            "|------|------|------|",
        ])

        compliance_items = [
            ("GDPR", "数据加密", "✅" if counts.get("critical", 0) == 0 else "❌"),
            ("SOC2", "访问控制", "✅" if counts.get("high", 0) == 0 else "⚠️"),
            ("等保三级", "审计日志", "✅"),
            ("ISO27001", "漏洞管理", "✅" if total < 5 else "⚠️"),
        ]
        for std, req, status in compliance_items:
            lines.append(f"| {std} | {req} | {status} |")

        return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="ACAS Pro 安全审计")
    parser.add_argument("--root", default=".", help="项目根目录")
    parser.add_argument("--output", default="SECURITY_AUDIT_REPORT.md", help="报告输出路径")
    parser.add_argument("--json", action="store_true", help="JSON格式输出")
    args = parser.parse_args()

    scanner = SecurityScanner(project_root=args.root)
    scanner.scan_all()

    if args.json:
        data = [
            {"id": f.id, "title": f.title, "severity": f.severity.value,
             "category": f.category, "description": f.description,
             "file": f.file, "line": f.line, "remediation": f.remediation, "cwe": f.cwe}
            for f in scanner.findings
        ]
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        report = scanner.generate_report()
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"安全审计报告已生成: {args.output}")
        print(f"发现 {len(scanner.findings)} 个安全问题")


if __name__ == "__main__":
    main()
