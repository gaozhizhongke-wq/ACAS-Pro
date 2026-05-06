"""ACAS Pro - 性能测试
使用 Locust 进行负载测试

注意：性能测试需要 ACAS Pro 服务运行在 localhost:8000。
手动运行: pytest tests/test_performance.py -m performance --run-performance
"""
import pytest
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict
import requests

# Check if server is running
import socket

def _server_available(host='localhost', port=8000, timeout=2):
    try:
        with socket.create_connection((host, port), timeout):
            return True
    except (ConnectionRefusedError, socket.timeout):
        return False

pytestmark = pytest.mark.skipif(
    not _server_available(),
    reason="Performance tests require ACAS Pro server running on localhost:8000"
)


class PerformanceBenchmark:
    """性能基准测试"""
    
    BASE_URL = "http://localhost:8000"
    
    def __init__(self):
        self.session = requests.Session()
        self.results: List[Dict] = []
    
    def measure_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """测量单次请求性能"""
        url = f"{self.BASE_URL}{endpoint}"
        start = time.perf_counter()
        
        try:
            response = self.session.request(method, url, timeout=30, **kwargs)
            elapsed = time.perf_counter() - start
            
            return {
                "endpoint": endpoint,
                "status_code": response.status_code,
                "response_time": elapsed,
                "success": response.status_code < 500,
                "content_length": len(response.content)
            }
        except Exception as e:
            return {
                "endpoint": endpoint,
                "status_code": 0,
                "response_time": time.perf_counter() - start,
                "success": False,
                "error": str(e)
            }
    
    def run_concurrent(self, method: str, endpoint: str, 
                       concurrency: int, total_requests: int, **kwargs) -> List[Dict]:
        """并发压力测试"""
        results = []
        
        def worker():
            return self.measure_request(method, endpoint, **kwargs)
        
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(worker) for _ in range(total_requests)]
            for future in as_completed(futures):
                results.append(future.result())
        
        return results
    
    def analyze_results(self, results: List[Dict]) -> Dict:
        """分析测试结果"""
        times = [r["response_time"] for r in results if r["success"]]
        failures = [r for r in results if not r["success"]]
        
        if not times:
            return {"error": "All requests failed"}
        
        times.sort()
        n = len(times)
        
        return {
            "total_requests": len(results),
            "successful": len(times),
            "failed": len(failures),
            "success_rate": len(times) / len(results),
            "min_time": min(times),
            "max_time": max(times),
            "mean_time": statistics.mean(times),
            "median_time": statistics.median(times),
            "p95_time": times[int(n * 0.95)],
            "p99_time": times[int(n * 0.99)],
            "std_dev": statistics.stdev(times) if n > 1 else 0,
            "rps": len(times) / sum(times)
        }


