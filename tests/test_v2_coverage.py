"""Test v2 modules coverage"""
import pytest
import tempfile
import os


class TestDatabaseV2:
    """Test database v2"""
    
    def test_database_manager_init(self):
        from acas_pro.core.database_v2 import DatabaseManager
        db = DatabaseManager()
        assert db is not None
    
    def test_database_execute(self):
        from acas_pro.core.database_v2 import DatabaseManager
        db = DatabaseManager()
        
        # Create table
        db.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, name TEXT)")
        
        # Insert
        db.execute("INSERT INTO test (name) VALUES (?)", ("test_name",))
        
        # Fetch
        result = db.fetchone("SELECT * FROM test WHERE name = ?", ("test_name",))
        assert result is not None
        assert result['name'] == 'test_name'
    
    def test_database_fetchall(self):
        from acas_pro.core.database_v2 import DatabaseManager
        db = DatabaseManager()
        
        db.execute("CREATE TABLE IF NOT EXISTS test2 (id INTEGER PRIMARY KEY, name TEXT)")
        db.execute("INSERT INTO test2 (name) VALUES (?)", ("item1",))
        db.execute("INSERT INTO test2 (name) VALUES (?)", ("item2",))
        
        results = db.fetchall("SELECT * FROM test2")
        assert len(results) >= 2
    
    def test_database_health_check(self):
        from acas_pro.core.database_v2 import DatabaseManager
        db = DatabaseManager()
        
        health = db.health_check()
        assert 'status' in health
    
    def test_database_close(self):
        from acas_pro.core.database_v2 import DatabaseManager
        db = DatabaseManager()
        db.close()
        # Should not raise


class TestLoggingV2:
    """Test logging v2"""
    
    def test_pii_redactor(self):
        from acas_pro.core.logging_v2 import PIIRedactor
        
        data = {
            'username': 'test',
            'password': 'secret123',
            'email': 'test@example.com'
        }
        
        redacted = PIIRedactor.redact(data)
        assert redacted['password'] == '***REDACTED***'
        assert redacted['username'] == 'test'
    
    def test_logger_factory(self):
        from acas_pro.core.logging_v2 import LoggerFactory
        factory = LoggerFactory()
        assert factory is not None
    
    def test_get_logger(self):
        from acas_pro.core.logging_v2 import get_logger
        logger = get_logger("test")
        assert logger is not None
    
    def test_structured_formatter(self):
        from acas_pro.core.logging_v2 import StructuredFormatter
        import logging
        
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO,
            pathname="", lineno=0,
            msg="test message", args=(),
            exc_info=None
        )
        
        output = formatter.format(record)
        assert 'test message' in output


class TestDIContainerV2:
    """Test DI container v2"""
    
    def test_container_singleton(self):
        from acas_pro.core.di_container import DIContainer
        container = DIContainer()
        
        # Register
        container.register_singleton(str, lambda: "singleton_value")
        
        # Resolve multiple times - should be same
        val1 = container.resolve(str)
        val2 = container.resolve(str)
        assert val1 == val2 == "singleton_value"
    
    def test_container_factory(self):
        from acas_pro.core.di_container import DIContainer
        container = DIContainer()
        
        counter = [0]
        def factory(c):
            counter[0] += 1
            return f"instance_{counter[0]}"
        
        container.register_factory(str, factory)
        
        # Factories return cached singletons by default
        val1 = container.resolve(str)
        val2 = container.resolve(str)
        assert val1 == val2
    
    def test_container_clear(self):
        from acas_pro.core.di_container import DIContainer
        container = DIContainer()
        
        container.register_singleton(str, lambda: "test")
        container.clear()
        
        assert not container.is_registered(str)


class TestIntegrationV2:
    """Integration tests for v2 modules"""
    
    def test_full_stack(self):
        from acas_pro.core.config_v2 import AppConfig
        from acas_pro.core.security_v2 import PasswordHasher
        from acas_pro.core.database_v2 import DatabaseManager
        
        # Create config
        config = AppConfig()
        config.security.secret_key = "test-secret"
        
        # Create hasher
        hasher = PasswordHasher(config.security)
        password_hash = hasher.hash("password123")
        
        # Create database
        db = DatabaseManager(config.database)
        db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, password TEXT)")
        db.execute("INSERT INTO users (password) VALUES (?)", (password_hash,))
        
        # Verify
        result = db.fetchone("SELECT password FROM users LIMIT 1")
        assert hasher.verify("password123", result['password'])
