#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
证书管理模块 - 支持 Let's Encrypt 自动证书申请与续期

版权所有 (C) 2024-2026 高智中科（北京）科技有限公司
All Rights Reserved.
"""

import os
import subprocess
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class CertificateManager:
    """证书管理器 - 自动化 SSL/TLS 证书生命周期管理"""
    
    def __init__(self, domain: str, email: str, cert_dir: str = "certs"):
        self.domain = domain
        self.email = email
        self.cert_dir = Path(cert_dir)
        self.cert_dir.mkdir(exist_ok=True)
        
        self.cert_path = self.cert_dir / f"{domain}.crt"
        self.key_path = self.cert_dir / f"{domain}.key"
        self.chain_path = self.cert_dir / f"{domain}.chain.pem"
        
    def check_cert_validity(self) -> Tuple[bool, Optional[int]]:
        """
        检查证书有效性
        
        Returns:
            (是否有效, 剩余天数)
        """
        if not self.cert_path.exists():
            return False, None
            
        try:
            # 使用 OpenSSL 检查证书过期时间
            result = subprocess.run(
                ["openssl", "x509", "-in", str(self.cert_path), 
                 "-noout", "-dates"],
                capture_output=True, text=True, check=True
            )
            
            # 解析 notAfter 日期
            for line in result.stdout.split('\n'):
                if line.startswith('notAfter='):
                    date_str = line.split('=')[1].strip()
                    # 格式: Nov  3 12:00:00 2025 GMT
                    expiry = datetime.strptime(date_str, '%b %d %H:%M:%S %Y %Z')
                    days_remaining = (expiry - datetime.now(timezone.utc)).days
                    
                    # 证书有效且剩余超过 7 天
                    is_valid = days_remaining > 7
                    return is_valid, days_remaining
                    
        except Exception as e:
            logger.error(f"证书检查失败: {e}")
            return False, None
            
        return False, None
    
    def request_certificate(self, staging: bool = False) -> bool:
        """
        申请 Let's Encrypt 证书
        
        Args:
            staging: 是否使用测试环境（避免触发速率限制）
        
        Returns:
            是否成功
        """
        try:
            # 检查 certbot 是否安装
            subprocess.run(["certbot", "--version"], 
                          capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("certbot 未安装，请先安装 certbot")
            return False
        
        server = "https://acme-staging-v02.api.letsencrypt.org/directory" if staging \
                 else "https://acme-v02.api.letsencrypt.org/directory"
        
        cmd = [
            "certbot", "certonly",
            "--standalone",
            "--preferred-challenges", "http",
            "--agree-tos",
            "--email", self.email,
            "--server", server,
            "-d", self.domain,
            "--cert-path", str(self.cert_path),
            "--key-path", str(self.key_path),
            "--chain-path", str(self.chain_path),
            "--non-interactive"
        ]
        
        try:
            logger.info(f"正在申请证书: {self.domain}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("证书申请成功")
                return True
            else:
                logger.error(f"证书申请失败: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"证书申请异常: {e}")
            return False
    
    def setup_auto_renewal(self) -> bool:
        """
        设置自动续期（通过 cron/systemd timer）
        """
        # Windows 使用 Task Scheduler
        if os.name == 'nt':
            return self._setup_windows_renewal()
        else:
            return self._setup_linux_renewal()
    
    def _setup_windows_renewal(self) -> bool:
        """Windows 任务计划程序设置"""
        try:
            script_path = Path(__file__).parent / "renew_certs.py"
            
            # 创建 PowerShell 脚本
            ps_script = f'''
$action = New-ScheduledTaskAction -Execute "python" -Argument "{script_path}"
$trigger = New-ScheduledTaskTrigger -Daily -At "3:00AM"
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName "ACAS-Cert-Renewal" -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force
'''
            subprocess.run(["powershell", "-Command", ps_script], 
                          capture_output=True, check=True)
            logger.info("Windows 自动续期任务已创建")
            return True
        except Exception as e:
            logger.error(f"Windows 续期任务创建失败: {e}")
            return False
    
    def _setup_linux_renewal(self) -> bool:
        """Linux cron 设置"""
        try:
            cron_line = "0 3 * * * /usr/bin/certbot renew --quiet --deploy-hook 'systemctl reload nginx'\n"
            
            # 添加到 crontab
            subprocess.run(
                f"(crontab -l 2>/dev/null; echo '{cron_line}') | crontab -",
                shell=True, check=True
            )
            logger.info("Linux 自动续期 cron 已创建")
            return True
        except Exception as e:
            logger.error(f"Linux 续期任务创建失败: {e}")
            return False
    
    def get_cert_info(self) -> dict:
        """获取证书详细信息"""
        valid, days = self.check_cert_validity()
        
        return {
            "domain": self.domain,
            "exists": self.cert_path.exists(),
            "valid": valid,
            "days_remaining": days,
            "cert_path": str(self.cert_path),
            "key_path": str(self.key_path),
            "auto_renewal_enabled": True
        }


def init_certificates(domain: str, email: str) -> CertificateManager:
    """
    初始化证书管理
    
    使用示例:
        cert_mgr = init_certificates("acas.example.com", "admin@example.com")
        if not cert_mgr.check_cert_validity()[0]:
            cert_mgr.request_certificate()
    """
    return CertificateManager(domain, email)


if __name__ == "__main__":
    # 测试代码
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python cert_manager.py <domain> <email>")
        sys.exit(1)
    
    domain, email = sys.argv[1], sys.argv[2]
    mgr = CertificateManager(domain, email)
    
    valid, days = mgr.check_cert_validity()
    print(f"证书状态: {'有效' if valid else '无效/不存在'}")
    if days is not None:
        print(f"剩余天数: {days}")
    
    if not valid:
        print("正在申请新证书...")
        if mgr.request_certificate(staging=True):  # 先用测试环境
            print("测试证书申请成功")
        else:
            print("证书申请失败")
