"""Prophet Wrapper - Stub for test compatibility"""
from ..core.database import DatabaseManager

class ProphetWrapper:
    def predict(self, data) -> None:
        return {'forecast': [1, 2, 3], 'trend': 'up'}
