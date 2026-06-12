# Routes package — export all blueprints
from acas_pro.web.routes.auth import bp as auth_bp
from acas_pro.web.routes.llm import bp as llm_bp
from acas_pro.web.routes.dashboard_stats import bp as dashboard_bp

__all__ = ["auth_bp", "llm_bp", "dashboard_bp"]
