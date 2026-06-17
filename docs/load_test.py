# ACAS Pro - 企业级自动获客系统
# 版权所有 (c) 2026 高智中科（北京）科技有限公司

"""
Locust 性能压测脚本
测试场景：并发登录、内容生成、账号管理、数据查询
支持分布式模式和HTML报告生成
"""

import time
import random
import logging
import os
from typing import Dict, List

logger = logging.getLogger(__name__)

try:
    from locust import HttpUser, task, between, events, tag  # noqa: F401
    from locust.runners import MasterRunner, WorkerRunner  # noqa: F401
    LOCUST_AVAILABLE = True
except ImportError:
    LOCUST_AVAILABLE = False
    logger.warning("locust 未安装，请运行: pip install locust")


# ============ 测试数据 ============

TEST_USERS = [
    {"username": "admin", "password": "admin123"},
    {"username": "operator", "password": "operator123"},
    {"username": "viewer", "password": "viewer123"},
]

CONTENT_TEMPLATES = [
    {"platform": "douyin", "style": "funny", "topic": "daily"},
    {"platform": "xiaohongshu", "style": "lifestyle", "topic": "beauty"},
    {"platform": "weibo", "style": "professional", "topic": "tech"},
    {"platform": "bilibili", "style": "creative", "topic": "gaming"},
]

ACCOUNT_ACTIONS = ["list", "create", "update", "delete", "analytics"]


# ============ 压测用户 ============

if LOCUST_AVAILABLE:

    class ACASProUser(HttpUser):
        """ACAS Pro 模拟用户"""

        wait_time = between(1, 3)
        host = os.getenv("LOCUST_HOST", "http://localhost:5002")

        def on_start(self):
            """登录获取Token"""
            user = random.choice(TEST_USERS)
            with self.client.post("/api/auth/login", json=user,
                                  catch_response=True) as resp:
                if resp.status_code == 200:
                    data = resp.json()
                    self.token = data.get("token", "")
                    resp.success()
                else:
                    self.token = ""
                    resp.failure(f"登录失败: {resp.status_code}")

        @task(5)
        @tag("content")
        def generate_content(self):
            """内容生成压测"""
            if not self.token:
                return
            template = random.choice(CONTENT_TEMPLATES)
            headers = {"Authorization": f"Bearer {self.token}"}
            with self.client.post("/api/content/generate",
                                  json=template, headers=headers,
                                  catch_response=True) as resp:
                if resp.status_code == 200:
                    resp.success()
                elif resp.status_code == 429:
                    resp.failure("限流")
                else:
                    resp.failure(f"内容生成失败: {resp.status_code}")

        @task(3)
        @tag("account")
        def manage_accounts(self):
            """账号管理压测"""
            if not self.token:
                return
            action = random.choice(ACCOUNT_ACTIONS)
            headers = {"Authorization": f"Bearer {self.token}"}
            endpoint = f"/api/accounts?action={action}"
            with self.client.get(endpoint, headers=headers,
                                 catch_response=True) as resp:
                if resp.status_code in (200, 201):
                    resp.success()
                else:
                    resp.failure(f"账号管理失败: {resp.status_code}")

        @task(2)
        @tag("query")
        def query_data(self):
            """数据查询压测"""
            if not self.token:
                return
            headers = {"Authorization": f"Bearer {self.token}"}
            endpoints = [
                "/api/dashboard/stats",
                "/api/inventory/status",
                "/api/sales/forecast",
                "/api/monitoring/metrics",
            ]
            endpoint = random.choice(endpoints)
            with self.client.get(endpoint, headers=headers,
                                 catch_response=True) as resp:
                if resp.status_code == 200:
                    resp.success()
                else:
                    resp.failure(f"查询失败: {resp.status_code}")

        @task(1)
        @tag("health")
        def health_check(self):
            """健康检查"""
            with self.client.get("/api/health", catch_response=True) as resp:
                if resp.status_code == 200:
                    resp.success()
                else:
                    resp.failure(f"健康检查失败: {resp.status_code}")


# ============ 性能指标收集 ============

