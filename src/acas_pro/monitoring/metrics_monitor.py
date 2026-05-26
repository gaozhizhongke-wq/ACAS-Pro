"""Metrics monitoring and aggregation."""

from typing import Dict, List, Optional
from datetime import datetime, timezone
from collections import defaultdict


class MetricsMonitor:
    """Collect, aggregate and report application metrics."""

    def __init__(self):
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histories: Dict[str, List[tuple]] = defaultdict(list)

    def increment(self, name: str, value: float = 1.0):
        self._counters[name] += value
        self._histories[name].append((datetime.now(timezone.utc).isoformat(), value))

    def gauge(self, name: str, value: float):
        self._gauges[name] = value

    def get_counter(self, name: str) -> float:
        return self._counters.get(name, 0.0)

    def get_gauge(self, name: str) -> Optional[float]:
        return self._gauges.get(name)

    def get_history(self, name: str, limit: int = 100) -> list:
        return self._histories.get(name, [])[-limit:]

    def report(self) -> dict:
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def reset(self):
        self._counters.clear()
        self._gauges.clear()
        self._histories.clear()
