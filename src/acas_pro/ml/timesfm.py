"""Time Series Forecasting Model - Stub implementation."""
from typing import List, Optional, Dict, Any


class TimesFMModel:
    """TimesFM model wrapper - Stub implementation."""
    
    def __init__(self, model_path: str = "", **kwargs):
        self.model_path = model_path
    
    def load(self):
        """Load model weights."""
        pass
    
    def forecast(
        self,
        history: List[float],
        horizon: int = 24,
        freq: str = "H"
    ) -> List[float]:
        """Generate forecast."""
        return [0.0] * horizon
    
    def evaluate(self, test_data: List[float], forecast: List[float]) -> Dict[str, float]:
        """Evaluate forecast accuracy."""
        return {"mae": 0.0, "rmse": 0.0, "mape": 0.0}


def load_model(model_path: str = "", **kwargs) -> TimesFMModel:
    """Load TimesFM model."""
    return TimesFMModel(model_path=model_path)


class TimesFMv2Model(TimesFMModel):
    """TimesFM v2 model - Stub implementation."""
    
    def forecast(self, history: List[float], horizon: int = 24, **kwargs) -> List[float]:
        """Generate forecast with v2 improvements."""
        return [0.0] * horizon
