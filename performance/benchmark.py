# ACAS Pro - 企业级自动获客系统
# 版权所有 (c) 2026 高智中科（北京）科技有限公司

"""
基准测试脚本
测试响应时间、吞吐量、并发数，与历史数据对比，性能回归检测
"""

import json
import time
import os
import logging
from datetime import datetime
from typing import Dict, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    name: str
    iterations: int = 100
    avg_ms: float = 0.0
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    min_ms: float = 0.0
    max_ms: float = 0.0
    throughput: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class BenchmarkRunner:
    """基准测试运行器"""

    def __init__(self, host: str = "http://localhost:5002"):
        self.host = host
        self.results: List[BenchmarkResult] = []
        self.history_file = "performance/benchmark_history.json"

    def _measure(self, func, iterations: int = 100) -> BenchmarkResult:
        times = []
        for _ in range(iterations):
            start = time.time()
            try:
                func()
                elapsed = (time.time() - start) * 1000
                times.append(elapsed)
            except Exception:
                times.append(-1)

        valid_times = sorted([t for t in times if t > 0])
        if not valid_times:
            return BenchmarkResult(name="unknown", iterations=iterations)

        n = len(valid_times)
        total_time = sum(valid_times) / 1000

        return BenchmarkResult(
            name="",
            iterations=n,
            avg_ms=round(sum(valid_times) / n, 2),
            p50_ms=round(valid_times[int(n * 0.5)], 2),
            p95_ms=round(valid_times[int(n * 0.95)], 2),
            p99_ms=round(valid_times[int(n * 0.99)], 2),
            min_ms=round(valid_times[0], 2),
            max_ms=round(valid_times[-1], 2),
            throughput=round(n / total_time, 2) if total_time > 0 else 0
        )

    def benchmark_health(self) -> BenchmarkResult:
        import urllib.request
        def req():
            urllib.request.urlopen(f"{self.host}/api/health", timeout=5)
        result = self._measure(req, 100)
        result.name = "health_check"
        return result

    def benchmark_login(self) -> BenchmarkResult:
        import urllib.request
        def req():
            data = json.dumps({"username": "admin", "password": "admin123"}).encode()
            r = urllib.request.Request(f"{self.host}/api/auth/login", data=data,
                                       headers={"Content-Type": "application/json"})
            urllib.request.urlopen(r, timeout=5)
        result = self._measure(req, 50)
        result.name = "login"
        return result

    def benchmark_dashboard(self) -> BenchmarkResult:
        import urllib.request
        def req():
            urllib.request.urlopen(f"{self.host}/api/dashboard/stats", timeout=5)
        result = self._measure(req, 50)
        result.name = "dashboard_stats"
        return result

    def run_all(self) -> List[BenchmarkResult]:
        logger.info("基准测试开始...")
        self.results = [
            self.benchmark_health(),
            self.benchmark_login(),
            self.benchmark_dashboard(),
        ]
        self._save_history()
        return self.results

    def _save_history(self):
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        history = []
        if os.path.exists(self.history_file):
            with open(self.history_file, "r", encoding="utf-8") as f:
                history = json.load(f)

        for r in self.results:
            history.append({
                "name": r.name, "avg_ms": r.avg_ms, "p50_ms": r.p50_ms,
                "p95_ms": r.p95_ms, "p99_ms": r.p99_ms, "min_ms": r.min_ms,
                "max_ms": r.max_ms, "throughput": r.throughput,
                "timestamp": r.timestamp
            })

        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

    def check_regression(self, threshold_pct: float = 20.0) -> Dict:
        """检测性能回归"""
        if not os.path.exists(self.history_file):
            return {"status": "no_history"}

        with open(self.history_file, "r", encoding="utf-8") as f:
            history = json.load(f)

        regressions = []
        for result in self.results:
            prev = [h for h in history if h["name"] == result.name]
            if len(prev) >= 2:
                last = prev[-2]
                if last["p95_ms"] > 0:
                    change_pct = (result.p95_ms - last["p95_ms"]) / last["p95_ms"] * 100
                    if change_pct > threshold_pct:
                        regressions.append({
                            "name": result.name,
                            "previous_p95": last["p95_ms"],
                            "current_p95": result.p95_ms,
                            "change_pct": round(change_pct, 2)
                        })

        return {
            "status": "regression_found" if regressions else "ok",
            "regressions": regressions,
            "threshold_pct": threshold_pct
        }

    def format_report(self) -> str:
        lines = [
            "ACAS Pro 基准测试报告",
            f"时间: {datetime.now().isoformat()}",
            f"目标: {self.host}",
            "=" * 50,
        ]

        for r in self.results:
            lines.extend([
                f"\n[{r.name}] ({r.iterations} 次)",
                f"  平均: {r.avg_ms}ms  P50: {r.p50_ms}ms",
                f"  P95: {r.p95_ms}ms    P99: {r.p99_ms}ms",
                f"  范围: {r.min_ms}ms ~ {r.max_ms}ms",
                f"  吞吐: {r.throughput} req/s",
            ])

        regression = self.check_regression()
        if regression["status"] == "regression_found":
            lines.extend(["\n⚠️ 性能回归:", "-" * 30])
            for reg in regression["regressions"]:
                lines.append(f"  {reg['name']}: P95 {reg['previous_p95']}ms -> {reg['current_p95']}ms (+{reg['change_pct']}%)")
        elif regression["status"] == "ok":
            lines.append("\n✅ 无性能回归")

        return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="ACAS Pro 基准测试")
    parser.add_argument("--host", default="http://localhost:5002")
    parser.add_argument("--regression-threshold", type=float, default=20.0)
    parser.add_argument("--report", help="报告输出文件")
    args = parser.parse_args()

    runner = BenchmarkRunner(host=args.host)
    runner.run_all()
    report = runner.format_report()
    print(report)

    if args.report:
        os.makedirs(os.path.dirname(args.report) or ".", exist_ok=True)
        with open(args.report, "w", encoding="utf-8") as f:
            f.write(report)


if __name__ == "__main__":
    main()
