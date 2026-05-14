"""LLM routes for ACAS Pro Web"""
from flask import Blueprint, request, jsonify, g
from acas_pro.core.config import config
from acas_pro.core.logging import get_logger
from acas_pro.llm.llm_client import LLMClient, LLMConfig as ClientLLMConfig, LLMProvider, LLMMessage

logger = get_logger(__name__)
bp = Blueprint('llm', __name__, url_prefix='/api/llm')

_PROVIDER_MAP = {
    'openai': LLMProvider.OPENAI,
    'anthropic': LLMProvider.ANTHROPIC,
    'kimi': LLMProvider.KIMI,
    'deepseek': LLMProvider.DEEPSEEK,
    'qwen': LLMProvider.QWEN,
    'lmstudio': LLMProvider.LMSTUDIO,
    'ollama': LLMProvider.OLLAMA,
}


def create_llm_client():
    """Bridge: config().py LLMConfig → llm_client.LLMConfig → LLMClient"""
    llm = config().llm
    if not llm.enabled or not llm.api_key:
        raise RuntimeError("LLM not configured. Set DEEPSEEK_API_KEY in .env or configure via Settings page.")
    
    provider_enum = _PROVIDER_MAP.get(llm.provider, LLMProvider.OPENAI)
    client_cfg = ClientLLMConfig(
        provider=provider_enum,
        api_key=llm.api_key,
        model=llm.model,
        base_url=llm.api_base,
        temperature=llm.temperature,
        max_tokens=llm.max_tokens,
    )
    return LLMClient(client_cfg)


@bp.route('/config', methods=['POST'])
def save_llm_config():
    """Save LLM configuration"""
    data = request.json or {}
    provider = data.get('provider', 'openai')
    api_key = data.get('api_key', '')
    api_base = data.get('api_base') or None
    model = data.get('model') or None

    # Update config
    config().llm.provider = provider
    if api_key:
        config().llm.api_key = api_key
    if api_base:
        config().llm.api_base = api_base
    if model:
        config().llm.model = model
    config().llm.enabled = True

    # Also update environment variable for runtime
    env_key = f"{provider.upper()}_API_KEY"
    import os
    os.environ[env_key] = api_key

    return jsonify({'success': True, 'message': 'Configuration saved'})


@bp.route('/chat', methods=['POST'])
def llm_chat():
    """Chat with LLM"""
    data = request.json or {}
    messages = data.get('messages', [])
    
    if not messages:
        return jsonify({'error': 'messages required'}), 400
    
    try:
        client = create_llm_client()
        llm_messages = [LLMMessage(role=m['role'], content=m['content']) for m in messages]
        response = client.chat(llm_messages)
        return jsonify({
            'success': True,
            'response': response.content,
            'model': config().llm.model,
            'provider': config().llm.provider
        })
    except Exception as e:
        logger.error(f"LLM chat error: {e}")
        return jsonify({'error': str(e)}), 500
