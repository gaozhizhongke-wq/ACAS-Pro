# -*- coding: utf-8 -*-
"""Health check routes for ACAS Pro."""

from flask import Blueprint, jsonify
from acas_pro.web.health import health_checker

bp = Blueprint("health", __name__, url_prefix="/api")


@bp.route("/health", methods=["GET"])
def health_check() -> None:
    """Liveness/readiness probe endpoint."""
    result = health_checker.check_all()
    status = result.get("status", "unknown")
    if status == "healthy":
        return jsonify(result), 200
    elif status == "degraded":
        return jsonify(
            result
        ), 200  # Still return 200 so load balancers don't kill the pod
    else:
        return jsonify(result), 503
