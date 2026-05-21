#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for alert/notifier.py module."""

import sys
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest

# Mock dependencies before import
if 'requests' not in sys.modules:
    sys.modules['requests'] = MagicMock()

from acas_pro.alert.notifier import (
    AlertChannel, AlertPriority, AlertMessage, AlertNotifier
)


class TestAlertMessage:
    """Test AlertMessage dataclass."""
    
    def test_default_message(self):
        msg = AlertMessage(title="Test", content="Hello")
        assert msg.title == "Test"
        assert msg.priority == AlertPriority.P3_ROUTINE
        assert msg.category == "general"
        assert msg.source == "acas"
        assert msg.timestamp is not None
        assert msg.metadata == {}
    
    def test_custom_message(self):
        msg = AlertMessage(
            title="Critical Alert",
            content="System down",
            priority=AlertPriority.P0_CRITICAL,
            category="system",
            source="monitor"
        )
        assert msg.priority == AlertPriority.P0_CRITICAL
    
    def test_to_markdown_p0(self):
        msg = AlertMessage(title="Fire", content="Server on fire", priority=AlertPriority.P0_CRITICAL)
        md = msg.to_markdown()
        assert "🔴" in md
        assert "Fire" in md
    
    def test_to_markdown_p3(self):
        msg = AlertMessage(title="Info", content="All good", priority=AlertPriority.P3_ROUTINE)
        md = msg.to_markdown()
        assert "🟢" in md
    
    def test_to_dict(self):
        msg = AlertMessage(title="Test", content="Hello", metadata={"key": "val"})
        d = msg.to_dict()
        assert d["title"] == "Test"
        assert d["priority"] == "p3"
        assert d["metadata"] == {"key": "val"}
        assert "timestamp" in d


class TestAlertChannel:
    def test_channels(self):
        assert AlertChannel.WECHAT_WORK.value == "wechat_work"
        assert AlertChannel.EMAIL.value == "email"
        assert AlertChannel.SMS.value == "sms"
        assert AlertChannel.WEBHOOK.value == "webhook"
        assert AlertChannel.DINGTALK.value == "dingtalk"
        assert AlertChannel.FEISHU.value == "feishu"


class TestAlertPriority:
    def test_priorities(self):
        assert AlertPriority.P0_CRITICAL.value == "p0"
        assert AlertPriority.P1_URGENT.value == "p1"
        assert AlertPriority.P2_ATTENTION.value == "p2"
        assert AlertPriority.P3_ROUTINE.value == "p3"


class TestAlertNotifier:
    @pytest.fixture
    def notifier(self):
        with patch('acas_pro.alert.notifier.config'):
            n = AlertNotifier()
            n.wechat_webhook = "https://example.com/wechat"
            n.dingtalk_webhook = "https://example.com/dingtalk"
            n.feishu_webhook = "https://example.com/feishu"
            n.smtp_host = "smtp.example.com"
            n.smtp_user = "test@example.com"
            n.smtp_password = "pass"
            n.enabled_channels = {
                AlertChannel.WECHAT_WORK: True,
                AlertChannel.DINGTALK: True,
                AlertChannel.FEISHU: True,
                AlertChannel.EMAIL: True,
            }
            return n
    
    def test_send_with_disabled_channel(self, notifier):
        notifier.enabled_channels[AlertChannel.SMS] = False
        msg = AlertMessage(title="Test", content="Hello")
        result = notifier.send(msg, channels=[AlertChannel.SMS])
        assert result[AlertChannel.SMS] == False
    
    def test_send_force_disabled(self, notifier):
        notifier.enabled_channels[AlertChannel.SMS] = False
        msg = AlertMessage(title="Test", content="Hello")
        with patch.object(notifier, '_send_wechat', return_value=True):
            result = notifier.send(msg, channels=[AlertChannel.WECHAT_WORK], force=True)
            assert result[AlertChannel.WECHAT_WORK] == True
    
    def test_send_exception_handling(self, notifier):
        msg = AlertMessage(title="Test", content="Hello")
        with patch.object(notifier, '_send_wechat', side_effect=Exception("Network error")):
            result = notifier.send(msg, channels=[AlertChannel.WECHAT_WORK])
            assert result[AlertChannel.WECHAT_WORK] == False
    
    def test_select_channels_p0(self, notifier):
        channels = notifier._select_channels(AlertPriority.P0_CRITICAL)
        assert AlertChannel.WECHAT_WORK in channels
    
    def test_select_channels_p3(self, notifier):
        channels = notifier._select_channels(AlertPriority.P3_ROUTINE)
        assert isinstance(channels, list)
    
    def test_send_records_history(self, notifier):
        msg = AlertMessage(title="Test", content="Hello")
        with patch.object(notifier, '_send_wechat', return_value=True):
            notifier.send(msg, channels=[AlertChannel.WECHAT_WORK])
            assert len(notifier._history) == 1
