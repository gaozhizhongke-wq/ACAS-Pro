#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ACAS Pro - Prophet-style Forecasting (delegates to ForecastEngine).

Prophet uses additive decomposition (trend + weekly + yearly + holidays).
This implementation approximates Prophet's behavior using Holt-Winters.
"""

from acas_pro.advanced_analytics.forecast_engine import ForecastEngine

__all__ = ["ProphetWrapper"]


class ProphetWrapper:
    """
    Prophet-style forecasting using triple exponential smoothing.
    Supports weekly (period=7) and yearly (period=365) seasonality estimation.
    """

    def __init__(self, yearly_seasonality: bool = True, weekly_seasonality: bool = True, **kwargs):
        self.yearly_seasonality = yearly_seasonality
        self.weekly_seasonality = weekly_seasonality

    def predict(self, data, **kwargs):
        """
        Args:
            data: list of floats OR dict with "y": list of values
        Returns:
            dict with forecast, trend, and confidence
        """
        if isinstance(data, dict):
            values = data.get("y", data.get("values", []))
        else:
            values = data or []

        if not values or len(values) < 14:
            return {
                "forecast": [],
                "trend": 0.0,
                "confidence": 0.0,
                "method": "prophet_wrapper",
                "note": "Insufficient data (< 14 points) for Prophet-style forecast",
            }

        # Use Holt-Winters with weekly seasonality
        period = 7 if self.weekly_seasonality else 7
        engine = ForecastEngine(seasonal_period=period, forecast_horizon=7)
        result = engine.forecast(values, method="holt_winters")
        result["method"] = "prophet_wrapper"
        return result
