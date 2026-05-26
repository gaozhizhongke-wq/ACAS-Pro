"""Dashboard, stats, products, festivals, accounts, and forecast routes."""
from flask import Blueprint, jsonify, request, g
from acas_pro.core.config import config
from acas_pro.core.database import DatabaseManager
from acas_pro.core.logging import get_logger

logger = get_logger(__name__)
bp = Blueprint('dashboard', __name__, url_prefix='')


@bp.route('/api/dashboard/stats')
def dashboard_stats():
    """Real dashboard data from database."""
    import logging
    lg = logging.getLogger(__name__)
    try:
        db = DatabaseManager()
        stats = {}

        try:
            result = db.fetchone(
                "SELECT COALESCE(SUM(amount), 0) AS total "
                "FROM transactions "
                "WHERE created_at >= datetime('now', '-30 days') "
                "  AND status IN ('completed', 'settled')"
            )
            stats['revenue'] = result['total'] if result else 0
        except Exception as e:
            lg.error(f'revenue query failed: {e}')
            stats['revenue'] = 0

        try:
            result = db.fetchone(
                "SELECT COUNT(*) AS cnt "
                "FROM orders "
                "WHERE status IN ('pending', 'processing', 'shipped')"
            )
            stats['active_orders'] = result['cnt'] if result else 0
        except Exception:
            try:
                result = db.fetchone(
                    "SELECT COUNT(*) AS cnt FROM transactions "
                    "WHERE created_at >= datetime('now', '-7 days')"
                )
                stats['active_orders'] = result['cnt'] if result else 0
            except Exception:
                stats['active_orders'] = 0

        try:
            result = db.fetchone(
                "SELECT COUNT(*) AS cnt FROM products WHERE stock_quantity > 0"
            )
            stats['inventory'] = result['cnt'] if result else 0
        except Exception as e:
            lg.error(f'inventory query failed: {e}')
            stats['inventory'] = 0

        try:
            result = db.fetchone(
                "SELECT COUNT(*) AS cnt "
                "FROM products "
                "WHERE stock_quantity > 0 AND stock_quantity <= reorder_point"
            )
            stats['low_stock'] = result['cnt'] if result else 0
        except Exception as e:
            lg.error(f'low_stock query failed: {e}')
            stats['low_stock'] = 0

        try:
            result = db.fetchone(
                "SELECT COUNT(*) AS cnt FROM audit_log WHERE severity IN ('critical', 'warning')"
            )
            stats['risk_alerts'] = result['cnt'] if result else 0
        except Exception as e:
            lg.error(f'risk_alerts query failed: {e}')
            stats['risk_alerts'] = 0

        stats['llm_enabled'] = config().llm.enabled
        stats['llm_provider'] = config().llm.provider if config().llm.enabled else 'disabled'
        return jsonify(stats)
    except Exception as e:
        lg.error(f'dashboard_stats fatal error: {e}', exc_info=True)
        return jsonify({
            'error': 'Dashboard data unavailable', 'detail': str(e), 'status': 'degraded',
            'revenue': 0, 'active_orders': 0, 'inventory': 0, 'low_stock': 0, 'risk_alerts': 0,
            'llm_enabled': config().llm.enabled,
            'llm_provider': config().llm.provider if config().llm.enabled else 'disabled',
        })


@bp.route('/api/festivals', methods=['GET'])
def list_festivals():
    db = DatabaseManager()
    try:
        rows = db.fetchall(
            "SELECT id, name, festival_type, date, region, description, marketing_tips, created_at "
            "FROM festival_calendar ORDER BY date"
        )
        return jsonify({'success': True, 'festivals': rows})
    except Exception as e:
        logger.error(f'festivals query failed: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/products', methods=['GET'])
def list_products():
    db = DatabaseManager()
    try:
        rows = db.fetchall(
            "SELECT id, name, category, price, stock_quantity, reorder_point, status "
            "FROM products ORDER BY name LIMIT 200"
        )
        return jsonify({'success': True, 'products': rows})
    except Exception as e:
        logger.error(f'products query failed: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/products/low-stock', methods=['GET'])
def low_stock_products():
    db = DatabaseManager()
    try:
        rows = db.fetchall(
            "SELECT id, name, category, price, stock_quantity, reorder_point, "
            "       (reorder_point - stock_quantity) AS deficit "
            "FROM products "
            "WHERE stock_quantity > 0 AND stock_quantity <= reorder_point "
            "ORDER BY deficit DESC"
        )
        return jsonify({'success': True, 'products': rows})
    except Exception as e:
        logger.error(f'low-stock query failed: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/accounts', methods=['GET'])
def list_accounts():
    db = DatabaseManager()
    try:
        rows = db.fetchall(
            "SELECT id, platform, account_name, followers, content_count, "
            "       total_views, total_likes, status, phase, last_login_at "
            "FROM platform_accounts ORDER BY platform LIMIT 100"
        )
        return jsonify({'success': True, 'accounts': rows})
    except Exception as e:
        logger.error(f'accounts query failed: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/forecast/daily', methods=['GET'])
def forecast_daily():
    db = DatabaseManager()
    try:
        rows = db.fetchall(
            "SELECT date, platform, SUM(revenue) AS revenue, "
            "       SUM(orders) AS orders, SUM(views) AS views "
            "FROM daily_metrics "
            "WHERE date >= date('now', '-30 days') "
            "GROUP BY date, platform "
            "ORDER BY date ASC LIMIT 90"
        )
        return jsonify({'success': True, 'data': rows})
    except Exception as e:
        logger.error(f'daily_metrics query failed: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500