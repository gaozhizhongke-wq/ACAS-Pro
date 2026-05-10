#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - LLM Tools Tests
"""

import pytest
from unittest.mock import Mock, patch

from acas_pro.llm.tools import ToolRegistry, ToolDefinition, ACASTools


class TestToolDefinition:
    """Tool definition tests"""
    
    def test_tool_creation(self):
        """Test tool creation"""
        def dummy_func():
            return "test"
        
        tool = ToolDefinition(
            name="test_tool",
            description="Test tool",
            parameters={"type": "object"},
            function=dummy_func
        )
        
        assert tool.name == "test_tool"
        assert tool.function is not None
    
    def test_tool_to_schema(self):
        """Test tool to schema"""
        tool = ToolDefinition(
            name="test_tool",
            description="Test tool",
            parameters={"type": "object", "properties": {}}
        )
        
        schema = tool.to_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "test_tool"


class TestToolRegistry:
    """Tool registry tests"""
    
    @pytest.fixture
    def registry(self):
        return ToolRegistry()
    
    def test_init(self, registry):
        """Test initialization"""
        assert len(registry._tools) == 0
    
    def test_register(self, registry):
        """Test register tool"""
        def dummy_func():
            return "result"
        
        registry.register(
            name="test_tool",
            description="Test tool",
            parameters={"type": "object"},
            function=dummy_func
        )
        
        assert "test_tool" in registry._tools
    
    def test_unregister(self, registry):
        """Test unregister tool"""
        def dummy_func():
            pass
        
        registry.register("test_tool", "Test", {}, dummy_func)
        result = registry.unregister("test_tool")
        
        assert result is True
        assert "test_tool" not in registry._tools
    
    def test_unregister_not_found(self, registry):
        """Test unregister not found"""
        result = registry.unregister("nonexistent")
        assert result is False
    
    def test_get_schema(self, registry):
        """Test get schema"""
        def dummy_func():
            pass
        
        registry.register("test_tool", "Test", {"type": "object"}, dummy_func)
        schema = registry.get_schema("test_tool")
        
        assert schema is not None
        assert schema["type"] == "function"
    
    def test_get_schema_not_found(self, registry):
        """Test get schema not found"""
        schema = registry.get_schema("nonexistent")
        assert schema is None
    
    def test_get_all_schemas(self, registry):
        """Test get all schemas"""
        def dummy_func():
            pass
        
        registry.register("tool1", "Tool 1", {}, dummy_func)
        registry.register("tool2", "Tool 2", {}, dummy_func)
        
        schemas = registry.get_all_schemas()
        assert len(schemas) == 2
    
    def test_execute(self, registry):
        """Test execute tool"""
        def dummy_func(arg1, arg2):
            return {"arg1": arg1, "arg2": arg2}
        
        registry.register("test_tool", "Test", {}, dummy_func)
        result = registry.execute("test_tool", arg1="a", arg2="b")
        
        assert result["arg1"] == "a"
        assert result["arg2"] == "b"
    
    def test_execute_not_found(self, registry):
        """Test execute not found"""
        with pytest.raises(ValueError):
            registry.execute("nonexistent")
    
    def test_execute_no_function(self, registry):
        """Test execute without function"""
        registry.register("no_func", "No func", {}, None)
        
        with pytest.raises(RuntimeError):
            registry.execute("no_func")
    
    def test_list_tools(self, registry):
        """Test list tools"""
        def dummy_func():
            pass
        
        registry.register("test_tool", "Test description", {"properties": {}}, dummy_func)
        tools = registry.list_tools()
        
        assert len(tools) == 1
        assert tools[0]["name"] == "test_tool"


class TestACASTools:
    """ACAS tools tests"""
    
    def test_init(self):
        """Test initialization"""
        tools = ACASTools()
        assert tools.registry is not None
    
    def test_tools_registered(self):
        """Test tools are registered"""
        tools = ACASTools()
        
        # Check some expected tools
        schemas = tools.registry.get_all_schemas()
        tool_names = [s["function"]["name"] for s in schemas]
        
        assert "sales_forecast" in tool_names
        assert "inventory_optimize" in tool_names
        assert "market_intelligence" in tool_names
        assert "content_create" in tool_names
    
    def test_sales_forecast(self):
        """Test sales forecast tool"""
        tools = ACASTools()
        result = tools._sales_forecast(product_id="test_001", days=7)
        
        assert "product_id" in result
        assert result["product_id"] == "test_001"
        assert "forecast_days" in result
    
    def test_inventory_optimize(self):
        """Test inventory optimize tool"""
        tools = ACASTools()
        result = tools._inventory_optimize(
            product_id="test_001",
            current_stock=100,
            lead_time_days=7
        )
        
        assert "product_id" in result
        assert "safety_stock" in result
        assert "reorder_point" in result
    
    def test_market_intelligence(self):
        """Test market intelligence tool"""
        tools = ACASTools()
        result = tools._market_intelligence(keyword="测试", days=7)
        
        assert "keyword" in result
        assert "period_days" in result
    
    def test_content_create(self):
        """Test content create tool"""
        tools = ACASTools()
        result = tools._content_create(
            topic="测试主题",
            platform="xiaohongshu",
            style="casual"
        )
        
        assert "topic" in result
        assert "platform" in result
        assert "content" in result
    
    def test_trend_monitor(self):
        """Test trend monitor tool"""
        tools = ACASTools()
        result = tools._trend_monitor(category="美妆", platform="all")
        
        assert "category" in result
        assert "trends" in result
    
    def test_account_analyze(self):
        """Test account analyze tool"""
        tools = ACASTools()
        result = tools._account_analyze(account_id="acc_001", metric="overview")
        
        assert "account_id" in result
        assert "metric" in result
    
    def test_ad_campaign_manage(self):
        """Test ad campaign manage tool"""
        tools = ACASTools()
        result = tools._ad_campaign_manage(action="create", budget=1000.0)
        
        assert "action" in result
        assert result["action"] == "create"
    
    def test_ecommerce_manage(self):
        """Test ecommerce manage tool"""
        tools = ACASTools()
        result = tools._ecommerce_manage(action="orders", shop_id="shop_001")
        
        assert "action" in result
        assert result["action"] == "orders"
    
    def test_data_query(self):
        """Test data query tool"""
        tools = ACASTools()
        result = tools._data_query(query_type="sales", time_range="30d")
        
        assert "query_type" in result
        assert "time_range" in result
    
    def test_festival_calendar(self):
        """Test festival calendar tool"""
        tools = ACASTools()
        result = tools._festival_calendar(month=6)
        
        assert "month" in result
        assert "events" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