@pytest.mark.performance
class TestAPIPerformance:
    """API 性能测试"""
    
    @pytest.fixture(scope="class")
    def benchmark(self):
        return PerformanceBenchmark()
    
    def test_health_endpoint_latency(self, benchmark):
        """健康检查端点延迟 < 100ms"""
        results = []
        for _ in range(100):
            r = benchmark.measure_request("GET", "/health")
            results.append(r)
        
        analysis = benchmark.analyze_results(results)
        
        assert analysis["success_rate"] >= 0.99, f"成功率 {analysis['success_rate']:.2%} < 99%"
        assert analysis["p95_time"] < 0.1, f"P95 延迟 {analysis['p95_time']*1000:.1f}ms >= 100ms"
        assert analysis["mean_time"] < 0.05, f"平均延迟 {analysis['mean_time']*1000:.1f}ms >= 50ms"
    
    def test_api_concurrent_load(self, benchmark):
        """API 并发负载测试"""
        # 100 并发，1000 请求
        results = benchmark.run_concurrent(
            "GET", "/api/v1/health",
            concurrency=100,
            total_requests=1000
        )
        
        analysis = benchmark.analyze_results(results)
        
        assert analysis["success_rate"] >= 0.95, f"成功率 {analysis['success_rate']:.2%} < 95%"
        assert analysis["p95_time"] < 0.5, f"P95 延迟 {analysis['p95_time']:.3f}s >= 500ms"
        assert analysis["rps"] >= 50, f"RPS {analysis['rps']:.1f} < 50"
    
    def test_forecast_endpoint_performance(self, benchmark):
        """预测端点性能"""
        payload = {
            "product_id": "test_product",
            "days": 30,
            "algorithm": "auto"
        }
        
        results = []
        for _ in range(50):
            r = benchmark.measure_request(
                "POST", "/api/v1/forecast",
                json=payload
            )
            results.append(r)
        
        analysis = benchmark.analyze_results(results)
        
        # 预测允许更长时间
        assert analysis["success_rate"] >= 0.90
        assert analysis["p95_time"] < 5.0, f"P95 延迟 {analysis['p95_time']:.1f}s >= 5s"
    
    def test_database_query_performance(self, benchmark):
        """数据库查询性能"""
        # 测试列表查询
        results = []
        for _ in range(200):
            r = benchmark.measure_request(
                "GET", "/api/v1/users?page=1&size=20"
            )
            results.append(r)
        
        analysis = benchmark.analyze_results(results)
        
        assert analysis["success_rate"] >= 0.99
        assert analysis["p95_time"] < 0.2, f"P95 延迟 {analysis['p95_time']*1000:.1f}ms >= 200ms"
    
    def test_memory_usage_stability(self, benchmark):
        """内存使用稳定性"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 执行大量请求
        for _ in range(500):
            benchmark.measure_request("GET", "/api/v1/health")
        
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_growth = final_memory - initial_memory
        
        # 内存增长应 < 50MB
        assert memory_growth < 50, f"内存增长 {memory_growth:.1f}MB >= 50MB"


@pytest.mark.performance
class TestDatabasePerformance:
    """数据库性能测试"""
    
    def test_connection_pool_performance(self, db_session):
        """连接池性能"""
        import time
        from concurrent.futures import ThreadPoolExecutor
        
        def query_task():
            start = time.perf_counter()
            result = db_session.execute("SELECT 1").fetchone()
            elapsed = time.perf_counter() - start
            return elapsed
        
        # 100 并发查询
        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = [executor.submit(query_task) for _ in range(1000)]
            times = [f.result() for f in futures]
        
        avg_time = statistics.mean(times)
        p95_time = sorted(times)[int(len(times) * 0.95)]
        
        assert avg_time < 0.01, f"平均查询时间 {avg_time*1000:.1f}ms >= 10ms"
        assert p95_time < 0.05, f"P95 查询时间 {p95_time*1000:.1f}ms >= 50ms"
    
    def test_large_result_set_performance(self, db_session):
        """大数据集查询性能"""
        import time
        
        start = time.perf_counter()
        result = db_session.execute("SELECT * FROM forecasts LIMIT 10000").fetchall()
        elapsed = time.perf_counter() - start
        
        assert elapsed < 1.0, f"大数据集查询 {elapsed:.2f}s >= 1s"


@pytest.mark.performance
class TestCachePerformance:
    """缓存性能测试"""
    
    def test_redis_read_performance(self, redis_client):
        """Redis 读取性能"""
        import time
        
        # 预热
        redis_client.set("perf_test_key", "value")
        
        times = []
        for _ in range(1000):
            start = time.perf_counter()
            redis_client.get("perf_test_key")
            times.append(time.perf_counter() - start)
        
        avg_time = statistics.mean(times)
        p99_time = sorted(times)[int(len(times) * 0.99)]
        
        assert avg_time < 0.001, f"Redis 平均读取 {avg_time*1000:.2f}ms >= 1ms"
        assert p99_time < 0.005, f"Redis P99 读取 {p99_time*1000:.2f}ms >= 5ms"
    
    def test_redis_write_performance(self, redis_client):
        """Redis 写入性能"""
        import time
        
        times = []
        for i in range(1000):
            start = time.perf_counter()
            redis_client.set(f"perf_test_{i}", f"value_{i}", ex=60)
            times.append(time.perf_counter() - start)
        
        avg_time = statistics.mean(times)
        
        assert avg_time < 0.002, f"Redis 平均写入 {avg_time*1000:.2f}ms >= 2ms"


@pytest.mark.performance
class TestLoadBalancing:
    """负载均衡测试"""
    
    def test_round_robin_distribution(self):
        """轮询负载均衡"""
        # 需要多实例环境
        pytest.skip("需要多实例部署环境")
    
    def test_sticky_session(self):
        """会话保持"""
        pytest.skip("需要多实例部署环境")


# Locust 负载测试配置
LOCUSTFILE = '''
from locust import HttpUser, task, between

class ACASUser(HttpUser):
    wait_time = between(1, 5)
    
    def on_start(self):
        """登录获取 token"""
        response = self.client.post("/api/v1/auth/login", json={
            "username": "test_user",
            "password": "test_pass"
        })
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = None
            self.headers = {}
    
    @task(10)
    def get_health(self):
        self.client.get("/health")
    
    @task(5)
    def get_forecasts(self):
        if self.headers:
            self.client.get("/api/v1/forecast", headers=self.headers)
    
    @task(3)
    def create_forecast(self):
        if self.headers:
            self.client.post("/api/v1/forecast", 
                headers=self.headers,
                json={"product_id": "test", "days": 30}
            )
    
    @task(2)
    def get_inventory(self):
        if self.headers:
            self.client.get("/api/v1/inventory", headers=self.headers)

# 运行: locust -f test_performance.py --host=http://localhost:8000
'''
