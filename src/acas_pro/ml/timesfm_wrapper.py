#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ACAS Pro - TimesFM Generic Wrapper (delegates to timesfm.py)."""

from acas_pro.ml.timesfm import TimesFMModel, load_model

__all__ = ["TimesFMWrapper"]


class TimesFMWrapper:
    """Generic TimesFM wrapper for ML pipeline compatibility."""

    def __init__(self, horizon: int = 7, seasonality: int = 7, **kwargs):
        self.horizon = horizon
        self._model = TimesFMModel(horizon=horizon, seasonality=seasonality, **kwargs)

    def predict(self, data, **kwargs):
        """
        Args:
            data: list of floats or dict with "values": [...]
        Returns:
            dict with forecast results
        """
        if isinstance(data, dict):
            values = data.get("values", data.get("data", []))
        else:
            values = data or []
        horizon = kwargs.get("horizon", self.horizon)
        return self._model.forecast(values, horizon=horizon)
