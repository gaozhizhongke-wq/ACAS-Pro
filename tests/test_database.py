"""Database tests for ACAS Pro"""
import pytest
import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from acas_pro.core.database import DatabaseManager


class TestDatabaseManager:
    """Test DatabaseManager functionality"""
    
    @pytest.fixture
    def db(self):
        """Create a temporary database for testing"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        db = DatabaseManager(f"sqlite:///{db_path}")
        yield db
        
        # Cleanup
        try:
            os.unlink(db_path)
        except:
            pass
    
    def test_database_connection(self, db):
        """Test database connection works"""
        result = db.execute_one("SELECT 1 as test")
        assert result is not None
        assert result['test'] == 1
    
    def test_execute_one(self, db):
        """Test execute_one method"""
        result = db.execute_one("SELECT 1 as col1, 2 as col2")
        assert result['col1'] == 1
        assert result['col2'] == 2
    
    def test_execute_many(self, db):
        """Test execute_many method"""
        results = db.execute_many("SELECT 1 as col UNION ALL SELECT 2")
        assert len(results) == 2
        assert results[0]['col'] == 1
        assert results[1]['col'] == 2
    
    def test_insert_and_select(self, db):
        """Test insert and select operations"""
        # Create test table
        db.execute_write("""
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        """)
        
        # Insert
        db.insert('test_table', {'name': 'Test Name'})
        
        # Select
        result = db.execute_one("SELECT * FROM test_table WHERE name = ?", ('Test Name',))
        assert result is not None
        assert result['name'] == 'Test Name'
    
    def test_update(self, db):
        """Test update method"""
        # Create test table
        db.execute_write("""
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                value INTEGER
            )
        """)
        
        # Insert
        db.insert('test_table', {'name': 'Test', 'value': 100})
        
        # Update with WHERE clause
        db.update('test_table', {'value': 200}, 'name = ?', ('Test',))
        
        # Verify
        result = db.execute_one("SELECT value FROM test_table WHERE name = 'Test'")
        assert result['value'] == 200
    
    def test_delete(self, db):
        """Test delete method"""
        # Create test table
        db.execute_write("""
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        """)
        
        # Insert
        db.insert('test_table', {'name': 'ToDelete'})
        
        # Delete
        db.delete('test_table', 'name = ?', ('ToDelete',))
        
        # Verify
        result = db.execute_one("SELECT * FROM test_table WHERE name = 'ToDelete'")
        assert result is None
    
    def test_transaction(self, db):
        """Test transaction support"""
        # Create test table
        db.execute_write("""
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                value INTEGER
            )
        """)
        
        # Transaction that commits
        with db.transaction() as txn:
            txn.execute("INSERT INTO test_table (value) VALUES (?)", (100,))
        
        result = db.execute_one("SELECT * FROM test_table")
        assert result is not None
        assert result['value'] == 100


class TestDatabaseHealth:
    """Test database health checks"""
    
    def test_health_check(self):
        """Test database health check"""
        db = DatabaseManager()
        health = db.health_check()
        assert 'status' in health
        assert health['status'] in ['healthy', 'unhealthy']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
