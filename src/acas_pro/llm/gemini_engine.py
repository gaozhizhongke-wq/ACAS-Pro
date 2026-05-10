#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Gemini (Google) LLM Engine
Production-grade Google AI API integration
"""

import os
from typing import List, Dict, Optional, Iterator
from dataclasses import dataclass
from datetime import datetime

from .base_engine import BaseLLMEngine, LLMMessage, LLMResponse, LLMStreamChunk


@dataclass
class GeminiConfig:
    """Gemini engine configuration"""
    api_key: str
    model: str = "gemini-1.5-pro"
    max_tokens: int = 8192
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    api_base: str = "https://generativelanguage.googleapis.com"


class GeminiEngine(BaseLLMEngine):
    """
    Google Gemini LLM Engine
    Supports Gemini 1.5 Pro and Flash models
    """
    
    AVAILABLE_MODELS = [
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-1.0-pro",
        "gemini-1.0-pro-vision",
    ]
    
    def __init__(self, config: GeminiConfig):
        self.config = config
        self._client = None
        self._model = None
        self._init_client()
    
    def _init_client(self):
        """Initialize Gemini client"""
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.config.api_key)
            
            self._model = genai.GenerativeModel(
                model_name=self.config.model,
                generation_config={
                    "temperature": self.config.temperature,
                    "top_p": self.config.top_p,
                    "top_k": self.config.top_k,
                    "max_output_tokens": self.config.max_tokens,
                }
            )
            self._client = genai
        except ImportError:
            raise RuntimeError(
                "google-generativeai package not installed. "
                "Run: pip install google-generativeai"
            )
    
    @property
    def name(self) -> str:
        return "gemini"
    
    @property
    def models(self) -> List[str]:
        return self.AVAILABLE_MODELS
    
    def _convert_messages(self, messages: List[LLMMessage]) -> tuple:
        """Convert messages to Gemini format"""
        system = ""
        gemini_messages = []
        
        for msg in messages:
            if msg.role == "system":
                system = msg.content
            elif msg.role == "user":
                gemini_messages.append({"role": "user", "parts": [msg.content]})
            elif msg.role == "assistant":
                gemini_messages.append({"role": "model", "parts": [msg.content]})
        
        return system, gemini_messages
    
    def chat(self, messages: List[LLMMessage]) -> LLMResponse:
        """Send chat request to Gemini"""
        if not self._model:
            raise RuntimeError("Gemini client not initialized")
        
        system, gemini_messages = self._convert_messages(messages)
        
        try:
            # Start chat
            chat = self._model.start_chat(history=gemini_messages[:-1] if len(gemini_messages) > 1 else [])
            
            # Send message
            response = chat.send_message(gemini_messages[-1]["parts"][0])
            
            return LLMResponse(
                content=response.text,
                model=self.config.model,
                usage={
                    "prompt_tokens": 0,  # Gemini doesn't provide token counts
                    "completion_tokens": 0,
                    "total_tokens": 0
                },
                finish_reason="stop"
            )
        except Exception as e:
            raise RuntimeError(f"Gemini API error: {e}")
    
    def chat_stream(self, messages: List[LLMMessage]) -> Iterator[LLMStreamChunk]:
        """Stream chat response from Gemini"""
        if not self._model:
            raise RuntimeError("Gemini client not initialized")
        
        system, gemini_messages = self._convert_messages(messages)
        
        try:
            chat = self._model.start_chat(history=gemini_messages[:-1] if len(gemini_messages) > 1 else [])
            
            for chunk in chat.send_message(gemini_messages[-1]["parts"][0], stream=True):
                yield LLMStreamChunk(
                    content=chunk.text,
                    is_finished=False
                )
            
            yield LLMStreamChunk(
                content="",
                is_finished=True
            )
        except Exception as e:
            raise RuntimeError(f"Gemini streaming error: {e}")
    
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
        # Gemini uses ~4 chars per token on average
        return len(text) // 4
    
    def health_check(self) -> Dict:
        """Check Gemini API health"""
        try:
            response = self.quick_chat("Hi", "Reply with: OK")
            return {
                "status": "healthy",
                "model": self.config.model,
                "response": response[:50]
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# Factory function
def create_gemini_engine(
    api_key: str = None,
    model: str = "gemini-1.5-pro"
) -> GeminiEngine:
    """Create Gemini engine with environment fallback"""
    api_key = api_key or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("Google API key required")
    
    config = GeminiConfig(
        api_key=api_key,
        model=model
    )
    return GeminiEngine(config)
