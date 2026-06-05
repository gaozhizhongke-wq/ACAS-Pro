"""Prometheus metrics endpoint for ACAS Pro."""
from flask import Blueprint, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter, Histogram, Gauge, Info

bp = Blueprint('metrics', __name__, url_prefix='/metrics')

# Application info
app_info = Info('acas_pro', 'ACAS Pro application information')

# Request metrics
request_count = Counter(
    'acas_pro_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

request_duration = Histogram(
    'acas_pro_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

# Business metrics
llm_requests = Counter(
    'acas_pro_llm_requests_total',
    'Total LLM API requests',
    ['provider', 'status']
)

llm_tokens = Counter(
    'acas_pro_llm_tokens_total',
    'Total LLM tokens consumed',
    ['provider', 'type']
)

active_users = Gauge(
    'acas_pro_active_users',
    'Number of active users'
)

db_connections = Gauge(
    'acas_pro_db_connections_active',
    'Active database connections'
)

# Error metrics
error_count = Counter(
    'acas_pro_errors_total',
    'Total errors',
    ['type', 'endpoint']
)


@bp.route('', methods=['GET'])
def metrics():
    """Expose Prometheus metrics."""
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)
