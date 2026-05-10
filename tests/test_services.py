#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 2: Service Layer Tests - Coverage Sprint

Target: Improve coverage for service modules
"""

import pytest
import os
import sys
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestOAuthService:
    """Test OAuth service"""
    
    @pytest.fixture
    def mock_config(self):
        config = Mock()
        config.qq_app_id = "test_qq_id"
        config.qq_app_key = "test_qq_key"
        config.qq_redirect_uri = "http://localhost/callback"
        config.wechat_app_id = "test_wechat_id"
        config.wechat_app_secret = "test_wechat_secret"
        config.wechat_redirect_uri = "http://localhost/callback"
        return config
    
    def test_oauth_service_initialization(self, mock_config):
        """Test OAuth service can be initialized"""
        from acas_pro.services.oauth.oauth_service import OAuthService
        
        service = OAuthService(mock_config)
        assert service is not None
        assert "qq" in service.available_providers()
        assert "wechat" in service.available_providers()
    
    def test_get_authorization_url_returns_state(self, mock_config):
        """Test authorization URL generation includes state"""
        from acas_pro.services.oauth.oauth_service import OAuthService
        
        service = OAuthService(mock_config)
        url, state = service.get_authorization_url("qq")
        
        assert url != ""
        assert state != ""
        assert "state=" in url
    
    def test_get_authorization_url_invalid_provider(self, mock_config):
        """Test invalid provider returns empty"""
        from acas_pro.services.oauth.oauth_service import OAuthService
        
        service = OAuthService(mock_config)
        url, state = service.get_authorization_url("invalid")
        
        assert url == ""
        assert state == ""
    
    @patch('urllib.request.urlopen')
    def test_get_access_token_http_error(self, mock_urlopen, mock_config):
        """Test access token retrieval handles HTTP errors"""
        from acas_pro.services.oauth.oauth_service import OAuthService, QQOAuth
        import urllib.error
        
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="test", code=400, msg="Bad Request", hdrs={}, fp=None
        )
        
        service = OAuthService(mock_config)
        result = service._providers["qq"].get_access_token("test_code")
        
        assert result is None
    
    @patch('urllib.request.urlopen')
    def test_get_access_token_url_error(self, mock_urlopen, mock_config):
        """Test access token retrieval handles URL errors"""
        from acas_pro.services.oauth.oauth_service import OAuthService
        import urllib.error
        
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
        
        service = OAuthService(mock_config)
        result = service._providers["qq"].get_access_token("test_code")
        
        assert result is None


class TestUserService:
    """Test User service"""
    
    @pytest.fixture
    def mock_db(self):
        db = Mock()
        db.fetchone = Mock(return_value=None)
        db.execute = Mock(return_value=1)
        return db
    
    @patch('acas_pro.services.user_service.db')
    @patch('acas_pro.services.user_service.rate_limiter')
    @patch('acas_pro.services.user_service.password_hasher')
    @patch('acas_pro.services.user_service.password_validator')
    def test_register_user_success(self, mock_validator, mock_hasher, mock_limiter, mock_db):
        """Test user registration success"""
        from acas_pro.services.user_service import user_service
        
        mock_validator.validate.return_value = (True, "")
        mock_hasher.hash.return_value = "hashed_password"
        mock_limiter.is_allowed.return_value = True
        mock_db.fetchone.return_value = None  # User doesn't exist
        
        success, message, profile = user_service.register(
            account="testuser",
            password="StrongPass123!",
            email="test@example.com"
        )
        
        assert success is True
        assert "success" in message.lower()
    
    @patch('acas_pro.services.user_service.db')
    @patch('acas_pro.services.user_service.rate_limiter')
    def test_register_duplicate_user(self, mock_limiter, mock_db):
        """Test registration with duplicate username"""
        from acas_pro.services.user_service import user_service
        
        mock_limiter.is_allowed.return_value = True
        mock_db.fetchone.return_value = {"id": "existing_user"}
        
        success, message, profile = user_service.register(
            account="existinguser",
            password="StrongPass123!"
        )
        
        assert success is False
        assert "exists" in message.lower() or "taken" in message.lower()
    
    @patch('acas_pro.services.user_service.db')
    @patch('acas_pro.services.user_service.rate_limiter')
    def test_register_rate_limited(self, mock_limiter, mock_db):
        """Test registration rate limiting"""
        from acas_pro.services.user_service import user_service
        
        mock_limiter.is_allowed.return_value = False
        
        success, message, profile = user_service.register(
            account="testuser",
            password="StrongPass123!"
        )
        
        assert success is False
        assert "rate" in message.lower() or "limit" in message.lower()
    
    @patch('acas_pro.services.user_service.db')
    @patch('acas_pro.services.user_service.rate_limiter')
    @patch('acas_pro.services.user_service.password_hasher')
    def test_login_success(self, mock_hasher, mock_limiter, mock_db):
        """Test user login success"""
        from acas_pro.services.user_service import user_service
        
        mock_limiter.is_allowed.return_value = True
        mock_db.fetchone.return_value = {
            "id": "user123",
            "password_hash": "hashed_pass",
            "status": "active"
        }
        mock_hasher.verify.return_value = True
        
        success, message, profile = user_service.login(
            account="testuser",
            password="correct_password"
        )
        
        assert success is True
    
    @patch('acas_pro.services.user_service.db')
    @patch('acas_pro.services.user_service.rate_limiter')
    def test_login_rate_limited(self, mock_limiter, mock_db):
        """Test login rate limiting"""
        from acas_pro.services.user_service import user_service
        
        mock_limiter.is_allowed.return_value = False
        
        success, message, profile = user_service.login(
            account="testuser",
            password="password"
        )
        
        assert success is False
        assert "rate" in message.lower() or "attempts" in message.lower()
    
    @patch('acas_pro.services.user_service.db')
    def test_get_profile_not_found(self, mock_db):
        """Test get profile for non-existent user"""
        from acas_pro.services.user_service import user_service
        
        mock_db.fetchone.return_value = None
        
        profile = user_service.get_profile("nonexistent")
        
        assert profile is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
