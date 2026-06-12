# -*- coding: utf-8 -*-
"""
Unit tests for ACAS Pro Agent Engine
"""
import json
import sqlite3
import time
from unittest.mock import MagicMock, patch

import pytest

from acas_pro.llm.agent_engine import (
    AgentEngine, AgentStatus, ActionType, AgentTask, AgentResult, AgentOrchestrator
)


def make_llm_response(content="", tool_calls=None, finish_reason="stop",
                      total_tokens=100, id="test-id"):
    """Helper: build a mock LLM response."""
    resp = MagicMock()
    resp.content = content
    resp.tool_calls = tool_calls or []
    resp.finish_reason = finish_reason
    resp.usage = {"total_tokens": total_tokens, "prompt_tokens": 50, "completion_tokens": 50}
    resp.id = id
    return resp


# ─────────────────────────────────────────────
# AgentEngine basic
# ─────────────────────────────────────────────

class TestAgentEngineInit:
    def test_init_without_registry(self):
        mock_llm = MagicMock()
        engine = AgentEngine(mock_llm)
        assert engine.llm is mock_llm
        assert engine.tools_registry is None
        assert engine.status == AgentStatus.IDLE
        assert engine._stop_flag is False
        assert engine._action_history == []

    def test_init_with_registry(self):
        mock_llm = MagicMock()
        mock_reg = MagicMock()
        engine = AgentEngine(mock_llm, tools_registry=mock_reg)
        assert engine.tools_registry is mock_reg


# ─────────────────────────────────────────────
# AgentEngine.execute() — no tool calls
# ─────────────────────────────────────────────

class TestAgentEngineExecuteText:
    def test_text_response_finish_stop(self):
        mock_llm = MagicMock()
        mock_llm.chat.return_value = make_llm_response(
            content="这是一个测试回答",
            finish_reason="stop"
        )
        engine = AgentEngine(mock_llm)
        task = AgentTask(id="t1", prompt="你好")

        result = engine.execute(task)

        assert result.status == AgentStatus.COMPLETED
        assert result.final_response == "这是一个测试回答"
        assert result.task_id == "t1"
        assert len(result.actions) == 1
        assert result.actions[0].type == ActionType.THINK
        mock_llm.chat.assert_called_once()

    def test_text_response_finish_length_triggers_continuation(self):
        """finish_reason='length' should add a continue message and NOT break."""
        mock_llm = MagicMock()
        # First call: length limit hit, Second call: stop
        mock_llm.chat.side_effect = [
            make_llm_response(content="部分回答...", finish_reason="length"),
            make_llm_response(content="完整回答", finish_reason="stop"),
        ]
        engine = AgentEngine(mock_llm)
        task = AgentTask(id="t2", prompt="写一篇长文章", max_steps=10)

        result = engine.execute(task)

        assert result.status == AgentStatus.COMPLETED
        assert mock_llm.chat.call_count == 2

    def test_text_response_finish_other(self):
        mock_llm = MagicMock()
        mock_llm.chat.return_value = make_llm_response(content="回答", finish_reason="other")
        engine = AgentEngine(mock_llm)
        result = engine.execute(AgentTask(id="t3", prompt="hi"))
        assert result.status == AgentStatus.COMPLETED


# ─────────────────────────────────────────────
# AgentEngine.execute() — with tool calls
# ─────────────────────────────────────────────

