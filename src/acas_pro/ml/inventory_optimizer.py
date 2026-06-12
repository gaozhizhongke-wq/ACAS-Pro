#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Inventory Optimization Engine
Enterprise inventory management with AI-powered recommendations
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone, timedelta
from statistics import mean, stdev

from ..core.logging import get_logger
from ..ml.timesfm_engine import timesfm_engine, ForecastResult

logger = get_logger(__name__)


@dataclass
class InventoryRecommendation:
    """Inventory optimization recommendation"""

    product_id: str
    product_name: str
    current_stock: int
    recommended_order_quantity: int
    urgency_level: str  # "critical", "high", "medium", "low"
    days_until_stockout: Optional[float]
    reorder_point: int
    safety_stock: int
    economic_order_qty: int
    reasoning: str
    confidence_score: float

    def to_dict(self) -> Dict:
        return {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "current_stock": self.current_stock,
            "recommended_order_quantity": self.recommended_order_quantity,
            "urgency_level": self.urgency_level,
            "days_until_stockout": round(self.days_until_stockout, 1)
            if self.days_until_stockout
            else None,
            "reorder_point": self.reorder_point,
            "safety_stock": self.safety_stock,
            "economic_order_qty": self.economic_order_qty,
            "reasoning": self.reasoning,
            "confidence_score": round(self.confidence_score, 2),
        }


@dataclass
class StockoutRisk:
    """Stockout risk assessment"""

    product_id: str
    risk_level: str  # "critical", "high", "medium", "low"
    probability: float  # 0-1
    estimated_stockout_date: Optional[datetime]
    revenue_at_risk: float
    impact_score: float  # 1-10
    mitigation_actions: List[str]


