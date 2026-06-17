#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Sales Forecasting Engine
Multi-method time series forecasting using pure numpy.

Methods:
  1. Simple Moving Average (SMA)
  2. Exponential Smoothing (SES) — single, double (Holt), triple (Holt-Winters)
  3. Linear Trend (OLS)

No external ML dependencies — pure numpy implementation.
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class ForecastResult:
    forecast: List[float]
    confidence: float        # 0-1
    method: str               # 'ses' | 'holt' | 'holt_winters' | 'sma' | 'linear'
    trend: float             # estimated trend per period
    seasonal: Optional[List[float]]  # seasonal indices if available
    residuals: List[float]   # in-sample residuals


class ForecastEngine:
    """
    Time series forecasting for business metrics.

    Args:
        alpha: SES smoothing parameter (0 < alpha <= 1)
        beta:  Trend smoothing parameter (Holt/Double SES)
        seasonal_period: Seasonal period for Holt-Winters (e.g. 7=daily-weekly)
        forecast_horizon: Number of periods to forecast (default 7)
    """

    def __init__(
        self,
        alpha: float = 0.3,
        beta: float = 0.1,
        seasonal_period: int = 7,
        forecast_horizon: int = 7,
    ) -> None:
        if not (0 < alpha <= 1):
            raise ValueError("alpha must be in (0, 1]")
        if not (0 <= beta <= 1):
            raise ValueError("beta must be in [0, 1]")
        if seasonal_period < 2:
            raise ValueError("seasonal_period must be >= 2")
        self.alpha = alpha
        self.beta = beta
        self.seasonal_period = seasonal_period
        self.forecast_horizon = forecast_horizon

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def forecast(
        self,
        data: List[float],
        method: str = "auto",
        horizon: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Generate forecasts from historical time series.

        Args:
            data: Historical values (e.g. daily sales)
            method: 'auto' | 'ses' | 'holt' | 'holt_winters' | 'sma' | 'linear'
            horizon: Override forecast_horizon for this call

        Returns:
            Dict with:
              - forecast: list of forecasted values
              - confidence: confidence score 0-1
              - method: which method was used
              - trend: trend coefficient
              - seasonal: seasonal indices (holt_winters only)
              - residuals: in-sample errors
              - next_period: predicted next value
        """
        if not data or len(data) < 3:
            return self._empty_result()

        arr = np.array(data, dtype=np.float64)
        arr = arr[np.isfinite(arr)]
        if len(arr) < 3:
            return self._empty_result()

        h = horizon or self.forecast_horizon

        # Auto-select method based on data length
        if method == "auto":
            if len(arr) >= 2 * self.seasonal_period:
                method = "holt_winters"
            elif len(arr) >= 10:
                method = "holt"
            elif len(arr) >= 5:
                method = "ses"
            else:
                method = "sma"

        if method == "holt_winters":
            result = self._holt_winters(arr, h)
        elif method == "holt":
            result = self._holt(arr, h)
        elif method == "ses":
            result = self._ses(arr, h)
        elif method == "linear":
            result = self._linear(arr, h)
        else:  # sma or fallback
            result = self._sma(arr, h)

        # Calculate confidence from residual variance
        residuals = result.residuals
        if len(residuals) > 1:
            mse = np.mean(np.array(residuals) ** 2)
            data_std = max(np.std(arr), 1e-9)
            # MAPE-like confidence: clamp to [0,1]
            rmse = np.sqrt(mse)
            confidence = float(np.clip(1 - rmse / data_std, 0.0, 1.0))
        else:
            confidence = 0.5

        return {
            "forecast": [round(v, 4) for v in result.forecast],
            "confidence": round(confidence, 3),
            "method": result.method,
            "trend": round(result.trend, 4),
            "seasonal": [round(v, 4) for v in result.seasonal] if result.seasonal else None,
            "residuals": [round(v, 4) for v in result.residuals],
            "next_period": round(result.forecast[0], 4) if result.forecast else 0.0,
        }

    # ------------------------------------------------------------------
    # Forecasting methods
    # ------------------------------------------------------------------

    def _sma(self, arr: np.ndarray, h: int) -> ForecastResult:
        """Simple Moving Average — last N periods average."""
        window = min(3, len(arr))
        base = float(np.mean(arr[-window:]))
        residuals = (arr - np.mean(arr)).tolist()
        return ForecastResult(
            forecast=[base] * h,
            confidence=0.5,
            method="sma",
            trend=0.0,
            seasonal=None,
            residuals=residuals,
        )

    def _ses(self, arr: np.ndarray, h: int) -> ForecastResult:
        """Simple Exponential Smoothing — weighted average with exponential decay."""
        alpha = self.alpha
        # Initialize: level = first value
        level = float(arr[0])
        residuals = [float(arr[0])]

        for i in range(1, len(arr)):
            residual = float(arr[i]) - level
            level = alpha * float(arr[i]) + (1 - alpha) * level
            residuals.append(residual)

        forecast = [level] * h
        trend = 0.0
        return ForecastResult(
            forecast=forecast,
            confidence=0.6,
            method="ses",
            trend=trend,
            seasonal=None,
            residuals=residuals,
        )

    def _holt(self, arr: np.ndarray, h: int) -> ForecastResult:
        """Holt's Linear — exponential smoothing with trend."""
        alpha, beta = self.alpha, self.beta
        # Initialize
        level = float(arr[0])
        trend = float(arr[min(1, len(arr)-1)]) - float(arr[0]) if len(arr) > 1 else 0.0
        residuals = [0.0]

        for i in range(1, len(arr)):
            prev_level = level
            level = alpha * float(arr[i]) + (1 - alpha) * (level + trend)
            trend = beta * (level - prev_level) + (1 - beta) * trend
            residuals.append(float(arr[i]) - prev_level - trend)

        forecast = [level + (i + 1) * trend for i in range(h)]
        return ForecastResult(
            forecast=forecast,
            confidence=0.7,
            method="holt",
            trend=float(trend),
            seasonal=None,
            residuals=residuals,
        )

    def _holt_winters(self, arr: np.ndarray, h: int) -> ForecastResult:
        """Holt-Winters — triple exponential smoothing with seasonality."""
        alpha, beta, gamma = self.alpha, self.beta, 0.1
        period = self.seasonal_period
        n = len(arr)

        if n < 2 * period:
            # Not enough data for full seasonal estimation — fall back to Holt
            return self._holt(arr, h)

        # Initialize level from first full seasonal period average
        level = float(np.mean(arr[:period]))
        # Initialize trend
        trend = float(np.mean(arr[period:2*period]) - np.mean(arr[:period])) / period
        # Initialize seasonal indices (multiplicative)
        seasonal = np.array([
            float(arr[i]) / max(level, 1e-9)
            for i in range(period)
        ])
        residuals: List[float] = []

        for i in range(period, n):
            prev_level = level
            level = alpha * (float(arr[i]) / max(seasonal[i % period], 1e-9)) \
                + (1 - alpha) * (level + trend)
            trend = beta * (level - prev_level) + (1 - beta) * trend
            seasonal[i % period] = gamma * (float(arr[i]) / max(level, 1e-9)) \
                + (1 - gamma) * seasonal[i % period]
            # Residuals: actual - (level + trend) * seasonal
            fitted = (level - trend) * seasonal[i % period]
            residuals.append(float(arr[i]) - fitted)

        # Forecast
        forecast = []
        for j in range(1, h + 1):
            s_idx = (n + j - 1) % period
            val = (level + j * trend) * seasonal[s_idx]
            forecast.append(max(val, 0.0))  # sales can't be negative

        return ForecastResult(
            forecast=forecast,
            confidence=0.75,
            method="holt_winters",
            trend=float(trend),
            seasonal=seasonal.tolist(),
            residuals=residuals,
        )

    def _linear(self, arr: np.ndarray, h: int) -> ForecastResult:
        """Ordinary Least Squares linear regression."""
        x = np.arange(len(arr), dtype=np.float64)
        x_mean = np.mean(x)
        y_mean = np.mean(arr)
        ss_x = np.sum((x - x_mean) ** 2)
        if ss_x < 1e-9:
            return self._sma(arr, h)

        slope = np.sum((x - x_mean) * (arr - y_mean)) / ss_x
        intercept = y_mean - slope * x_mean

        fitted = slope * x + intercept
        residuals = (arr - fitted).tolist()

        future_x = np.arange(len(arr), len(arr) + h, dtype=np.float64)
        forecast = (slope * future_x + intercept).tolist()

        return ForecastResult(
            forecast=forecast,
            confidence=0.65,
            method="linear",
            trend=float(slope),
            seasonal=None,
            residuals=residuals,
        )

    @staticmethod
    def _empty_result() -> Dict[str, Any]:
        return {
            "forecast": [],
            "confidence": 0.0,
            "method": "none",
            "trend": 0.0,
            "seasonal": None,
            "residuals": [],
            "next_period": 0.0,
        }