class TestAgentEngineExecuteToolCalls:
    def test_single_tool_call(self):
        mock_llm = MagicMock()
        tool_call = {
            "id": "call_1",
            "type": "function",
            "function": {
                "name": "sales_forecast",
                "arguments": json.dumps({"product_id": "P001", "days": 7})
            }
        }
        mock_llm.chat.side_effect = [
            make_llm_response(content="正在查询...", tool_calls=[tool_call]),
            make_llm_response(content="预测完成", finish_reason="stop"),
        ]

        mock_reg = MagicMock()
        mock_reg.get_all_schemas.return_value = [{"type": "function"}]
        mock_reg.execute.return_value = {"product_id": "P001", "predictions": [100, 110]}

        engine = AgentEngine(mock_llm, tools_registry=mock_reg)
        result = engine.execute(AgentTask(id="t4", prompt="预测", tools=["sales_forecast"]))

        assert result.status == AgentStatus.COMPLETED
        assert len(result.actions) == 3  # THINK + USE_TOOL + THINK
        tool_action = result.actions[1]
        assert tool_action.type == ActionType.USE_TOOL
        assert tool_action.tool_name == "sales_forecast"
        assert tool_action.tool_args == {"product_id": "P001", "days": 7}
        assert tool_action.result == {"product_id": "P001", "predictions": [100, 110]}
        mock_reg.execute.assert_called_once_with("sales_forecast", product_id="P001", days=7)

    def test_tool_call_sqlite3_error_caught(self):
        mock_llm = MagicMock()
        tool_call = {
            "id": "call_2",
            "type": "function",
            "function": {"name": "sales_forecast", "arguments": json.dumps({"product_id": "P002"})}
        }
        mock_llm.chat.side_effect = [
            make_llm_response(content="调用工具", tool_calls=[tool_call]),
            make_llm_response(content="完成", finish_reason="stop"),
        ]
        mock_reg = MagicMock()
        mock_reg.get_all_schemas.return_value = []
        mock_reg.execute.side_effect = sqlite3.Error("DB error")

        engine = AgentEngine(mock_llm, tools_registry=mock_reg)
        result = engine.execute(AgentTask(id="t5", prompt="查"))

        # Should not raise; tool action should be ERROR type
        tool_action = result.actions[1]
        assert tool_action.type == ActionType.ERROR
        assert "DB error" in tool_action.result.get("error", "")

    def test_tool_call_value_error_caught(self):
        mock_llm = MagicMock()
        tool_call = {
            "id": "call_3",
            "type": "function",
            "function": {"name": "inventory_optimize", "arguments": json.dumps({"product_id": "P003"})}
        }
        mock_llm.chat.side_effect = [
            make_llm_response(content="调", tool_calls=[tool_call]),
            make_llm_response(content="完成", finish_reason="stop"),
        ]
        mock_reg = MagicMock()
        mock_reg.get_all_schemas.return_value = []
        mock_reg.execute.side_effect = ValueError("bad value")

        engine = AgentEngine(mock_llm, tools_registry=mock_reg)
        result = engine.execute(AgentTask(id="t6", prompt="调"))

        tool_action = result.actions[1]
        assert tool_action.type == ActionType.ERROR


# ─────────────────────────────────────────────
# AgentEngine.execute() — max_steps & timeout
# ─────────────────────────────────────────────

class TestAgentEngineExecuteLimits:
    def test_max_steps_reached(self):
        mock_llm = MagicMock()
        # All responses are tool calls so loop never ends
        tool_call = {
            "id": "call_x", "type": "function",
            "function": {"name": "noop", "arguments": json.dumps({})}
        }
        mock_llm.chat.return_value = make_llm_response(
            content="继续", tool_calls=[tool_call]
        )
        mock_reg = MagicMock()
        mock_reg.get_all_schemas.return_value = []
        mock_reg.execute.return_value = {"ok": True}

        engine = AgentEngine(mock_llm, tools_registry=mock_reg)
        task = AgentTask(id="t7", prompt="repeat", max_steps=3)
        result = engine.execute(task)

        # Should hit max_steps and break
        assert result.status == AgentStatus.COMPLETED
        assert "[达到最大步骤限制 3]" in result.final_response
        assert mock_llm.chat.call_count == 3

    def test_timeout_triggers_failure(self):
        """Timeout fires when elapsed > task.timeout_seconds.
        We mock LLM to return a tool_call (loops forever) while patching time.time
        so elapsed jumps past timeout_seconds.
        """
        mock_llm = MagicMock()
        tool_call = {
            "id": "call_t", "type": "function",
            "function": {"name": "noop", "arguments": json.dumps({})}
        }
        mock_llm.chat.return_value = make_llm_response(
            content="continuing...", tool_calls=[tool_call]
        )
        mock_reg = MagicMock()
        mock_reg.get_all_schemas.return_value = []
        mock_reg.execute.return_value = {"ok": True}

        engine = AgentEngine(mock_llm, tools_registry=mock_reg)
        task = AgentTask(id="t8", prompt="slow", timeout_seconds=1, max_steps=10)

        with patch("acas_pro.llm.agent_engine.time.time") as mock_t:
            # Call 1: start_time=0; Call 2: elapsed=0; Call 3: elapsed=999 → timeout
            mock_t.side_effect = [0.0, 0.0, 999.0, 999.0, 999.0]
            result = engine.execute(task)

        assert result.status == AgentStatus.FAILED
        assert "执行超时" in result.final_response


# ─────────────────────────────────────────────
# AgentEngine.execute() — outer exception
# ─────────────────────────────────────────────

class TestAgentEngineExecuteExceptions:
    @pytest.mark.parametrize("exc", [
        sqlite3.Error("db"),
        ValueError("val"),
        RuntimeError("run"),
    ])
    def test_outer_exception_caught(self, exc):
        mock_llm = MagicMock()
        mock_llm.chat.side_effect = exc
        engine = AgentEngine(mock_llm)
        result = engine.execute(AgentTask(id="t9", prompt="err"))

        assert result.status == AgentStatus.FAILED
        assert "执行失败" in result.final_response


