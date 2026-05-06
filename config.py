#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro 统一配置管理
只从 .env 文件读取，无其他来源
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


def load_env_file(filepath: str = ".env") -> dict:
    """加载 .env 文件，返回配置字典"""
    config = {}
    env_path = Path(filepath)
    
    if not env_path.exists():
        return config
    
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                config[key.strip()] = value.strip()
    
    return config


@dataclass
class LLMConfig:
    provider: str = "deepseek"
    api_key: str = ""
    model: str = "deepseek-chat"
    enabled: bool = False
    
    @classmethod
    def from_env(cls, env_path: str = ".env") -> "LLMConfig":
        """从 .env 文件加载配置"""
        config = load_env_file(env_path)
        
        api_key = config.get('LLM_API_KEY', '')
        
        return cls(
            provider=config.get('LLM_PROVIDER', 'deepseek'),
            api_key=api_key,
            model=config.get('LLM_MODEL', 'deepseek-chat'),
            enabled=bool(api_key and len(api_key) > 10)
        )
    
    def validate(self) -> tuple[bool, str]:
        """验证配置有效性"""
        if not self.api_key:
            return False, "API Key 未配置"
        if not self.api_key.startswith(('sk-', 'ak-')):
            return False, "API Key 格式不正确"
        return True, "配置有效"


@dataclass  
class AppConfig:
    llm: LLMConfig
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 5000
    
    @classmethod
    def load(cls, env_path: str = ".env") -> "AppConfig":
        """加载完整配置"""
        env_config = load_env_file(env_path)
        
        return cls(
            llm=LLMConfig.from_env(env_path),
            debug=env_config.get('DEBUG', 'false').lower() == 'true',
            host=env_config.get('HOST', '0.0.0.0'),
            port=int(env_config.get('PORT', '5000'))
        )


# 全局配置实例
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """获取全局配置（单例）"""
    global _config
    if _config is None:
        _config = AppConfig.load()
    return _config


def reload_config() -> AppConfig:
    """重新加载配置"""
    global _config
    _config = AppConfig.load()
    return _config


if __name__ == "__main__":
    # 测试配置加载
    config = get_config()
    print(f"Provider: {config.llm.provider}")
    print(f"Model: {config.llm.model}")
    print(f"Enabled: {config.llm.enabled}")
    valid, msg = config.llm.validate()
    print(f"Validation: {msg}")
