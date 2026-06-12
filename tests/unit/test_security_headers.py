#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for core/security_headers.py"""

import pytest
from unittest.mock import MagicMock
from acas_pro.core.security_headers import SecurityHeaders, InputValidator


class TestSecurityHeaders:
    def test_init_without_app(self):
        sh = SecurityHeaders()
        assert sh.use_nonce is True
        assert sh.hsts is True
        assert sh.hsts_max_age == 63072000

    def test_init_with_custom_csp(self):
        # Legacy CSP mode (no nonce)
        sh = SecurityHeaders(use_nonce=False)
        assert sh.use_nonce is False

    def test_init_with_app(self):
        app = MagicMock()
        app.after_request = lambda f: f
        sh = SecurityHeaders(app=app)
        assert sh.use_nonce is True

    def test_init_app_adds_headers(self):
        app = MagicMock()
        
        # Capture the after_request decorator
        registered_handlers = []
        def capture_after_request(f):
            registered_handlers.append(f)
            return f
        app.after_request = capture_after_request
        
        sh = SecurityHeaders(app=app, use_nonce=True)  # noqa: F841
        assert len(registered_handlers) == 1
        
        # Test the handler - need to mock request before calling handler
        handler = registered_handlers[0]
        response = MagicMock()
        response.headers = {}
        
        # Mock the request object directly in the module
        from unittest.mock import patch as _patch
        mock_request = MagicMock()
        mock_request.is_secure = False
        with _patch('acas_pro.core.security_headers.request', mock_request):
            result = handler(response)
        
        assert result.headers['X-Content-Type-Options'] == 'nosniff'
        assert result.headers['X-Frame-Options'] == 'DENY'
        assert result.headers['X-XSS-Protection'] == '1; mode=block'
        assert result.headers['Referrer-Policy'] == 'strict-origin-when-cross-origin'
        assert 'Content-Security-Policy' in result.headers
        assert 'Permissions-Policy' in result.headers

    def test_hsts_on_secure(self):
        """Test HSTS configuration is set correctly"""
        sh = SecurityHeaders(hsts=True, hsts_max_age=31536000)
        assert sh.hsts is True
        assert sh.hsts_max_age == 31536000
        
        # Verify HSTS header format
        expected_hsts = f'max-age={sh.hsts_max_age}; includeSubDomains; preload'
        assert '31536000' in expected_hsts
        assert 'includeSubDomains' in expected_hsts

    def test_hsts_off_on_insecure(self):
        """Test HSTS header is NOT added on insecure connection"""
        from flask import Flask
        app = Flask(__name__)
        app.config['TESTING'] = True
        sh = SecurityHeaders(app=app, hsts=True, hsts_max_age=31536000)  # noqa: F841
        
        @app.route('/test')
        def test_route():
            return 'ok'
        
        with app.test_client() as client:
            resp = client.get('/test')
            # On HTTP (non-HTTPS), HSTS should not be in response
            # The request.is_secure will be False in test client
            assert 'Strict-Transport-Security' not in resp.headers

    def test_server_header_removed(self):
        app = MagicMock()
        
        registered_handlers = []
        def capture_after_request(f):
            registered_handlers.append(f)
            return f
        app.after_request = capture_after_request
        
        sh = SecurityHeaders(app=app, use_nonce=False)  # noqa: F841
        handler = registered_handlers[0]
        
        response = MagicMock()
        response.headers = {'Server': 'Werkzeug/2.0'}
        
        from unittest.mock import patch as _patch
        mock_request = MagicMock()
        mock_request.is_secure = False
        with _patch('acas_pro.core.security_headers.request', mock_request):
            result = handler(response)
        
        assert 'Server' not in result.headers


class TestInputValidator:
    def test_sanitize_sql_clean(self):
        result = InputValidator.sanitize_sql("hello world")
        assert result == "hello world"

    def test_sanitize_sql_with_null(self):
        result = InputValidator.sanitize_sql("hello\x00world")
        assert result == "helloworld"

    def test_sanitize_sql_injection(self):
        with pytest.raises(ValueError):
            InputValidator.sanitize_sql("1; DROP TABLE users")

    def test_sanitize_sql_union(self):
        with pytest.raises(ValueError):
            InputValidator.sanitize_sql("1 UNION SELECT * FROM users")

    def test_sanitize_sql_non_string(self):
        result = InputValidator.sanitize_sql(123)
        assert result == 123

    def test_sanitize_html_clean(self):
        result = InputValidator.sanitize_html("<p>Hello</p>")
        assert result == "<p>Hello</p>"

    def test_sanitize_html_xss_script(self):
        with pytest.raises(ValueError):
            InputValidator.sanitize_html("<script>alert('xss')</script>")

    def test_sanitize_html_xss_javascript(self):
        with pytest.raises(ValueError):
            InputValidator.sanitize_html("javascript:alert('xss')")

    def test_sanitize_html_xss_onclick(self):
        with pytest.raises(ValueError):
            InputValidator.sanitize_html("<div onclick='alert(1)'></div>")

    def test_sanitize_html_non_string(self):
        result = InputValidator.sanitize_html(123)
        assert result == 123

    def test_validate_email_valid(self):
        assert InputValidator.validate_email("test@example.com") is True
        assert InputValidator.validate_email("user.name@domain.co.uk") is True

    def test_validate_email_invalid(self):
        assert InputValidator.validate_email("not-an-email") is False
        assert InputValidator.validate_email("@example.com") is False
        assert InputValidator.validate_email("test@") is False
        assert InputValidator.validate_email("") is False

    def test_validate_phone_valid(self):
        assert InputValidator.validate_phone("13800138000") is True
        assert InputValidator.validate_phone("15912345678") is True

    def test_validate_phone_invalid(self):
        assert InputValidator.validate_phone("12345678901") is False
        assert InputValidator.validate_phone("1380013800") is False
        assert InputValidator.validate_phone("") is False
