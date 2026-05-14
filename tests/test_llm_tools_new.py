"""Tests for llm.tools module (197 stmts, currently 17%)."""
import sys
from unittest.mock import MagicMock, patch
import pytest


class TestToolDefinition:
    def test_to_schema(self):
        from acas_pro.llm.tools import ToolDefinition
        td = ToolDefinition(
            name="test_tool",
            description="A test tool",
            parameters={"type": "object", "properties": {}},
            function=lambda: "ok"
        )
        schema = td.to_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "test_tool"
        assert schema["function"]["description"] == "A test tool"


class TestToolRegistry:
    def test_register_and_get(self):
        from acas_pro.llm.tools import ToolRegistry
        reg = ToolRegistry()
        reg.register("test", "desc", {"type": "object"}, lambda x: x)
        schema = reg.get_schema("test")
        assert schema is not None
        assert schema["function"]["name"] == "test"

    def test_get_schema_not_found(self):
        from acas_pro.llm.tools import ToolRegistry
        reg = ToolRegistry()
        assert reg.get_schema("nonexistent") is None

    def test_get_all_schemas(self):
        from acas_pro.llm.tools import ToolRegistry
        reg = ToolRegistry()
        reg.register("t1", "d1", {"type": "object"}, lambda: None)
        reg.register("t2", "d2", {"type": "object"}, lambda: None)
        schemas = reg.get_all_schemas()
        assert len(schemas) == 2

    def test_execute_success(self):
        from acas_pro.llm.tools import ToolRegistry
        reg = ToolRegistry()
        reg.register("add", "Add numbers", {"type": "object"}, lambda a, b: a + b)
        result = reg.execute("add", a=1, b=2)
        assert result == 3

    def test_execute_not_found(self):
        from acas_pro.llm.tools import ToolRegistry
        reg = ToolRegistry()
        with pytest.raises(ValueError, match="not found"):
            reg.execute("nonexistent")

    def test_execute_no_function(self):
        from acas_pro.llm.tools import ToolRegistry
        reg = ToolRegistry()
        reg.register("nofunc", "desc", {"type": "object"}, None)
        # Should return error dict since function is None
        with pytest.raises(RuntimeError, match="no implementation"):
            reg.execute("nofunc")

    def test_execute_function_error(self):
        from acas_pro.llm.tools import ToolRegistry
        reg = ToolRegistry()
        def bad_func():
            raise ValueError("test error")
        reg.register("bad", "desc", {"type": "object"}, bad_func)
        result = reg.execute("bad")
        assert "error" in result

    def test_unregister(self):
        from acas_pro.llm.tools import ToolRegistry
        reg = ToolRegistry()
        reg.register("temp", "desc", {"type": "object"}, lambda: None)
        assert reg.unregister("temp") is True
        assert reg.get_schema("temp") is None

    def test_unregister_not_found(self):
        from acas_pro.llm.tools import ToolRegistry
        reg = ToolRegistry()
        assert reg.unregister("nonexistent") is False

    def test_list_tools(self):
        from acas_pro.llm.tools import ToolRegistry
        reg = ToolRegistry()
        reg.register("t1", "Tool one", {"type": "object", "properties": {"a": {"type": "string"}}}, lambda: None)
        tools = reg.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "t1"
        assert "a" in tools[0]["parameters"]


class TestACASTools:
    """Tests for ACASTools class which registers many built-in tools."""

    def setup_method(self):
        self._patches = []
        # Patch heavy imports so ACASTools can initialize
        self._patches.append(patch('acas_pro.llm.tools.ACASTools._sales_forecast', MagicMock(return_value={"ok": True})))
        self._patches.append(patch('acas_pro.llm.tools.ACASTools._inventory_optimize', MagicMock(return_value={"ok": True})))
        self._patches.append(patch('acas_pro.llm.tools.ACASTools._market_intelligence', MagicMock(return_value={"ok": True})))
        self._patches.append(patch('acas_pro.llm.tools.ACASTools._content_create', MagicMock(return_value={"ok": True})))
        self._patches.append(patch('acas_pro.llm.tools.ACASTools._trend_monitor', MagicMock(return_value={"ok": True})))
        self._patches.append(patch('acas_pro.llm.tools.ACASTools._account_analyze', MagicMock(return_value={"ok": True})))
        self._patches.append(patch('acas_pro.llm.tools.ACASTools._ad_campaign_manage', MagicMock(return_value={"ok": True})))
        self._patches.append(patch('acas_pro.llm.tools.ACASTools._ecommerce_manage', MagicMock(return_value={"ok": True})))
        self._patches.append(patch('acas_pro.llm.tools.ACASTools._data_query', MagicMock(return_value={"ok": True})))
        self._patches.append(patch('acas_pro.llm.tools.ACASTools._festival_calendar', MagicMock(return_value={"ok": True})))
        for p in self._patches:
            p.start()
        if 'acas_pro.llm.tools' in sys.modules:
            del sys.modules['acas_pro.llm.tools']

    def teardown_method(self):
        for p in self._patches:
            p.stop()

    def test_acas_tools_initialization(self):
        from acas_pro.llm.tools import ACASTools
        tools = ACASTools()
        assert len(tools.registry._tools) == 10

    def test_tool_names(self):
        from acas_pro.llm.tools import ACASTools
        tools = ACASTools()
        names = list(tools.registry._tools.keys())
        assert "sales_forecast" in names
        assert "inventory_optimize" in names
        assert "market_intelligence" in names
        assert "content_create" in names
        assert "trend_monitor" in names
        assert "account_analyze" in names
        assert "ad_campaign_manage" in names
        assert "ecommerce_manage" in names
        assert "data_query" in names
        assert "festival_calendar" in names

    def test_get_all_schemas(self):
        from acas_pro.llm.tools import ACASTools
        tools = ACASTools()
        schemas = tools.registry.get_all_schemas()
        assert len(schemas) == 10

    def test_list_tools(self):
        from acas_pro.llm.tools import ACASTools
        tools = ACASTools()
        tool_list = tools.registry.list_tools()
        assert len(tool_list) == 10
