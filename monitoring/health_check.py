# ACAS Pro - 企业级自动获客系统
# 版权所有 (c) 2026 高智中科（北京）科技有限公司

"""
系统健康检查模块
检查所有组件状态，生成健康报告
"""

import json
import time
import socket
import logging
import platform
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    name: str
    status: HealthStatus = HealthStatus.UNKNOWN
    message: str = ""
    response_time_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    last_check: str = field(default_factory=lambda: datetime.now().isoformat())


class HealthChecker:
    """系统健康检查器"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.results: List[ComponentHealth] = []
        self.start_time = time.time()

    def check_tcp_port(self, host: str, port: int, timeout: float = 3.0) -> ComponentHealth:
        """检查TCP端口是否可达"""
        start = time.time()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            elapsed = (time.time() - start) * 1000
            sock.close()

            if result == 0:
                return ComponentHealth(
                    name=f"{host}:{port}",
                    status=HealthStatus.HEALTHY,
                    message="端口可达",
                    response_time_ms=round(elapsed, 2)
                )
            else:
                return ComponentHealth(
                    name=f"{host}:{port}",
                    status=HealthStatus.UNHEALTHY,
                    message=f"端口不可达 (errno={result})",
                    response_time_ms=round(elapsed, 2)
                )
        except socket.timeout:
            return ComponentHealth(
                name=f"{host}:{port}",
                status=HealthStatus.UNHEALTHY,
                message="连接超时",
                response_time_ms=round(timeout * 1000, 2)
            )
        except Exception as e:
            return ComponentHealth(
                name=f"{host}:{port}",
                status=HealthStatus.UNKNOWN,
                message=str(e)
            )

    def check_http_endpoint(self, url: str, timeout: float = 5.0,
                            expected_status: int = 200) -> ComponentHealth:
        """检查HTTP端点"""
        import urllib.request
        import urllib.error

        start = time.time()
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                elapsed = (time.time() - start) * 1000
                status_code = resp.getcode()

                if status_code == expected_status:
                    return ComponentHealth(
                        name=url,
                        status=HealthStatus.HEALTHY,
                        message=f"HTTP {status_code}",
                        response_time_ms=round(elapsed, 2)
                    )
                else:
                    return ComponentHealth(
                        name=url,
                        status=HealthStatus.DEGRADED,
                        message=f"HTTP {status_code} (expected {expected_status})",
                        response_time_ms=round(elapsed, 2)
                    )
        except urllib.error.HTTPError as e:
            elapsed = (time.time() - start) * 1000
            return ComponentHealth(
                name=url,
                status=HealthStatus.DEGRADED,
                message=f"HTTP {e.code}",
                response_time_ms=round(elapsed, 2)
            )
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            return ComponentHealth(
                name=url,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                response_time_ms=round(elapsed, 2)
            )

    def check_database(self, db_url: str = None) -> ComponentHealth:
        """检查数据库连接"""
        start = time.time()
        try:
            from dotenv import load_dotenv
            load_dotenv()
            url = db_url or os.getenv("DATABASE_URL", "")

            if not url:
                return ComponentHealth(
                    name="database",
                    status=HealthStatus.UNKNOWN,
                    message="未配置DATABASE_URL，使用SQLite本地模式"
                )

            if "postgresql" in url or "postgres" in url:
                import psycopg2
                conn = psycopg2.connect(url, connect_timeout=5)
                cur = conn.cursor()
                cur.execute("SELECT 1")
                cur.close()
                conn.close()
            elif "sqlite" in url:
                import sqlite3
                conn = sqlite3.connect(url.replace("sqlite:///", ""))
                cur = conn.cursor()
                cur.execute("SELECT 1")
                cur.close()
                conn.close()

            elapsed = (time.time() - start) * 1000
            return ComponentHealth(
                name="database",
                status=HealthStatus.HEALTHY,
                message="数据库连接正常",
                response_time_ms=round(elapsed, 2)
            )
        except ImportError:
            return ComponentHealth(
                name="database",
                status=HealthStatus.DEGRADED,
                message="数据库驱动未安装"
            )
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"数据库连接失败: {e}",
                response_time_ms=round(elapsed, 2)
            )

    def check_redis(self, host: str = "localhost", port: int = 6379,
                    password: str = None) -> ComponentHealth:
        """检查Redis连接"""
        start = time.time()
        try:
            import redis
            r = redis.Redis(host=host, port=port, password=password, socket_timeout=5)
            r.ping()
            elapsed = (time.time() - start) * 1000
            info = r.info("server")
            return ComponentHealth(
                name="redis",
                status=HealthStatus.HEALTHY,
                message="Redis连接正常",
                response_time_ms=round(elapsed, 2),
                details={"version": info.get("redis_version", "unknown")}
            )
        except ImportError:
            return ComponentHealth(
                name="redis",
                status=HealthStatus.DEGRADED,
                message="redis模块未安装，使用LRU缓存降级"
            )
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            return ComponentHealth(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                message=f"Redis连接失败: {e}",
                response_time_ms=round(elapsed, 2)
            )

    def check_certificates(self, cert_dir: str = "certs") -> ComponentHealth:
        """检查TLS证书状态"""
        cert_path = os.path.join(cert_dir, "server.crt")
        if not os.path.exists(cert_path):
            return ComponentHealth(
                name="tls_cert",
                status=HealthStatus.UNKNOWN,
                message="证书文件不存在"
            )

        try:
            from cryptography import x509
            from cryptography.hazmat.backends import default_backend
            with open(cert_path, "rb") as f:
                cert = x509.load_pem_x509_certificate(f.read(), default_backend())

            days_left = (cert.not_valid_after_utc - datetime.now().days).days if hasattr(cert, 'not_valid_after_utc') else 0

            if days_left < 0:
                status = HealthStatus.UNHEALTHY
                msg = f"证书已过期 {abs(days_left)} 天"
            elif days_left < 7:
                status = HealthStatus.DEGRADED
                msg = f"证书即将过期（剩余 {days_left} 天）"
            else:
                status = HealthStatus.HEALTHY
                msg = f"证书有效（剩余 {days_left} 天）"

            return ComponentHealth(
                name="tls_cert",
                status=status,
                message=msg,
                details={"expires": str(cert.not_valid_after_utc) if hasattr(cert, 'not_valid_after_utc') else "unknown"}
            )
        except ImportError:
            return ComponentHealth(
                name="tls_cert",
                status=HealthStatus.UNKNOWN,
                message="cryptography模块未安装，无法检查证书"
            )
        except Exception as e:
            return ComponentHealth(
                name="tls_cert",
                status=HealthStatus.UNKNOWN,
                message=str(e)
            )

    def check_disk_space(self, path: str = "/", min_percent: float = 10.0) -> ComponentHealth:
        """检查磁盘空间"""
        try:
            if platform.system() == "Windows":
                import ctypes
                free_bytes = ctypes.c_ulonglong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    ctypes.c_wchar_p(path), None, None, ctypes.pointer(free_bytes)
                )
                free_gb = free_bytes.value / (1024 ** 3)
            else:
                stat = os.statvfs(path)
                free_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)

            if free_gb < 1:
                status = HealthStatus.UNHEALTHY
                msg = f"磁盘空间不足: {free_gb:.1f}GB"
            elif free_gb < 10:
                status = HealthStatus.DEGRADED
                msg = f"磁盘空间偏低: {free_gb:.1f}GB"
            else:
                status = HealthStatus.HEALTHY
                msg = f"磁盘空间正常: {free_gb:.1f}GB"

            return ComponentHealth(
                name="disk",
                status=status,
                message=msg,
                details={"free_gb": round(free_gb, 2)}
            )
        except Exception as e:
            return ComponentHealth(
                name="disk",
                status=HealthStatus.UNKNOWN,
                message=str(e)
            )

    def run_all_checks(self) -> Dict[str, Any]:
        """运行所有健康检查"""
        self.results = []

        # 系统信息
        system_info = {
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "python": platform.python_version(),
            "uptime_seconds": round(time.time() - self.start_time, 2)
        }

        # API服务
        api_port = self.config.get("api_port", 5002)
        self.results.append(self.check_tcp_port("localhost", api_port))

        # HTTP健康端点
        self.results.append(
            self.check_http_endpoint(f"http://localhost:{api_port}/api/health")
        )

        # 数据库
        self.results.append(self.check_database())

        # Redis
        redis_host = self.config.get("redis_host", "localhost")
        redis_port = self.config.get("redis_port", 6379)
        self.results.append(self.check_redis(redis_host, redis_port))

        # TLS证书
        self.results.append(self.check_certificates(
            self.config.get("cert_dir", "certs")
        ))

        # 磁盘空间
        disk_path = "C:\\" if platform.system() == "Windows" else "/"
        self.results.append(self.check_disk_space(disk_path))

        # 汇总
        status_counts = {}
        for r in self.results:
            status_counts[r.status.value] = status_counts.get(r.status.value, 0) + 1

        if status_counts.get("unhealthy", 0) > 0:
            overall = HealthStatus.UNHEALTHY
        elif status_counts.get("degraded", 0) > 0:
            overall = HealthStatus.DEGRADED
        elif status_counts.get("healthy", 0) > 0:
            overall = HealthStatus.HEALTHY
        else:
            overall = HealthStatus.UNKNOWN

        return {
            "status": overall.value,
            "timestamp": datetime.now().isoformat(),
            "system": system_info,
            "components": [
                {
                    "name": r.name,
                    "status": r.status.value,
                    "message": r.message,
                    "response_time_ms": r.response_time_ms,
                    "details": r.details
                }
                for r in self.results
            ],
            "summary": status_counts
        }

    def format_report(self, report: Dict[str, Any]) -> str:
        """格式化健康报告"""
        status_icon = {
            "healthy": "✅",
            "degraded": "⚠️",
            "unhealthy": "❌",
            "unknown": "❓"
        }

        lines = [
            f"{'='*50}",
            f"  ACAS Pro 系统健康报告",
            f"  {report['timestamp']}",
            f"{'='*50}",
            "",
            f"整体状态: {status_icon.get(report['status'], '?')} {report['status'].upper()}",
            "",
            "组件详情:",
            "-" * 40
        ]

        for comp in report["components"]:
            icon = status_icon.get(comp["status"], "?")
            rt = f" ({comp['response_time_ms']}ms)" if comp["response_time_ms"] else ""
            lines.append(f"  {icon} {comp['name']}: {comp['message']}{rt}")

        lines.extend([
            "",
            "汇总:",
            "-" * 40
        ])

        for status, count in report["summary"].items():
            icon = status_icon.get(status, "?")
            lines.append(f"  {icon} {status}: {count}")

        lines.append(f"\n{'='*50}")
        return "\n".join(lines)


def main():
    """命令行入口"""
    import argparse
    parser = argparse.ArgumentParser(description="ACAS Pro 健康检查")
    parser.add_argument("--json", action="store_true", help="输出JSON格式")
    parser.add_argument("--api-port", type=int, default=5002, help="API端口")
    args = parser.parse_args()

    checker = HealthChecker(config={"api_port": args.api_port})
    report = checker.run_all_checks()

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(checker.format_report(report))


if __name__ == "__main__":
    main()
