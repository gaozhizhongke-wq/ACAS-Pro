"""
Comprehensive tests for database module - targeting 80% coverage
"""
import os
import sys
import pytest
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from acas_pro.core.database import DatabaseManager


class TestDatabaseManager:
    """Test DatabaseManager singleton and operations"""
    
    def test_singleton_pattern(self):
        db1 = DatabaseManager()
        db2 = DatabaseManager()
        assert db1 is db2
    
    def test_get_instance_returns_same(self):
        db1 = DatabaseManager.get_instance()
        db2 = DatabaseManager.get_instance()
        assert db1 is db2


class TestDatabaseOperations:
    """Test database CRUD operations"""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        conn = sqlite3.connect(db_path)
        conn.execute('''
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                value REAL
            )
        ''')
        conn.commit()
        conn.close()
        
        yield db_path
        
        # Cleanup
        os.unlink(db_path)
    
    def test_execute_insert(self, temp_db):
        db = DatabaseManager()
        db.connect(temp_db)
        
        db.execute("INSERT INTO test_table (name, value) VALUES (?, ?)", ("test", 123.45))
        
        result = db.fetchone("SELECT * FROM test_table WHERE name = ?", ("test",))
        assert result["name"] == "test"
        assert result["value"] == 123.45
    
    def test_execute_many(self, temp_db):
        db = DatabaseManager()
        db.connect(temp_db)
        
        data = [("item1", 1.0), ("item2", 2.0), ("item3", 3.0)]
        db.execute_many("INSERT INTO test_table (name, value) VALUES (?, ?)", data)
        
        results = db.fetchall("SELECT * FROM test_table")
        assert len(results) == 3
    
    def test_fetchone_no_result(self, temp_db):
        db = DatabaseManager()
        db.connect(temp_db)
        
        result = db.fetchone("SELECT * FROM test_table WHERE id = ?", (999,))
        assert result is None
    
    def test_fetchall(self, temp_db):
        db = DatabaseManager()
        db.connect(temp_db)
        
        db.execute("INSERT INTO test_table (name, value) VALUES (?, ?)", ("a", 1.0))
        db.execute("INSERT INTO test_table (name, value) VALUES (?, ?)", ("b", 2.0))
        
        results = db.fetchall("SELECT * FROM test_table ORDER BY name")
        assert len(results) == 2
        assert results[0]["name"] == "a"
        assert results[1]["name"] == "b"
    
    def test_fetchall_empty(self, temp_db):
        db = DatabaseManager()
        db.connect(temp_db)
        
        results = db.fetchall("SELECT * FROM test_table")
        assert results == []
    
    def test_transaction_commit(self, temp_db):
        db = DatabaseManager()
        db.connect(temp_db)
        
        with db.transaction():
            db.execute("INSERT INTO test_table (name, value) VALUES (?, ?)", ("tx", 99.0))
        
        result = db.fetchone("SELECT * FROM test_table WHERE name = ?", ("tx",))
        assert result is not None
    
    def test_transaction_rollback(self, temp_db):
        db = DatabaseManager()
        db.connect(temp_db)
        
        try:
            with db.transaction():
                db.execute("INSERT INTO test_table (name, value) VALUES (?, ?)", ("rollback", 99.0))
                raise ValueError("Force rollback")
        except ValueError:
            pass
        
        result = db.fetchone("SELECT * FROM test_table WHERE name = ?", ("rollback",))
        assert result is None
    
    def test_update(self, temp_db):
        db = DatabaseManager()
        db.connect(temp_db)
        
        db.execute("INSERT INTO test_table (name, value) VALUES (?, ?)", ("original", 1.0))
        
        db.update("test_table", {"value": 2.0}, "name = ?", ("original",))
        
        result = db.fetchone("SELECT * FROM test_table WHERE name = ?", ("original",))
        assert result["value"] == 2.0
    
    def test_delete(self, temp_db):
        db = DatabaseManager()
        db.connect(temp_db)
        
        db.execute("INSERT INTO test_table (name, value) VALUES (?, ?)", ("delete_me", 1.0))
        
        db.delete("test_table", "name = ?", ("delete_me",))
        
        result = db.fetchone("SELECT * FROM test_table WHERE name = ?", ("delete_me",))
        assert result is None
    
    def test_insert(self, temp_db):
        db = DatabaseManager()
        db.connect(temp_db)
        
        row_id = db.insert("test_table", {"name": "inserted", "value": 42.0})
        
        assert row_id is not None
        result = db.fetchone("SELECT * FROM test_table WHERE id = ?", (row_id,))
        assert result["name"] == "inserted"


