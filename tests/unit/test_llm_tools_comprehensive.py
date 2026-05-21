#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for llm/tools.py"""

import pytest
from unittest.mock import MagicMock, patch
from acas_pro.llm.tools import ToolDefinition, ToolRegistry, ACASTools


class TestToolDefinition:
    def test_to_schema(self):
        tool = ToolDefinition(
            name="test_tool",
            description="A test tool",
            parameters={"type": "object", "properties": {}},
            function=lambda x: x
        )
        schema = tool.to_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "test_tool"
        assert schema["function"]["description"] == "A test tool"


class TestToolRegistry:
    def setup_method(self):
        self.registry = ToolRegistry()

    def test_register(self):
        def dummy_func(x: int) -> int:
            return x * 2
        self.registry.register("double", "Double a number", {"type": "object", "properties": {"x": {"type": "integer"}}}, dummy_func)
        assert "double" in self.registry._tools

    def test_unregister_existing(self):
        def dummy_func():
            pass
        self.registry.register("test", "Test", {}, dummy_func)
        assert self.registry.unregister("test") is True
        assert "test" not in self.registry._tools

    def test_unregister_nonexistent(self):
        assert self.registry.unregister("nonexistent") is False

    def test_get_schema(self):
        def dummy_func():
            pass
        self.registry.register("test", "Test", {"type": "object", "properties": {}}, dummy_func)
        schema = self.registry.get_schema("test")
        assert schema is not None
        assert schema["function"]["name"] == "test"

    def test_get_schema_missing(self):
        assert self.registry.get_schema("missing") is None

    def test_get_all_schemas(self):
        def dummy_func():
            pass
        self.registry.register("a", "A", {}, dummy_func)
        self.registry.register("b", "B", {}, dummy_func)
        schemas = self.registry.get_all_schemas()
        assert len(schemas) == 2

    def test_execute(self):
        def add(a: int, b: int) -> int:
            return a + b
        self.registry.register("add", "Add numbers", {"type": "object", "properties": {}}, add)
        result = self.registry.execute("add", a=2, b=3)
        assert result == 5

    def test_execute_not_found(self):
        with pytest.raises(ValueError, match="Tool not found"):
            self.registry.execute("missing")

    def test_execute_no_function(self):
        self.registry._tools["no_func"] = ToolDefinition("no_func", "No func", {}, None)
        with pytest.raises(RuntimeError, match="no implementation"):
            self.registry.execute("no_func")

    def test_execute_error(self):
        def bad_func():
            raise RuntimeError("boom")
        self.registry.register("bad", "Bad", {}, bad_func)
        result = self.registry.execute("bad")
        assert "error" in result

    def test_list_tools(self):
        def dummy_func():
            pass
        self.registry.register("tool1", "Tool 1", {"type": "object", "properties": {"x": {"type": "string"}}}, dummy_func)
        tools = self.registry.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "tool1"


