import pytest
import json
from unittest.mock import patch, MagicMock
from flask import Flask


@pytest.fixture
def app():
    app = Flask(__name__)
    from acas_pro.web.routes.dashboard import bp
    app.register_blueprint(bp)
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


class TestDashboardIndex:
    def test_index_returns_html(self, client):
        response = client.get('/')
        assert response.status_code == 200
        assert b'<!DOCTYPE html>' in response.data
        assert b'ACAS Pro' in response.data

    def test_index_contains_dashboard_elements(self, client):
        response = client.get('/')
        assert response.status_code == 200
        assert b'active-users' in response.data
        assert b'content-count' in response.data
        assert b'pending-tasks' in response.data
        assert b'api-calls' in response.data

    def test_index_contains_javascript(self, client):
        response = client.get('/')
        assert response.status_code == 200
        assert b'loadDashboard' in response.data
        assert b'fetch(' in response.data


class TestDashboardStats:
    def test_stats_success(self, client):
        """Test successful stats retrieval"""
        with patch('acas_pro.core.database.db') as mock_db:
            mock_db.fetchall.side_effect = [
                [{'cnt': 5}],
                [{'cnt': 10}],
                [{'total': 1000.0}],
                [{'cnt': 3}],
                [{'cnt': 2}],
                [{'cnt': 15}],
                [{'cnt': 8}],
                [{'cnt': 1}],
                [{'cnt': 50}],
            ]
            response = client.get('/api/stats')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'stats' in data
            stats = data['stats']
            assert stats['active_users'] == 5
            assert stats['products_count'] == 10
            assert stats['total_revenue'] == 1000.0
            assert stats['transactions_today'] == 3
            assert stats['pending_tasks'] == 2
            assert stats['content_count'] == 23
            assert stats['alerts_count'] == 1
            assert stats['api_calls_today'] == 50

    def test_stats_empty_database(self, client):
        with patch('acas_pro.core.database.db') as mock_db:
            mock_db.fetchall.return_value = []
            response = client.get('/api/stats')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            stats = data['stats']
            assert stats['active_users'] == 0
            assert stats['total_revenue'] == 0.0

    def test_stats_database_error(self, client):
        import sqlite3
        with patch('acas_pro.core.database.db') as mock_db:
            mock_db.fetchall.side_effect = sqlite3.OperationalError('no such table')
            response = client.get('/api/stats')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'stats' in data

    def test_stats_partial_data(self, client):
        import sqlite3
        with patch('acas_pro.core.database.db') as mock_db:
            mock_db.fetchall.side_effect = [
                [{'cnt': 5}],
                sqlite3.OperationalError('no such table'),
                [{'total': 500.0}],
                [{'cnt': 2}],
                [{'cnt': 1}],
                [{'cnt': 10}],
                [{'cnt': 5}],
                [{'cnt': 0}],
                [{'cnt': 20}],
            ]
            response = client.get('/api/stats')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            stats = data['stats']
            assert stats['active_users'] == 5
            assert stats['total_revenue'] == 500.0


class TestRecentActivity:
    def test_activity_from_audit_log(self, client):
        with patch('acas_pro.core.database.db') as mock_db:
            mock_db.fetchall.return_value = [
                {'time': '2026-05-30 10:00:00', 'event': 'LOGIN', 'status': 'info'},
                {'time': '2026-05-30 09:30:00', 'event': 'ORDER_CREATED', 'status': 'success'},
                {'time': '2026-05-30 09:00:00', 'event': 'PAYMENT_FAILED', 'status': 'warning'},
            ]
            response = client.get('/api/activity')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert len(data['activities']) == 3
            assert data['activities'][0]['event'] == 'LOGIN'
            assert data['activities'][1]['event'] == 'ORDER_CREATED'

    def test_activity_fallback_to_transactions(self, client):
        import sqlite3
        with patch('acas_pro.core.database.db') as mock_db:
            mock_db.fetchall.side_effect = [
                sqlite3.OperationalError('no such table'),
                [
                    {'time': '2026-05-30 10:00:00', 'event': 'purchase', 'status': 'completed'},
                    {'time': '2026-05-30 09:00:00', 'event': 'refund', 'status': 'pending'},
                ]
            ]
            response = client.get('/api/activity')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert len(data['activities']) == 2
            assert 'Transaction' in data['activities'][0]['event']

    def test_activity_empty_database(self, client):
        import sqlite3
        with patch('acas_pro.core.database.db') as mock_db:
            mock_db.fetchall.side_effect = [
                sqlite3.OperationalError('no such table'),
                sqlite3.OperationalError('no such table'),
            ]
            response = client.get('/api/activity')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert len(data['activities']) == 1
            assert 'No activity' in data['activities'][0]['event']

    def test_activity_error_handling(self, client):
        with patch('acas_pro.core.database.db') as mock_db:
            mock_db.fetchall.side_effect = Exception('Unexpected error')
            response = client.get('/api/activity')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'activities' in data


class TestDashboardTemplate:
    def test_template_contains_api_endpoints(self, client):
        response = client.get('/')
        html = response.data.decode('utf-8')
        assert '/api/health' in html
        assert '/api/stats' in html
        assert '/api/activity' in html
        assert '/api/auth/me' in html

    def test_template_contains_styling(self, client):
        response = client.get('/')
        html = response.data.decode('utf-8')
        assert '<style>' in html
        assert 'background' in html
        assert 'color' in html

    def test_template_responsive_design(self, client):
        response = client.get('/')
        html = response.data.decode('utf-8')
        assert '@media' in html
        assert 'max-width' in html
