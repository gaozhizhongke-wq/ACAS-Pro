"""TimesFM Wrapper - Stub for test compatibility"""


class TimesFMWrapper:
    def predict(self, data) -> None:
        return {"forecast": [1, 2, 3], "horizon": 3}
