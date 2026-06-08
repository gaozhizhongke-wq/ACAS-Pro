"""Health monitoring for system components."""

from typing import Dict, Optional
from datetime import datetime, timezone


class HealthMonitor:
    """Monitor system health and report status."""

    def __init__(self):
        self._checks: Dict[str, dict] = {}
        self._status = "healthy"

    def register_check(self, name: str, check_fn=None) -> None:
        self._checks[name] = {"fn": check_fn, "status": "unknown", "last_check": None}

    def check(self, name: Optional[str] = None) -> dict:
        if name:
            info = self._checks.get(name, {})
            return {"name": name, "status": info.get("status", "unknown")}
        results = {}
        for n, info in self._checks.items():
            results[n] = info.get("status", "unknown")
        return results

    def update_status(self, name: str, status: str) -> None:
        if name in self._checks:
            self._checks[name]["status"] = status
            self._checks[name]["last_check"] = datetime.now(timezone.utc).isoformat()

    @property
    def overall_status(self) -> str:
        statuses = [v.get("status", "unknown") for v in self._checks.values()]
        if any(s == "unhealthy" for s in statuses):
            return "unhealthy"
        if any(s == "degraded" for s in statuses):
            return "degraded"
        return "healthy"

    def report(self) -> dict:
        return {
            "overall_status": self.overall_status,
            "checks": dict(self._checks),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


health_monitor = HealthMonitor()
