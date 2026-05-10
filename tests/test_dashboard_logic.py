#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Dashboard Logic Tests
"""

import pytest
from datetime import datetime
from unittest.mock import Mock

from acas_pro.ui.logic.dashboard_logic import (
    DashboardLogic, KPIData, QuickAction, AlertItem
)


class TestKPIData:
    """Test KPI data structure"""
    
    def test_kpi_creation(self):
        """Test KPI data creation"""
        kpi = KPIData(
            title="Test KPI",
            value="100",
            subtitle="Test subtitle",
            color="#ff0000",
            trend=5.5
        )
        assert kpi.title == "Test KPI"
        assert kpi.value == "100"
        assert kpi.trend == 5.5
    
    def test_kpi_default_trend(self):
        """Test KPI with default trend"""
        kpi = KPIData(
            title="Test",
            value="0",
            subtitle="",
            color="#000000"
        )
        assert kpi.trend == 0.0


class TestQuickAction:
    """Test quick action structure"""
    
    def test_action_creation(self):
        """Test quick action creation"""
        action = QuickAction(
            id="test_action",
            label="Test Label",
            icon="🔧"
        )
        assert action.id == "test_action"
        assert action.label == "Test Label"
        assert action.callback is None
    
    def test_action_with_callback(self):
        """Test quick action with callback"""
        callback = Mock()
        action = QuickAction(
            id="action1",
            label="Action",
            icon="⚙️",
            callback=callback
        )
        assert action.callback is callback


class TestAlertItem:
    """Test alert item structure"""
    
    def test_alert_creation(self):
        """Test alert creation"""
        alert = AlertItem(
            level="critical",
            message="Test alert",
            timestamp=datetime.now(),
            action_required=True
        )
        assert alert.level == "critical"
        assert alert.action_required is True
    
    def test_alert_default_action(self):
        """Test alert with default action_required"""
        alert = AlertItem(
            level="low",
            message="Info",
            timestamp=datetime.now()
        )
        assert alert.action_required is False


class TestDashboardLogic:
    """Test dashboard logic"""
    
    @pytest.fixture
    def logic(self):
        return DashboardLogic()
    
    @pytest.fixture
    def mock_services(self):
        user_service = Mock()
        user_service.get_current.return_value = {'nickname': 'TestUser'}
        analytics_service = Mock()
        return user_service, analytics_service
    
    def test_init(self, logic):
        """Test initialization"""
        assert logic._user is None
        assert logic._kpis == []
        assert logic._alerts == []
    
    def test_colors_defined(self, logic):
        """Test color scheme is defined"""
        assert "success" in logic.COLORS
        assert "danger" in logic.COLORS
        assert "warning" in logic.COLORS
    
    def test_load_user(self, logic, mock_services):
        """Test loading user"""
        user_service, _ = mock_services
        logic.user_service = user_service
        
        user = logic.load_user()
        
        assert user is not None
        assert user['nickname'] == 'TestUser'
        assert logic._user == user
    
    def test_load_user_no_service(self, logic):
        """Test loading user without service"""
        user = logic.load_user()
        assert user is None
    
    def test_get_welcome_message_with_user(self, logic, mock_services):
        """Test welcome message with user"""
        user_service, _ = mock_services
        logic.user_service = user_service
        logic.load_user()
        
        message = logic.get_welcome_message()
        
        assert "TestUser" in message
        assert "欢迎回来" in message
    
    def test_get_welcome_message_no_user(self, logic):
        """Test welcome message without user"""
        message = logic.get_welcome_message()
        assert "用户" in message
    
    def test_get_subtitle(self, logic):
        """Test subtitle"""
        subtitle = logic.get_subtitle()
        assert isinstance(subtitle, str)
        assert len(subtitle) > 0
    
    def test_calculate_kpis(self, logic):
        """Test KPI calculation"""
        data = {
            'revenue': 100000,
            'revenue_prev': 90000,
            'active_orders': 500,
            'orders_prev': 450,
            'inventory_count': 1000,
            'low_stock_count': 5,
            'critical_alerts': 1,
            'high_alerts': 2,
            'medium_alerts': 3,
        }
        
        kpis = logic.calculate_kpis(data)
        
        assert len(kpis) == 4
        assert kpis[0].title == "总营收"
        assert kpis[1].title == "活跃订单"
        assert kpis[2].title == "库存商品"
        assert kpis[3].title == "风险预警"
    
    def test_calculate_kpis_default_data(self, logic):
        """Test KPI calculation with default data"""
        kpis = logic.calculate_kpis()
        
        assert len(kpis) == 4
        assert all(isinstance(kpi, KPIData) for kpi in kpis)
    
    def test_calculate_kpis_trends(self, logic):
        """Test KPI trends calculation"""
        data = {
            'revenue': 110000,
            'revenue_prev': 100000,
            'active_orders': 550,
            'orders_prev': 500,
        }
        
        kpis = logic.calculate_kpis(data)
        
        assert kpis[0].trend == 10.0  # (110000-100000)/100000 * 100
        assert kpis[1].trend == 10.0  # (550-500)/500 * 100
    
    def test_get_quick_actions(self, logic):
        """Test getting quick actions"""
        actions = logic.get_quick_actions()
        
        assert len(actions) == 4
        assert all(isinstance(a, QuickAction) for a in actions)
        assert actions[0].id == "forecast"
    
    def test_get_alerts(self, logic):
        """Test getting alerts"""
        logic._alerts = [
            AlertItem(level="critical", message="Alert 1", timestamp=datetime.now()),
            AlertItem(level="high", message="Alert 2", timestamp=datetime.now()),
        ]
        
        alerts = logic.get_alerts()
        
        assert len(alerts) == 2
    
    def test_get_alerts_with_limit(self, logic):
        """Test getting alerts with limit"""
        logic._alerts = [
            AlertItem(level="low", message=f"Alert {i}", timestamp=datetime.now())
            for i in range(20)
        ]
        
        alerts = logic.get_alerts(limit=5)
        
        assert len(alerts) == 5
    
    def test_refresh_data(self, logic, mock_services):
        """Test refreshing all data"""
        user_service, _ = mock_services
        logic.user_service = user_service
        
        data = logic.refresh_data()
        
        assert 'user' in data
        assert 'kpis' in data
        assert 'alerts' in data
        assert len(data['kpis']) == 4
    
    def test_format_currency_large(self, logic):
        """Test currency formatting for large values"""
        result = logic._format_currency(15000)
        assert "万" in result
        assert "¥" in result
    
    def test_format_currency_small(self, logic):
        """Test currency formatting for small values"""
        result = logic._format_currency(9999)
        assert "万" not in result
        assert "¥" in result
    
    def test_format_number_large(self, logic):
        """Test number formatting for large values"""
        result = logic._format_number(15000)
        assert "万" in result
    
    def test_format_number_small(self, logic):
        """Test number formatting for small values"""
        result = logic._format_number(999)
        assert "," in result or "999" in result
    
    def test_format_trend_positive(self, logic):
        """Test trend formatting for positive values"""
        result = logic._format_trend(5.5)
        assert "↑" in result
        assert "5.5" in result
    
    def test_format_trend_negative(self, logic):
        """Test trend formatting for negative values"""
        result = logic._format_trend(-3.2)
        assert "↓" in result
        assert "3.2" in result
    
    def test_format_trend_zero(self, logic):
        """Test trend formatting for zero"""
        result = logic._format_trend(0)
        assert "→" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
