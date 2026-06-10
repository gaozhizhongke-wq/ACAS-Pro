"""
智能出价引擎
支持多种出价策略和自动优化
"""

import random
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from ..core.logging import logger


class BiddingStrategy(Enum):
    """出价策略"""
    MANUAL = "manual"                  # 手动出价
    AUTO_OCPC = "auto_ocpc"            # 自动oCPC
    AUTO_OCPM = "auto_ocpm"            # 自动oCPM
    MAX_CONVERSION = "max_conversion"  # 最大转化
    TARGET_CPA = "target_cpa"          # 目标CPA
    TARGET_ROI = "target_roi"          # 目标ROI


class BidAdjustmentRule(Enum):
    """出价调整规则"""
    TIME_OF_DAY = "time_of_day"        # 时段调整
    DEVICE = "device"                  # 设备调整
    GEO = "geo"                        # 地域调整
    AUDIENCE = "audience"              # 人群调整
    PERFORMANCE = "performance"        # 效果调整


@dataclass
class BidAdjustment:
    """出价调整项"""
    rule_type: BidAdjustmentRule
    condition: str                     # 条件描述
    adjustment_percent: float          # 调整百分比（如 1.2 表示+20%）
    is_active: bool = True


@dataclass
class BiddingConfig:
    """出价配置"""
    strategy: BiddingStrategy
    base_bid: float                    # 基础出价
    max_bid: Optional[float] = None    # 最高出价限制
    min_bid: Optional[float] = None    # 最低出价限制
    target_cpa: Optional[float] = None # 目标CPA
    target_roi: Optional[float] = None # 目标ROI
    adjustments: Optional[List[BidAdjustment]] = None
    
    def __post_init__(self) -> None:
        if self.adjustments is None:
            self.adjustments = []


