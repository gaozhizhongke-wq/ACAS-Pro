"""Tests for LLM engines (claude_engine, gemini_engine) - currently at 0%."""
import sys
from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import dataclass
from typing import List

import pytest


class TestClaudeEngine:
    """Tests for llm.claude_engine module."""

    def setup_method(self):
        self._patches = []
        # Mock anthropic
        mock_anthropic = MagicMock()
        self.mock_client = MagicMock()
        mock_anthropic.Anthropic = MagicMock(return_value=self.mock_client)
        self._patches.append(patch.dict('sys.modules', {'anthropic': mock_anthropic}))
        # Need base_engine
        if 'acas_pro.llm.base_engine' not in sys.modules:
            # Define base classes inline
            from typing import Optional, Any, Iterator
            from dataclasses import dataclass, field

            @dataclass
            class LLMMessage:
                role: str
                content: str

            @dataclass
            class LLMResponse:
                content: str
                model: str = ""
                usage: dict = field(default_factory=dict)
                finish_reason: str = ""

            @dataclass
            class LLMStreamChunk:
                content: str
                is_finished: bool = False

            class BaseLLMEngine:
                pass

            mod = type(sys)('acas_pro.llm.base_engine')
            mod.LLMMessage = LLMMessage
            mod.LLMResponse = LLMResponse
            mod.LLMStreamChunk = LLMStreamChunk
            mod.BaseLLMEngine = BaseLLMEngine
            sys.modules['acas_pro.llm.base_engine'] = mod

        for p in self._patches:
            p.start()
        if 'acas_pro.llm.claude_engine' in sys.modules:
            del sys.modules['acas_pro.llm.claude_engine']

    def teardown_method(self):
        for p in self._patches:
            p.stop()

    def test_claude_config(self):
        from acas_pro.llm.claude_engine import ClaudeConfig
        cfg = ClaudeConfig(api_key="sk-test", model="claude-3-opus-20240229")
        assert cfg.api_key == "sk-test"
        assert cfg.model == "claude-3-opus-20240229"
        assert cfg.max_tokens == 4096
        assert cfg.temperature == 0.7

    def test_claude_engine_creation(self):
        from acas_pro.llm.claude_engine import ClaudeEngine, ClaudeConfig
        cfg = ClaudeConfig(api_key="sk-test")
        engine = ClaudeEngine(cfg)
        assert engine.name == "claude"
        assert len(engine.models) == 4

    def test_claude_convert_messages(self):
        from acas_pro.llm.claude_engine import ClaudeEngine, ClaudeConfig
        from acas_pro.llm.base_engine import LLMMessage
        engine = ClaudeEngine(ClaudeConfig(api_key="sk-test"))
        msgs = [
            LLMMessage(role="system", content="You are helpful"),
            LLMMessage(role="user", content="Hello"),
        ]
        system, converted = engine._convert_messages(msgs)
        assert system == "You are helpful"
        assert len(converted) == 1
        assert converted[0]["role"] == "user"

    def test_claude_chat(self):
        from acas_pro.llm.claude_engine import ClaudeEngine, ClaudeConfig
        from acas_pro.llm.base_engine import LLMMessage

        engine = ClaudeEngine(ClaudeConfig(api_key="sk-test"))

        # Mock API response
        mock_response = MagicMock()
        mock_content = MagicMock()
        mock_content.text = "Hello! How can I help?"
        mock_response.content = [mock_content]
        mock_response.model = "claude-3-opus-20240229"
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 20
        mock_response.stop_reason = "end_turn"
        self.mock_client.messages.create.return_value = mock_response

        msgs = [LLMMessage(role="user", content="Hi")]
        result = engine.chat(msgs)
        assert result.content == "Hello! How can I help?"
        assert result.model == "claude-3-opus-20240229"

    def test_claude_chat_error(self):
        from acas_pro.llm.claude_engine import ClaudeEngine, ClaudeConfig
        from acas_pro.llm.base_engine import LLMMessage

        engine = ClaudeEngine(ClaudeConfig(api_key="sk-test"))
        self.mock_client.messages.create.side_effect = Exception("API error")

        with pytest.raises(RuntimeError, match="Claude API error"):
            engine.chat([LLMMessage(role="user", content="Hi")])

    def test_claude_quick_chat(self):
        from acas_pro.llm.claude_engine import ClaudeEngine, ClaudeConfig

        engine = ClaudeEngine(ClaudeConfig(api_key="sk-test"))
        mock_response = MagicMock()
        mock_content = MagicMock()
        mock_content.text = "OK"
        mock_response.content = [mock_content]
        mock_response.model = "claude-3-opus"
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 5
        mock_response.usage.output_tokens = 2
        mock_response.stop_reason = "end_turn"
        self.mock_client.messages.create.return_value = mock_response

        result = engine.quick_chat("Hi", "Reply: OK")
        assert result == "OK"

    def test_claude_count_tokens(self):
        from acas_pro.llm.claude_engine import ClaudeEngine, ClaudeConfig
        engine = ClaudeEngine(ClaudeConfig(api_key="sk-test"))
        count = engine.count_tokens("Hello world!")
        assert count > 0

    def test_create_claude_engine_with_key(self):
        from acas_pro.llm.claude_engine import create_claude_engine
        engine = create_claude_engine(api_key="sk-test")
        assert engine.name == "claude"

    def test_create_claude_engine_no_key(self):
        from acas_pro.llm.claude_engine import create_claude_engine
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="API key required"):
                create_claude_engine()

    def test_claude_health_check_healthy(self):
        from acas_pro.llm.claude_engine import ClaudeEngine, ClaudeConfig
        engine = ClaudeEngine(ClaudeConfig(api_key="sk-test"))
        mock_response = MagicMock()
        mock_content = MagicMock()
        mock_content.text = "OK"
        mock_response.content = [mock_content]
        mock_response.model = "claude-3-opus"
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 5
        mock_response.usage.output_tokens = 2
        mock_response.stop_reason = "end_turn"
        self.mock_client.messages.create.return_value = mock_response

        result = engine.health_check()
        assert result["status"] == "healthy"

    def test_claude_health_check_unhealthy(self):
        from acas_pro.llm.claude_engine import ClaudeEngine, ClaudeConfig
        engine = ClaudeEngine(ClaudeConfig(api_key="sk-test"))
        self.mock_client.messages.create.side_effect = Exception("error")
        result = engine.health_check()
        assert result["status"] == "unhealthy"

    def test_claude_chat_no_client(self):
        from acas_pro.llm.claude_engine import ClaudeEngine, ClaudeConfig
        from acas_pro.llm.base_engine import LLMMessage
        engine = ClaudeEngine(ClaudeConfig(api_key="sk-test"))
        engine._client = None
        with pytest.raises(RuntimeError):
            engine.chat([LLMMessage(role="user", content="Hi")])


