#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ACAS Pro - Simple Forecasting (delegates to ForecastEngine)."""

from acas_pro.advanced_analytics.forecast_engine import ForecastEngine

__all__ = ["Forecast"]


class Forecast:
    """Wrapper around ForecastEngine for backward compatibility."""

    def predict(self, data, **kwargs):
        if isinstance(data, list):
            engine = ForecastEngine()
            result = engine.forecast(data)
            return result
        # Support dict input: {"values": [...], "horizon": int}
        if isinstance(data, dict):
            values = data.get("values", data.get("data", []))
            horizon = data.get("horizon", kwargs.get("horizon", 7))
            engine = ForecastEngine(forecast_horizon=horizon)
            return engine.forecast(values)
        return {"forecast": [], "confidence": 0.0}
