"""Sklearn Wrapper - Stub for test compatibility"""
from ..core.database import DatabaseManager

class SklearnWrapper:
    def predict(self, data) -> None:
        return {'prediction': 'class_A', 'probability': 0.9}
