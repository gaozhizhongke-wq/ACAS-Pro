#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ACAS Pro - TimesFM V2 (delegates to timesfm.py for compatibility)."""

from acas_pro.ml.timesfm import TimesFMModel, load_model

__all__ = ["TimesFMV2"]


class TimesFMV2:
    """V2 wrapper — delegates to TimesFMModel."""

    def __init__(self, model_path: str = "", horizon: int = 7, **kwargs):
        self._model = TimesFMModel(model_path=model_path, horizon=horizon, **kwargs)

    def predict(self, data, **kwargs):
        """
        Args:
            data: list of floats or dict with "values": [...]
        Returns:
            dict with forecast results
        """
        if isinstance(data, dict):
            values = data.get("values", data.get("forecast", []))
            horizon = kwargs.get("horizon", data.get("horizon", 7))
        else:
            values = data or []
            horizon = kwargs.get("horizon", 7)
        return self._model.forecast(values, horizon=horizon)
