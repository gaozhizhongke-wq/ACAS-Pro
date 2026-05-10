#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Alert Notifier Tests
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from acas_pro.alert.notifier import (
    AlertNotifier, AlertMessage, AlertChannel, AlertPriority,
    send_critical_alert, send_urgent_alert
)


class TestAlertPriority:
    """Alert priority enum tests"""
    
    def test_priority_values(self):
        """Test priority values"""
        assert AlertPriority.P0_CRITICAL.value == "p0"
        assert AlertPriority.P1_URGENT.value == "p1"
        assert AlertPriority.P2_ATTENTION.value == "p2"
        assert AlertPriority.P3_ROUTINE.value == "p3"


class TestAlertChannel:
    """Alert channel enum tests"""
    
    def test_channel_values(self):
        """Test channel values"""
        assert AlertChannel.WECHAT_WORK.value == "wechat_work"
        assert AlertChannel.EMAIL.value == "email"
        assert AlertChannel.SMS.value == "sms"
        assert AlertChannel.WEBHOOK.value == "webhook"
        assert AlertChannel.DINGTALK.value == "dingtalk"
        assert AlertChannel.FEISHU.value == "feishu"


class TestAlertMessage:
    """Alert message tests"""
    
    def test_message_creation(self):
        """Test message creation"""
        alert = AlertMessage(
            title="Test Alert",
            content="Test content",
            priority=AlertPriority.P1_URGENT,
            category="test"
        )
        
        assert alert.title == "Test Alert"
        assert alert.priority == AlertPriority.P1_URGENT
        assert alert.timestamp is not None
    
    def test_message_to_markdown(self):
        """Test message to markdown"""
        alert = AlertMessage(
            title="Test",
            content="Content",
            priority=AlertPriority.P0_CRITICAL
        )
        
        md = alert.to_markdown()
        assert "Test" in md
        assert "Content" in md
        assert "🔴" in md  # P0 emoji
    
    def test_message_to_dict(self):
        """Test message to dict"""
        alert = AlertMessage(
            title="Test",
            content="Content",
            priority=AlertPriority.P2_ATTENTION
        )
        
        data = alert.to_dict()
        assert data['title'] == "Test"
        assert data['priority'] == "p2"


class TestAlertNotifier:
    """Alert notifier tests"""
    
    @pytest.fixture
    def notifier(self):
        return AlertNotifier()
    
    def test_init(self, notifier):
        """Test initialization"""
        assert notifier._max_history == 1000
        assert len(notifier._history) == 0
    
    def test_select_channels_p0(self, notifier):
        """Test channel selection for P0"""
        notifier.enabled_channels = {
            AlertChannel.WECHAT_WORK: True,
            AlertChannel.DINGTALK: True,
            AlertChannel.EMAIL: True,
        }
        
        channels = notifier._select_channels(AlertPriority.P0_CRITICAL)
        assert len(channels) >= 2
    
    def test_select_channels_p3(self, notifier):
        """Test channel selection for P3"""
        channels = notifier._select_channels(AlertPriority.P3_ROUTINE)
        assert AlertChannel.WECHAT_WORK in channels
    
    def test_get_feishu_color(self, notifier):
        """Test Feishu color mapping"""
        assert notifier._get_feishu_color(AlertPriority.P0_CRITICAL) == "red"
        assert notifier._get_feishu_color(AlertPriority.P1_URGENT) == "orange"
        assert notifier._get_feishu_color(AlertPriority.P2_ATTENTION) == "yellow"
        assert notifier._get_feishu_color(AlertPriority.P3_ROUTINE) == "blue"
    
    def test_record_alert(self, notifier):
        """Test record alert"""
        alert = AlertMessage(title="Test", content="Content")
        results = {AlertChannel.WECHAT_WORK: True}
        
        notifier._record_alert(alert, results)
        
        assert len(notifier._history) == 1
    
    def test_get_history(self, notifier):
        """Test get history"""
        alert = AlertMessage(title="Test", content="Content")
        notifier._record_alert(alert, {})
        
        history = notifier.get_history()
        assert len(history) == 1
    
    def test_configure_channel(self, notifier):
        """Test configure channel"""
        notifier.configure_channel(
            AlertChannel.WECHAT_WORK,
            webhook="https://test.com/webhook"
        )
        
        assert notifier.wechat_webhook == "https://test.com/webhook"
        assert notifier.enabled_channels[AlertChannel.WECHAT_WORK] is True


class TestConvenienceFunctions:
    """Convenience function tests"""
    
    @patch('acas_pro.alert.notifier.alert_manager')
    def test_send_critical_alert(self, mock_manager):
        """Test send critical alert"""
        mock_manager.send.return_value = {AlertChannel.WECHAT_WORK: True}
        
        result = send_critical_alert("Critical", "Content")
        
        mock_manager.send.assert_called_once()
        call_args = mock_manager.send.call_args[0][0]
        assert call_args.priority == AlertPriority.P0_CRITICAL
    
    @patch('acas_pro.alert.notifier.alert_manager')
    def test_send_urgent_alert(self, mock_manager):
        """Test send urgent alert"""
        mock_manager.send.return_value = {AlertChannel.WECHAT_WORK: True}
        
        result = send_urgent_alert("Urgent", "Content")
        
        mock_manager.send.assert_called_once()
        call_args = mock_manager.send.call_args[0][0]
        assert call_args.priority == AlertPriority.P1_URGENT


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
