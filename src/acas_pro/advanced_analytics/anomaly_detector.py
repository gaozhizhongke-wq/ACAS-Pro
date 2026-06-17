#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Anomaly Detection Engine
Statistical and Z-score based anomaly detection for business metrics.

Uses multiple detection methods:
  1. Z-score  — standard deviations from rolling mean
  2. IQR      — interquartile range (robust to outliers)
  3. Rolling  — compare against recent window average

No external ML dependencies — pure numpy implementation.
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class AnomalyResult:
    is_anomaly: bool
    score: float          # 0=normal, 1=strongly anomalous
    method: str            # 'zscore' | 'iqr' | 'rolling'
    threshold: float       # threshold that was used
    value: float           # input value
    context: Dict[str, float]  # mean, std, median, etc.


class AnomalyDetector:
    """
    Detect anomalies in time-series or batch numeric data.

    Args:
        z_threshold: Z-score threshold (default 3.0 = 3 std devs)
        iqr_multiplier: IQR multiplier (default 1.5)
        window_size: Rolling window size (default 7)
        sensitivity: 0-1 float to adjust all thresholds (lower = more sensitive)
    """

    def __init__(
        self,
        z_threshold: float = 3.0,
        iqr_multiplier: float = 1.5,
        window_size: int = 7,
        sensitivity: float = 1.0,
    ) -> None:
        if not (0.1 < sensitivity <= 1.0):
            raise ValueError("sensitivity must be in (0.1, 1.0]")
        self.z_threshold = z_threshold * sensitivity
        self.iqr_multiplier = iqr_multiplier / sensitivity
        self.window_size = window_size

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(self, data: List[float]) -> Dict[str, Any]:
        """
        Detect anomalies in a list of numeric values.

        Args:
            data: List of numeric values (e.g. daily revenue, hourly clicks)

        Returns:
            Dict with:
              - anomalies: list of anomaly indices
              - scores: anomaly scores per point (0=normal, 1=anomalous)
              - summary: statistics and method used
        """
        if not data:
            return self._empty_result()

        arr = np.array(data, dtype=np.float64)

        # Remove NaN/Inf
        arr = arr[np.isfinite(arr)]
        if len(arr) < 3:
            return self._empty_result()

        # Run all three methods
        zscore_results = self._detect_zscore(arr)
        iqr_results = self._detect_iqr(arr)
        rolling_results = self._detect_rolling(arr)

        # Combine: mark as anomaly if ANY method detects it
        combined_scores = np.maximum.reduce([
            zscore_results.scores,
            iqr_results.scores,
            rolling_results.scores,
        ])

        anomaly_indices = np.where(combined_scores > 0.5)[0].tolist()

        return {
            "anomalies": anomaly_indices,
            "scores": combined_scores.tolist(),
            "summary": {
                "total_points": len(data),
                "valid_points": len(arr),
                "anomaly_count": len(anomaly_indices),
                "anomaly_rate": round(len(anomaly_indices) / len(arr), 4) if arr.size else 0,
                "methods_used": ["zscore", "iqr", "rolling"],
                "zscore_threshold": round(self.z_threshold, 3),
                "iqr_multiplier": round(self.iqr_multiplier, 3),
                "window_size": self.window_size,
                "mean": round(float(np.mean(arr)), 4),
                "std": round(float(np.std(arr)), 4),
                "median": round(float(np.median(arr)), 4),
            },
        }

    def detect_point(self, value: float, baseline: List[float]) -> AnomalyResult:
        """Detect if a single value is anomalous against a baseline population."""
        if not baseline:
            return AnomalyResult(
                is_anomaly=False,
                score=0.0,
                method="none",
                threshold=0.0,
                value=value,
                context={},
            )

        arr = np.array(baseline, dtype=np.float64)
        arr = arr[np.isfinite(arr)]

        # Primary: Z-score
        zscore_result = self._detect_zscore(arr)
        zscore_val = abs(value - zscore_result.context["mean"]) / max(zscore_result.context["std"], 1e-9)

        if zscore_val > self.z_threshold:
            return AnomalyResult(
                is_anomaly=True,
                score=min(zscore_val / self.z_threshold, 1.0),
                method="zscore",
                threshold=self.z_threshold,
                value=value,
                context=zscore_result.context,
            )

        # Secondary: IQR
        iqr_result = self._detect_iqr(arr)
        if iqr_result.scores[-1] > 0.5:
            return iqr_result

        # Tertiary: Rolling
        rolling_result = self._detect_rolling(arr)
        return rolling_result

    # ------------------------------------------------------------------
    # Internal detection methods
    # ------------------------------------------------------------------

    def _detect_zscore(self, arr: np.ndarray) -> AnomalyResult:
        """Z-score: values beyond N standard deviations from mean."""
        mean = np.mean(arr)
        std = np.std(arr)
        if std < 1e-9:
            return AnomalyResult(False, 0.0, "zscore", self.z_threshold, 0.0, {})

        zscores = np.abs((arr - mean) / std)
        scores = np.where(zscores > self.z_threshold, 1.0, 0.0)
        # Continuous score
        scores_cont = np.clip((zscores - self.z_threshold) / self.z_threshold, 0.0, 1.0)

        return AnomalyResult(
            is_anomaly=bool(np.any(scores > 0.5)),
            score=float(np.max(scores_cont)),
            method="zscore",
            threshold=self.z_threshold,
            value=float(arr[-1]),
            context={"mean": float(mean), "std": float(std)},
        )

    def _detect_iqr(self, arr: np.ndarray) -> AnomalyResult:
        """IQR: values outside Q1 - 1.5*IQR and Q3 + 1.5*IQR."""
        q1 = np.percentile(arr, 25)
        q3 = np.percentile(arr, 75)
        iqr = q3 - q1
        if iqr < 1e-9:
            return AnomalyResult(False, 0.0, "iqr", self.iqr_multiplier, 0.0, {})

        lower = q1 - self.iqr_multiplier * iqr
        upper = q3 + self.iqr_multiplier * iqr

        scores = np.zeros(len(arr))
        below = arr < lower
        above = arr > upper
        scores[below] = np.clip((lower - arr[below]) / iqr, 0.0, 1.0)
        scores[above] = np.clip((arr[above] - upper) / iqr, 0.0, 1.0)

        return AnomalyResult(
            is_anomaly=bool(np.any(scores > 0.5)),
            score=float(np.max(scores)),
            method="iqr",
            threshold=self.iqr_multiplier,
            value=float(arr[-1]),
            context={"q1": float(q1), "q3": float(q3), "iqr": float(iqr)},
        )

    def _detect_rolling(self, arr: np.ndarray) -> AnomalyResult:
        """Rolling: value deviates significantly from recent window average."""
        w = min(self.window_size, len(arr) - 1)
        if w < 1:
            return AnomalyResult(False, 0.0, "rolling", 0.0, 0.0, {})

        scores = np.zeros(len(arr))
        for i in range(w, len(arr)):
            window = arr[max(0, i - w):i]
            wmean = np.mean(window)
            wstd = max(np.std(window), 1e-9)
            z = abs(arr[i] - wmean) / wstd
            scores[i] = min(z / self.z_threshold, 1.0)

        return AnomalyResult(
            is_anomaly=bool(np.any(scores > 0.5)),
            score=float(np.max(scores)),
            method="rolling",
            threshold=self.z_threshold,
            value=float(arr[-1]),
            context={"window_size": w},
        )

    @staticmethod
    def _empty_result() -> Dict[str, Any]:
        return {
            "anomalies": [],
            "scores": [],
            "summary": {
                "total_points": 0,
                "anomaly_count": 0,
                "anomaly_rate": 0.0,
                "methods_used": [],
            },
        }
