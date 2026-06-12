"""Prometheus metrics endpoint for ACAS Pro."""

from flask import Blueprint, Response

try:
    from prometheus_client import (
        generate_latest,
        CONTENT_TYPE_LATEST,
        CollectorRegistry,
        Counter,
        Histogram,
        Gauge,
        Info,
    )

    _HAS_PROMETHEUS = True
except ImportError:
    _HAS_PROMETHEUS = False

bp = Blueprint("metrics", __name__, url_prefix="/metrics")

# Use a dedicated registry so re-imports / multiple create_app() calls
# never clash with the default global registry.
_registry = None
_metrics = {}


def _init_metrics() -> None:
    """Lazily initialise metrics on first request (idempotent)."""
    global _registry, _metrics
    if _registry is not None:
        return
    if not _HAS_PROMETHEUS:
        return

    _registry = CollectorRegistry()

    _metrics["app_info"] = Info(
        "acas_pro",
        "ACAS Pro application information",
        registry=_registry,
    )
    _metrics["request_count"] = Counter(
        "acas_pro_http_requests_total",
        "Total HTTP requests",
        ["method", "endpoint", "status_code"],
        registry=_registry,
    )
    _metrics["request_duration"] = Histogram(
        "acas_pro_http_request_duration_seconds",
        "HTTP request duration in seconds",
        ["method", "endpoint"],
        registry=_registry,
    )
    _metrics["llm_requests"] = Counter(
        "acas_pro_llm_requests_total",
        "Total LLM API requests",
        ["provider", "status"],
        registry=_registry,
    )
    _metrics["llm_tokens"] = Counter(
        "acas_pro_llm_tokens_total",
        "Total LLM tokens consumed",
        ["provider", "type"],
        registry=_registry,
    )
    _metrics["active_users"] = Gauge(
        "acas_pro_active_users",
        "Number of active users",
        registry=_registry,
    )
    _metrics["db_connections"] = Gauge(
        "acas_pro_db_connections_active",
        "Active database connections",
        registry=_registry,
    )
    _metrics["error_count"] = Counter(
        "acas_pro_errors_total",
        "Total errors",
        ["type", "endpoint"],
        registry=_registry,
    )


@bp.route("", methods=["GET"])
def metrics() -> Response:
    """Expose Prometheus metrics."""
    if not _HAS_PROMETHEUS:
        return Response(
            "prometheus_client not installed", status=503, mimetype="text/plain"
        )
    _init_metrics()
    return Response(generate_latest(_registry), mimetype=CONTENT_TYPE_LATEST)  # type: ignore[arg-type]