class PerformanceMetrics:
    """性能指标收集器"""

    def __init__(self):
        self.request_times: List[float] = []
        self.error_count: int = 0
        self.total_requests: int = 0
        self.start_time: float = 0

    def record(self, response_time: float, success: bool):
        self.total_requests += 1
        self.request_times.append(response_time)
        if not success:
            self.error_count += 1

    def get_summary(self) -> Dict:
        if not self.request_times:
            return {"total": 0, "errors": 0, "rps": 0}

        sorted_times = sorted(self.request_times)
        total_time = sum(sorted_times)
        n = len(sorted_times)

        return {
            "total_requests": self.total_requests,
            "error_count": self.error_count,
            "error_rate": round(self.error_count / self.total_requests * 100, 2),
            "avg_ms": round(total_time / n, 2),
            "p50_ms": round(sorted_times[int(n * 0.5)], 2),
            "p95_ms": round(sorted_times[int(n * 0.95)], 2),
            "p99_ms": round(sorted_times[int(n * 0.99)], 2),
            "min_ms": round(sorted_times[0], 2),
            "max_ms": round(sorted_times[-1], 2),
            "rps": round(n / max(time.time() - self.start_time, 1), 2) if self.start_time else 0
        }

    def format_report(self) -> str:
        s = self.get_summary()
        return (
            f"性能测试报告\n"
            f"{'='*40}\n"
            f"总请求数: {s['total_requests']}\n"
            f"错误数: {s['error_count']} ({s['error_rate']}%)\n"
            f"平均响应: {s['avg_ms']}ms\n"
            f"P50: {s['p50_ms']}ms\n"
            f"P95: {s['p95_ms']}ms\n"
            f"P99: {s['p99_ms']}ms\n"
            f"最小/最大: {s['min_ms']}ms / {s['max_ms']}ms\n"
            f"吞吐量: {s['rps']} req/s\n"
        )


# ============ 负载级别预设 ============

LOAD_PROFILES = {
    "low": {"users": 10, "spawn_rate": 2, "run_time": "60s"},
    "medium": {"users": 50, "spawn_rate": 5, "run_time": "180s"},
    "high": {"users": 200, "spawn_rate": 10, "run_time": "300s"},
    "peak": {"users": 500, "spawn_rate": 20, "run_time": "600s"},
}


def generate_locust_config(profile: str = "medium", host: str = "http://localhost:5002") -> str:
    """生成 Locust 配置文件"""
    p = LOAD_PROFILES.get(profile, LOAD_PROFILES["medium"])
    return f"""# ACAS Pro Locust 配置
host = "{host}"
users = {p['users']}
spawn_rate = {p['spawn_rate']}
run_time = "{p['run_time']}"
"""


# ============ 命令行入口 ============

def main():
    """性能测试命令行入口（非Locust模式的独立压测）"""
    import argparse
    import urllib.request
    import urllib.error
    import concurrent.futures

    parser = argparse.ArgumentParser(description="ACAS Pro 性能压测")
    parser.add_argument("--host", default="http://localhost:5002")
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--endpoint", default="/api/health")
    parser.add_argument("--report", help="报告输出文件")
    args = parser.parse_args()

    metrics = PerformanceMetrics()
    metrics.start_time = time.time()

    def make_request(i):
        start = time.time()
        try:
            req = urllib.request.Request(f"{args.host}{args.endpoint}")
            with urllib.request.urlopen(req, timeout=10) as resp:
                elapsed = (time.time() - start) * 1000
                success = resp.getcode() == 200
                return elapsed, success
        except Exception:
            elapsed = (time.time() - start) * 1000
            return elapsed, False

    print(f"压测启动: {args.concurrency} 并发, {args.requests} 请求")
    print(f"目标: {args.host}{args.endpoint}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [executor.submit(make_request, i) for i in range(args.requests)]
        for future in concurrent.futures.as_completed(futures):
            elapsed, success = future.result()
            metrics.record(elapsed, success)
            if metrics.total_requests % 10 == 0:
                print(f"  进度: {metrics.total_requests}/{args.requests}")

    report = metrics.format_report()
    print("\n" + report)

    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"报告已保存: {args.report}")


if __name__ == "__main__":
    main()
