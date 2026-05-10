"""
Phase 2: 分析引擎模块测试
覆盖: attribution_engine, smart_decider, alert_notifier
"""
import pytest
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# 导入被测模块
from acas_pro.advanced_analytics.attribution_engine import (
    AttributionEngine, TouchPoint, AttributionModel, ChannelType
)
from acas_pro.advanced_analytics.smart_decider import (
    SmartDecider, DecisionPriority
)
from acas_pro.alert.notifier import (
    AlertNotifier, AlertMessage, AlertChannel, AlertPriority
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def attribution_engine():
    """AttributionEngine 实例"""
    return AttributionEngine()


@pytest.fixture
def smart_decider():
    """SmartDecider 实例"""
    return SmartDecider()


@pytest.fixture
def alert_notifier():
    """AlertNotifier 实例"""
    return AlertNotifier()


@pytest.fixture
def sample_touchpoints():
    """示例触点列表"""
    now = datetime.now()
    return [
        TouchPoint(
            channel="抖音",
            channel_type=ChannelType.VIDEO_PLATFORM,
            campaign="春季大促",
            ad_group="美妆组",
            keyword="口红",
            timestamp=now - timedelta(days=3),
            value=1000.0,
            conversions=10,
            impressions=10000,
            clicks=500,
            cost=200.0
        ),
        TouchPoint(
            channel="小红书",
            channel_type=ChannelType.SOCIAL_MEDIA,
            campaign="KOL合作",
            ad_group="美妆博主",
            keyword="护肤",
            timestamp=now - timedelta(days=2),
            value=500.0,
            conversions=5,
            impressions=5000,
            clicks=200,
            cost=100.0
        ),
        TouchPoint(
            channel="淘宝",
            channel_type=ChannelType.ECOMMERCE,
            campaign="直通车",
            ad_group="面霜",
            keyword="保湿面霜",
            timestamp=now - timedelta(days=1),
            value=800.0,
            conversions=8,
            impressions=8000,
            clicks=400,
            cost=150.0
        ),
    ]


@pytest.fixture
def sample_alert_message():
    """示例告警消息"""
    return AlertMessage(
        title="测试告警",
        content="这是一条测试告警消息",
        priority=AlertPriority.P2_ATTENTION,
        source="test_module",
        timestamp=datetime.now()
    )


# ============================================================================
# AttributionEngine Tests
# ============================================================================

class TestAttributionEngine:
    """AttributionEngine 测试"""

    def test_init(self):
        """测试初始化"""
        engine = AttributionEngine()
        assert engine is not None

    def test_init_with_config(self):
        """测试带配置初始化"""
        config = {"default_model": "last_touch"}
        engine = AttributionEngine(config=config)
        assert engine is not None

    def test_analyze_first_touch(self, attribution_engine, sample_touchpoints):
        """测试首次触达归因"""
        now = datetime.now()
        report = attribution_engine.analyze(
            touchpoints=sample_touchpoints,
            model=AttributionModel.FIRST_TOUCH,
            start_date=now - timedelta(days=7),
            end_date=now
        )
        assert report is not None
        assert report.model == AttributionModel.FIRST_TOUCH

    def test_analyze_last_touch(self, attribution_engine, sample_touchpoints):
        """测试末次触达归因"""
        now = datetime.now()
        report = attribution_engine.analyze(
            touchpoints=sample_touchpoints,
            model=AttributionModel.LAST_TOUCH,
            start_date=now - timedelta(days=7),
            end_date=now
        )
        assert report is not None
        assert report.model == AttributionModel.LAST_TOUCH

    def test_analyze_linear(self, attribution_engine, sample_touchpoints):
        """测试线性归因"""
        now = datetime.now()
        report = attribution_engine.analyze(
            touchpoints=sample_touchpoints,
            model=AttributionModel.LINEAR,
            start_date=now - timedelta(days=7),
            end_date=now
        )
        assert report is not None
        assert report.model == AttributionModel.LINEAR

    def test_compare_models(self, attribution_engine, sample_touchpoints):
        """测试模型对比"""
        now = datetime.now()
        comparison = attribution_engine.compare_models(
            touchpoints=sample_touchpoints,
            start_date=now - timedelta(days=7),
            end_date=now
        )
        assert comparison is not None
        assert isinstance(comparison, dict)

    def test_export_report_json(self, attribution_engine, sample_touchpoints):
        """测试导出报告 JSON"""
        now = datetime.now()
        report = attribution_engine.analyze(
            touchpoints=sample_touchpoints,
            model=AttributionModel.LINEAR,
            start_date=now - timedelta(days=7),
            end_date=now
        )
        exported = attribution_engine.export_report(report, format='json')
        assert exported is not None
        assert isinstance(exported, str)


# ============================================================================
# SmartDecider Tests
# ============================================================================

class TestSmartDecider:
    """SmartDecider 测试"""

    def test_init(self):
        """测试初始化"""
        decider = SmartDecider()
        assert decider is not None

    def test_init_with_config(self):
        """测试带配置初始化"""
        config = {"auto_approve": False}
        decider = SmartDecider(config=config)
        assert decider is not None

    def test_analyze_and_decide(self, smart_decider):
        """测试分析并决策"""
        metrics = {
            "conversion_rate": 0.05,
            "cost_per_conversion": 50.0,
            "roi": 2.5,
            "ctr": 0.03
        }
        decisions = smart_decider.analyze_and_decide(metrics)
        assert decisions is not None
        assert isinstance(decisions, list)

    def test_analyze_and_decide_with_historical(self, smart_decider):
        """测试带历史数据分析"""
        metrics = {
            "conversion_rate": 0.03,
            "cost_per_conversion": 80.0,
            "roi": 1.2,
            "ctr": 0.02
        }
        historical = {
            "avg_conversion_rate": 0.05,
            "avg_roi": 2.0
        }
        decisions = smart_decider.analyze_and_decide(metrics, historical_data=historical)
        assert decisions is not None

    def test_get_pending_decisions(self, smart_decider):
        """测试获取待处理决策"""
        pending = smart_decider.get_pending_decisions()
        assert pending is not None
        assert isinstance(pending, list)

    def test_get_pending_decisions_with_priority(self, smart_decider):
        """测试按优先级获取待处理决策"""
        pending = smart_decider.get_pending_decisions(
            min_priority=DecisionPriority.P1_HIGH
        )
        assert pending is not None
        assert isinstance(pending, list)

    def test_approve_decision(self, smart_decider):
        """测试批准决策"""
        # 先生成一个决策
        metrics = {"conversion_rate": 0.03, "roi": 1.0}
        decisions = smart_decider.analyze_and_decide(metrics)
        if decisions:
            result = smart_decider.approve_decision(decisions[0].decision_id)
            assert result is True or result is False
        else:
            pytest.skip("无决策可批准")

    def test_skip_decision(self, smart_decider):
        """测试跳过决策"""
        metrics = {"conversion_rate": 0.03, "roi": 1.0}
        decisions = smart_decider.analyze_and_decide(metrics)
        if decisions:
            result = smart_decider.skip_decision(decisions[0].decision_id, reason="测试跳过")
            assert result is True or result is False
        else:
            pytest.skip("无决策可跳过")

    def test_generate_report(self, smart_decider):
        """测试生成报告"""
        now = datetime.now()
        report = smart_decider.generate_report(
            period_start=now - timedelta(days=7),
            period_end=now
        )
        assert report is not None

    def test_export_decisions(self, smart_decider):
        """测试导出决策"""
        metrics = {"conversion_rate": 0.03, "roi": 1.0}
        decisions = smart_decider.analyze_and_decide(metrics)
        if decisions:
            exported = smart_decider.export_decisions(decisions, format='json')
            assert exported is not None
        else:
            pytest.skip("无决策可导出")


# ============================================================================
# AlertNotifier Tests
# ============================================================================

class TestAlertNotifier:
    """AlertNotifier 测试"""

    def test_init(self):
        """测试初始化"""
        notifier = AlertNotifier()
        assert notifier is not None

    def test_configure_channel(self, alert_notifier):
        """测试配置渠道"""
        alert_notifier.configure_channel(
            AlertChannel.EMAIL,
            smtp_server="smtp.example.com",
            sender="test@example.com"
        )
        # 无异常即成功

    def test_send_email(self, alert_notifier, sample_alert_message):
        """测试发送邮件告警"""
        result = alert_notifier.send(
            sample_alert_message,
            channels=[AlertChannel.EMAIL]
        )
        assert result is not None
        assert isinstance(result, dict)

    def test_send_webhook(self, alert_notifier, sample_alert_message):
        """测试发送 Webhook 告警"""
        alert_notifier.configure_channel(
            AlertChannel.WEBHOOK,
            url="https://example.com/webhook"
        )
        result = alert_notifier.send(
            sample_alert_message,
            channels=[AlertChannel.WEBHOOK]
        )
        assert result is not None

    def test_get_history(self, alert_notifier):
        """测试获取历史记录"""
        history = alert_notifier.get_history(limit=10)
        assert history is not None
        assert isinstance(history, list)

    def test_send_force(self, alert_notifier, sample_alert_message):
        """测试强制发送"""
        result = alert_notifier.send(
            sample_alert_message,
            channels=[AlertChannel.EMAIL],
            force=True
        )
        assert result is not None