# ─────────────────────────────────────────────
# AgentEngine.execute_async()
# ─────────────────────────────────────────────

class TestAgentEngineExecuteAsync:
    def test_async_basic(self):
        mock_llm = MagicMock()
        mock_llm.chat.return_value = make_llm_response(content="async回答", finish_reason="stop")
        engine = AgentEngine(mock_llm)

        results = []

        def cb(result):
            results.append(result)

        thread = engine.execute_async(AgentTask(id="t10", prompt="async"), callback=cb)
        thread.join(timeout=5)

        assert len(results) == 1
        assert results[0].final_response == "async回答"

    def test_async_with_string_task(self):
        """execute_async accepts str task (defensive conversion). AgentTask requires id."""
        mock_llm = MagicMock()
        mock_llm.chat.return_value = make_llm_response(content="str回答", finish_reason="stop")
        engine = AgentEngine(mock_llm)

        results = []
        thread = engine.execute_async(
            AgentTask(id="async_str", prompt="string task"),
            callback=lambda r: results.append(r)
        )
        thread.join(timeout=5)

        assert len(results) == 1
        assert results[0].final_response == "str回答"


# ─────────────────────────────────────────────
# AgentEngine.stop()
# ─────────────────────────────────────────────

class TestAgentEngineStop:
    def test_stop_sets_flag_and_status(self):
        mock_llm = MagicMock()
        mock_llm.chat.side_effect = lambda *a, **kw: time.sleep(10)
        engine = AgentEngine(mock_llm)

        # Start async and immediately stop
        thread = engine.execute_async(AgentTask(id="t11", prompt="block", timeout_seconds=100))
        time.sleep(0.1)
        engine.stop()
        thread.join(timeout=2)

        assert engine.status == AgentStatus.STOPPED


# ─────────────────────────────────────────────
# AgentEngine._build_messages
# ─────────────────────────────────────────────

class TestAgentEngineBuildMessages:
    def test_without_context(self):
        mock_llm = MagicMock()
        engine = AgentEngine(mock_llm)
        task = AgentTask(id="t12", prompt="hello")

        msgs = engine._build_messages(task)

        assert msgs[0].role == "system"
        assert msgs[0].content == engine.SYSTEM_PROMPT
        assert msgs[-1].role == "user"
        assert msgs[-1].content == "hello"

    def test_with_context(self):
        mock_llm = MagicMock()
        engine = AgentEngine(mock_llm)
        task = AgentTask(id="t13", prompt="分析", context={"sales": 1000})

        msgs = engine._build_messages(task)

        assert len(msgs) == 3  # system + context + user
        context_msg = msgs[1]
        assert context_msg.role == "system"
        assert "sales" in context_msg.content


# ─────────────────────────────────────────────
# AgentEngine._get_tool_schemas
# ─────────────────────────────────────────────

class TestAgentEngineGetToolSchemas:
    def test_no_registry(self):
        engine = AgentEngine(MagicMock())
        assert engine._get_tools_schema([]) == []

    def test_all_tools(self):
        mock_reg = MagicMock()
        mock_reg.get_all_schemas.return_value = [{"name": "sales_forecast"}, {"name": "inventory"}]
        engine = AgentEngine(MagicMock(), tools_registry=mock_reg)
        schemas = engine._get_tools_schema([])
        assert schemas == [{"name": "sales_forecast"}, {"name": "inventory"}]
        mock_reg.get_all_schemas.assert_called_once()

    def test_filtered_tools(self):
        mock_reg = MagicMock()
        mock_reg.get_schema.side_effect = lambda n: {"name": n}
        engine = AgentEngine(MagicMock(), tools_registry=mock_reg)
        schemas = engine._get_tools_schema(["sales_forecast", "inventory"])
        assert schemas == [{"name": "sales_forecast"}, {"name": "inventory"}]


# ─────────────────────────────────────────────
# AgentEngine._execute_tool
# ─────────────────────────────────────────────

class TestAgentEngineExecuteTool:
    def test_no_registry_raises(self):
        engine = AgentEngine(MagicMock())
        with pytest.raises(RuntimeError, match="No tools registry"):
            engine._execute_tool("some_tool", {})

    def test_registry_called(self):
        mock_reg = MagicMock()
        mock_reg.execute.return_value = {"result": "ok"}
        engine = AgentEngine(MagicMock(), tools_registry=mock_reg)
        result = engine._execute_tool("test_tool", {"arg": 1})
        assert result == {"result": "ok"}
        mock_reg.execute.assert_called_once_with("test_tool", arg=1)


