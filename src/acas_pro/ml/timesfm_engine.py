#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - TimesFM Sales Forecasting Engine
Enterprise-grade time series forecasting with StatsForecast + Holt-Winters fallback
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
from datetime import datetime, timezone, timedelta
from statistics import mean, stdev

from pathlib import Path
from ..core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ForecastPoint:
    """Single forecast point"""
    timestamp: datetime
    value: float
    lower_bound: float
    upper_bound: float
    confidence: float


@dataclass
class ForecastResult:
    """Complete forecast result"""
    product_id: str
    forecast: List[ForecastPoint]
    trend_direction: str  # "up", "down", "stable"
    trend_magnitude: float  # percentage
    seasonality_detected: bool
    model_version: str
    generated_at: datetime
    
    def to_dict(self) -> Dict:
        return {
            "product_id": self.product_id,
            "trend_direction": self.trend_direction,
            "trend_magnitude": self.trend_magnitude,
            "seasonality_detected": self.seasonality_detected,
            "model_version": self.model_version,
            "generated_at": self.generated_at.isoformat(),
            "forecast": [
                {
                    "date": p.timestamp.strftime("%Y-%m-%d"),
                    "value": round(p.value, 2),
                    "lower": round(p.lower_bound, 2),
                    "upper": round(p.upper_bound, 2),
                    "confidence": round(p.confidence, 2)
                }
                for p in self.forecast
            ]
        }


def _try_statsforecast(values: np.ndarray, horizon: int, season_length: int = 7) -> Optional[Dict]:
    """
    Try StatsForecast AutoTheta for prediction
    Returns None if fails
    """
    try:
        from statsforecast import StatsForecast
        from statsforecast.models import AutoTheta, AutoETS
        
        # Prepare data
        n = len(values)
        df_data = {
            'unique_id': ['product'] * n,
            'ds': list(range(n)),  # Integer time index
            'y': values.tolist()
        }
        
        import pandas as pd
        df = pd.DataFrame(df_data)
        
        # Use AutoTheta (robust for various patterns)
        sf = StatsForecast(
            models=[AutoTheta(season_length=season_length)],
            freq=1  # Integer frequency
        )
        
        sf.fit(df)
        forecast_df = sf.predict(h=horizon)
        
        predictions = forecast_df['AutoTheta'].values.tolist()
        
        # Calculate confidence intervals
        std = np.std(values[-14:]) if len(values) >= 14 else np.std(values) * 0.5
        lower = [p - 1.96 * std * (1 + i * 0.02) for i, p in enumerate(predictions)]
        upper = [p + 1.96 * std * (1 + i * 0.02) for i, p in enumerate(predictions)]
        
        return {
            "values": [max(0, p) for p in predictions],
            "lower": [max(0, l) for l in lower],
            "upper": upper
        }
    except Exception as e:
        logger.debug(f"StatsForecast failed: {e}")
        return None