class TestGeminiEngine:
    """Tests for llm.gemini_engine module."""

    def setup_method(self):
        self._patches = []
        # Mock google.generativeai
        mock_genai = MagicMock()
        self.mock_model = MagicMock()
        mock_genai.GenerativeModel = MagicMock(return_value=self.mock_model)
        mock_genai.configure = MagicMock()
        mock_google = MagicMock()
        mock_google.generativeai = mock_genai
        self._patches.append(patch.dict('sys.modules', {'google': mock_google, 'google.generativeai': mock_genai}))

        # Ensure base_engine exists
        if 'acas_pro.llm.base_engine' not in sys.modules:
            from typing import Optional, Any, Iterator
            from dataclasses import dataclass, field

            @dataclass
            class LLMMessage:
                role: str
                content: str

            @dataclass
            class LLMResponse:
                content: str
                model: str = ""
                usage: dict = field(default_factory=dict)
                finish_reason: str = ""

            @dataclass
            class LLMStreamChunk:
                content: str
                is_finished: bool = False

            class BaseLLMEngine:
                pass

            mod = type(sys)('acas_pro.llm.base_engine')
            mod.LLMMessage = LLMMessage
            mod.LLMResponse = LLMResponse
            mod.LLMStreamChunk = LLMStreamChunk
            mod.BaseLLMEngine = BaseLLMEngine
            sys.modules['acas_pro.llm.base_engine'] = mod

        for p in self._patches:
            p.start()
        if 'acas_pro.llm.gemini_engine' in sys.modules:
            del sys.modules['acas_pro.llm.gemini_engine']

    def teardown_method(self):
        for p in self._patches:
            p.stop()

    def test_gemini_config(self):
        from acas_pro.llm.gemini_engine import GeminiConfig
        cfg = GeminiConfig(api_key="key123")
        assert cfg.api_key == "key123"
        assert cfg.model == "gemini-1.5-pro"
        assert cfg.max_tokens == 8192

    def test_gemini_engine_creation(self):
        from acas_pro.llm.gemini_engine import GeminiEngine, GeminiConfig
        engine = GeminiEngine(GeminiConfig(api_key="key123"))
        assert engine.name == "gemini"
        assert len(engine.models) == 4

    def test_gemini_convert_messages(self):
        from acas_pro.llm.gemini_engine import GeminiEngine, GeminiConfig
        from acas_pro.llm.base_engine import LLMMessage
        engine = GeminiEngine(GeminiConfig(api_key="key123"))
        msgs = [
            LLMMessage(role="system", content="Be helpful"),
            LLMMessage(role="user", content="Hi"),
            LLMMessage(role="assistant", content="Hello!"),
        ]
        system, converted = engine._convert_messages(msgs)
        assert system == "Be helpful"
        assert len(converted) == 2
        assert converted[0]["role"] == "user"
        assert converted[1]["role"] == "model"

    def test_gemini_chat(self):
        from acas_pro.llm.gemini_engine import GeminiEngine, GeminiConfig
        from acas_pro.llm.base_engine import LLMMessage

        engine = GeminiEngine(GeminiConfig(api_key="key123"))

        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Hello from Gemini"
        mock_chat.send_message.return_value = mock_response
        self.mock_model.start_chat.return_value = mock_chat

        msgs = [LLMMessage(role="user", content="Hi")]
        result = engine.chat(msgs)
        assert result.content == "Hello from Gemini"

    def test_gemini_chat_error(self):
        from acas_pro.llm.gemini_engine import GeminiEngine, GeminiConfig
        from acas_pro.llm.base_engine import LLMMessage

        engine = GeminiEngine(GeminiConfig(api_key="key123"))
        mock_chat = MagicMock()
        mock_chat.send_message.side_effect = Exception("API error")
        self.mock_model.start_chat.return_value = mock_chat

        with pytest.raises(RuntimeError, match="Gemini API error"):
            engine.chat([LLMMessage(role="user", content="Hi")])

    def test_gemini_no_client(self):
        from acas_pro.llm.gemini_engine import GeminiEngine, GeminiConfig
        from acas_pro.llm.base_engine import LLMMessage
        engine = GeminiEngine(GeminiConfig(api_key="key123"))
        engine._model = None
        with pytest.raises(RuntimeError):
            engine.chat([LLMMessage(role="user", content="Hi")])

    def test_gemini_quick_chat(self):
        from acas_pro.llm.gemini_engine import GeminiEngine, GeminiConfig
        engine = GeminiEngine(GeminiConfig(api_key="key123"))
        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "OK"
        mock_chat.send_message.return_value = mock_response
        self.mock_model.start_chat.return_value = mock_chat
        result = engine.quick_chat("Hi", "Reply OK")
        assert result == "OK"

    def test_gemini_count_tokens(self):
        from acas_pro.llm.gemini_engine import GeminiEngine, GeminiConfig
        engine = GeminiEngine(GeminiConfig(api_key="key123"))
        assert engine.count_tokens("Hello world") > 0

    def test_gemini_health_check_healthy(self):
        from acas_pro.llm.gemini_engine import GeminiEngine, GeminiConfig
        engine = GeminiEngine(GeminiConfig(api_key="key123"))
        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "OK"
        mock_chat.send_message.return_value = mock_response
        self.mock_model.start_chat.return_value = mock_chat
        result = engine.health_check()
        assert result["status"] == "healthy"

    def test_gemini_health_check_unhealthy(self):
        from acas_pro.llm.gemini_engine import GeminiEngine, GeminiConfig
        engine = GeminiEngine(GeminiConfig(api_key="key123"))
        mock_chat = MagicMock()
        mock_chat.send_message.side_effect = Exception("err")
        self.mock_model.start_chat.return_value = mock_chat
        result = engine.health_check()
        assert result["status"] == "unhealthy"

    def test_create_gemini_engine(self):
        from acas_pro.llm.gemini_engine import create_gemini_engine
        engine = create_gemini_engine(api_key="key123")
        assert engine.name == "gemini"

    def test_create_gemini_no_key(self):
        from acas_pro.llm.gemini_engine import create_gemini_engine
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="API key required"):
                create_gemini_engine()


# Need os import for the test
import os
