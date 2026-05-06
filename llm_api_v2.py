#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro LLM API Service v2
统一错误格式、健康检查、配置验证
"""

import os
import sys
import time
import traceback
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config import get_config, reload_config

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# 服务启动时间
START_TIME = time.time()


def success_response(data: dict, message: str = "success") -> dict:
    """统一成功响应格式"""
    return {
        "success": True,
        "message": message,
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    }


def error_response(message: str, code: str = "INTERNAL_ERROR", status_code: int = 500) -> tuple:
    """统一错误响应格式"""
    response = {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
    }
    return jsonify(response), status_code


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    config = get_config()
    llm_valid, llm_msg = config.llm.validate()
    
    return jsonify({
        "status": "healthy" if llm_valid else "degraded",
        "version": "2.0.0",
        "uptime": time.time() - START_TIME,
        "services": {
            "llm": {
                "enabled": config.llm.enabled,
                "provider": config.llm.provider,
                "valid": llm_valid,
                "message": llm_msg
            }
        }
    })


@app.route('/api/config', methods=['GET'])
def get_config_endpoint():
    """获取当前配置（脱敏）"""
    config = get_config()
    return jsonify(success_response({
        "provider": config.llm.provider,
        "model": config.llm.model,
        "enabled": config.llm.enabled,
        "api_key_preview": config.llm.api_key[:10] + "..." if config.llm.api_key else None
    }))


@app.route('/api/chat', methods=['POST'])
def chat():
    """聊天接口"""
    try:
        config = get_config()
        
        # 检查 LLM 配置
        if not config.llm.enabled:
            return error_response(
                "LLM 未配置，请检查 .env 文件中的 LLM_API_KEY",
                "LLM_NOT_CONFIGURED",
                503
            )
        
        valid, msg = config.llm.validate()
        if not valid:
            return error_response(msg, "INVALID_CONFIG", 400)
        
        # 获取请求数据
        data = request.get_json()
        if not data:
            return error_response("请求体不能为空", "EMPTY_BODY", 400)
        
        message = data.get('message', '').strip()
        if not message:
            return error_response("消息不能为空", "EMPTY_MESSAGE", 400)
        
        # 尝试导入 LLM 客户端
        try:
            from acas_pro.llm.llm_client import LLMClient, LLMConfig as LLMClientConfig
            from acas_pro.llm.llm_client import LLMProvider, LLMMessage
        except ImportError as e:
            return error_response(
                f"LLM 客户端加载失败: {str(e)}",
                "CLIENT_LOAD_ERROR",
                500
            )
        
        # 创建客户端
        provider_map = {
            'openai': LLMProvider.OPENAI,
            'anthropic': LLMProvider.ANTHROPIC,
            'kimi': LLMProvider.KIMI,
            'deepseek': LLMProvider.DEEPSEEK,
            'qwen': LLMProvider.QWEN,
        }
        
        llm_config = LLMClientConfig(
            provider=provider_map.get(config.llm.provider, LLMProvider.DEEPSEEK),
            api_key=config.llm.api_key,
            model=config.llm.model or None,
            max_tokens=4096,
            temperature=0.7
        )
        
        client = LLMClient(llm_config)
        
        # 发送消息
        messages = [LLMMessage(role="user", content=message)]
        response = client.chat(messages)
        
        return jsonify(success_response({
            "response": response.content,
            "model": config.llm.model,
            "provider": config.llm.provider,
            "tokens": response.total_tokens
        }))
        
    except Exception as e:
        traceback.print_exc()
        return error_response(
            f"处理请求时出错: {str(e)}",
            "PROCESSING_ERROR",
            500
        )


@app.route('/api/reload-config', methods=['POST'])
def reload_config_endpoint():
    """重新加载配置"""
    try:
        config = reload_config()
        valid, msg = config.llm.validate()
        return jsonify(success_response({
            "reloaded": True,
            "llm_valid": valid,
            "message": msg
        }))
    except Exception as e:
        return error_response(f"重新加载配置失败: {str(e)}", "RELOAD_ERROR", 500)


@app.errorhandler(404)
def not_found(error):
    return error_response("接口不存在", "NOT_FOUND", 404)


@app.errorhandler(500)
def internal_error(error):
    return error_response("服务器内部错误", "INTERNAL_ERROR", 500)


if __name__ == '__main__':
    config = get_config()
    print("=" * 50)
    print("ACAS Pro LLM API v2")
    print("=" * 50)
    print(f"Config file: .env")
    print(f"Provider: {config.llm.provider}")
    print(f"Model: {config.llm.model}")
    print(f"Enabled: {config.llm.enabled}")
    valid, msg = config.llm.validate()
    print(f"Status: {msg}")
    print("=" * 50)
    print(f"Health check: http://{config.host}:{config.port}/health")
    print(f"API endpoint: http://{config.host}:{config.port}/api/chat")
    print("=" * 50)
    
    app.run(
        host=config.host,
        port=config.port,
        debug=config.debug
    )
