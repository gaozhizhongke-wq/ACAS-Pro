"""LLM routes for ACAS Pro Web"""

import json
import sqlite3
from flask import Blueprint, request, jsonify, g
from typing import Any
from pydantic import ValidationError

from acas_pro.core.config import config
from acas_pro.core.logging import get_logger
from acas_pro.llm.llm_client import (
    LLMClient,
    LLMConfig as ClientLLMConfig,
    LLMProvider,
    LLMMessage,
)
from acas_pro.web.schemas import (
    LLMChatRequest,
    LLMChatResponse,
    LLMConfigRequest,
    LLMConfigResponse,
    AuthErrorResponse,
)

logger = get_logger(__name__)
bp = Blueprint("llm", __name__, url_prefix="/api/llm")

_PROVIDER_MAP = {
    "openai": LLMProvider.OPENAI,
    "anthropic": LLMProvider.ANTHROPIC,
    "kimi": LLMProvider.KIMI,
    "deepseek": LLMProvider.DEEPSEEK,
    "qwen": LLMProvider.QWEN,
    "lmstudio": LLMProvider.LMSTUDIO,
    "ollama": LLMProvider.OLLAMA,
}


def create_llm_client() -> Any:
    """Bridge: config.py LLMConfig → llm_client.LLMConfig → LLMClient"""
    llm = config.llm
    if not llm.enabled or not llm.api_key:
        raise RuntimeError(
            "LLM not configured. Set DEEPSEEK_API_KEY in .env or configure via Settings page."
        )

    provider_enum = _PROVIDER_MAP.get(llm.provider, LLMProvider.OPENAI)
    client_cfg = ClientLLMConfig(
        provider=provider_enum,
        api_key=llm.api_key,
        model=llm.model,
        api_base=getattr(llm, "api_base", None) or getattr(llm, "base_url", None),
        temperature=llm.temperature,
        max_tokens=llm.max_tokens,
    )
    return LLMClient(client_cfg)


@bp.route("/config", methods=["POST"])
def save_llm_config() -> Any:
    """Save LLM configuration with Pydantic validation (requires authentication)"""
    if not hasattr(g, "user") or not g.user:
        return jsonify(
            AuthErrorResponse(error="Authentication required").model_dump(mode="json")
        ), 401

    try:
        req = LLMConfigRequest.model_validate(request.json or {})
    except ValidationError as e:
        logger.warning(f"LLM config validation failed: {e}")
        return jsonify(
            AuthErrorResponse(error=f"Validation error: {e}").model_dump(mode="json")
        ), 400

    # Update config
    config.llm.provider = req.provider
    config.llm.api_key = req.api_key
    if req.api_base:
        config.llm.base_url = req.api_base
    if req.model:
        config.llm.model = req.model
    config.llm.enabled = True

    # NOTE: API key is stored in config object only, NOT in environment variable
    # to prevent leakage to subprocesses. The config object is in-memory and
    # not exposed to process environment.

    return jsonify(
        LLMConfigResponse(success=True, message="Configuration saved").model_dump(
            mode="json"
        )
    ), 200


@bp.route("/chat", methods=["POST"])
def llm_chat() -> Any:
    """Chat with LLM with Pydantic validation"""
    try:
        req = LLMChatRequest.model_validate(request.json or {})
    except ValidationError as e:
        logger.warning(f"LLM chat validation failed: {e}")
        return jsonify(
            AuthErrorResponse(error=f"Validation error: {e}").model_dump(mode="json")
        ), 400

    try:
        client = create_llm_client()
        llm_messages = [
            LLMMessage(role=m.role, content=m.content) for m in req.messages
        ]
        response = client.chat(llm_messages)
        return jsonify(
            LLMChatResponse(
                success=True,
                content=response.content,
                usage=getattr(response, "usage", None),
            ).model_dump(mode="json")
        ), 200
    except ConnectionError as e:
        logger.error(f"LLM connection error: {e}")
        return jsonify(
            AuthErrorResponse(error="LLM service unavailable").model_dump(mode="json")
        ), 503
    except TimeoutError as e:
        logger.error(f"LLM timeout error: {e}")
        return jsonify(
            AuthErrorResponse(error="LLM request timed out").model_dump(mode="json")
        ), 504
    except RuntimeError as e:
        logger.error(f"LLM runtime error: {e}")
        return jsonify(AuthErrorResponse(error=str(e)).model_dump(mode="json")), 500
    except (sqlite3.Error, ValueError, RuntimeError, json.JSONDecodeError) as e:
        logger.error(f"LLM unexpected error: {e}")
        return jsonify(
            AuthErrorResponse(error="LLM service error").model_dump(mode="json")
        ), 500
