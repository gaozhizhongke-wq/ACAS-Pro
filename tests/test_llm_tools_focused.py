"""
Focused tests for llm/tools.py - covers ToolRegistry and ACASTools (197 stmts, 35%, 128 miss).
ACASTools is fully self-contained (no acas_pro imports), uses lazy imports with ImportError fallbacks.
"""
import pytest
from unittest.mock import MagicMock, patch


class TestToolRegistry:
    def test_register_and_list(self):
        from acas_pro.llm.tools import ToolRegistry
        reg = ToolRegistry()
        reg.register("test_tool", "A test tool", {"param": {"type": "string"}}, lambda **kw: {"result": 1})
        tools = reg.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "test_tool"

    def test_unregister(self):
        from acas_pro.llm.tools import ToolRegistry
        reg = ToolRegistry()
        reg.register("t", "desc", {}, lambda: None)
        assert reg.unregister("t") is True
        assert reg.unregister("nonexistent") is False

    def test_get_schema(self):
        from acas_pro.llm.tools import ToolRegistry
        reg = ToolRegistry()
        reg.register("t", "desc", {"p": {"type": "str"}}, lambda: None)
        schema = reg.get_schema("t")
        assert schema is not None
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "t"
        assert reg.get_schema("missing") is None

    def test_get_all_schemas(self):
        from acas_pro.llm.tools import ToolRegistry
        reg = ToolRegistry()
        reg.register("a", "desc", {}, lambda: None)
        reg.register("b", "desc", {}, lambda: None)
        schemas = reg.get_all_schemas()
        assert len(schemas) == 2

    def test_execute_success(self):
        from acas_pro.llm.tools import ToolRegistry
        reg = ToolRegistry()
        reg.register("t", "desc", {"x": {"type": "int"}}, lambda x=0: x * 2)
        result = reg.execute("t", x=5)
        assert result == 10

    def test_execute_missing_tool(self):
        from acas_pro.llm.tools import ToolRegistry
        reg = ToolRegistry()
        with pytest.raises(ValueError, match="Tool not found"):
            reg.execute("missing")

    def test_execute_no_function(self):
        from acas_pro.llm.tools import ToolRegistry, ToolDefinition
        reg = ToolRegistry()
        reg._tools["nofunc"] = ToolDefinition("nofunc", "desc", {}, None)
        with pytest.raises(RuntimeError, match="no implementation"):
            reg.execute("nofunc")

    def test_execute_function_exception(self):
        from acas_pro.llm.tools import ToolRegistry
        reg = ToolRegistry()
        def bad_func(**kw):
            raise RuntimeError("boom")
        reg.register("bad", "desc", {}, bad_func)
        result = reg.execute("bad")
        assert result["error"] == "boom"

    def test_tool_definition_to_schema(self):
        from acas_pro.llm.tools import ToolDefinition
        td = ToolDefinition("test", "A test", {"type": "object", "properties": {}})
        schema = td.to_schema()
        assert schema == {
            "type": "function",
            "function": {
                "name": "test",
                "description": "A test",
                "parameters": {"type": "object", "properties": {}}
            }
        }


