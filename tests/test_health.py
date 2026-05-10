"""Health check tests for ACAS Pro"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from acas_pro.web.health import HealthChecker, HealthStatus, HealthCheckResult


class TestHealthChecker:
    """Test health checker functionality"""
    
    @pytest.fixture
    def checker(self):
        return HealthChecker()
    
    def test_check_all_returns_dict(self, checker):
        """Test check_all returns proper structure"""
        result = checker.check_all()
        
        assert isinstance(result, dict)
        assert 'status' in result
        assert 'timestamp' in result
        assert 'version' in result
        assert 'checks' in result
    
    def test_health_status_values(self, checker):
        """Test health status is valid"""
        result = checker.check_all()
        
        assert result['status'] in ['healthy', 'degraded', 'unhealthy']
    
    def test_checks_list_not_empty(self, checker):
        """Test that checks list is not empty"""
        result = checker.check_all()
        
        assert len(result['checks']) > 0
    
    def test_each_check_has_required_fields(self, checker):
        """Test each check has required fields"""
        result = checker.check_all()
        
        for check in result['checks']:
            assert 'name' in check
            assert 'status' in check
            assert 'response_time_ms' in check
            assert 'message' in check
    
    def test_database_check_exists(self, checker):
        """Test that database check exists"""
        result = checker.check_all()
        
        check_names = [c['name'] for c in result['checks']]
        assert 'database' in check_names
    
    def test_config_check_exists(self, checker):
        """Test that configuration check exists"""
        result = checker.check_all()
        
        check_names = [c['name'] for c in result['checks']]
        assert 'configuration' in check_names
    
    def test_disk_check_exists(self, checker):
        """Test that disk space check exists"""
        result = checker.check_all()
        
        check_names = [c['name'] for c in result['checks']]
        assert 'disk_space' in check_names


class TestHealthStatus:
    """Test HealthStatus enum"""
    
    def test_status_values(self):
        """Test status enum values"""
        assert HealthStatus.HEALTHY.value == 'healthy'
        assert HealthStatus.DEGRADED.value == 'degraded'
        assert HealthStatus.UNHEALTHY.value == 'unhealthy'


class TestHealthCheckResult:
    """Test HealthCheckResult dataclass"""
    
    def test_result_creation(self):
        """Test creating a health check result"""
        result = HealthCheckResult(
            name='test_check',
            status=HealthStatus.HEALTHY,
            response_time_ms=10.5,
            message='Test passed'
        )
        
        assert result.name == 'test_check'
        assert result.status == HealthStatus.HEALTHY
        assert result.response_time_ms == 10.5
        assert result.message == 'Test passed'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
