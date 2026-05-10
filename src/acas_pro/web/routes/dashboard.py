"""Dashboard routes for ACAS Pro Web"""
from flask import Blueprint, render_template_string, jsonify
from acas_pro.core.config import config
from acas_pro.core.logging import get_logger

logger = get_logger(__name__)
bp = Blueprint('dashboard', __name__)

# HTML template will be loaded from separate file or kept here for now
# TODO: Move to templates/dashboard.html


@bp.route('/')
def index():
    """Main dashboard page"""
    llm_provider = config.llm.provider if config.llm.enabled else '未启用'
    llm_key = config.llm.api_key
    llm_key_mask = llm_key[:8] + '****' if llm_key and len(llm_key) > 8 else '未设置'
    
    # For now, return a simple message. Full HTML template extraction is TODO.
    return jsonify({
        'message': 'ACAS Pro Web API',
        'llm_provider': llm_provider,
        'llm_enabled': config.llm.enabled
    })


@bp.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint for load balancers and monitoring"""
    from datetime import datetime, timezone
    from acas_pro.core.database import db
    
    db_health = db.health_check()
    
    return jsonify({
        'status': 'healthy' if db_health['status'] == 'healthy' else 'degraded',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'version': config.version,
        'database': db_health
    })
