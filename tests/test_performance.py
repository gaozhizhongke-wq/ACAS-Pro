"""Performance tests for ACAS Pro API

Load testing and performance benchmarks using pytest-benchmark.
"""
import pytest
import sys
import os
import time
import concurrent.futures

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

os.environ['ACAS_ENV'] = 'testing'
os.environ['SECRET_KEY'] = 'test-secret-key-for-performance-tests'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

from web_app import app


@pytest.fixture
def client():
    """Create a test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def auth_token(client):
    """Get authentication token for performance tests"""
    # Register and login
    client.post('/api/auth/register',
                json={'account': 'perfuser', 'password': 'PerfP@ss123'})
    
    response = client.post('/api/auth/login',
                          json={'account': 'perfuser', 'password': 'PerfP@ss123'})
    
    return response.get_json()['token']


class TestHealthEndpointPerformance:
    """Performance tests for health endpoint"""
    
    def test_health_check_response_time(self, client):
        """Test health check responds within acceptable time"""
        start = time.time()
        response = client.get('/api/health')
        duration = time.time() - start
        
        assert response.status_code == 200
        assert duration < 1.0  # Should respond within 1 second
    
    def test_health_check_concurrent_requests(self, client):
        """Test health check under concurrent load"""
        def make_request():
            return client.get('/api/health')
        
        # Make 10 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # All should succeed
        assert all(r.status_code == 200 for r in results)


class TestAuthEndpointPerformance:
    """Performance tests for authentication endpoints"""
    
    def test_login_response_time(self, client):
        """Test login responds within acceptable time"""
        # Register first
        client.post('/api/auth/register',
                   json={'account': 'logintest', 'password': 'TestP@ss123'})
        
        start = time.time()
        response = client.post('/api/auth/login',
                              json={'account': 'logintest', 'password': 'TestP@ss123'})
        duration = time.time() - start
        
        assert response.status_code == 200
        assert duration < 2.0  # Login should complete within 2 seconds
    
    def test_token_verification_performance(self, client, auth_token):
        """Test token verification is fast"""
        headers = {'Authorization': f'Bearer {auth_token}'}
        
        start = time.time()
        response = client.get('/api/auth/me', headers=headers)
        duration = time.time() - start
        
        assert response.status_code == 200
        assert duration < 0.5  # Token verification should be fast


class TestDatabasePerformance:
    """Performance tests for database operations"""
    
    def test_database_query_performance(self, client):
        """Test database queries are optimized"""
        from acas_pro.core.database import DatabaseManager
        
        db = DatabaseManager()
        
        # Test simple query performance
        start = time.time()
        result = db.execute_one("SELECT 1 as test")
        duration = time.time() - start
        
        assert result is not None
        assert duration < 0.1  # Simple query should be very fast


# Benchmark tests (if pytest-benchmark is installed)
try:
    import pytest_benchmark
    
    def test_health_check_benchmark(benchmark, client):
        """Benchmark health check endpoint"""
        result = benchmark(client.get, '/api/health')
        assert result.status_code == 200
    
    def test_login_benchmark(benchmark, client):
        """Benchmark login endpoint"""
        # Register first (not part of benchmark)
        client.post('/api/auth/register',
                   json={'account': 'benchuser', 'password': 'BenchP@ss123'})
        
        def login():
            return client.post('/api/auth/login',
                              json={'account': 'benchuser', 'password': 'BenchP@ss123'})
        
        result = benchmark(login)
        assert result.status_code == 200

except ImportError:
    pass  # pytest-benchmark not installed


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
