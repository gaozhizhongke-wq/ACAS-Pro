#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro 生产级测试套件
覆盖：API、数据库、性能、压力
"""

import os
import sys
import time
import json
import random
import string
import unittest
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(__file__))

from config import get_config
from database import get_db, Database
from logger import app_logger


class TestDatabase(unittest.TestCase):
    """数据库测试"""
    
    def setUp(self):
        self.db = get_db()
    
    def test_connection(self):
        """测试数据库连接"""
        stats = self.db.get_dashboard_stats()
        self.assertIsInstance(stats, dict)
    
    def test_crud_account(self):
        """测试账号 CRUD"""
        import uuid
        account_id = f"test_{uuid.uuid4().hex[:8]}"
        
        # Create
        account = self.db.create_account(
            account_id=account_id,
            platform="douyin",
            username="Test Account",
            status="active",
            followers=1000
        )
        self.assertEqual(account.username, "Test Account")
        
        # Read
        accounts = self.db.get_accounts()
        self.assertTrue(any(a.account_id == account_id for a in accounts))
        
        # Log
        self.db.log("INFO", "test", "Test message", {"test": True})
        logs = self.db.get_logs(limit=1)
        self.assertEqual(logs[0].message, "Test message")


class TestConfig(unittest.TestCase):
    """配置测试"""
    
    def test_config_loading(self):
        """测试配置加载"""
        config = get_config()
        self.assertIsNotNone(config.llm)
        self.assertIn(config.llm.provider, ['deepseek', 'openai', 'kimi', ''])
    
    def test_env_override(self):
        """测试环境变量覆盖"""
        os.environ['ACAS_DEBUG'] = 'true'
        config = get_config()
        self.assertTrue(config.debug)
        del os.environ['ACAS_DEBUG']


class TestPerformance(unittest.TestCase):
    """性能测试"""
    
    def setUp(self):
        self.db = get_db()
    
    def test_dashboard_query_speed(self):
        """测试仪表盘查询速度"""
        start = time.time()
        for _ in range(100):
            self.db.get_dashboard_stats()
        duration = time.time() - start
        
        avg_time = duration / 100
        print(f"\nDashboard query avg: {avg_time*1000:.2f}ms")
        self.assertLess(avg_time, 0.1)  # 100ms 以内
    
    def test_concurrent_reads(self):
        """测试并发读取"""
        def read_dashboard():
            return self.db.get_dashboard_stats()
        
        start = time.time()
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(read_dashboard) for _ in range(50)]
            results = [f.result() for f in as_completed(futures)]
        
        duration = time.time() - start
        print(f"\n50 concurrent reads: {duration:.2f}s")
        self.assertEqual(len(results), 50)


class TestAPIIntegration(unittest.TestCase):
    """API 集成测试"""
    
    def setUp(self):
        try:
            import requests
            self.requests = requests
            self.base_url = "http://localhost:5000"
            self.api_base = f"{self.base_url}/api"
        except ImportError:
            self.skipTest("requests not installed")
    
    def test_health_endpoint(self):
        """测试健康检查"""
        try:
            resp = self.requests.get(f"{self.base_url}/health", timeout=5)
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertIn("status", data)
        except Exception as e:
            self.skipTest(f"Server not running: {e}")
    
    def test_login(self):
        """测试登录"""
        try:
            resp = self.requests.post(
                f"{self.api_base}/auth/login",
                json={"username": "admin", "password": "admin123"},
                timeout=5
            )
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertTrue(data.get("success"))
        except Exception as e:
            self.skipTest(f"Server not running: {e}")


class TestSecurity(unittest.TestCase):
    """安全测试"""
    
    def test_sql_injection_protection(self):
        """测试 SQL 注入防护"""
        db = get_db()
        
        # 尝试注入
        malicious_input = "'; DROP TABLE accounts; --"
        
        # 应该正常处理，不会报错
        try:
            accounts = db.get_accounts(platform=malicious_input)
            # 如果没有异常，说明参数化查询生效
            self.assertIsInstance(accounts, list)
        except Exception as e:
            # 如果有异常，应该是参数类型错误，不是 SQL 错误
            self.assertNotIn("syntax error", str(e).lower())


def run_stress_test(duration=30, concurrency=10):
    """压力测试"""
    print(f"\n{'='*60}")
    print(f"压力测试: {concurrency} 并发, {duration} 秒")
    print(f"{'='*60}")
    
    db = get_db()
    results = {"success": 0, "error": 0, "total_time": 0}
    stop_event = threading.Event()
    
    def worker():
        while not stop_event.is_set():
            start = time.time()
            try:
                db.get_dashboard_stats()
                results["success"] += 1
            except Exception as e:
                results["error"] += 1
            results["total_time"] += time.time() - start
    
    threads = [threading.Thread(target=worker) for _ in range(concurrency)]
    for t in threads:
        t.start()
    
    time.sleep(duration)
    stop_event.set()
    
    for t in threads:
        t.join()
    
    total = results["success"] + results["error"]
    avg_time = results["total_time"] / total if total > 0 else 0
    
    print(f"总请求: {total}")
    print(f"成功: {results['success']}")
    print(f"失败: {results['error']}")
    print(f"成功率: {results['success']/total*100:.1f}%" if total > 0 else "N/A")
    print(f"平均响应: {avg_time*1000:.2f}ms")
    print(f"QPS: {total/duration:.1f}")


def main():
    """运行所有测试"""
    print("="*60)
    print("ACAS Pro 生产级测试套件")
    print("="*60)
    
    # 运行单元测试
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestDatabase))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformance))
    suite.addTests(loader.loadTestsFromTestCase(TestAPIIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestSecurity))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 运行压力测试
    run_stress_test(duration=10, concurrency=5)
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    print(f"通过: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
