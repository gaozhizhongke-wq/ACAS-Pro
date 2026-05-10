#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase A: 服务层扩展测试
覆盖: user_service, oauth_service, notification_service
"""

import pytest
import os
import sys
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestUserServiceExtended:
    """UserService 扩展测试"""
    
    @pytest.fixture
    def mock_db(self):
        db = Mock()
        db.execute_one = Mock(return_value=None)
        db.execute = Mock(return_value=[])
        db.insert = Mock(return_value="new_user_id")
        return db
    
    @patch('acas_pro.services.user_service.db')
    @patch('acas_pro.services.user_service.rate_limiter')
    def test_register_password_too_short(self, mock_limiter, mock_db):
        """测试密码太短被拒绝"""
        from acas_pro.services.user_service import user_service
        
        mock_limiter.is_allowed.return_value = True
        mock_db.execute_one.return_value = None
        
        success, message, profile = user_service.register(
            account="testuser",
            password="short"  # 太短
        )
        
        assert success is False
        assert "password" in message.lower() or "密码" in message
    
    @patch('acas_pro.services.user_service.db')
    @patch('acas_pro.services.user_service.rate_limiter')
    def test_register_invalid_email(self, mock_limiter, mock_db):
        """测试无效邮箱格式"""
        from acas_pro.services.user_service import user_service
        
        mock_limiter.is_allowed.return_value = True
        mock_db.execute_one.return_value = None
        
        success, message, profile = user_service.register(
            account="testuser",
            password="StrongPass123!",
            email="invalid-email"
        )
        
        assert success is False
    
    @patch('acas_pro.services.user_service.db')
    @patch('acas_pro.services.user_service.rate_limiter')
    def test_login_user_not_found(self, mock_limiter, mock_db):
        """测试登录用户不存在"""
        from acas_pro.services.user_service import user_service
        
        mock_limiter.is_allowed.return_value = True
        mock_db.execute_one.return_value = None
        
        success, message, profile = user_service.login(
            account="nonexistent",
            password="anypassword"
        )
        
        assert success is False
        assert "not found" in message.lower() or "不存在" in message
    
    @patch('acas_pro.services.user_service.db')
    @patch('acas_pro.services.user_service.rate_limiter')
    def test_login_wrong_password(self, mock_limiter, mock_db):
        """测试密码错误"""
        from acas_pro.services.user_service import user_service
        from acas_pro.core.security import password_hasher
        
        mock_limiter.is_allowed.return_value = True
        mock_db.execute_one.return_value = {
            "id": "user123",
            "password_hash": "correct_hash",
            "status": "active"
        }
        
        with patch.object(password_hasher, 'verify', return_value=False):
            success, message, profile = user_service.login(
                account="testuser",
                password="wrongpassword"
            )
        
        assert success is False
    
    @patch('acas_pro.services.user_service.db')
    def test_update_profile_success(self, mock_db):
        """测试更新用户信息"""
        from acas_pro.services.user_service import user_service
        
        mock_db.execute_one.return_value = {
            "id": "user123",
            "nickname": "Old Name",
            "email": "old@example.com"
        }
        
        result = user_service.update_profile(
            user_id="user123",
            nickname="New Name",
            email="new@example.com"
        )
        
        assert result is True
    
    @patch('acas_pro.services.user_service.db')
    def test_change_password_success(self, mock_db):
        """测试修改密码"""
        from acas_pro.services.user_service import user_service
        from acas_pro.core.security import password_hasher
        
        mock_db.execute_one.return_value = {
            "id": "user123",
            "password_hash": "old_hash"
        }
        
        with patch.object(password_hasher, 'verify', return_value=True):
            with patch.object(password_hasher, 'hash', return_value="new_hash"):
                result = user_service.change_password(
                    user_id="user123",
                    old_password="OldPass123!",
                    new_password="NewPass123!"
                )
        
        assert result is True


class TestNotificationService:
    """通知服务测试"""
    
    def test_send_email_notification(self):
        """测试发送邮件通知"""
        from acas_pro.services.notification import notification_service
        
        with patch.object(notification_service, '_send_email', return_value=True):
            result = notification_service.send(
                user_id="user123",
                channel="email",
                title="Test",
                content="Test content"
            )
            assert result is True
    
    def test_send_sms_notification(self):
        """测试发送短信通知"""
        from acas_pro.services.notification import notification_service
        
        with patch.object(notification_service, '_send_sms', return_value=True):
            result = notification_service.send(
                user_id="user123",
                channel="sms",
                title="Test",
                content="Test content"
            )
            assert result is True
    
    def test_send_push_notification(self):
        """测试推送通知"""
        from acas_pro.services.notification import notification_service
        
        with patch.object(notification_service, '_send_push', return_value=True):
            result = notification_service.send(
                user_id="user123",
                channel="push",
                title="Test",
                content="Test content"
            )
            assert result is True
    
    def test_notification_preferences(self):
        """测试通知偏好设置"""
        from acas_pro.services.notification import notification_service
        
        # 设置偏好
        notification_service.set_preferences(
            user_id="user123",
            preferences={
                "email": True,
                "sms": False,
                "push": True
            }
        )
        
        # 获取偏好
        prefs = notification_service.get_preferences("user123")
        assert prefs is not None


class TestOAuthServiceExtended:
    """OAuth 服务扩展测试"""
    
    @pytest.fixture
    def mock_config(self):
        config = Mock()
        config.qq_app_id = "test_qq_id"
        config.qq_app_key = "test_qq_key"
        config.qq_redirect_uri = "http://localhost/callback"
        config.wechat_app_id = "test_wechat_id"
        config.wechat_app_secret = "test_wechat_secret"
        config.weibo_client_id = "test_weibo_id"
        config.weibo_client_secret = "test_weibo_secret"
        return config
    
    def test_oauth_qq_flow(self, mock_config):
        """测试 QQ OAuth 流程"""
        from acas_pro.services.oauth.oauth_service import OAuthService
        
        service = OAuthService(mock_config)
        
        # 获取授权 URL
        url, state = service.get_authorization_url("qq")
        assert url != ""
        assert state != ""
        
        # 验证 state 存储
        assert service.verify_state(state) is True
    
    def test_oauth_wechat_flow(self, mock_config):
        """测试微信 OAuth 流程"""
        from acas_pro.services.oauth.oauth_service import OAuthService
        
        service = OAuthService(mock_config)
        
        url, state = service.get_authorization_url("wechat")
        assert url != ""
        assert "weixin" in url or "wechat" in url.lower()
    
    def test_oauth_invalid_provider(self, mock_config):
        """测试无效 provider"""
        from acas_pro.services.oauth.oauth_service import OAuthService
        
        service = OAuthService(mock_config)
        
        url, state = service.get_authorization_url("invalid_provider")
        assert url == ""
        assert state == ""
    
    def test_oauth_state_verification(self, mock_config):
        """测试 state 验证"""
        from acas_pro.services.oauth.oauth_service import OAuthService
        
        service = OAuthService(mock_config)
        
        # 无效 state
        assert service.verify_state("invalid_state") is False
        
        # 过期 state
        import time
        old_state = f"expired_{int(time.time()) - 400}"
        assert service.verify_state(old_state) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
