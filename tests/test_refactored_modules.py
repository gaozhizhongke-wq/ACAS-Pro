"""Test Refactored Modules - Architecture v2"""
import pytest
from unittest.mock import MagicMock, patch, Mock


class TestSecurityRefactored:
    """Test refactored security module"""
    
    def test_password_validator_class(self):
        from acas_pro.core.security import PasswordValidator
        validator = PasswordValidator()
        assert validator is not None
    
    def test_password_hasher_class(self):
        from acas_pro.core.security import PasswordHasher
        hasher = PasswordHasher()
        assert hasher is not None
    
    def test_jwt_manager_class(self):
        from acas_pro.core.security import JWTManager
        manager = JWTManager()
        assert manager is not None
    
    def test_session_manager_class(self):
        from acas_pro.core.security import SessionManager
        manager = SessionManager()
        assert manager is not None
    
    def test_crypto_manager_class(self):
        from acas_pro.core.security import CryptoManager
        manager = CryptoManager()
        assert manager is not None
    
    def test_lazy_getters_exist(self):
        from acas_pro.core.security import (
            get_password_validator, get_password_hasher,
            get_jwt_manager, get_session_manager, get_crypto_manager
        )
        assert callable(get_password_validator)
        assert callable(get_password_hasher)
        assert callable(get_jwt_manager)
        assert callable(get_session_manager)
        assert callable(get_crypto_manager)


class TestDatabaseRefactored:
    """Test refactored database module"""
    
    def test_database_manager_class(self):
        from acas_pro.core.database import DatabaseManager
        db = DatabaseManager()
        assert db is not None
    
    def test_get_db_exists(self):
        from acas_pro.core.database import get_db
        assert callable(get_db)


class TestTimesFMRefactored:
    """Test refactored TimesFM engine"""
    
    def test_timesfm_engine_class(self):
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        engine = TimesFMEngine()
        assert engine is not None
    
    def test_forecast_point_class(self):
        from acas_pro.ml.timesfm_engine import ForecastPoint
        from datetime import datetime, timezone
        point = ForecastPoint(
            timestamp=datetime.now(timezone.utc),
            value=100.0,
            lower_bound=90.0,
            upper_bound=110.0,
            confidence=0.95
        )
        assert point.value == 100.0
    
    def test_forecast_result_class(self):
        from acas_pro.ml.timesfm_engine import ForecastResult, ForecastPoint
        from datetime import datetime, timezone
        
        result = ForecastResult(
            product_id="test",
            forecast=[],
            trend_direction="up",
            trend_magnitude=5.0,
            seasonality_detected=True,
            model_version="v1",
            generated_at=datetime.now(timezone.utc)
        )
        assert result.product_id == "test"


class TestAllModulesImport:
    """Test all modules can be imported after refactoring"""
    
    def test_core_modules(self):
        from acas_pro.core import config, security, database, logging
        assert config is not None
        assert security is not None
        assert database is not None
        assert logging is not None
    
    def test_ml_modules(self):
        from acas_pro.ml import timesfm_engine, inventory_optimizer
        assert timesfm_engine is not None
        assert inventory_optimizer is not None
    
    def test_web_modules(self):
        from acas_pro.web import routes
        assert routes is not None
