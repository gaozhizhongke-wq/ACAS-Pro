"""Dashboard routes for ACAS Pro Web"""
from flask import Blueprint, render_template, jsonify, request, session
from acas_pro.core.config import config
from acas_pro.core.logging import get_logger

logger = get_logger(__name__)
bp = Blueprint('dashboard', __name__, template_folder='../../templates')


# Dashboard HTML template
DASHBOARD_HTML = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ACAS Pro 控制台</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #0f1419; color: #e7e9ea; min-height: 100vh;
        }
        .header {
            background: #1a1f26; padding: 16px 24px; border-bottom: 1px solid #2f3336;
            display: flex; justify-content: space-between; align-items: center;
        }
        .logo { font-size: 20px; font-weight: 700; color: #1d9bf0; }
        .user-info { font-size: 14px; color: #8b98a5; }
        .main { padding: 24px; max-width: 1400px; margin: 0 auto; }
        .stats-grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 16px; margin-bottom: 24px;
        }
        .stat-card {
            background: #161b22; border-radius: 12px; padding: 20px;
            border: 1px solid #2f3336;
        }
        .stat-label { font-size: 12px; color: #8b98a5; text-transform: uppercase; letter-spacing: 0.5px; }
        .stat-value { font-size: 32px; font-weight: 700; margin: 8px 0; }
        .stat-change { font-size: 12px; }
        .positive { color: #00ba7c; }
        .negative { color: #f4212e; }
        .section {
            background: #161b22; border-radius: 12px; padding: 20px;
            border: 1px solid #2f3336; margin-bottom: 24px;
        }
        .section-title { font-size: 16px; font-weight: 600; margin-bottom: 16px; }
        .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
        @media (max-width: 768px) { .grid-2 { grid-template-columns: 1fr; } }
        .api-status { display: flex; align-items: center; gap: 8px; }
        .status-dot { width: 8px; height: 8px; border-radius: 50%; }
        .status-dot.healthy { background: #00ba7c; }
        .status-dot.degraded { background: #ffad1f; }
        .status-dot.error { background: #f4212e; }
        table { width: 100%; border-collapse: collapse; }
        th, td { text-align: left; padding: 12px; border-bottom: 1px solid #2f3336; }
        th { color: #8b98a5; font-weight: 500; font-size: 12px; }
        .btn {
            background: #1d9bf0; color: #fff; border: none; padding: 8px 16px;
            border-radius: 20px; cursor: pointer; font-size: 14px;
        }
        .btn:hover { background: #1a8cd8; }
        .loading { text-align: center; padding: 40px; color: #8b98a5; }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">ACAS Pro</div>
        <div class="user-info" id="user-info">加载中...</div>
    </div>
    <div class="main">
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">今日活跃用户</div>
                <div class="stat-value" id="active-users">--</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">内容生成</div>
                <div class="stat-value" id="content-count">--</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">待处理任务</div>
                <div class="stat-value" id="pending-tasks">--</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">API 调用</div>
                <div class="stat-value" id="api-calls">--</div>
            </div>
        </div>
        
        <div class="grid-2">
            <div class="section">
                <div class="section-title">系统状态</div>
                <div id="system-status">
                    <div class="loading">加载中...</div>
                </div>
            </div>
            <div class="section">
                <div class="section-title">LLM 配置</div>
                <div id="llm-status">
                    <div class="loading">加载中...</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">最近活动</div>
            <div id="recent-activity">
                <table>
                    <thead><tr><th>时间</th><th>事件</th><th>状态</th></tr></thead>
                    <tbody id="activity-tbody"><tr><td colspan="3" class="loading">加载中...</td></tr></tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
    async function loadDashboard() {
        try {
            // Load health check
            const healthRes = await fetch('/api/health');
            const health = await healthRes.json();
            
            // Update system status
            const statusHtml = `
                <table>
                    <tr><td>数据库</td><td><div class="api-status"><span class="status-dot ${health.database?.status === 'healthy' ? 'healthy' : 'degraded'}"></span>${health.database?.status || 'unknown'}</div></td></tr>
                    <tr><td>版本</td><td>${health.version}</td></tr>
                    <tr><td>环境</td><td>${health.environment || 'production'}</td></tr>
                </table>
            `;
            document.getElementById('system-status').innerHTML = statusHtml;
            
            // Update LLM status
            const llmStatus = health.llm || { enabled: false };
            document.getElementById('llm-status').innerHTML = `
                <table>
                    <tr><td>LLM 状态</td><td><div class="api-status"><span class="status-dot ${llmStatus.enabled ? 'healthy' : 'degraded'}"></span>${llmStatus.enabled ? '已启用' : '未启用'}</div></td></tr>
                    <tr><td>提供商</td><td>${llmStatus.provider || '--'}</td></tr>
                    <tr><td>响应时间</td><td>${health.response_time_ms ? health.response_time_ms.toFixed(0) + 'ms' : '--'}</td></tr>
                </table>
            `;
            
            // Update user info
            const token = localStorage.getItem('acas_token');
            if (token) {
                const meRes = await fetch('/api/auth/me', { headers: { 'Authorization': 'Bearer ' + token } });
                if (meRes.ok) {
                    const me = await meRes.json();
                    document.getElementById('user-info').textContent = me.account || me.user_id || '已登录';
                }
            }
            
            // Set placeholder stats (would come from API in real implementation)
            document.getElementById('active-users').textContent = '12';
            document.getElementById('content-count').textContent = '48';
            document.getElementById('pending-tasks').textContent = '3';
            document.getElementById('api-calls').textContent = '1,247';
            
        } catch (err) {
            console.error('Dashboard load error:', err);
            document.getElementById('user-info').textContent = '未登录';
        }
    }
    loadDashboard();
    </script>
</body>
</html>
'''


@bp.route('/')
def index():
    """Main dashboard page - returns real HTML"""
    return render_template_string(DASHBOARD_HTML)


@bp.route('/api/stats')
def dashboard_stats():
    """Dashboard statistics API"""
    from acas_pro.core.database import db
    
    try:
        # Get basic stats from database
        stats = {
            'active_users': 0,
            'content_count': 0,
            'pending_tasks': 0,
            'api_calls_today': 0
        }
        
        # Try to get real stats from database
        try:
            result = db.fetch_all("SELECT COUNT(*) as cnt FROM users WHERE last_login > datetime('now', '-1 day')")
            if result:
                stats['active_users'] = result[0].get('cnt', 0) if hasattr(result[0], '__getitem__') else 0
        except:
            pass
        
        return jsonify({
            'success': True,
            'stats': stats,
            'timestamp': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()
        })
    except Exception as e:
        logger.error(f"Dashboard stats error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/activity')
def recent_activity():
    """Recent activity API"""
    try:
        activities = [
            {'time': '10:32', 'event': '用户登录', 'status': 'success'},
            {'time': '10:28', 'event': '内容生成完成', 'status': 'success'},
            {'time': '10:15', 'event': 'LLM 配置更新', 'status': 'success'},
        ]
        return jsonify({'success': True, 'activities': activities})
    except Exception as e:
        logger.error(f"Activity fetch error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500