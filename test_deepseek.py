#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek API 连接测试脚本
"""

import os
import sys

# Load .env file first
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                os.environ[key] = value

# Add src to path
src_path = os.path.join(os.path.dirname(__file__), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from acas_pro.core.config import config
from acas_pro.llm.llm_client import LLMClient, LLMConfig, LLMProvider, LLMMessage


def test_deepseek_connection():
    """测试 DeepSeek API 连接"""
    print("=" * 60)
    print("DeepSeek API Connection Test")
    print("=" * 60)
    
    # 显示当前配置
    print(f"\n[Config] Current LLM Config:")
    print(f"  - Enabled: {config.llm.enabled}")
    print(f"  - Provider: {config.llm.provider}")
    print(f"  - Model: {config.llm.model}")
    print(f"  - API Base: {config.llm.api_base}")
    print(f"  - API Key: {'SET [OK]' if config.llm.api_key else 'NOT SET [FAIL]'}")
    
    if not config.llm.enabled:
        print("\n[FAIL] LLM not enabled")
        print("\nPlease set environment variable:")
        print("  $env:DEEPSEEK_API_KEY = \"sk-your-api-key\"")
        return False
    
    if not config.llm.api_key:
        print("\n[FAIL] API Key not set")
        return False
    
    # 创建 LLM 客户端
    try:
        provider_map = {
            'deepseek': LLMProvider.DEEPSEEK,
            'openai': LLMProvider.OPENAI,
            'anthropic': LLMProvider.ANTHROPIC,
            'kimi': LLMProvider.KIMI,
            'qwen': LLMProvider.QWEN,
        }
        
        provider = provider_map.get(config.llm.provider, LLMProvider.DEEPSEEK)
        
        llm_config = LLMConfig(
            provider=provider,
            api_key=config.llm.api_key,
            api_base=config.llm.api_base,
            model=config.llm.model,
            max_tokens=config.llm.max_tokens,
            temperature=config.llm.temperature,
            top_p=config.llm.top_p
        )
        
        client = LLMClient(llm_config)
        print(f"\n[OK] LLM Client created")
        
        # 发送测试消息
        print("\n[Sending] Test message...")
        messages = [
            LLMMessage(role="system", content="You are a helpful assistant."),
            LLMMessage(role="user", content="Hi! Introduce yourself in one sentence.")
        ]
        
        response = client.chat(messages)
        
        print(f"\n[Response]:")
        print(f"  - Model: {response.model}")
        print(f"  - Content: {response.content}")
        print(f"  - Token Usage: {response.usage}")
        print(f"  - Latency: {response.latency_ms}ms")
        
        print("\n[SUCCESS] DeepSeek API connected!")
        return True
        
    except Exception as e:
        print(f"\n[FAIL] Connection failed: {e}")
        return False


def test_quick_chat():
    """Test quick chat"""
    print("\n" + "=" * 60)
    print("Quick Chat Test")
    print("=" * 60)
    
    try:
        from acas_pro.core.config import config
        from acas_pro.llm.llm_client import LLMClient, LLMConfig, LLMProvider
        
        provider_map = {
            'deepseek': LLMProvider.DEEPSEEK,
            'openai': LLMProvider.OPENAI,
            'anthropic': LLMProvider.ANTHROPIC,
            'kimi': LLMProvider.KIMI,
            'qwen': LLMProvider.QWEN,
        }
        
        provider = provider_map.get(config.llm.provider, LLMProvider.DEEPSEEK)
        
        llm_config = LLMConfig(
            provider=provider,
            api_key=config.llm.api_key,
            api_base=config.llm.api_base,
            model=config.llm.model
        )
        
        client = LLMClient(llm_config)
        
        # Test content creation
        prompt = """
Create a promotional copy for an intelligent customer acquisition software.
Product: ACAS Pro
Features: AI-driven customer acquisition, sales forecasting, content creation
Target: Small business owners
Requirements: Within 100 words, highlight AI advantages
"""
        
        print(f"\n[Prompt]:\n{prompt}")
        print("\n[Generating]...")
        
        result = client.quick_chat(
            prompt=prompt,
            system="You are an expert marketing copywriter."
        )
        
        print(f"\n[Result]:\n{result}")
        return True
        
    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        return False


if __name__ == "__main__":
    # Test connection
    if test_deepseek_connection():
        # Test chat
        test_quick_chat()
    
    print("\n" + "=" * 60)
    print("Test completed")
    print("=" * 60)
