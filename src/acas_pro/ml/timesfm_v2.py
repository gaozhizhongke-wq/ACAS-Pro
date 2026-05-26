"""TimesFM v2 Model - Stub implementation.

This is a stub for the TimesFM v2 model.
"""

from .timesfm import TimesFMModel, load_model

# Re-export for import compatibility
__all__ = ["TimesFMModel", "load_model", "TimesFMv2Model"]


class TimesFMv2Model(TimesFMModel):
    """TimesFM v2 model - Stub implementation."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.version = "2.0"
    
    def forecast(self, history, horizon=24, **kwargs):
        """Generate forecast with v2 improvements."""
        return [0.0] * horizon
