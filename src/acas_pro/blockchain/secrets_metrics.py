"""Secrets metrics for blockchain module."""


class SecretsMetrics:
    """Track and report secrets/metrics for the blockchain layer."""

    def __init__(self):
        self._metrics: dict = {}

    def record(self, name: str, value: float = 1.0, tags: dict = None):
        self._metrics[name] = {"value": value, "tags": tags or {}}

    def get(self, name: str, default: float = 0.0) -> float:
        return self._metrics.get(name, {}).get("value", default)

    def report(self) -> dict:
        return dict(self._metrics)

    def reset(self):
        self._metrics.clear()