class TimesFMEngine:
    """
    TimesFM-inspired forecasting engine
    Uses StatsForecast AutoTheta with Holt-Winters fallback
    """
    
    MODEL_VERSION = "acas-pro-2.0-statsforecast"
    
    @property
    def _STATUS_FILE(self) -> Path:
        """Lazy-loaded status file path"""
        return Path.home() / ".acas-pro" / ".statsforecast_status"
    
    def __init__(self):
        self.alpha = 0.3  # Level smoothing
        self.beta = 0.1   # Trend smoothing
        self.gamma = 0.1  # Seasonal smoothing
        self.season_length = 7  # Weekly seasonality
        self.statsforecast_ok = self._load_statsforecast_status()
        logger.info(f"TimesFM Engine initialized (StatsForecast available: {self.statsforecast_ok})")
    
    def _load_statsforecast_status(self) -> bool:
        """Load StatsForecast availability from persistent storage"""
        try:
            if self._STATUS_FILE.exists():
                import json
                data = json.loads(self._STATUS_FILE.read_text())
                # Reset if last failure was > 24 hours ago
                if data.get("available", True) is False:
                    last_fail = datetime.fromisoformat(data.get("last_failure", "2000-01-01"))
                    if (datetime.now(timezone.utc) - last_fail).total_seconds() > 86400:
                        return True  # Retry after 24h
                return data.get("available", True)
        except Exception:
            pass
        return True
    
    def _save_statsforecast_status(self, available: bool):
        """Persist StatsForecast availability status"""
        try:
            import json
            self._STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "available": available,
                "last_failure": datetime.now(timezone.utc).isoformat() if not available else None,
                "updated": datetime.now(timezone.utc).isoformat()
            }
            self._STATUS_FILE.write_text(json.dumps(data))
        except Exception as e:
            logger.debug(f"Failed to save statsforecast status: {e}")
    
    def forecast(
        self,
        product_id: str,
        historical_data: List[Tuple[datetime, float]],
        horizon_days: int = 30,
        confidence_level: float = 0.8
    ) -> ForecastResult:
        """
        Generate sales forecast
        
        Args:
            product_id: Product identifier
            historical_data: List of (timestamp, value) tuples
            horizon_days: Number of days to forecast
            confidence_level: Confidence level for intervals
        
        Returns:
            ForecastResult with predictions and metadata
        """
        if len(historical_data) < 14:
            logger.warning(f"Insufficient data for {product_id}: {len(historical_data)} points")
            return self._generate_fallback_forecast(product_id, historical_data, horizon_days)
        
        # Sort by timestamp
        data = sorted(historical_data, key=lambda x: x[0])
        values = np.array([v for _, v in data], dtype=np.float64)
        
        # Detect trend
        trend = self._calculate_trend(values.tolist())
        
        # Detect seasonality
        has_seasonality = self._detect_seasonality(values.tolist())
        
        # Try StatsForecast first
        forecast_values = None
        lower_bounds = None
        upper_bounds = None
        model_used = self.MODEL_VERSION
        
        if self.statsforecast_ok:
            sf_result = _try_statsforecast(values, horizon_days, self.season_length)
            if sf_result is not None:
                forecast_values = sf_result["values"]
                lower_bounds = sf_result["lower"]
                upper_bounds = sf_result["upper"]
                model_used = self.MODEL_VERSION
                logger.info(f"StatsForecast prediction successful for {product_id}")
            else:
                self.statsforecast_ok = False
                logger.warning("StatsForecast failed, falling back to Holt-Winters")
        
        # Fallback to Holt-Winters
        if forecast_values is None:
            forecast_values = self._holt_winters_forecast(values.tolist(), horizon_days, has_seasonality)
            model_used = f"{self.MODEL_VERSION}-holtwinters"
            
            # Calculate confidence intervals for Holt-Winters
            z_score = 1.28 if confidence_level == 0.8 else 1.96
            residuals = self._calculate_residuals(values.tolist())
            std_error = stdev(residuals) if len(residuals) > 1 else mean(residuals) * 0.1
            
            lower_bounds = [max(0, v - z_score * std_error * (1 + i * 0.02)) for i, v in enumerate(forecast_values)]
            upper_bounds = [v + z_score * std_error * (1 + i * 0.02) for i, v in enumerate(forecast_values)]
        
        # Build forecast points
        last_date = data[-1][0]
        forecast_points = []
        
        for i in range(horizon_days):
            date = last_date + timedelta(days=i+1)
            forecast_points.append(ForecastPoint(
                timestamp=date,
                value=forecast_values[i],
                lower_bound=lower_bounds[i],
                upper_bound=upper_bounds[i],
                confidence=max(0.5, confidence_level - i * 0.01)
            ))
        
        return ForecastResult(
            product_id=product_id,
            forecast=forecast_points,
            trend_direction=trend["direction"],
            trend_magnitude=trend["magnitude"],
            seasonality_detected=has_seasonality,
            model_version=model_used,
            generated_at=datetime.now(timezone.utc)
        )
    
    def _calculate_trend(self, values: List[float]) -> Dict:
        """Calculate trend direction and magnitude"""
        if len(values) < 14:
            return {"direction": "stable", "magnitude": 0.0}
        
        # Compare first and second half
        mid = len(values) // 2
        first_half = mean(values[:mid])
        second_half = mean(values[mid:])
        
        if first_half == 0:
            return {"direction": "stable", "magnitude": 0.0}
        
        change_pct = ((second_half - first_half) / first_half) * 100
        
        if change_pct > 10:
            direction = "up"
        elif change_pct < -10:
            direction = "down"
        else:
            direction = "stable"
        
        return {"direction": direction, "magnitude": abs(change_pct)}
    
    def _detect_seasonality(self, values: List[float]) -> bool:
        """Detect weekly seasonality pattern"""
        if len(values) < 21:  # Need at least 3 weeks
            return False
        
        # Calculate day-of-week averages
        dow_values = [[] for _ in range(7)]
        for i, v in enumerate(values):
            dow_values[i % 7].append(v)
        
        dow_means = [mean(d) if d else 0 for d in dow_values]
        overall_mean = mean(dow_means)
        
        # Check if any day deviates significantly
        variance = sum((m - overall_mean) ** 2 for m in dow_means) / 7
        return variance > (overall_mean * 0.1) ** 2
    
    def _holt_winters_forecast(
        self, 
        values: List[float], 
        horizon: int,
        use_seasonality: bool
    ) -> List[float]:
        """Holt-Winters exponential smoothing"""
        n = len(values)
        
        # Initialize level and trend
        level = values[0]
        trend = (values[1] - values[0]) if n > 1 else 0
        
        # Initialize seasonal components
        if use_seasonality:
            seasonal = [values[i] - level for i in range(min(self.season_length, n))]
        else:
            seasonal = [0] * self.season_length
        
        # Fit model
        for i, actual in enumerate(values):
            if i == 0:
                continue
            
            # Calculate seasonal index
            s_idx = i % self.season_length
            
            # Update level
            new_level = self.alpha * (actual - seasonal[s_idx]) + (1 - self.alpha) * (level + trend)
            
            # Update trend
            new_trend = self.beta * (new_level - level) + (1 - self.beta) * trend
            
            # Update seasonal
            if use_seasonality:
                seasonal[s_idx] = self.gamma * (actual - new_level) + (1 - self.gamma) * seasonal[s_idx]
            
            level = new_level
            trend = new_trend
        
        # Generate forecast
        forecast = []
        for i in range(horizon):
            s_idx = (n + i) % self.season_length
            val = level + trend * (i + 1) + (seasonal[s_idx] if use_seasonality else 0)
            forecast.append(max(0, val))
        
        return forecast
    
    def _calculate_residuals(self, values: List[float]) -> List[float]:
        """Calculate residuals from simple moving average"""
        if len(values) < 2:
            return [0]
        
        window = min(7, len(values) // 2)
        residuals = []
        
        for i in range(window, len(values)):
            predicted = mean(values[i-window:i])
            residuals.append(abs(values[i] - predicted))
        
        return residuals if residuals else [0]
    
    def _generate_fallback_forecast(
        self,
        product_id: str,
        historical_data: List[Tuple[datetime, float]],
        horizon_days: int
    ) -> ForecastResult:
        """Generate fallback forecast when insufficient data"""
        if historical_data:
            last_value = historical_data[-1][1]
            last_date = historical_data[-1][0]
        else:
            last_value = 100
            last_date = datetime.now(timezone.utc)
        
        forecast_points = []
        for i in range(horizon_days):
            date = last_date + timedelta(days=i+1)
            forecast_points.append(ForecastPoint(
                timestamp=date,
                value=last_value,
                lower_bound=last_value * 0.8,
                upper_bound=last_value * 1.2,
                confidence=0.5
            ))
        
        return ForecastResult(
            product_id=product_id,
            forecast=forecast_points,
            trend_direction="stable",
            trend_magnitude=0.0,
            seasonality_detected=False,
            model_version=f"{self.MODEL_VERSION}-fallback",
            generated_at=datetime.now(timezone.utc)
        )


# Global instance
timesfm_engine = TimesFMEngine()
