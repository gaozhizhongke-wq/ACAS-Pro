"""Dashboard routes for ACAS Pro Web"""

from typing import Any
from flask import Blueprint, render_template, jsonify
from datetime import datetime, timezone
from acas_pro.core.logging import get_logger
import sqlite3

logger = get_logger(__name__)
bp = Blueprint("dashboard", __name__, template_folder="../../templates")


# Dashboard HTML template


@bp.route("/")
def index() -> Any:
    """Main dashboard page - returns real HTML"""
    from acas_pro.core.config import get_config
    cfg = get_config()
    llm_provider = cfg.llm.provider if cfg.llm.enabled else 'not configured'
    key_val = cfg.llm.api_key
    llm_key_mask = ('*' * 20) + key_val[-4:] if key_val else 'not set'
    
    return render_template(
        "dashboard.html",
        llm_provider=llm_provider,
        llm_key_mask=llm_key_mask,
        llm_enabled=cfg.llm.enabled,
    )


@bp.route("/api/stats")
def dashboard_stats() -> Any:
    """Dashboard statistics API - production-grade with explicit error handling"""
    from acas_pro.core.database import db

    stats = {
        "active_users": 0,
        "content_count": 0,
        "pending_tasks": 0,
        "api_calls_today": 0,
        "products_count": 0,
        "total_revenue": 0.0,
        "transactions_today": 0,
        "alerts_count": 0,
    }

    # 1. Active users (last 24h)
    try:
        result = db.fetchall(
            "SELECT COUNT(*) as cnt FROM users WHERE last_login > datetime('now', '-1 day')"
        )
        if result and len(result) > 0:
            stats["active_users"] = int(result[0].get("cnt", 0))
    except sqlite3.OperationalError as e:
        logger.warning(f"[dashboard_stats] users table query failed: {e}")
    except Exception as e:
        logger.error(f"[dashboard_stats] Unexpected error querying users: {e}")

    # 2. Products count
    try:
        result = db.fetchall("SELECT COUNT(*) as cnt FROM products")
        if result and len(result) > 0:
            stats["products_count"] = int(result[0].get("cnt", 0))
    except sqlite3.OperationalError as e:
        logger.warning(f"[dashboard_stats] products table query failed: {e}")
    except Exception as e:
        logger.error(f"[dashboard_stats] Unexpected error querying products: {e}")

    # 3. Total revenue (completed transactions)
    try:
        result = db.fetchall(
            "SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE status = 'completed'"
        )
        if result and len(result) > 0:
            stats["total_revenue"] = float(result[0].get("total", 0.0))
    except sqlite3.OperationalError as e:
        logger.warning(f"[dashboard_stats] transactions revenue query failed: {e}")
    except Exception as e:
        logger.error(f"[dashboard_stats] Unexpected error querying revenue: {e}")

    # 4. Transactions today
    try:
        result = db.fetchall(
            "SELECT COUNT(*) as cnt FROM transactions WHERE created_at > datetime('now', 'start of day')"
        )
        if result and len(result) > 0:
            stats["transactions_today"] = int(result[0].get("cnt", 0))
    except sqlite3.OperationalError as e:
        logger.warning(f"[dashboard_stats] transactions today query failed: {e}")
    except Exception as e:
        logger.error(
            f"[dashboard_stats] Unexpected error querying transactions today: {e}"
        )

    # 5. Pending tasks (publish_tasks)
    try:
        result = db.fetchall(
            "SELECT COUNT(*) as cnt FROM publish_tasks WHERE status = 'pending'"
        )
        if result and len(result) > 0:
            stats["pending_tasks"] = int(result[0].get("cnt", 0))
    except sqlite3.OperationalError as e:
        logger.warning(f"[dashboard_stats] publish_tasks query failed: {e}")
    except Exception as e:
        logger.error(f"[dashboard_stats] Unexpected error querying pending tasks: {e}")

    # 6. Content count (generated_scripts + publish_tasks)
    try:
        scripts = db.fetchall("SELECT COUNT(*) as cnt FROM generated_scripts")
        tasks = db.fetchall("SELECT COUNT(*) as cnt FROM publish_tasks")
        cnt = 0
        if scripts and len(scripts) > 0:
            cnt += int(scripts[0].get("cnt", 0))
        if tasks and len(tasks) > 0:
            cnt += int(tasks[0].get("cnt", 0))
        stats["content_count"] = cnt
    except sqlite3.OperationalError as e:
        logger.warning(f"[dashboard_stats] content count query failed: {e}")
    except Exception as e:
        logger.error(f"[dashboard_stats] Unexpected error querying content: {e}")

    # 7. Alerts count (unacknowledged)
    try:
        result = db.fetchall(
            "SELECT COUNT(*) as cnt FROM data_alerts WHERE acknowledged = 0"
        )
        if result and len(result) > 0:
            stats["alerts_count"] = int(result[0].get("cnt", 0))
    except sqlite3.OperationalError as e:
        logger.warning(f"[dashboard_stats] data_alerts query failed: {e}")
    except Exception as e:
        logger.error(f"[dashboard_stats] Unexpected error querying alerts: {e}")

    # 8. API calls today (from audit_log)
    try:
        result = db.fetchall(
            "SELECT COUNT(*) as cnt FROM audit_log WHERE timestamp > datetime('now', 'start of day')"
        )
        if result and len(result) > 0:
            stats["api_calls_today"] = int(result[0].get("cnt", 0))
    except sqlite3.OperationalError as e:
        logger.warning(f"[dashboard_stats] audit_log query failed: {e}")
    except Exception as e:
        logger.error(f"[dashboard_stats] Unexpected error querying audit log: {e}")

    return jsonify(
        {
            "success": True,
            "stats": stats,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


@bp.route("/api/activity")
def recent_activity() -> Any:
    """Recent activity API - reads from audit_log with explicit error handling"""
    from acas_pro.core.database import db

    activities = []

    # Try audit_log first
    try:
        rows = db.fetchall(
            "SELECT timestamp as time, event_type as event, severity as status "
            "FROM audit_log ORDER BY timestamp DESC LIMIT 20"
        )
        if rows:
            for r in rows:
                activities.append(
                    {
                        "time": str(r.get("time", ""))[:19] if r.get("time") else "",
                        "event": r.get("event", ""),
                        "status": r.get("status", "info"),
                    }
                )
    except sqlite3.OperationalError as e:
        logger.warning(f"[recent_activity] audit_log query failed: {e}")
    except Exception as e:
        logger.error(f"[recent_activity] Unexpected error querying audit_log: {e}")

    # Fallback: try transactions
    if not activities:
        try:
            rows = db.fetchall(
                "SELECT created_at as time, type as event, status "
                "FROM transactions ORDER BY created_at DESC LIMIT 10"
            )
            if rows:
                for r in rows:
                    activities.append(
                        {
                            "time": str(r.get("time", ""))[:19]
                            if r.get("time")
                            else "",
                            "event": f"Transaction: {r.get('event', '')}",
                            "status": r.get("status", "completed"),
                        }
                    )
        except sqlite3.OperationalError as e:
            logger.warning(f"[recent_activity] transactions query failed: {e}")
        except Exception as e:
            logger.error(
                f"[recent_activity] Unexpected error querying transactions: {e}"
            )

    if not activities:
        activities = [{"time": "-", "event": "No activity recorded", "status": "info"}]

    return jsonify({"success": True, "activities": activities})
