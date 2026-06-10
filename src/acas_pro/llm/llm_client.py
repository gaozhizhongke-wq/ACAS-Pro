#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - LLM Client
Unified interface for multiple LLM providers
"""

import json
import time
import hashlib
import secrets
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Any, AsyncIterator
from enum import Enum
import urllib.request
import urllib.error
import urllib.parse

# Try importing aiohttp for async HTTP
try:
    import aiohttp
    _HAS_AIOHTTP = True
except ImportError:
    _HAS_AIOHTTP = False


def _safe_urlopen(req, **kwargs):
    """Validate URL scheme before opening (http/https only)."""
    url = req.full_url if hasattr(req, 'full_url') else str(req)
    scheme = urllib.parse.urlparse(url).scheme
    if scheme not in ('http', 'https'):
        raise ValueError(
            f"Unsupported URL scheme: {scheme!r} (only http/https allowed)"
        )
    return urllib.request.urlopen(req, **kwargs)  # nosec B310  # validated scheme above


class LLMProvider(Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    KIMI = "kimi"
    DEEPSEEK = "deepseek"
    QWEN = "qwen"
    LMSTUDIO = "lmstudio"
    OLLAMA = "ollama"
    CUSTOM = "custom"


@dataclass
class LLMMessage:
    """LLM message structure"""
    role: str  # system, user, assistant
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None
    tool_call_id: Optional[str] = None


@dataclass
class LLMResponse:
    """LLM response structure"""
    content: str
    role: str = "assistant"
    model: str = ""
    usage: Dict[str, int] = field(default_factory=dict)
    tool_calls: Optional[List[Dict]] = None
    finish_reason: str = "stop"
    latency_ms: int = 0


@dataclass
class LLMConfig:
    """LLM provider configuration"""
    provider: LLMProvider = LLMProvider.OPENAI
    api_key: str = ""
    api_base: str = ""
    model: str = ""
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 0.9
    stream: bool = False
    
    # Provider-specific defaults
    def __post_init__(self) -> None:
        if not self.api_base:
            self.api_base = self._get_default_base()
        if not self.model:
            self.model = self._get_default_model()
    
    def _get_default_base(self) -> str:
        defaults = {
            LLMProvider.OPENAI: "https://api.openai.com/v1",
            LLMProvider.ANTHROPIC: "https://api.anthropic.com/v1",
            LLMProvider.KIMI: "https://api.moonshot.cn/v1",
            LLMProvider.DEEPSEEK: "https://api.deepseek.com/v1",
            LLMProvider.QWEN: "https://dashscope.aliyuncs.com/compatible-mode/v1",
            LLMProvider.LMSTUDIO: "http://localhost:1234/v1",
            LLMProvider.OLLAMA: "http://localhost:11434/v1",
            LLMProvider.CUSTOM: ""
        }
        return defaults.get(self.provider, "")
    
    def _get_default_model(self) -> str:
        defaults = {
            LLMProvider.OPENAI: "gpt-4o",
            LLMProvider.ANTHROPIC: "claude-sonnet-4-20250514",
            LLMProvider.KIMI: "moonshot-v1-128k",
            LLMProvider.DEEPSEEK: "deepseek-chat",
            LLMProvider.QWEN: "qwen-max",
            LLMProvider.LMSTUDIO: "local-model",
            LLMProvider.OLLAMA: "llama3",
            LLMProvider.CUSTOM: ""
        }
        return defaults.get(self.provider, "")


class BaseLLMProvider(ABC):
    """Base class for LLM providers"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self._token_cache: Dict[str, Any] = {}
    
    @abstractmethod
    def chat(self, messages: List[LLMMessage], 
             tools: Optional[List[Dict]] = None,
             **kwargs) -> LLMResponse:
        """Send chat completion request"""
        pass
    
    @abstractmethod
    def stream_chat(self, messages: List[LLMMessage],
                    tools: Optional[List[Dict]] = None,
                    **kwargs) -> Any:
        """Stream chat completion (returns generator)"""
        pass
    
    def _make_request(self, url: str, data: Dict, headers: Dict) -> Dict:
        """Make HTTP request (sync)"""
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers=headers,
            method='POST'
        )
        try:
            with _safe_urlopen(req, timeout=120) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise RuntimeError(f"API Error {e.code}: {error_body}")


    async def _make_request_async(self, url: str, data: Dict, headers: Dict) -> Dict:
        """Make HTTP request (async)"""
        if not _HAS_AIOHTTP:
            return await asyncio.to_thread(self._make_request, url, data, headers)
        
        timeout = aiohttp.ClientTimeout(total=120)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=data, headers=headers) as response:
                    if response.status != 200:
                        error_body = await response.text()
                        raise RuntimeError(f"API Error {response.status}: {error_body}")
                    return await response.json()
        except aiohttp.ClientError as e:
            raise RuntimeError(f"HTTP Error: {e}")


