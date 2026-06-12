#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for llm/tools.py - ToolRegistry and ToolDefinition."""

from unittest.mock import MagicMock
import sys
import pytest

if 'numpy' not in sys.modules:
    sys.modules['numpy'] = MagicMock()


class TestToolDefinition:
    def test_to_schema(self):
        from acas_pro.llm.tools import ToolDefinition
        td = ToolDefinition(
            name="test_tool",
            description="A test tool",
            parameters={"type": "object", "properties": {"x": {"type": "integer"}}}
        )
        schema = td.to_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "test_tool"
        assert "parameters" in schema["function"]

class TestToolRegistry:
    def test_register(self):
        from acas_pro.llm.tools import ToolRegistry
        reg = ToolRegistry()
        reg.register("add", "Add numbers", {"type": "object"}, lambda a, b: a + b)
        assert len(reg.list_tools()) == 1

    def test_unregister(self):
        from acas_pro.llm.tools import ToolRegistry
        reg = ToolRegistry()
        reg.register("add", "Add", {"type": "object"}, lambda a, b: a + b)
        assert reg.unregister("add") == True  # noqa: E712
        assert reg.unregister("add") == False  # noqa: E712

    def test_get_schema(self):
        from acas_pro.llm.tools import ToolRegistry
        reg = ToolRegistry()
        reg.register("test", "Test", {"type": "object"}, lambda: None)
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
        reg.register("a", "A", {"type": "object"}, lambda: None)
        reg.register("b", "B", {"type": "object"}, lambda: None)
        schemas = reg.get_all_schemas()
        assert len(schemas) == 2

    def test_execute(self):
        from acas_pro.llm.tools import ToolRegistry
        reg = ToolRegistry()
        reg.register("add", "Add", {"type": "object"}, lambda a, b: a + b)
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
        reg.register("nofunc", "No func", {"type": "object"}, None)
        with pytest.raises(RuntimeError, match="no implementation"):
            reg.execute("nofunc")

    def test_execute_error_handling(self):
        from acas_pro.llm.tools import ToolRegistry
        def bad_fn():
            raise ValueError("oops")
        reg = ToolRegistry()
        reg.register("bad", "Bad", {"type": "object"}, bad_fn)
        result = reg.execute("bad")
        assert "error" in result

    def test_list_tools(self):
        from acas_pro.llm.tools import ToolRegistry
        reg = ToolRegistry()
        reg.register("calc", "Calculator", {
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}}
        }, lambda a, b: a + b)
        tools = reg.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "calc"
        assert "a" in tools[0]["parameters"]