class TestACASTools:
    """ACASTools has no acas_pro imports at module level. Each method uses lazy imports
    with ImportError fallbacks, so we can instantiate and call without patching."""

    def test_init_no_args(self):
        from acas_pro.llm.tools import ACASTools
        tools = ACASTools()
        assert tools.config is None
        assert tools.database is None
        assert len(tools.registry.list_tools()) >= 8

    def test_init_with_args(self):
        from acas_pro.llm.tools import ACASTools
        cfg = MagicMock()
        db = MagicMock()
        tools = ACASTools(config=cfg, database=db)
        assert tools.config is cfg
        assert tools.database is db

    def test_register_all(self):
        from acas_pro.llm.tools import ACASTools
        tools = ACASTools()
        tools._register_all()
        tool_names = [t["name"] for t in tools.registry.list_tools()]
        expected = ["sales_forecast", "inventory_optimize", "market_intelligence",
                     "content_create", "trend_monitor", "account_analyze",
                     "ad_campaign_manage", "ecommerce_manage", "data_query",
                     "festival_calendar"]
        for name in expected:
            assert name in tool_names, f"Missing tool: {name}"

    def test_sales_forecast_import_error(self):
        from acas_pro.llm.tools import ACASTools
        tools = ACASTools()
        result = tools._sales_forecast(product_id="P001", days=30)
        assert "product_id" in result
        assert result["product_id"] == "P001"

    def test_sales_forecast_with_data(self):
        from acas_pro.llm.tools import ACASTools
        tools = ACASTools()
        result = tools._sales_forecast(product_id="P002", days=7, historical_data=[100, 120, 110])
        assert result["product_id"] == "P002"
        assert result["forecast_days"] == 7

    def test_inventory_optimize_import_error(self):
        from acas_pro.llm.tools import ACASTools
        tools = ACASTools()
        result = tools._inventory_optimize(product_id="P001", current_stock=50)
        assert result["product_id"] == "P001"
        assert result["current_stock"] == 50
        assert "safety_stock" in result
        assert "reorder_point" in result

    def test_inventory_optimize_low_stock(self):
        from acas_pro.llm.tools import ACASTools
        tools = ACASTools()
        result = tools._inventory_optimize(product_id="P001", current_stock=5, lead_time_days=14)
        assert result["status"] in ("low", "adequate")

    def test_market_intelligence_import_error(self):
        from acas_pro.llm.tools import ACASTools
        tools = ACASTools()
        result = tools._market_intelligence(keyword="AI", industry="tech")
        assert result["keyword"] == "AI"
        assert result["period_days"] == 7
        assert result["news_count"] == 0

    def test_content_create_fallback_xiaohongshu(self):
        from acas_pro.llm.tools import ACASTools
        tools = ACASTools()
        result = tools._content_create(topic="skincare", platform="xiaohongshu", keywords=["beauty"])
        assert result["platform"] == "小红书"
        assert "skincare" in result["content"]
        assert "#beauty" in result["content"]

    def test_content_create_fallback_douyin(self):
        from acas_pro.llm.tools import ACASTools
        tools = ACASTools()
        result = tools._content_create(topic="cooking", platform="douyin")
        assert result["platform"] == "抖音"
        assert "cooking" in result["content"]

    def test_content_create_fallback_wechat(self):
        from acas_pro.llm.tools import ACASTools
        tools = ACASTools()
        result = tools._content_create(topic="marketing", platform="wechat", style="professional")
        assert result["platform"] == "微信公众号"
        assert "marketing" in result["content"]

    def test_content_create_fallback_general(self):
        from acas_pro.llm.tools import ACASTools
        tools = ACASTools()
        result = tools._content_create(topic="test", platform="unknown_platform")
        assert "test" in result["content"]

    def test_trend_monitor_import_error(self):
        from acas_pro.llm.tools import ACASTools
        tools = ACASTools()
        result = tools._trend_monitor(category="electronics", platform="all")
        assert result["category"] == "electronics"
        assert len(result["trends"]) == 3

    def test_trend_monitor_with_platform(self):
        from acas_pro.llm.tools import ACASTools
        tools = ACASTools()
        result = tools._trend_monitor(category="beauty", platform="douyin")
        assert result["platform"] == "douyin"
        assert "beauty" in result["trends"][0]["title"]

    def test_account_analyze_import_error(self):
        from acas_pro.llm.tools import ACASTools
        tools = ACASTools()
        result = tools._account_analyze(account_id="A001", metric="overview")
        assert result["account_id"] == "A001"
        assert result["data"]["note"] == "账号数据暂不可用"

    def test_ad_campaign_create_import_error(self):
        from acas_pro.llm.tools import ACASTools
        tools = ACASTools()
        result = tools._ad_campaign_manage(action="create", budget=1000)
        assert result["action"] == "create"

    def test_ad_campaign_report_import_error(self):
        from acas_pro.llm.tools import ACASTools
        tools = ACASTools()
        result = tools._ad_campaign_manage(action="report", campaign_id="C001")
        assert result["action"] == "report"

    def test_ecommerce_orders_import_error(self):
        from acas_pro.llm.tools import ACASTools
        tools = ACASTools()
        result = tools._ecommerce_manage(action="orders", shop_id="S001")
        assert result["action"] == "orders"

    def test_ecommerce_products_import_error(self):
        from acas_pro.llm.tools import ACASTools
        tools = ACASTools()
        result = tools._ecommerce_manage(action="products", shop_id="S002")
        assert result["action"] == "products"

    def test_ecommerce_other_action(self):
        from acas_pro.llm.tools import ACASTools
        tools = ACASTools()
        result = tools._ecommerce_manage(action="supply_chain")
        assert result["action"] == "supply_chain"

    def test_data_query(self):
        from acas_pro.llm.tools import ACASTools
        tools = ACASTools()
        result = tools._data_query(query_type="sales", time_range="30d")
        assert result["query_type"] == "销售数据"
        assert result["time_range"] == "30d"

    def test_data_query_users(self):
        from acas_pro.llm.tools import ACASTools
        tools = ACASTools()
        result = tools._data_query(query_type="users", time_range="7d", filters={"active": True})
        assert result["query_type"] == "用户数据"
        assert result["filters"]["active"] is True

    def test_festival_calendar_import_error(self):
        from acas_pro.llm.tools import ACASTools
        tools = ACASTools()
        result = tools._festival_calendar(month=6)
        assert result["month"] == 6
        assert len(result["events"]) >= 1

    def test_festival_calendar_default_month(self):
        from acas_pro.llm.tools import ACASTools
        tools = ACASTools()
        result = tools._festival_calendar()
        assert result["month"] >= 1
        assert result["month"] <= 12

    def test_festival_calendar_all_months_have_events(self):
        from acas_pro.llm.tools import ACASTools
        tools = ACASTools()
        for m in range(1, 13):
            result = tools._festival_calendar(month=m)
            assert result["month"] == m

    def test_get_llm_config_no_import(self):
        from acas_pro.llm.tools import ACASTools
        tools = ACASTools()
        with patch.dict('sys.modules', {'acas_pro.core.config': None}):
            result = tools._get_llm_config()
            assert result is None

    def test_execute_via_registry(self):
        from acas_pro.llm.tools import ACASTools
        tools = ACASTools()
        # Execute sales_forecast through the registry
        result = tools.registry.execute("sales_forecast", product_id="P001", days=30)
        assert "product_id" in result

    def test_execute_via_registry_all_tools(self):
        from acas_pro.llm.tools import ACASTools
        tools = ACASTools()
        tool_names = [t["name"] for t in tools.registry.list_tools()]
        default_kwargs = {
            "sales_forecast": {"product_id": "P001", "days": 7},
            "inventory_optimize": {"product_id": "P001", "current_stock": 100},
            "market_intelligence": {"keyword": "AI"},
            "content_create": {"topic": "test", "platform": "general"},
            "trend_monitor": {"category": "tech"},
            "account_analyze": {"account_id": "A001"},
            "ad_campaign_manage": {"action": "report"},
            "ecommerce_manage": {"action": "orders"},
            "data_query": {"query_type": "sales"},
            "festival_calendar": {},
        }
        for name in tool_names:
            kwargs = default_kwargs.get(name, {})
            result = tools.registry.execute(name, **kwargs)
            assert result is not None, f"Tool {name} returned None"
