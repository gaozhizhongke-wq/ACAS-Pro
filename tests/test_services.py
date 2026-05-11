#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Service Layer Tests"""

import pytest
import os
import sys
from unittest.mock import Mock, patch

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


class TestSecurityService:
    """Test security utilities"""
    
    def test_password_validation(self):
        """Test password validator"""
        from acas_pro.core.security import password_validator
        
        is_valid, msg = password_validator.validate("StrongP@ss123")
        assert is_valid is True
        
        is_valid, msg = password_validator.validate("weak")
        assert is_valid is False
    
    def test_password_hashing(self):
        """Test password hasher"""
        from acas_pro.core.security import password_hasher
        
        hashed = password_hasher.hash("password123")
        assert hashed != "password123"
        assert password_hasher.verify("password123", hashed) is True
        assert password_hasher.verify("wrong", hashed) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
