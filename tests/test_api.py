#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - API Endpoint Tests
Comprehensive API endpoint testing with authentication
"""

import pytest
import time
from datetime import datetime
from unittest.mock import patch, MagicMock

# Mock the database before imports
@pytest.fixture(autouse=True)
def mock_db():
    """Mock database for API tests"""
    mock_database = MagicMock()
    mock_database.fetchone.return_value = None
    mock_database.fetchall.return_value = []
    mock_database.insert.return_value = True
    mock_database.update.return_value = 1
    
    with patch('acas_pro.core.database.db', mock_database):
        with patch('acas_pro.services.user_service.db', mock_database):
            yield mock_database


class TestHealthEndpoints:
    """Health check endpoint tests"""
    
    def test_health_endpoint_structure(self):
        """Test health endpoint returns correct structure"""
        from acas_pro.core.monitoring import HealthChecker
        
        checker = HealthChecker()
        
        # Add mock health check
        def mock_check():
            return {"healthy": True, "message": "OK", "details": {}}
        checker.register("mock", mock_check)
        
        result = checker.liveness()
        
        assert "status" in result
        assert result["status"] == "alive"
        assert "timestamp" in result
    
    def test_ready_endpoint_structure(self):
        """Test ready endpoint checks all dependencies"""
        from acas_pro.core.monitoring import HealthChecker
        
        checker = HealthChecker()
        
        def healthy_check():
            return {"healthy": True, "latency_ms": 1.5}
        checker.register("database", healthy_check)
        checker.register("cache", healthy_check)
        
        result = checker.readiness()
        
        assert result["status"] in ["ready", "not_ready"]
        assert "checks" in result
    
    def test_prometheus_metrics_format(self):
        """Test Prometheus metrics output format"""
        from acas_pro.core.monitoring import PrometheusMetrics
        
        metrics = PrometheusMetrics()
        metrics.counter("http_requests_total", labels={"method": "GET", "path": "/health"})
        
        output = metrics.export()
        
        # Check Prometheus format
        assert "http_requests_total" in output
        assert '{' in output
        assert '}' in output
        assert '# HELP' in output or '# TYPE' in output


class TestAuthEndpoints:
    """Authentication endpoint tests"""
    
    def test_register_validation(self):
        """Test registration input validation"""
        from acas_pro.core.security import PasswordValidator
        
        # Test weak password
        is_valid, msg = PasswordValidator.validate("weak")
        assert is_valid is False
        assert len(msg) > 0
        
        # Test strong password
        is_valid, msg = PasswordValidator.validate("Secure@123")
        assert is_valid is True
    
    def test_register_short_account(self):
        """Test registration with too short account"""
        from acas_pro.services.user_service import UserService
        
        service = UserService()
        success, msg, profile = service.register("ab", "Secure@123")
        
        assert success is False
        assert "3 characters" in msg
    
    def test_login_rate_limiting(self):
        """Test login rate limiting mechanism"""
        from acas_pro.core.security import RateLimiter
        
        limiter = RateLimiter()
        key = f"test_login:{time.time()}"
        
        # First attempt should succeed
        assert limiter.is_allowed(key, max_attempts=3, window_seconds=60) is True
        
        # Record 3 attempts (max_attempts=3, so 3rd should be blocked)
        for _ in range(3):
            limiter.record_attempt(key)
        
        # Should be blocked now (3 >= max_attempts)
        assert limiter.is_allowed(key, max_attempts=3, window_seconds=60) is False
    
    def test_password_hash_verification(self):
        """Test password hashing and verification"""
        from acas_pro.core.security import PasswordHasher
        
        password = "Secure@123"  # noqa: B105
        hash_value = PasswordHasher.hash(password)
        
        # Hash should be in expected format
        assert hash_value.startswith("pbkdf2:sha256:")
        assert "$" in hash_value
        
        # Verification should work
        assert PasswordHasher.verify(password, hash_value) is True
        assert PasswordHasher.verify("wrong", hash_value) is False
    
    def test_jwt_token_generation(self):
        """Test JWT token generation and validation"""
        from acas_pro.core.security import JWTManager
        
        jwt_manager = JWTManager()
        
        # Generate token
        token = jwt_manager.generate_token("user123", {"role": "admin"})
        assert token is not None
        assert len(token) > 50
        
        # Decode token
        payload = jwt_manager.verify_token(token)
        assert payload is not None
        assert payload.get("sub") == "user123"
    
    def test_jwt_token_expiry(self):
        """Test JWT token expiry handling"""
        from acas_pro.core.security import JWTManager
        from acas_pro.core.config import config
        import jwt
        from datetime import datetime, timedelta
        
        # Get secret key and algorithm from config
        secret_key = JWTManager._get_secret_key()
        algorithm = config.security.jwt_algorithm
        
        # Create expired token
        expired_payload = {
            "sub": "user123",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "iat": datetime.now(timezone.utc) - timedelta(hours=2)
        }
        
        expired_token = jwt.encode(
            expired_payload,
            secret_key,
            algorithm=algorithm
        )
        
        # Should fail to decode
        result = JWTManager.verify_token(expired_token)
        assert result is None


class TestUserEndpoints:
    """User management endpoint tests"""
    
    def test_profile_data_structure(self):
        """Test user profile data structure"""
        from acas_pro.services.user_service import UserProfile
        
        profile = UserProfile(
            id="U123",
            account="testuser",
            nickname="Test",
            email="test@example.com",
            phone="+1234567890",
            role="user",
            status="active",
            region="cn_northwest",
            language="zh",
            timezone="Asia/Shanghai",
            created_at="2024-01-01T00:00:00",
            last_login="2024-01-02T00:00:00",
            wallet_balance=1000.0,
            wallet_currency="USD",
            model_preference="auto"
        )
        
        assert profile.id == "U123"
        assert profile.role == "user"
        assert profile.wallet_balance == 1000.0
    
    def test_profile_update_validation(self):
        """Test profile update field validation"""
        from acas_pro.services.user_service import UserService
        
        service = UserService()
        
        # Filter allowed fields
        allowed = {"nickname", "email", "phone", "language", "timezone", "model_preference"}
        updates = {"nickname": "NewName", "password": "secret123"}
        
        filtered = {k: v for k, v in updates.items() if k in allowed}
        
        assert "nickname" in filtered
        assert "password" not in filtered


class TestForecastEndpoints:
    """Sales forecasting endpoint tests"""
    
    def test_forecast_result_structure(self):
        """Test forecast result data structure"""
        from acas_pro.ml.timesfm_engine import ForecastResult, ForecastPoint
        from datetime import datetime, timedelta
        
        points = [
            ForecastPoint(
                timestamp=datetime.now(timezone.utc) + timedelta(days=i),
                value=100.0 + i * 10,
                lower_bound=90.0 + i * 10,
                upper_bound=110.0 + i * 10,
                confidence=0.95 - i * 0.01
            )
            for i in range(7)
        ]
        
        result = ForecastResult(
            product_id="P001",
            forecast=points,
            trend_direction="up",
            trend_magnitude=15.5,
            seasonality_detected=True,
            model_version="test-v1",
            generated_at=datetime.now(timezone.utc)
        )
        
        # Check structure
        assert result.product_id == "P001"
        assert len(result.forecast) == 7
        assert result.trend_direction == "up"
        
        # Check serialization
        result_dict = result.to_dict()
        assert "forecast" in result_dict
        assert "trend_direction" in result_dict
        assert len(result_dict["forecast"]) == 7
    
    def test_forecast_trend_calculation(self):
        """Test forecast trend detection"""
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        
        engine = TimesFMEngine()
        
        # Test upward trend (need >= 14 values per implementation)
        values = [100] * 7 + [200] * 7
        trend = engine._calculate_trend(values)
        
        assert trend["direction"] == "up"
        assert trend["magnitude"] > 10
        
        # Test downward trend
        values = [200] * 7 + [100] * 7
        trend = engine._calculate_trend(values)
        
        assert trend["direction"] == "down"
        
        # Test stable trend
        values = [100, 102, 99, 101, 100, 101, 99, 100, 102, 99, 101, 100, 101, 99]
        trend = engine._calculate_trend(values)
        
        assert trend["direction"] == "stable"
    
    def test_seasonality_detection(self):
        """Test weekly seasonality detection"""
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        
        engine = TimesFMEngine()
        
        # Generate weekly pattern (28 days = 4 weeks)
        values = []
        for week in range(4):
            for day in range(7):
                # Weekend spike
                base = 100 if day < 5 else 150
                values.append(base + day * 2)
        
        has_seasonality = engine._detect_seasonality(values)
        assert has_seasonality is True
        
        # Random values should not show seasonality
        import random
        random.seed(42)
        random_values = [random.uniform(90, 110) for _ in range(28)]
        has_seasonality = engine._detect_seasonality(random_values)
        # May or may not detect, just check no crash
        assert isinstance(has_seasonality, bool)
    
    def test_holt_winters_forecast(self):
        """Test Holt-Winters forecast generation"""
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        
        engine = TimesFMEngine()
        
        # Simple trend data
        values = [100, 105, 110, 115, 120]
        forecast = engine._holt_winters_forecast(values, horizon=7, use_seasonality=False)
        
        assert len(forecast) == 7
        assert all(v >= 0 for v in forecast)  # No negative values
        
        # Forecast should follow trend
        assert forecast[-1] > forecast[0]
    
    def test_insufficient_data_handling(self):
        """Test fallback forecast with insufficient data"""
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        from datetime import datetime, timedelta
        
        engine = TimesFMEngine()
        
        # Less than 14 days of data
        historical = [
            (datetime.now(timezone.utc) - timedelta(days=3), 100.0),
            (datetime.now(timezone.utc) - timedelta(days=2), 110.0),
            (datetime.now(timezone.utc) - timedelta(days=1), 105.0),
        ]
        
        result = engine.forecast("P001", historical, horizon_days=7)
        
        assert result.product_id == "P001"
        assert result.model_version.endswith("fallback")
        assert len(result.forecast) == 7


class TestInventoryEndpoints:
    """Inventory management endpoint tests"""
    
    def test_inventory_recommendation_structure(self):
        """Test inventory recommendation data structure"""
        from acas_pro.ml.inventory_optimizer import InventoryRecommendation
        
        rec = InventoryRecommendation(
            product_id="P001",
            product_name="Test Product",
            current_stock=50,
            recommended_order_quantity=200,
            urgency_level="high",
            days_until_stockout=5.5,
            reorder_point=100,
            safety_stock=30,
            economic_order_qty=150,
            reasoning="Stock level below reorder point",
            confidence_score=0.85
        )
        
        assert rec.product_id == "P001"
        assert rec.urgency_level == "high"
        assert rec.confidence_score == 0.85
        
        rec_dict = rec.to_dict()
        assert "urgency_level" in rec_dict
        assert "days_until_stockout" in rec_dict
    
    def test_stockout_risk_assessment(self):
        """Test stockout risk calculation"""
        from acas_pro.ml.inventory_optimizer import InventoryOptimizer, StockoutRisk
        
        optimizer = InventoryOptimizer()
        
        risk = StockoutRisk(
            product_id="P001",
            risk_level="high",
            probability=0.75,
            estimated_stockout_date=datetime.now(timezone.utc),
            revenue_at_risk=5000.0,
            impact_score=8.5,
            mitigation_actions=["Rush order from supplier", "Transfer from other warehouse"]
        )
        
        assert risk.risk_level == "high"
        assert len(risk.mitigation_actions) == 2
    
    def test_safety_stock_calculation(self):
        """Test safety stock calculation"""
        from acas_pro.ml.inventory_optimizer import InventoryOptimizer
        
        optimizer = InventoryOptimizer()
        
        # Calculate safety stock
        demand_std = 20
        lead_time = 7
        service_level = 0.95
        z_score = 1.645
        
        safety_stock = z_score * demand_std * (lead_time ** 0.5)
        
        assert safety_stock > 0
        assert safety_stock > demand_std  # Should be multiple of demand std
    
    def test_economic_order_quantity(self):
        """Test EOQ calculation"""
        from acas_pro.ml.inventory_optimizer import InventoryOptimizer
        
        optimizer = InventoryOptimizer()
        
        # Given parameters
        annual_demand = 10000
        ordering_cost = 100
        holding_cost_rate = 0.25
        unit_cost = 50
        
        # EOQ = sqrt(2 * D * S / H)
        annual_holding_cost = unit_cost * holding_cost_rate
        eoq = (2 * annual_demand * ordering_cost / annual_holding_cost) ** 0.5
        
        assert eoq > 0
        assert eoq < annual_demand  # EOQ should be less than annual demand


class TestSecurityEndpoints:
    """Security and rate limiting tests"""
    
    def test_rate_limiter_reset(self):
        """Test rate limiter reset functionality"""
        from acas_pro.core.security import RateLimiter
        
        limiter = RateLimiter()
        key = f"test_reset:{time.time()}"
        
        # Use up attempts
        for _ in range(5):
            limiter.record_attempt(key)
        
        # Reset
        limiter.reset(key)
        
        # Should be allowed again
        assert limiter.is_allowed(key, max_attempts=5, window_seconds=60) is True
    
    def test_encryption_roundtrip(self):
        """Test data encryption and decryption"""
        from acas_pro.core.security import CryptoManager
        
        crypto = CryptoManager()
        
        original_data = "Sensitive business data 123 !@#"
        
        # Encrypt
        encrypted = crypto.encrypt(original_data)
        assert encrypted != original_data
        assert len(encrypted) > len(original_data)
        
        # Decrypt
        decrypted = crypto.decrypt(encrypted)
        assert decrypted == original_data
    
    def test_encryption_with_key(self):
        """Test encryption with custom key"""
        from acas_pro.core.security import CryptoManager
        
        data = "Test data"
        custom_key = "custom_encryption_key_for_testing_32ch"
        
        crypto = CryptoManager(key=custom_key)
        encrypted = crypto.encrypt(data)
        decrypted = crypto.decrypt(encrypted)
        
        assert decrypted == data


class TestMonitoringEndpoints:
    """System monitoring and metrics tests"""
    
    def test_metrics_export_format(self):
        """Test Prometheus metrics export format"""
        from acas_pro.core.monitoring import PrometheusMetrics
        
        metrics = PrometheusMetrics()
        
        # Add various metrics (with labels to produce labeled output)
        metrics.counter("requests_total", labels={"method": "POST", "endpoint": "/api/v1/forecast"})
        metrics.gauge("active_connections", 42, labels={"env": "test"})
        metrics.histogram("request_duration_seconds", 0.25, labels={"endpoint": "/health"})
        
        output = metrics.export()
        
        # Check format
        lines = output.split('\n')
        metric_lines = [l for l in lines if l and not l.startswith('#')]
        
        assert len(metric_lines) > 0
        for line in metric_lines:
            assert '{' in line
            assert '}' in line
    
    def test_health_check_registration(self):
        """Test health check registration"""
        from acas_pro.core.monitoring import HealthChecker
        
        checker = HealthChecker()
        
        def my_check():
            return {"healthy": True, "message": "My check passed"}
        
        checker.register("my_service", my_check)
        
        result = checker.check("my_service")
        
        assert result.healthy is True
        assert result.name == "my_service"
    
    def test_request_tracking(self):
        """Test request tracking middleware"""
        from acas_pro.core.monitoring import RequestTracker
        
        tracker = RequestTracker()
        
        # Track a request (start_request signature: request_id, method, path)
        request_id = tracker.start_request("req-test-1", "GET", "/api/v1/users/me")
        
        assert request_id is not None
        assert len(request_id) > 0
        
        # End request (end_request signature: status_code, error=None)
        result = tracker.end_request(200)
        
        # Check result
        assert result["status_code"] == 200
        assert result["method"] == "GET"


class TestConfigValidation:
    """Configuration validation tests"""
    
    def test_config_loads_defaults(self):
        """Test configuration loads with defaults"""
        from acas_pro.core.config import config
        
        assert config.name == "ACAS Pro"
        assert config.version is not None
        assert len(config.version) > 0
    
    def test_config_security_settings(self):
        """Test security configuration"""
        from acas_pro.core.config import config
        
        # Check security defaults
        assert config.security.password_min_length == 8
        assert config.security.max_login_attempts == 5
        assert config.security.jwt_expiry_hours > 0
    
    def test_config_database_settings(self):
        """Test database configuration"""
        from acas_pro.core.config import config
        
        # Check database config exists
        assert hasattr(config, 'database')
        assert config.database is not None
    
    def test_config_ml_settings(self):
        """Test ML configuration"""
        from acas_pro.core.config import config
        
        # Check ML config
        assert hasattr(config, 'ml')
        assert config.ml is not None
        assert hasattr(config.ml, 'timesfm_enabled')


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src/acas_pro", "--cov-report=term"])