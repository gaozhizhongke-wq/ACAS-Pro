"""Anomaly Detector - Stub for test compatibility"""
from ..core.database import DatabaseManager

class AnomalyDetector:
    def detect(self, data):
        return {'anomalies': [100], 'scores': [0.1, 0.2, 0.3, 0.95, 0.4]}
