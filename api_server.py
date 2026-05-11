#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro 统一 API 服务 v2.1
整合 LLM + 数据管理 + 视频处理
生产级：错误处理、日志、认证、监控

版权所有 (C) 2024-2026 高智中科（北京）科技有限公司
All Rights Reserved.
"""

import os
import sys
import uuid
import json
import time
import traceback
from datetime import datetime
from datetime import timezone
from functools import wraps

from flask import Flask, request, jsonify, g
from flask_cors import CORS

# 添加路径
sys.path.insert(0, os.path.dirname(__file__))

from config import get_config
from database import get_db, Database
from logger import app_logger, api_logger, log_execution
from middleware import RequestMiddleware, SecurityHeaders, RateLimiter, metrics

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
# CORS 配置：生产环境通过 ALLOWED_ORIGINS 环境变量控制
ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', 'http://localhost:8080,http://127.0.0.1:8080,http://localhost:5000')
CORS(app, resources={r"/api/*": {"origins": ALLOWED_ORIGINS.split(',') if ',' in ALLOWED_ORIGINS else ALLOWED_ORIGINS}})

# 初始化中间件
RequestMiddleware(app)
SecurityHeaders(app)
rate_limiter = RateLimiter(max_requests=100, window=60)

# Token 认证：从环境变量读取 demo token
# 生产环境应设置 API_DEMO_TOKEN 环境变量
DEMO_TOKEN = os.environ.get('API_DEMO_TOKEN', 'demo-token-2024')
VALID_TOKENS = {DEMO_TOKEN: {"role": "admin", "name": "管理员"}}

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else None
        
        if not token or token not in VALID_TOKENS:
            return jsonify({"success": False, "error": {"code": "UNAUTHORIZED", "message": "未授权访问"}}), 401
        
        g.user = VALID_TOKENS[token]
        return f(*args, **kwargs)
    return decorated

def check_rate_limit():
    """检查速率限制"""
    ip = request.remote_addr or 'unknown'
    if not rate_limiter.is_allowed(ip):
        return jsonify({
            "success": False,
            "error": {"code": "RATE_LIMITED", "message": "请求过于频繁，请稍后再试"},
            "retry_after": 60
        }), 429
    return None

def success_response(data=None, message="success"):
    return jsonify({
        "success": True,
        "message": message,
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

def error_response(message, code="ERROR", status_code=500):
    # 记录错误日志
    db = get_db()
    db.log("ERROR", request.endpoint or "unknown", message, {
        "code": code,
        "path": request.path,
        "method": request.method
    })
    
    return jsonify({
        "success": False,
        "error": {"code": code, "message": message},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }), status_code

# ========== 健康检查 ==========

@app.route('/health')
def health():
    """健康检查端点"""
    config = get_config()
    db = get_db()
    
    # 检查数据库
    try:
        stats = db.get_dashboard_stats()
        db_status = "healthy"
    except Exception as e:
        stats = {}
        db_status = f"error: {str(e)}"
    
    # 检查磁盘空间
    import shutil
    disk = shutil.disk_usage('.')
    disk_free_gb = disk.free / (1024**3)
    
    return jsonify({
        "status": "healthy" if db_status == "healthy" and disk_free_gb > 1 else "degraded",
        "version": "2.1.0-prod",
        "uptime": time.time() - getattr(g, 'start_time', time.time()),
        "services": {
            "database": db_status,
            "llm": {"enabled": config.llm.enabled, "provider": config.llm.provider},
            "disk": {"free_gb": round(disk_free_gb, 2), "status": "ok" if disk_free_gb > 1 else "low"}
        },
        "metrics": metrics.get_summary(),
        "stats": stats
    })

@app.route('/metrics')
def get_metrics():
    """获取性能指标"""
    return jsonify(metrics.get_summary())

# ========== 认证 ==========

@app.route('/api/auth/login', methods=['POST'])
def login():
    """登录（演示用，实际应验证密码）"""
    data = request.get_json() or {}
    username = data.get('username', '')
    password = data.get('password', '')
    
    demo_user = os.environ.get('DEMO_USERNAME', 'admin')  # noqa: B105
    demo_pass = os.environ.get('DEMO_PASSWORD', 'admin123')  # noqa: B105
    if username == demo_user and password == demo_pass:
        token = os.environ.get('API_DEMO_TOKEN', 'demo-token-2024')
        return success_response({"token": token, "user": {"name": "管理员", "role": "admin"}})
    
    return error_response("用户名或密码错误", "INVALID_CREDENTIALS", 401)

# ========== 仪表盘 ==========

@app.route('/api/dashboard')
# @require_auth  # 演示时暂时关闭
def dashboard():
    try:
        db = get_db()
        stats = db.get_dashboard_stats()
        return success_response(stats)
    except Exception as e:
        return error_response(f"获取统计数据失败: {str(e)}", "DB_ERROR")

# ========== 账号管理 ==========

@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    try:
        db = get_db()
        platform = request.args.get('platform')
        accounts = db.get_accounts(platform=platform)
        return success_response([{
            "id": a.id,
            "platform": a.platform,
            "username": a.username,
            "status": a.status,
            "followers": a.followers,
            "created_at": a.created_at.isoformat() if a.created_at else None
        } for a in accounts])
    except Exception as e:
        return error_response(str(e), "DB_ERROR")

@app.route('/api/accounts', methods=['POST'])
def create_account():
    try:
        data = request.get_json() or {}
        db = get_db()
        
        account = db.create_account(
            account_id=str(uuid.uuid4())[:8],
            platform=data.get('platform', 'weibo'),
            username=data.get('username', '未命名'),
            status=data.get('status', 'active'),
            followers=data.get('followers', 0)
        )
        
        db.log("INFO", "accounts", f"创建账号: {account.username}")
        return success_response({"id": account.id}, "账号创建成功")
    except Exception as e:
        return error_response(str(e), "CREATE_ERROR")

# ========== 客户管理 ==========

@app.route('/api/customers', methods=['GET'])
def get_customers():
    try:
        db = get_db()
        status = request.args.get('status')
        customers = db.get_customers(status=status)
        return success_response([{
            "id": c.id,
            "name": c.name,
            "phone": c.phone,
            "email": c.email,
            "source": c.source,
            "status": c.status,
            "created_at": c.created_at.isoformat() if c.created_at else None
        } for c in customers])
    except Exception as e:
        return error_response(str(e), "DB_ERROR")

@app.route('/api/customers', methods=['POST'])
def create_customer():
    try:
        data = request.get_json() or {}
        db = get_db()
        
        customer = db.create_customer(
            customer_id=str(uuid.uuid4())[:8],
            name=data.get('name', '未命名'),
            phone=data.get('phone'),
            email=data.get('email'),
            source=data.get('source', 'manual'),
            status=data.get('status', 'new'),
            notes=data.get('notes')
        )
        
        return success_response({"id": customer.id}, "客户创建成功")
    except Exception as e:
        return error_response(str(e), "CREATE_ERROR")

# ========== 内容管理 ==========

@app.route('/api/contents', methods=['GET'])
def get_contents():
    try:
        db = get_db()
        status = request.args.get('status')
        contents = db.get_contents(status=status)
        return success_response([{
            "id": c.id,
            "title": c.title,
            "platform": c.platform,
            "content_type": c.content_type,
            "status": c.status,
            "created_at": c.created_at.isoformat() if c.created_at else None
        } for c in contents])
    except Exception as e:
        return error_response(str(e), "DB_ERROR")

@app.route('/api/contents', methods=['POST'])
def create_content():
    try:
        data = request.get_json() or {}
        db = get_db()
        
        content = db.create_content(
            content_id=str(uuid.uuid4())[:8],
            title=data.get('title', '未命名'),
            content=data.get('content'),
            platform=data.get('platform'),
            content_type=data.get('content_type', 'article'),
            status=data.get('status', 'draft')
        )
        
        return success_response({"id": content.id}, "内容创建成功")
    except Exception as e:
        return error_response(str(e), "CREATE_ERROR")

# ========== 营销活动 ==========

@app.route('/api/campaigns', methods=['GET'])
def get_campaigns():
    try:
        db = get_db()
        campaigns = db.get_campaigns()
        return success_response([{
            "id": c.id,
            "name": c.name,
            "campaign_type": c.campaign_type,
            "status": c.status,
            "start_date": c.start_date.isoformat() if c.start_date else None,
            "end_date": c.end_date.isoformat() if c.end_date else None,
            "budget": c.budget
        } for c in campaigns])
    except Exception as e:
        return error_response(str(e), "DB_ERROR")

@app.route('/api/campaigns', methods=['POST'])
def create_campaign():
    try:
        data = request.get_json() or {}
        db = get_db()
        
        campaign = db.create_campaign(
            campaign_id=str(uuid.uuid4())[:8],
            name=data.get('name', '未命名活动'),
            campaign_type=data.get('campaign_type', 'general'),
            status=data.get('status', 'draft'),
            budget=data.get('budget', 0)
        )
        
        return success_response({"id": campaign.id}, "活动创建成功")
    except Exception as e:
        return error_response(str(e), "CREATE_ERROR")

# ========== 结算管理 ==========

@app.route('/api/settlements', methods=['GET'])
def get_settlements():
    try:
        db = get_db()
        settlements = db.get_settlements()
        return success_response([{
            "id": s.id,
            "settlement_type": s.settlement_type,
            "amount": s.amount,
            "currency": s.currency,
            "status": s.status,
            "party_name": s.party_name,
            "created_at": s.created_at.isoformat() if s.created_at else None
        } for s in settlements])
    except Exception as e:
        return error_response(str(e), "DB_ERROR")

@app.route('/api/settlements', methods=['POST'])
def create_settlement():
    try:
        data = request.get_json() or {}
        db = get_db()
        
        settlement = db.create_settlement(
            settlement_id=str(uuid.uuid4())[:8],
            settlement_type=data.get('settlement_type', 'revenue'),
            amount=float(data.get('amount', 0)),
            party_name=data.get('party_name', '未知'),
            description=data.get('description')
        )
        
        return success_response({"id": settlement.id}, "结算记录创建成功")
    except Exception as e:
        return error_response(str(e), "CREATE_ERROR")

# ========== LLM 聊天 ==========

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        config = get_config()
        
        if not config.llm.enabled:
            return error_response("LLM 未配置", "LLM_NOT_CONFIGURED", 503)
        
        data = request.get_json() or {}
        message = data.get('message', '').strip()
        
        if not message:
            return error_response("消息不能为空", "EMPTY_MESSAGE", 400)
        
        # 尝试调用 LLM
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
            from acas_pro.llm.llm_client import LLMClient, LLMConfig, LLMProvider, LLMMessage
            
            provider_map = {
                'openai': LLMProvider.OPENAI,
                'deepseek': LLMProvider.DEEPSEEK,
                'kimi': LLMProvider.KIMI,
            }
            
            llm_config = LLMConfig(
                provider=provider_map.get(config.llm.provider, LLMProvider.DEEPSEEK),
                api_key=config.llm.api_key,
                model=config.llm.model or None
            )
            
            client = LLMClient(llm_config)
            response = client.chat([LLMMessage(role="user", content=message)])
            
            return success_response({
                "response": response.content,
                "model": config.llm.model,
                "tokens": response.total_tokens
            })
            
        except ImportError:
            # LLM 模块不可用，返回模拟响应
            return success_response({
                "response": f"[模拟模式] 收到消息: {message[:50]}...\n\n实际 LLM 模块加载失败，这是演示响应。",
                "model": "demo",
                "tokens": 0
            })
            
    except Exception as e:
        traceback.print_exc()
        return error_response(f"处理失败: {str(e)}", "PROCESSING_ERROR")

# ========== 日志查询 ==========

@app.route('/api/logs', methods=['GET'])
def get_logs():
    try:
        db = get_db()
        level = request.args.get('level')
        limit = int(request.args.get('limit', 100))
        logs = db.get_logs(level=level, limit=limit)
        return success_response([{
            "id": l.id,
            "level": l.level,
            "module": l.module,
            "message": l.message,
            "created_at": l.created_at.isoformat() if l.created_at else None
        } for l in logs])
    except Exception as e:
        return error_response(str(e), "DB_ERROR")

# ========== 错误处理 ==========

@app.errorhandler(404)
def not_found(e):
    return error_response("接口不存在", "NOT_FOUND", 404)

@app.errorhandler(500)
def internal_error(e):
    return error_response("服务器内部错误", "INTERNAL_ERROR", 500)

@app.errorhandler(Exception)
def handle_exception(e):
    traceback.print_exc()
    return error_response(str(e), "UNHANDLED_ERROR", 500)

# ========== 启动 ==========

if __name__ == '__main__':
    config = get_config()
    
    print("=" * 60)
    print("ACAS Pro API Server v2.0 (Production)")
    print("=" * 60)
    print(f"Database: SQLite (acas_pro.db)")
    print(f"LLM: {config.llm.provider} ({'enabled' if config.llm.enabled else 'disabled'})")
    print(f"Auth: demo-token-2024")
    print("-" * 60)
    print(f"Health:  http://localhost:5000/health")
    print(f"API:     http://localhost:5000/api/")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=False)
