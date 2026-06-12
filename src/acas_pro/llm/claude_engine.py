#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Claude (Anthropic) LLM Engine
Production-grade Anthropic API integration
"""

import os
import sqlite3
import logging
from typing import List, Dict, Iterator
from dataclasses import dataclass
import json

from .base_engine import BaseLLMEngine, LLMMessage, LLMResponse, LLMStreamChunk

logger = logging.getLogger(__name__)


@dataclass
class ClaudeConfig:
    """Claude engine configuration"""

    api_key: str
    model: str = "claude-3-opus-20240229"
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 0.9
    api_base: str = "https://api.anthropic.com"


class ClaudeEngine(BaseLLMEngine):
    """
    Anthropic Claude LLM Engine
    Supports Claude 3 Opus, Sonnet, and Haiku models
    """

    AVAILABLE_MODELS = [
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
        "claude-3-5-sonnet-20241022",
    ]

    def __init__(self, config: ClaudeConfig):
        self.config = config
        self._client = None
        self._init_client()

    def _init_client(self) -> None:
        """Initialize Anthropic client"""
        try:
            import anthropic

            self._client = anthropic.Anthropic(
                api_key=self.config.api_key, base_url=self.config.api_base
            )
        except ImportError:
            raise RuntimeError(
                "anthropic package not installed. Run: pip install anthropic"
            )

    @property
    def name(self) -> str:
        return "claude"

    @property
    def models(self) -> List[str]:
        return self.AVAILABLE_MODELS

    def _convert_messages(self, messages: List[LLMMessage]) -> tuple:
        """Convert messages to Claude format"""
        system = ""
        claude_messages = []

        for msg in messages:
            if msg.role == "system":
                system = msg.content
            else:
                claude_messages.append({"role": msg.role, "content": msg.content})

        return system, claude_messages

    def chat(self, messages: List[LLMMessage]) -> LLMResponse:
        """Send chat request to Claude"""
        if not self._client:
            raise RuntimeError("Claude client not initialized")

        system, claude_messages = self._convert_messages(messages)

        try:
            response = self._client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                system=system,
                messages=claude_messages,
            )

            return LLMResponse(
                content=response.content[0].text,
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens
                    + response.usage.output_tokens,
                },
                finish_reason=response.stop_reason,
            )
        except (
            sqlite3.Error,
            ValueError,
            RuntimeError,
            json.JSONDecodeError,
            Exception,
        ) as e:
            logger.exception(f"Error in chat: {e}")
            raise RuntimeError(f"Claude API error: {e}")

    def chat_stream(self, messages: List[LLMMessage]) -> Iterator[LLMStreamChunk]:
        """Stream chat response from Claude"""
        if not self._client:
            raise RuntimeError("Claude client not initialized")

        system, claude_messages = self._convert_messages(messages)

        try:
            with self._client.messages.stream(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=system,
                messages=claude_messages,
            ) as stream:
                for text in stream.text_stream:
                    yield LLMStreamChunk(content=text, is_finished=False)

                yield LLMStreamChunk(content="", is_finished=True)
        except (
            sqlite3.Error,
            ValueError,
            RuntimeError,
            json.JSONDecodeError,
            Exception,
        ) as e:
            logger.exception(f"Error in chat_stream: {e}")
            raise RuntimeError(f"Claude streaming error: {e}")

    def quick_chat(self, message: str, system: str = None) -> str:
        """Quick single-turn chat"""
        messages = []
        if system:
            messages.append(LLMMessage(role="system", content=system))
        messages.append(LLMMessage(role="user", content=message))

        response = self.chat(messages)
        return response.content

    def count_tokens(self, text: str) -> int:
        """Count tokens in text (approximation)"""
        # Claude uses ~4 chars per token on average
        return len(text) // 4

    def health_check(self) -> Dict:
        """Check Claude API health"""
        try:
            # Try a simple request
            response = self.quick_chat("Hi", "Reply with: OK")
            return {
                "status": "healthy",
                "model": self.config.model,
                "response": response[:50],
            }
        except (
            sqlite3.Error,
            ValueError,
            RuntimeError,
            json.JSONDecodeError,
            Exception,
        ) as e:
            logger.exception(f"Error in health_check: {e}")
            return {"status": "unhealthy", "error": str(e)}


# Factory function
def create_claude_engine(
    api_key: str = None, model: str = "claude-3-opus-20240229"
) -> ClaudeEngine:
    """Create Claude engine with environment fallback"""
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("Anthropic API key required")

    config = ClaudeConfig(api_key=api_key, model=model)
    return ClaudeEngine(config)
