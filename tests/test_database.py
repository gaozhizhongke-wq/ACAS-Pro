#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Database Tests
Tests for database operations, transactions, and concurrency
"""

import pytest
from datetime import datetime
from unittest.mock import patch

from acas_pro.core.database import DatabaseManager


class TestDatabaseManager:
    """Database manager tests"""
    
    def test_insert_and_fetch(self, temp_db):
        """Test insert and fetch operations"""
        user_id = "U_TEST_001"
        now = datetime.utcnow().isoformat()
        
        # Insert user
        temp_db.insert("users", {
            "id": user_id,
            "account_type": "email",
            "account": "test@example.com",
            "password_hash": "test_hash",
            "nickname": "Test User",
            "role": "user",
            "status": "active",
            "region": "global",
            "language": "zh",
            "timezone": "UTC",
            "created_at": now
        })
        
        # Fetch user
        user = temp_db.fetchone("SELECT * FROM users WHERE id = ?", (user_id,))
        
        assert user is not None
        assert user['id'] == user_id
        assert user['account'] == "test@example.com"
        assert user['nickname'] == "Test User"
    
    def test_update(self, temp_db):
        """Test update operation"""
        user_id = "U_TEST_002"
        now = datetime.utcnow().isoformat()
        
        # Insert user
        temp_db.insert("users", {
            "id": user_id,
            "account_type": "email",
            "account": "update@example.com",
            "password_hash": "test_hash",
            "nickname": "Before Update",
            "role": "user",
            "status": "active",
            "region": "global",
            "language": "zh",
            "timezone": "UTC",
            "created_at": now
        })
        
        # Update
        count = temp_db.update(
            "users",
            {"nickname": "After Update"},
            "id = ?",
            (user_id,)
        )
        
        assert count == 1
        
        # Verify
        user = temp_db.fetchone("SELECT nickname FROM users WHERE id = ?", (user_id,))
        assert user['nickname'] == "After Update"
    
    def test_delete(self, temp_db):
        """Test delete operation"""
        user_id = "U_TEST_003"
        now = datetime.utcnow().isoformat()
        
        # Insert user
        temp_db.insert("users", {
            "id": user_id,
            "account_type": "email",
            "account": "delete@example.com",
            "password_hash": "test_hash",
            "nickname": "To Delete",
            "role": "user",
            "status": "active",
            "region": "global",
            "language": "zh",
            "timezone": "UTC",
            "created_at": now
        })
        
        # Delete
        count = temp_db.delete("users", "id = ?", (user_id,))
        assert count == 1
        
        # Verify
        user = temp_db.fetchone("SELECT * FROM users WHERE id = ?", (user_id,))
        assert user is None
    
    def test_fetchall(self, temp_db):
        """Test fetchall operation"""
        now = datetime.utcnow().isoformat()
        
        # Insert multiple users
        for i in range(5):
            temp_db.insert("users", {
                "id": f"U_MULTI_{i:03d}",
                "account_type": "email",
                "account": f"multi{i}@example.com",
                "password_hash": "test_hash",
                "nickname": f"User {i}",
                "role": "user",
                "status": "active",
                "region": "global",
                "language": "zh",
                "timezone": "UTC",
                "created_at": now
            })
        
        # Fetch all
        users = temp_db.fetchall("SELECT * FROM users WHERE id LIKE 'U_MULTI_%' ORDER BY id")
        
        assert len(users) == 5
        assert users[0]['nickname'] == "User 0"
        assert users[4]['nickname'] == "User 4"
    
    def test_transaction_commit(self, temp_db):
        """Test transaction commits correctly"""
        user_id = "U_TX_001"
        now = datetime.utcnow().isoformat()
        
        with temp_db.transaction() as conn:
            conn.execute("""
                INSERT INTO users (id, account_type, account, password_hash, nickname, role, status, region, language, timezone, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, "email", "tx@example.com", "hash", "TX User", "user", "active", "global", "zh", "UTC", now))
        
        # Should be committed
        user = temp_db.fetchone("SELECT * FROM users WHERE id = ?", (user_id,))
        assert user is not None
    
    def test_transaction_rollback(self, temp_db):
        """Test transaction rolls back on error"""
        user_id = "U_TX_002"
        now = datetime.utcnow().isoformat()
        
        try:
            with temp_db.transaction() as conn:
                conn.execute("""
                    INSERT INTO users (id, account_type, account, password_hash, nickname, role, status, region, language, timezone, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (user_id, "email", "rollback@example.com", "hash", "Rollback User", "user", "active", "global", "zh", "UTC", now))
                
                # Raise error to trigger rollback
                raise Exception("Simulated error")
        except Exception:
            pass
        
        # Should NOT exist (rolled back)
        user = temp_db.fetchone("SELECT * FROM users WHERE id = ?", (user_id,))
        assert user is None


class TestAuditLog:
    """Audit log tests"""
    
    def test_audit_log_insert(self, temp_db):
        """Test audit log is written"""
        import uuid
        now = datetime.utcnow().isoformat()
        unique_event = f"TEST_EVENT_{uuid.uuid4().hex[:8]}"
        
        temp_db.insert("audit_log", {
            "timestamp": now,
            "event_type": unique_event,
            "user_id": "U001",
            "ip_address": "127.0.0.1",
            "details": '{"test": true}',
            "severity": "info"
        })
        
        logs = temp_db.fetchall(f"SELECT * FROM audit_log WHERE event_type = '{unique_event}'")
        assert len(logs) == 1
        assert logs[0]['user_id'] == "U001"
