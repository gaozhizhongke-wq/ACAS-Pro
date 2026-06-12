# -*- coding: utf-8 -*-
"""Tests for DatabaseManager.transaction() context manager."""
import pytest
from unittest.mock import MagicMock, patch
import sys

sys.path.insert(0, 'src')


class TestDatabaseManagerTransaction:
    """Test suite for DatabaseManager.transaction() context manager."""

    @patch('acas_pro.core.database._get_logger')
    def test_transaction_commit_on_success(self, mock_logger):
        """Transaction should commit when no exception occurs."""
        from acas_pro.core.database import DatabaseManager

        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Create instance without calling __init__
        db = object.__new__(DatabaseManager)
        db._is_postgres = True
        db._pool = mock_pool
        db._db_path = None
        db._local = None

        # Execute transaction
        with db.transaction() as cursor:
            cursor.execute("INSERT INTO test VALUES (1)")

        # Verify commit was called
        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_pool.putconn.assert_called_once_with(mock_conn)

    @patch('acas_pro.core.database._get_logger')
    def test_transaction_rollback_on_exception(self, mock_logger):
        """Transaction should rollback when exception occurs."""
        from acas_pro.core.database import DatabaseManager

        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        db = object.__new__(DatabaseManager)
        db._is_postgres = True
        db._pool = mock_pool
        db._db_path = None
        db._local = None

        # Execute transaction that raises exception
        with pytest.raises(ValueError):
            with db.transaction() as cursor:
                cursor.execute("INSERT INTO test VALUES (1)")
                raise ValueError("Test error")

        # Verify rollback was called, commit was not
        mock_conn.rollback.assert_called_once()
        mock_conn.commit.assert_not_called()
        mock_cursor.close.assert_called_once()
        mock_pool.putconn.assert_called_once_with(mock_conn)

    @patch('acas_pro.core.database._get_logger')
    def test_transaction_connection_cleanup_on_error(self, mock_logger):
        """Ensure connection is always returned to pool even on error."""
        from acas_pro.core.database import DatabaseManager

        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        db = object.__new__(DatabaseManager)
        db._is_postgres = True
        db._pool = mock_pool
        db._db_path = None
        db._local = None

        with pytest.raises(Exception):
            with db.transaction() as cursor:  # noqa: F841
                raise Exception("Force error")

        # Connection should still be returned to pool
        mock_pool.putconn.assert_called_once_with(mock_conn)

    def test_transaction_sqlite_mode(self):
        """Transaction should use SQLite connection when not in postgres mode."""
        from acas_pro.core.database import DatabaseManager

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.execute.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []

        db = object.__new__(DatabaseManager)
        db._is_postgres = False
        db._pool = None
        db._get_sqlite_connection = lambda: mock_conn

        # Execute transaction
        with db.transaction() as cursor:
            cursor.execute("INSERT INTO test VALUES (1)")

        # SQLite should use conn.execute, not pool
        mock_conn.execute.assert_called()