class InventoryOptimizer:
    """
    Enterprise inventory optimizer
    - Demand forecasting integration
    - Safety stock optimization
    - Economic order quantity calculation
    - Risk-based prioritization
    """

    def __init__(self):
        self.service_level = 0.95  # 95% service level
        self.lead_time_days = 7  # Default lead time
        self.holding_cost_rate = 0.25  # 25% annual holding cost
        self.ordering_cost = 100  # Fixed cost per order
        self.stockout_cost = 500  # Cost per stockout

    def optimize_inventory(
        self,
        inventory_data: List[Dict],
        sales_history: Dict[str, List[Tuple[datetime, float]]],
        forecast_days: int = 30,
    ) -> List[InventoryRecommendation]:
        """
        Generate inventory optimization recommendations

        Args:
            inventory_data: List of {product_id, name, stock, cost, price}
            sales_history: Dict of product_id -> [(date, quantity)]
            forecast_days: Forecast horizon

        Returns:
            List of recommendations sorted by urgency
        """
        recommendations = []

        for item in inventory_data:
            product_id = item.get("product_id")
            history = sales_history.get(product_id, [])

            rec = self._analyze_product(item, history, forecast_days)
            recommendations.append(rec)

        # Sort by urgency
        urgency_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        recommendations.sort(key=lambda x: urgency_order.get(x.urgency_level, 4))

        return recommendations

    def _analyze_product(
        self, item: Dict, history: List[Tuple[datetime, float]], forecast_days: int
    ) -> InventoryRecommendation:
        """Analyze single product and generate recommendation"""

        product_id = item.get("product_id", "")
        product_name = item.get("name", product_id)
        current_stock = item.get("stock", 0)
        unit_cost = item.get("cost", 10.0)

        # Calculate historical demand stats
        if len(history) >= 7:
            daily_demand = (
                [v for _, v in history[-30:]]
                if len(history) >= 30
                else [v for _, v in history]
            )
            avg_demand = mean(daily_demand)
            demand_std = (
                stdev(daily_demand) if len(daily_demand) > 1 else avg_demand * 0.2
            )
        else:
            avg_demand = 10  # Default assumption
            demand_std = 5

        # Get forecast
        if len(history) >= 14:
            forecast = timesfm_engine.forecast(product_id, history, forecast_days)
            sum(p.value for p in forecast.forecast)
            demand_trend = forecast.trend_direction
        else:
            avg_demand * forecast_days
            demand_trend = "stable"

        # Calculate safety stock (using normal distribution)
        # SS = Z * σ * sqrt(L)
        z_score = 1.65  # 95% service level
        safety_stock = int(z_score * demand_std * (self.lead_time_days**0.5))
        safety_stock = max(safety_stock, int(avg_demand * 3))  # Minimum 3 days

        # Calculate reorder point
        reorder_point = int(avg_demand * self.lead_time_days + safety_stock)

        # Calculate Economic Order Quantity (EOQ)
        annual_demand = avg_demand * 365
        if annual_demand > 0 and unit_cost > 0:
            holding_cost_per_unit = unit_cost * self.holding_cost_rate
            eoq = int(
                (2 * annual_demand * self.ordering_cost / holding_cost_per_unit) ** 0.5
            )
            eoq = max(eoq, int(avg_demand * 14))  # Minimum 2 weeks
        else:
            eoq = int(avg_demand * 30)  # Default to 1 month

        # Calculate days until stockout
        if avg_demand > 0:
            days_until_stockout = current_stock / avg_demand
        else:
            days_until_stockout = 999

        # Determine urgency and recommendation
        if current_stock <= safety_stock:
            urgency = "critical"
            order_qty = max(eoq, reorder_point - current_stock + safety_stock)
            reasoning = f"库存低于安全库存({safety_stock})。预计{days_until_stockout:.1f}天内缺货，需立即补货。"
        elif current_stock <= reorder_point:
            urgency = "high"
            order_qty = max(
                int(eoq * 0.8), reorder_point - current_stock + int(safety_stock * 0.5)
            )
            reasoning = (
                f"库存低于再订货点({reorder_point})。建议尽快补货以避免缺货风险。"
            )
        elif days_until_stockout <= self.lead_time_days + 7:
            urgency = "medium"
            order_qty = int(eoq * 0.6)
            reasoning = f"库存将在{days_until_stockout:.1f}天内耗尽。建议提前备货。"
        else:
            urgency = "low"
            order_qty = int(eoq * 0.3)
            reasoning = "库存充足。可维持正常销售，建议监控需求变化。"

        # Adjust for demand trend
        if demand_trend == "up":
            order_qty = int(order_qty * 1.2)
            reasoning += " 检测到上升趋势，已增加建议订货量。"
        elif demand_trend == "down":
            order_qty = int(order_qty * 0.8)
            reasoning += " 检测到下降趋势，已减少建议订货量。"

        # Ensure minimum order quantity
        order_qty = max(order_qty, 10)

        # Calculate confidence based on data quality
        confidence = min(0.95, 0.5 + len(history) / 200)

        return InventoryRecommendation(
            product_id=product_id,
            product_name=product_name,
            current_stock=current_stock,
            recommended_order_quantity=order_qty,
            urgency_level=urgency,
            days_until_stockout=days_until_stockout
            if days_until_stockout < 999
            else None,
            reorder_point=reorder_point,
            safety_stock=safety_stock,
            economic_order_qty=eoq,
            reasoning=reasoning,
            confidence_score=confidence,
        )

    def assess_stockout_risks(
        self, inventory_data: List[Dict], sales_forecasts: Dict[str, ForecastResult]
    ) -> List[StockoutRisk]:
        """Assess stockout risks for all products"""
        risks = []

        for item in inventory_data:
            product_id = item.get("product_id")
            current_stock = item.get("stock", 0)
            unit_price = item.get("price", 0)

            forecast = sales_forecasts.get(product_id)
            if not forecast:
                continue

            # Calculate cumulative demand
            cumulative_demand = 0
            stockout_day = None
            for i, point in enumerate(forecast.forecast):
                cumulative_demand += point.value
                if cumulative_demand >= current_stock and stockout_day is None:
                    stockout_day = i + 1

            if stockout_day is None:
                # No stockout in forecast period
                risk = StockoutRisk(
                    product_id=product_id,
                    risk_level="low",
                    probability=0.1,
                    estimated_stockout_date=None,
                    revenue_at_risk=0,
                    impact_score=2,
                    mitigation_actions=["继续监控需求变化"],
                )
            else:
                # Calculate risk metrics
                days_to_stockout = stockout_day
                revenue_at_risk = (
                    sum(p.value for p in forecast.forecast[stockout_day:]) * unit_price
                )

                if days_to_stockout <= 7:
                    risk_level = "critical"
                    probability = 0.9
                    impact = 9
                    actions = ["立即发起紧急补货", "联系供应商确认交期", "考虑调拨库存"]
                elif days_to_stockout <= 14:
                    risk_level = "high"
                    probability = 0.7
                    impact = 7
                    actions = ["尽快安排补货", "评估替代供应商", "通知销售团队"]
                elif days_to_stockout <= 21:
                    risk_level = "medium"
                    probability = 0.5
                    impact = 5
                    actions = ["计划补货", "监控销售趋势"]
                else:
                    risk_level = "low"
                    probability = 0.3
                    impact = 3
                    actions = ["维持当前策略"]

                stockout_date = datetime.now(timezone.utc) + timedelta(
                    days=days_to_stockout
                )

                risk = StockoutRisk(
                    product_id=product_id,
                    risk_level=risk_level,
                    probability=probability,
                    estimated_stockout_date=stockout_date,
                    revenue_at_risk=revenue_at_risk,
                    impact_score=impact,
                    mitigation_actions=actions,
                )

            risks.append(risk)

        # Sort by risk level
        risk_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        risks.sort(key=lambda x: risk_order.get(x.risk_level, 4))

        return risks

    def calculate_inventory_metrics(
        self, recommendations: List[InventoryRecommendation]
    ) -> Dict:
        """Calculate aggregate inventory metrics"""
        if not recommendations:
            return {}

        total_stock = sum(r.current_stock for r in recommendations)
        total_recommended = sum(r.recommended_order_quantity for r in recommendations)

        urgency_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for r in recommendations:
            urgency_counts[r.urgency_level] = urgency_counts.get(r.urgency_level, 0) + 1

        return {
            "total_products": len(recommendations),
            "total_current_stock": total_stock,
            "total_recommended_order": total_recommended,
            "urgency_distribution": urgency_counts,
            "critical_items": urgency_counts["critical"],
            "high_priority_items": urgency_counts["high"],
            "average_confidence": mean(r.confidence_score for r in recommendations),
        }


# Global instance
inventory_optimizer = InventoryOptimizer()