class OpenAIProvider(BaseLLMProvider):
    """OpenAI-compatible provider (works for OpenAI, DeepSeek, Qwen, LMStudio)"""
    
    def chat(self, messages: List[LLMMessage], 
             tools: Optional[List[Dict]] = None,
             **kwargs) -> LLMResponse:
        start_time = time.time()
        
        # Build request
        payload = {
            "model": kwargs.get('model', self.config.model),
            "messages": [self._format_message(m) for m in messages],
            "max_tokens": kwargs.get('max_tokens', self.config.max_tokens),
            "temperature": kwargs.get('temperature', self.config.temperature),
            "top_p": kwargs.get('top_p', self.config.top_p),
            "stream": False
        }
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        
        # Make request
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}"
        }
        
        # Add provider-specific headers
        if self.config.provider == LLMProvider.KIMI:
            headers["X-Timestamp"] = str(int(time.time()))
        
        url = f"{self.config.api_base}/chat/completions"
        response_data = self._make_request(url, payload, headers)
        
        # Parse response
        choice = response_data['choices'][0]
        message = choice['message']
        
        return LLMResponse(
            content=message.get('content', ''),
            role=message.get('role', 'assistant'),
            model=response_data.get('model', self.config.model),
            usage=response_data.get('usage', {}),
            tool_calls=message.get('tool_calls'),
            finish_reason=choice.get('finish_reason', 'stop'),
            latency_ms=int((time.time() - start_time) * 1000)
        )

    async def chat_async(self, messages: List[LLMMessage],
                        tools: Optional[List[Dict]] = None,
                        **kwargs) -> LLMResponse:
        """Chat with async HTTP"""
        start_time = time.time()
        
        payload = {
            "model": kwargs.get('model', self.config.model),
            "messages": [self._format_message(m) for m in messages],
            "max_tokens": kwargs.get('max_tokens', self.config.max_tokens),
            "temperature": kwargs.get('temperature', self.config.temperature),
            "top_p": kwargs.get('top_p', self.config.top_p),
            "stream": False
        }
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}"
        }
        if self.config.provider == LLMProvider.KIMI:
            headers["X-Timestamp"] = str(int(time.time()))
        
        url = f"{self.config.api_base}/chat/completions"
        response_data = await self._make_request_async(url, payload, headers)
        
        choice = response_data['choices'][0]
        message = choice['message']
        
        return LLMResponse(
            content=message.get('content', ''),
            role=message.get('role', 'assistant'),
            model=response_data.get('model', self.config.model),
            usage=response_data.get('usage', {}),
            tool_calls=message.get('tool_calls'),
            finish_reason=choice.get('finish_reason', 'stop'),
            latency_ms=int((time.time() - start_time) * 1000)
        )
    
    def stream_chat(self, messages: List[LLMMessage],
                    tools: Optional[List[Dict]] = None,
                    **kwargs):
        """Stream chat - simplified version using iterative requests"""
        # Note: For true streaming, use async HTTP client
        # This is a simplified sync version
        response = self.chat(messages, tools, **kwargs)
        yield response
    
    def _format_message(self, msg: LLMMessage) -> Dict:
        """Format message for OpenAI API"""
        result = {"role": msg.role, "content": msg.content}
        if msg.name:
            result["name"] = msg.name
        if msg.tool_calls:
            result["tool_calls"] = msg.tool_calls
        if msg.tool_call_id:
            result["tool_call_id"] = msg.tool_call_id
        return result


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider"""
    
    def chat(self, messages: List[LLMMessage],
             tools: Optional[List[Dict]] = None,
             **kwargs) -> LLMResponse:
        start_time = time.time()
        
        # Extract system message
        system_msg = ""
        chat_messages = []
        for msg in messages:
            if msg.role == "system":
                system_msg = msg.content
            else:
                chat_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        payload = {
            "model": kwargs.get('model', self.config.model),
            "max_tokens": kwargs.get('max_tokens', self.config.max_tokens),
            "messages": chat_messages,
            "temperature": kwargs.get('temperature', self.config.temperature)
        }
        
        if system_msg:
            payload["system"] = system_msg
        
        if tools:
            payload["tools"] = self._format_tools(tools)
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        url = f"{self.config.api_base}/messages"
        response_data = self._make_request(url, payload, headers)
        
        # Parse response
        content_blocks = response_data.get('content', [])
        text_content = ""
        tool_calls = []
        
        for block in content_blocks:
            if block.get('type') == 'text':
                text_content += block.get('text', '')
            elif block.get('type') == 'tool_use':
                tool_calls.append({
                    "id": block.get('id'),
                    "type": "function",
                    "function": {
                        "name": block.get('name'),
                        "arguments": json.dumps(block.get('input', {}))
                    }
                })
        
        return LLMResponse(
            content=text_content,
            role="assistant",
            model=response_data.get('model', self.config.model),
            usage=response_data.get('usage', {}),
            tool_calls=tool_calls if tool_calls else None,
            finish_reason=response_data.get('stop_reason', 'stop'),
            latency_ms=int((time.time() - start_time) * 1000)
        )

    async def chat_async(self, messages: List[LLMMessage],
                        tools: Optional[List[Dict]] = None,
                        **kwargs) -> LLMResponse:
        """Chat with async HTTP (Anthropic)"""
        start_time = time.time()
        
        system_msg = ""
        chat_messages = []
        for msg in messages:
            if msg.role == "system":
                system_msg = msg.content
            else:
                chat_messages.append({"role": msg.role, "content": msg.content})
        
        payload = {
            "model": kwargs.get('model', self.config.model),
            "max_tokens": kwargs.get('max_tokens', self.config.max_tokens),
            "messages": chat_messages,
            "temperature": kwargs.get('temperature', self.config.temperature)
        }
        if system_msg:
            payload["system"] = system_msg
        if tools:
            payload["tools"] = self._format_tools(tools)
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        url = f"{self.config.api_base}/messages"
        response_data = await self._make_request_async(url, payload, headers)
        
        content_blocks = response_data.get('content', [])
        text_content = ""
        tool_calls = []
        
        for block in content_blocks:
            if block.get('type') == 'text':
                text_content += block.get('text', '')
            elif block.get('type') == 'tool_use':
                tool_calls.append({
                    "id": block.get('id'),
                    "type": block.get('type'),
                    "function": block.get('input', {})
                })
        
        return LLMResponse(
            content=text_content,
            role='assistant',
            model=response_data.get('model', self.config.model),
            usage=response_data.get('usage', {}),
            tool_calls=tool_calls if tool_calls else None,
            finish_reason=response_data.get('stop_reason', 'stop'),
            latency_ms=int((time.time() - start_time) * 1000)
        )
    
    def stream_chat(self, messages: List[LLMMessage],
                    tools: Optional[List[Dict]] = None,
                    **kwargs):
        """Stream chat for Anthropic"""
        response = self.chat(messages, tools, **kwargs)
        yield response
    
    def _format_tools(self, tools: List[Dict]) -> List[Dict]:
        """Format tools for Anthropic API"""
        anthropic_tools = []
        for tool in tools:
            if tool.get('type') == 'function':
                func = tool['function']
                anthropic_tools.append({
                    "name": func['name'],
                    "description": func.get('description', ''),
                    "input_schema": func.get('parameters', {})
                })
        return anthropic_tools


class LLMClient:
    """
    Unified LLM Client
    Provides a simple interface for multiple LLM providers
    """
    
    _providers: Dict[LLMProvider, type] = {
        LLMProvider.OPENAI: OpenAIProvider,
        LLMProvider.DEEPSEEK: OpenAIProvider,
        LLMProvider.QWEN: OpenAIProvider,
        LLMProvider.KIMI: OpenAIProvider,
        LLMProvider.LMSTUDIO: OpenAIProvider,
        LLMProvider.OLLAMA: OpenAIProvider,
        LLMProvider.CUSTOM: OpenAIProvider,
        LLMProvider.ANTHROPIC: AnthropicProvider,
    }
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self._provider = self._create_provider()
    
    def _create_provider(self) -> BaseLLMProvider:
        """Create appropriate provider instance"""
        provider_class = self._providers.get(self.config.provider, OpenAIProvider)
        return provider_class(self.config)
    
    def chat(self, messages: List[LLMMessage],
             tools: Optional[List[Dict]] = None,
             **kwargs) -> LLMResponse:
        """Send chat completion request"""
        return self._provider.chat(messages, tools, **kwargs)
    
    async def chat_async(self, messages: List[LLMMessage],
                        tools: Optional[List[Dict]] = None,
                        **kwargs) -> LLMResponse:
        """Send chat completion request (async)"""
        return await self._provider.chat_async(messages, tools, **kwargs)  # type: ignore[attr-defined]
    
    def stream_chat(self, messages: List[LLMMessage],
                    tools: Optional[List[Dict]] = None,
                    **kwargs):
        """Stream chat completion"""
        yield from self._provider.stream_chat(messages, tools, **kwargs)
    
    def quick_chat(self, prompt: str, system: str = "") -> str:
        """Quick single-turn chat"""
        messages = []
        if system:
            messages.append(LLMMessage(role="system", content=system))
        messages.append(LLMMessage(role="user", content=prompt))
        
        response = self.chat(messages)
        return response.content
    
    def count_tokens(self, text: str) -> int:
        """Estimate token count (simplified)"""
        # Rough estimation: ~4 chars per token for Chinese, ~4 chars per token for English
        # This is a simple approximation
        return len(text) // 4
    
    @staticmethod
    def list_models(provider: LLMProvider) -> List[str]:
        """Get available models for a provider"""
        models = {
            LLMProvider.OPENAI: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
            LLMProvider.ANTHROPIC: ["claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022", "claude-3-opus-20240229"],
            LLMProvider.KIMI: ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
            LLMProvider.DEEPSEEK: ["deepseek-chat", "deepseek-coder", "deepseek-reasoner"],
            LLMProvider.QWEN: ["qwen-max", "qwen-plus", "qwen-turbo", "qwen-vl-plus"],
            LLMProvider.LMSTUDIO: ["local-model"],  # User's loaded model
            LLMProvider.OLLAMA: ["llama3", "llama2", "mistral", "codellama"],
            LLMProvider.CUSTOM: []
        }
        return models.get(provider, [])