class BiddingEngine:
    """智能出价引擎"""
    
    # 时段系数（24小时）
    TIME_MULTIPLIERS = {
        0: 0.8, 1: 0.7, 2: 0.6, 3: 0.6, 4: 0.7, 5: 0.8,
        6: 0.9, 7: 1.0, 8: 1.1, 9: 1.2, 10: 1.2, 11: 1.1,
        12: 1.0, 13: 1.0, 14: 1.1, 15: 1.2, 16: 1.3, 17: 1.3,
        18: 1.2, 19: 1.1, 20: 1.0, 21: 0.9, 22: 0.9, 23: 0.8
    }
    
    # 设备系数
    DEVICE_MULTIPLIERS = {
        'mobile': 1.0,
        'tablet': 0.9,
        'desktop': 0.8
    }
    
    # 地域系数（示例）
    GEO_MULTIPLIERS = {
        'tier1': 1.3,      # 一线城市
        'tier2': 1.1,      # 二线城市
        'tier3': 0.9,      # 三线城市
        'tier4': 0.8,      # 四线及以下
        'rural': 0.7       # 农村
    }
    
    def __init__(self):
        self.logger = logger.getChild("bidding_engine")
    
    def calculate_bid(self, config: BiddingConfig, 
                     context: Dict[str, Any]) -> float:
        """
        计算最终出价
        
        Args:
            config: 出价配置
            context: 上下文信息 {
                'hour': 当前小时,
                'device': 设备类型,
                'geo_tier': 城市级别,
                'audience_score': 人群质量分 (0-1),
                'historical_ctr': 历史CTR,
                'competition_level': 竞争程度 (low/medium/high)
            }
        """
        base_bid = config.base_bid
        
        # 应用时段调整
        hour = context.get('hour', datetime.now().hour)
        time_multiplier = self.TIME_MULTIPLIERS.get(hour, 1.0)
        
        # 应用设备调整
        device = context.get('device', 'mobile')
        device_multiplier = self.DEVICE_MULTIPLIERS.get(device, 1.0)
        
        # 应用地域调整
        geo_tier = context.get('geo_tier', 'tier2')
        geo_multiplier = self.GEO_MULTIPLIERS.get(geo_tier, 1.0)
        
        # 应用人群质量调整
        audience_score = context.get('audience_score', 0.5)
        audience_multiplier = 0.8 + (audience_score * 0.4)  # 0.8 - 1.2
        
        # 应用竞争程度调整
        competition = context.get('competition_level', 'medium')
        competition_multipliers = {'low': 0.9, 'medium': 1.0, 'high': 1.2}
        competition_multiplier = competition_multipliers.get(competition, 1.0)
        
        # 计算最终出价
        final_bid = base_bid * time_multiplier * device_multiplier * \
                   geo_multiplier * audience_multiplier * competition_multiplier
        
        # 应用自定义调整规则
        for adjustment in config.adjustments:
            if adjustment.is_active:
                final_bid *= adjustment.adjustment_percent
        
        # 应用策略特定调整
        final_bid = self._apply_strategy_adjustment(
            config, final_bid, context
        )
        
        # 限制在最小/最大出价范围内
        if config.min_bid is not None:
            final_bid = max(final_bid, config.min_bid)
        if config.max_bid is not None:
            final_bid = min(final_bid, config.max_bid)
        
        return round(final_bid, 2)
    
    def _apply_strategy_adjustment(self, config: BiddingConfig, 
                                   bid: float, context: Dict[str, Any]) -> float:
        """应用策略特定调整"""
        
        if config.strategy == BiddingStrategy.TARGET_CPA:
            # 目标CPA策略：根据历史表现调整
            current_cpa = context.get('current_cpa')
            if current_cpa and config.target_cpa:
                ratio = current_cpa / config.target_cpa
                if ratio > 1.2:
                    # CPA过高，降低出价
                    bid *= 0.9
                elif ratio < 0.8:
                    # CPA过低，可以提高出价获取更多转化
                    bid *= 1.1
        
        elif config.strategy == BiddingStrategy.TARGET_ROI:
            # 目标ROI策略
            current_roi = context.get('current_roi')
            if current_roi and config.target_roi:
                ratio = current_roi / config.target_roi
                if ratio > 1.2:
                    bid *= 1.1
                elif ratio < 0.8:
                    bid *= 0.9
        
        elif config.strategy == BiddingStrategy.MAX_CONVERSION:
            # 最大转化策略：根据预算消耗速度调整
            budget_usage = context.get('budget_usage', 0.5)
            if budget_usage < 0.3:
                # 预算消耗慢，提高出价
                bid *= 1.15
            elif budget_usage > 0.8:
                # 预算消耗快，降低出价
                bid *= 0.85
        
        return bid
    
    def optimize_bidding(self, config: BiddingConfig, 
                        performance_data: List[Dict[str, Any]]) -> BiddingConfig:
        """
        基于历史表现优化出价配置
        
        Args:
            config: 当前出价配置
            performance_data: 历史表现数据列表
                [{date, impressions, clicks, conversions, spend, ctr, cvr}, ...]
        """
        if not performance_data:
            return config
        
        # 计算平均表现
        avg_ctr = sum(d.get('ctr', 0) for d in performance_data) / len(performance_data)
        avg_cvr = sum(d.get('cvr', 0) for d in performance_data) / len(performance_data)
        avg_cpc = sum(d.get('spend', 0) for d in performance_data) / \
                  max(sum(d.get('clicks', 0) for d in performance_data), 1)
        
        # 创建新的配置
        new_config = BiddingConfig(
            strategy=config.strategy,
            base_bid=config.base_bid,
            max_bid=config.max_bid,
            min_bid=config.min_bid,
            target_cpa=config.target_cpa,
            target_roi=config.target_roi,
            adjustments=config.adjustments.copy()
        )
        
        # 根据表现调整基础出价
        if config.strategy == BiddingStrategy.TARGET_CPA and config.target_cpa:
            current_cpa = sum(d.get('spend', 0) for d in performance_data) / \
                         max(sum(d.get('conversions', 0) for d in performance_data), 1)
            
            if current_cpa > config.target_cpa * 1.2:
                # CPA过高，降低出价
                new_config.base_bid *= 0.9
                self.logger.info(f"CPA过高 ({current_cpa:.2f} > {config.target_cpa:.2f})，降低出价")
            elif current_cpa < config.target_cpa * 0.8:
                # CPA有空间，可以提高出价
                new_config.base_bid *= 1.05
                self.logger.info(f"CPA有优化空间 ({current_cpa:.2f} < {config.target_cpa:.2f})，适度提高出价")
        
        # 根据CTR调整时段系数
        if avg_ctr < 0.01:
            # CTR过低，降低高峰时段出价
            new_config.adjustments.append(BidAdjustment(
                rule_type=BidAdjustmentRule.TIME_OF_DAY,
                condition="高峰时段CTR优化",
                adjustment_percent=0.9
            ))
        
        return new_config
    
    def get_bid_suggestion(self, platform: str, objective: str,
                          target_audience_size: int) -> Dict[str, Any]:
        """
        获取出价建议
        
        Args:
            platform: 平台名称
            objective: 推广目标
            target_audience_size: 目标人群规模
        """
        # 基础出价建议（按平台和目标）
        base_suggestions = {
            'ocean_engine': {
                'conversion': {'min': 5.0, 'suggested': 10.0, 'max': 50.0},
                'click': {'min': 0.5, 'suggested': 1.0, 'max': 5.0},
                'impression': {'min': 5.0, 'suggested': 10.0, 'max': 30.0}
            },
            'magnetic': {
                'conversion': {'min': 3.0, 'suggested': 8.0, 'max': 40.0},
                'click': {'min': 0.3, 'suggested': 0.8, 'max': 4.0},
                'impression': {'min': 3.0, 'suggested': 8.0, 'max': 25.0}
            },
            'tencent': {
                'conversion': {'min': 4.0, 'suggested': 9.0, 'max': 45.0},
                'click': {'min': 0.4, 'suggested': 0.9, 'max': 4.5},
                'impression': {'min': 4.0, 'suggested': 9.0, 'max': 28.0}
            }
        }
        
        suggestion = base_suggestions.get(platform, {}).get(objective, {
            'min': 1.0, 'suggested': 5.0, 'max': 30.0
        })
        
        # 根据人群规模调整
        if target_audience_size < 10000:
            # 小众人群，出价可以更高
            suggestion['suggested'] *= 1.2
            suggestion['max'] *= 1.1
        elif target_audience_size > 1000000:
            # 大众人群，出价可以降低
            suggestion['suggested'] *= 0.9
            suggestion['min'] *= 0.9
        
        return {
            'platform': platform,
            'objective': objective,
            'audience_size': target_audience_size,
            'bid_range': {
                'min': round(suggestion['min'], 2),
                'suggested': round(suggestion['suggested'], 2),
                'max': round(suggestion['max'], 2)
            },
            'strategy_recommendation': self._get_strategy_recommendation(
                platform, objective
            )
        }
    
    def _get_strategy_recommendation(self, platform: str, objective: str) -> str:
        """获取策略推荐"""
        recommendations = {
            ('ocean_engine', 'conversion'): '建议使用oCPM自动出价，配合深度转化优化',
            ('ocean_engine', 'click'): '建议使用自动出价，关注CTR优化',
            ('magnetic', 'conversion'): '建议使用最大转化策略，快速起量',
            ('magnetic', 'click'): '建议使用CPC手动出价，控制成本',
            ('tencent', 'conversion'): '建议使用oCPA，稳定转化成本',
            ('tencent', 'click'): '建议使用自动出价，关注点击质量'
        }
        
        return recommendations.get(
            (platform, objective),
            '建议使用自动出价策略，根据数据表现调整'
        )
    
    def simulate_bidding(self, config: BiddingConfig, 
                        scenarios: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        模拟不同场景下的出价表现
        
        Args:
            config: 出价配置
            scenarios: 场景列表
        """
        results = []
        
        for scenario in scenarios:
            bid = self.calculate_bid(config, scenario)
            
            # 模拟效果（简化模型）
            win_probability = min(0.9, bid / (bid + 10))  # 获胜概率
            expected_impressions = scenario.get('available_impressions', 1000) * win_probability
            expected_ctr = 0.02 + (scenario.get('audience_score', 0.5) * 0.03)
            expected_clicks = expected_impressions * expected_ctr
            expected_cost = expected_clicks * bid
            
            results.append({
                'scenario': scenario,
                'bid': bid,
                'win_probability': round(win_probability, 3),
                'expected_impressions': int(expected_impressions),
                'expected_clicks': int(expected_clicks),
                'expected_cost': round(expected_cost, 2),
                'expected_cpc': round(expected_cost / max(expected_clicks, 1), 2)
            })
        
        return results