class TestACASTools:
    def setup_method(self):
        self.tools = ACASTools()

    def test_init(self):
        assert self.tools.registry is not None
        assert len(self.tools.registry.list_tools()) > 0

    def test_sales_forecast(self):
        result = self.tools._sales_forecast("prod_1", days=7)
        assert "product_id" in result
        assert result["product_id"] == "prod_1"
        assert "forecast_days" in result
        # Either has predictions or error
        assert "predictions" in result or "error" in result

    def test_sales_forecast_with_data(self):
        result = self.tools._sales_forecast("prod_1", days=7, historical_data=[10, 20, 30, 40, 50])
        assert "product_id" in result

    def test_inventory_optimize(self):
        result = self.tools._inventory_optimize("prod_1", current_stock=100)
        assert "product_id" in result
        assert result["current_stock"] == 100
        assert "safety_stock" in result
        assert "reorder_point" in result

    def test_inventory_optimize_fallback(self):
        result = self.tools._inventory_optimize("prod_1", current_stock=10, lead_time_days=14)
        assert result["product_id"] == "prod_1"
        assert "status" in result

    def test_market_intelligence(self):
        result = self.tools._market_intelligence(keyword="AI", days=7)
        assert "keyword" in result
        assert result["keyword"] == "AI"
        assert "period_days" in result

    def test_market_intelligence_no_keyword(self):
        result = self.tools._market_intelligence(industry="tech")
        assert "keyword" in result
        assert result["keyword"] == "tech"

    def test_content_create(self):
        result = self.tools._content_create(topic=" skincare", platform="xiaohongshu")
        assert "topic" in result
        assert "platform" in result
        assert "content" in result
        assert len(result["content"]) > 0

    def test_content_create_douyin(self):
        result = self.tools._content_create(topic="fitness", platform="douyin", style="humorous")
        assert "platform" in result
        assert result["content"] is not None

    def test_content_create_wechat(self):
        result = self.tools._content_create(topic="marketing", platform="wechat")
        assert "content" in result

    def test_content_create_general(self):
        result = self.tools._content_create(topic="test", platform="general")
        assert "content" in result

    def test_trend_monitor(self):
        result = self.tools._trend_monitor(category="beauty")
        assert "category" in result
        assert "trends" in result
        assert len(result["trends"]) > 0

    def test_trend_monitor_all(self):
        result = self.tools._trend_monitor(platform="all")
        assert "trends" in result

    def test_account_analyze(self):
        result = self.tools._account_analyze("account_1")
        assert "account_id" in result
        assert result["account_id"] == "account_1"

    def test_account_analyze_metric(self):
        result = self.tools._account_analyze("account_1", metric="growth")
        assert result["metric"] == "growth"

    def test_ad_campaign_create(self):
        result = self.tools._ad_campaign_manage("create", budget=1000)
        assert result["action"] == "create"
        assert "summary" in result

    def test_ad_campaign_report(self):
        result = self.tools._ad_campaign_manage("report", campaign_id="camp_1")
        assert result["action"] == "report"

    def test_ad_campaign_other(self):
        result = self.tools._ad_campaign_manage("pause")
        assert result["action"] == "pause"

    def test_ecommerce_orders(self):
        result = self.tools._ecommerce_manage("orders", shop_id="shop_1")
        assert result["action"] == "orders"
        assert "summary" in result

    def test_ecommerce_products(self):
        result = self.tools._ecommerce_manage("products", shop_id="shop_1")
        assert result["action"] == "products"

    def test_ecommerce_other(self):
        result = self.tools._ecommerce_manage("shop_stats")
        assert result["action"] == "shop_stats"

    def test_data_query_sales(self):
        result = self.tools._data_query("sales")
        assert "query_type" in result
        assert result["query_type"] == "销售数据"

    def test_data_query_users(self):
        result = self.tools._data_query("users", time_range="7d")
        assert result["time_range"] == "7d"

    def test_festival_calendar(self):
        result = self.tools._festival_calendar(month=6)
        assert "month" in result
        assert result["month"] == 6
        assert "events" in result
        assert len(result["events"]) > 0

    def test_festival_calendar_no_month(self):
        result = self.tools._festival_calendar()
        assert "month" in result
        assert "events" in result

    def test_festival_calendar_category(self):
        result = self.tools._festival_calendar(month=11, category="电商")
        assert "events" in result

    def test_get_llm_config(self):
        config = self.tools._get_llm_config()
        # May return None if no config available
        assert config is None or hasattr(config, 'api_key')

    def test_all_tools_registered(self):
        tools = self.tools.registry.list_tools()
        tool_names = [t["name"] for t in tools]
        expected = ["sales_forecast", "inventory_optimize", "market_intelligence",
                   "content_create", "trend_monitor", "account_analyze",
                   "ad_campaign_manage", "ecommerce_manage", "data_query", "festival_calendar"]
        for name in expected:
            assert name in tool_names, f"Tool {name} not registered"
