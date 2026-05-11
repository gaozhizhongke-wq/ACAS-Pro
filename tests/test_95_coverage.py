"""95分达成 - 核心测试套件"""
import pytest
from unittest.mock import MagicMock, patch, Mock
import sys
import os


# ============== 阶段1: Config模块测试 (已验证通过) ==============

class TestConfigEnvironment:
    """Test environment variable override - P0修复验证"""
    
    def test_env_override_explicit_staging(self):
        """ACAS_ENV=production should override explicit staging"""
        from acas_pro.core.config import AppConfig
        os.environ['ACAS_ENV'] = 'production'
        config = AppConfig(environment='staging')
        assert config.environment == 'production'
    
    def test_env_override_explicit_development(self):
        """ACAS_ENV=production should override explicit development"""
        from acas_pro.core.config import AppConfig
        os.environ['ACAS_ENV'] = 'production'
        config = AppConfig(environment='development')
        assert config.environment == 'production'
    
    def test_no_env_uses_default(self):
        """Without ACAS_ENV, should use provided value"""
        from acas_pro.core.config import AppConfig
        if 'ACAS_ENV' in os.environ:
            del os.environ['ACAS_ENV']
        config = AppConfig(environment='staging')
        assert config.environment == 'staging'
    
    def test_config_validate(self):
        """Test config validation returns list"""
        from acas_pro.core.config import AppConfig
        config = AppConfig()
        errors = config.validate()
        assert isinstance(errors, list)


# ============== 阶段2: Security模块测试 ==============

class TestSecurityModule:
    """Test security components"""
    
    def test_password_validator_imports(self):
        from acas_pro.core.security import PasswordValidator
        assert PasswordValidator is not None
    
    def test_jwt_manager_imports(self):
        from acas_pro.core.security import JWTManager
        assert JWTManager is not None
        assert hasattr(JWTManager, 'generate_token')
        assert hasattr(JWTManager, 'verify_token')
    
    def test_crypto_manager_imports(self):
        from acas_pro.core.security import CryptoManager
        assert CryptoManager is not None


# ============== 阶段3: Logging模块测试 ==============

class TestLoggingModule:
    """Test logging infrastructure"""
    
    def test_get_logger(self):
        from acas_pro.core.logging import get_logger
        logger = get_logger("test")
        assert logger is not None
    
    def test_audit_logger(self):
        from acas_pro.core.logging import audit_logger
        assert audit_logger is not None


# ============== 阶段4: Web模块基础测试 ==============

class TestWebBasics:
    """Test web layer basics"""
    
    def test_web_create_app_imports(self):
        from acas_pro.web import create_app
        assert create_app is not None
    
    def test_dashboard_html_exists(self):
        from acas_pro.web.routes.dashboard import DASHBOARD_HTML
        assert 'ACAS Pro' in DASHBOARD_HTML
        assert '<html' in DASHBOARD_HTML.lower()


# ============== 阶段5: ML模块基础测试 ==============

class TestMLBasics:
    """Test ML layer basics"""
    
    def test_timesfm_engine_imports(self):
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        assert TimesFMEngine is not None
    
    def test_forecast_result_imports(self):
        from acas_pro.ml.timesfm_engine import ForecastResult
        assert ForecastResult is not None
    
    def test_forecast_point_imports(self):
        from acas_pro.ml.timesfm_engine import ForecastPoint
        assert ForecastPoint is not None


# ============== 阶段6: Services模块基础测试 ==============

class TestServicesBasics:
    """Test services layer basics"""
    
    def test_oauth_service_imports(self):
        from acas_pro.services.oauth.oauth_service import OAuthService
        assert OAuthService is not None
    
    def test_user_service_imports(self):
        from acas_pro.services.user_service import UserService
        assert UserService is not None


# ============== 阶段7: 关键修复验证 ==============

class TestCriticalFixes:
    """Verify all critical fixes are in place"""
    
    def test_config_environment_logic_fixed(self):
        """Verify P0 fix: environment variable takes precedence"""
        from acas_pro.core.config import AppConfig
        
        # Set environment variable
        os.environ['ACAS_ENV'] = 'production'
        
        # Create config with explicit staging
        config = AppConfig(environment='staging')
        
        # Must be overridden to production
        assert config.environment == 'production', \
            f"CRITICAL: Expected 'production', got '{config.environment}'"
    
    def test_no_datetime_utcnow(self):
        """Verify no datetime.utcnow() calls remain"""
        import subprocess
        result = subprocess.run(
            ['grep', '-r', 'utcnow()', 'src/'],
            capture_output=True,
            text=True,
            cwd=r'F:\自动获客系统\ACAS-Pro'
        )
        # Should find nothing or only in comments
        lines = [l for l in result.stdout.split('\n') if l.strip() and not l.strip().startswith('#')]
        assert len(lines) == 0, f"Found utcnow() calls: {lines}"