# ─────────────────────────────────────────────
# AgentOrchestrator
# ─────────────────────────────────────────────

class TestAgentOrchestratorCreateAgent:
    def test_create_agent_no_specialty(self):
        mock_llm = MagicMock()  # noqa: F841
        mock_reg = MagicMock()
        config = MagicMock()
        orch = AgentOrchestrator(config, tools_registry=mock_reg)

        agent = orch.create_agent("agent_1")

        assert "agent_1" in orch._agents
        assert agent.tools_registry is mock_reg
        assert agent.llm is orch._agents["agent_1"].llm

    def test_create_agent_with_specialty(self):
        config = MagicMock()
        orch = AgentOrchestrator(config)
        agent = orch.create_agent("analyst", specialty="数据分析")

        assert "analyst" in orch._agents
        assert "数据分析" in agent.SYSTEM_PROMPT


class TestAgentOrchestratorExecuteParallel:
    def test_parallel_basic(self):
        """execute_parallel creates agents and runs them in threads."""
        mock_llm_instance = MagicMock()
        mock_llm_instance.chat.return_value = make_llm_response(
            content="parallel完成", finish_reason="stop"
        )
        config = MagicMock()
        orch = AgentOrchestrator(config)
        # LLMClient is imported into agent_engine namespace
        with patch("acas_pro.llm.agent_engine.LLMClient", return_value=mock_llm_instance):
            tasks = [
                AgentTask(id="p1", prompt="task1"),
                AgentTask(id="p2", prompt="task2"),
            ]
            results = orch.execute_parallel(tasks)

        assert "p1" in results
        assert "p2" in results


class TestAgentOrchestratorExecutePipeline:
    def test_pipeline_sequential(self):
        """execute_pipeline runs tasks sequentially; pass_results=True injects prior result."""
        mock_llm_instance = MagicMock()
        mock_llm_instance.chat.return_value = make_llm_response(
            content="pipeline完成", finish_reason="stop"
        )
        config = MagicMock()
        orch = AgentOrchestrator(config)
        with patch("acas_pro.llm.agent_engine.LLMClient", return_value=mock_llm_instance):
            tasks = [
                AgentTask(id="step1", prompt="step1"),
                AgentTask(id="step2", prompt="step2", context={}),
            ]
            results = orch.execute_pipeline(tasks, pass_results=True)

        assert len(results) == 2
        assert results[0].final_response == "pipeline完成"
        # Second task has context injected from first result
        assert "step2" in [r.task_id for r in results]

    def test_pipeline_stops_on_failure(self):
        config = MagicMock()
        orch = AgentOrchestrator(config)
        mock_llm_instance = MagicMock()
        mock_llm_instance.chat.return_value = make_llm_response(
            content="fail", finish_reason="stop"
        )
        with patch("acas_pro.llm.llm_client.LLMClient", return_value=mock_llm_instance):
            tasks = [
                AgentTask(id="f1", prompt="f1"),
                AgentTask(id="f2", prompt="f2"),
                AgentTask(id="f3", prompt="f3"),
            ]
            # First task succeeds, second fails
            with patch.object(AgentEngine, "execute", side_effect=[
                AgentResult(task_id="f1", status=AgentStatus.COMPLETED,
                            final_response="ok", actions=[], total_tokens=0, total_time_ms=0),
                AgentResult(task_id="f2", status=AgentStatus.FAILED,
                            final_response="fail", actions=[], total_tokens=0, total_time_ms=0),
            ]):
                results = orch.execute_pipeline(tasks)

        # Should stop after FAILED
        assert len(results) == 2
        assert results[-1].status == AgentStatus.FAILED


# ─────────────────────────────────────────────
# Status / history helpers
# ─────────────────────────────────────────────

class TestAgentEngineHelpers:
    def test_get_status(self):
        engine = AgentEngine(MagicMock())
        assert engine.get_status() == AgentStatus.IDLE

    def test_get_action_history_empty(self):
        engine = AgentEngine(MagicMock())
        assert engine.get_action_history() == []

    def test_get_action_history_after_run(self):
        mock_llm = MagicMock()
        mock_llm.chat.return_value = make_llm_response(content="answer", finish_reason="stop")
        engine = AgentEngine(mock_llm)
        engine.execute(AgentTask(id="h1", prompt="hi"))
        history = engine.get_action_history()
        assert len(history) == 1
        assert history[0].type == ActionType.THINK