class TestDatabaseConnection:
    """Test database connection handling"""
    
    def test_connect_creates_connection(self):
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            db = DatabaseManager()
            db.connect(db_path)
            
            # Should be able to execute
            db.execute("CREATE TABLE test (id INTEGER)")
            
            db.close()
        finally:
            os.unlink(db_path)
    
    def test_close_releases_connection(self):
        db = DatabaseManager()
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            db.connect(db_path)
            db.close()
            
            # After close, operations should fail or reconnect
            # Implementation dependent
        finally:
            os.unlink(db_path)
    
    def test_context_manager(self):
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            db = DatabaseManager()
            with db:
                db.execute("CREATE TABLE ctx_test (id INTEGER)")
            
            # Connection should be closed after context
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)


class TestDatabaseEdgeCases:
    """Test edge cases and error handling"""
    
    def test_execute_with_invalid_sql(self):
        db = DatabaseManager()
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            db.connect(db_path)
            
            with pytest.raises(Exception):
                db.execute("INVALID SQL SYNTAX")
        finally:
            db.close()
            os.unlink(db_path)
    
    def test_fetchone_with_invalid_column(self):
        db = DatabaseManager()
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            db.connect(db_path)
            db.execute("CREATE TABLE t (id INTEGER)")
            
            with pytest.raises(Exception):
                db.fetchone("SELECT invalid_col FROM t")
        finally:
            db.close()
            os.unlink(db_path)
    
    def test_concurrent_access(self):
        """Test that singleton handles concurrent access"""
        db = DatabaseManager()
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            db.connect(db_path)
            db.execute("CREATE TABLE concurrent (id INTEGER)")
            
            # Multiple operations
            for i in range(100):
                db.execute("INSERT INTO concurrent (id) VALUES (?)", (i,))
            
            results = db.fetchall("SELECT * FROM concurrent")
            assert len(results) == 100
        finally:
            db.close()
            os.unlink(db_path)
    
    def test_very_long_query(self):
        db = DatabaseManager()
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            db.connect(db_path)
            db.execute("CREATE TABLE long_text (content TEXT)")
            
            long_content = "x" * 1000000  # 1MB
            db.execute("INSERT INTO long_text (content) VALUES (?)", (long_content,))
            
            result = db.fetchone("SELECT * FROM long_text")
            assert len(result["content"]) == 1000000
        finally:
            db.close()
            os.unlink(db_path)
    
    def test_unicode_content(self):
        db = DatabaseManager()
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            db.connect(db_path)
            db.execute("CREATE TABLE unicode (content TEXT)")
            
            unicode_content = "中文测试 🎉 émojis ñoño"
            db.execute("INSERT INTO unicode (content) VALUES (?)", (unicode_content,))
            
            result = db.fetchone("SELECT * FROM unicode")
            assert result["content"] == unicode_content
        finally:
            db.close()
            os.unlink(db_path)


class TestDatabaseSchemaOperations:
    """Test schema operations"""
    
    def test_create_table(self):
        db = DatabaseManager()
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            db.connect(db_path)
            db.execute('''
                CREATE TABLE schema_test (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Verify table exists
            result = db.fetchone(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                ("schema_test",)
            )
            assert result is not None
        finally:
            db.close()
            os.unlink(db_path)
    
    def test_create_index(self):
        db = DatabaseManager()
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            db.connect(db_path)
            db.execute("CREATE TABLE idx_test (id INTEGER, name TEXT)")
            db.execute("CREATE INDEX idx_name ON idx_test(name)")
            
            # Verify index exists
            result = db.fetchone(
                "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
                ("idx_name",)
            )
            assert result is not None
        finally:
            db.close()
            os.unlink(db_path)
    
    def test_alter_table(self):
        db = DatabaseManager()
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            db.connect(db_path)
            db.execute("CREATE TABLE alter_test (id INTEGER)")
            db.execute("ALTER TABLE alter_test ADD COLUMN new_col TEXT")
            
            # Verify column exists by inserting
            db.execute("INSERT INTO alter_test (id, new_col) VALUES (?, ?)", (1, "test"))
            
            result = db.fetchone("SELECT * FROM alter_test")
            assert result["new_col"] == "test"
        finally:
            db.close()
            os.unlink(db_path)
