"""
归因分析引擎 - 多触点归因模型
支持首次触达、末次触达、线性、TimeDecay等多种归因模型
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum
import json

# For test compatibility


class AttributionModel(Enum):
    """归因模型类型"""

    FIRST_TOUCH = "first_touch"  # 首次触达
    LAST_TOUCH = "last_touch"  # 末次触达
    LINEAR = "linear"  # 线性归因
    TIME_DECAY = "time_decay"  # 时间衰减
    POSITION_BASED = "position_based"  # 位置加权
    DATA_DRIVEN = "data_driven"  # 数据驱动


class ChannelType(Enum):
    """渠道类型"""

    ORGANIC_SEARCH = "organic_search"  # 自然搜索
    PAID_SEARCH = "paid_search"  # 付费搜索
    SOCIAL_MEDIA = "social_media"  # 社交媒体
    VIDEO_PLATFORM = "video_platform"  # 视频平台
    ECOMMERCE = "ecommerce"  # 电商平台
    DIRECT = "direct"  # 直访
    EMAIL = "email"  # 邮件营销
    REFERRAL = "referral"  # 引荐链接
    DISPLAY = "display"  # 展示广告
    INFLUENCER = "influencer"  # KOL/网红


@dataclass
class TouchPoint:
    """触点数据"""

    channel: str
    channel_type: ChannelType
    campaign: str
    ad_group: str
    keyword: str
    timestamp: datetime
    value: float = 0.0  # 带来的价值（GMV/线索等）
    conversions: int = 0
    impressions: int = 0
    clicks: int = 0
    cost: float = 0.0  # 花费


@dataclass
class AttributionResult:
    """归因结果"""

    channel: str
    channel_type: ChannelType
    model: AttributionModel

    # 基础指标
    total_touchpoints: int
    conversions: int
    revenue: float
    cost: float

    # 归因指标
    attributed_conversions: float
    attributed_revenue: float
    attribution_weight: float  # 归因权重 0-1

    # ROI指标
    roi: float
    cpa: float  # 单次获取成本
    roas: float  # 广告支出回报率

    # 渠道效率
    conversion_rate: float
    click_rate: float
    ctr: float  # 点击率

    confidence: float = 0.0  # 置信度


@dataclass
class AttributionReport:
    """归因分析报告"""

    report_id: str
    created_at: datetime
    model: AttributionModel
    start_date: datetime
    end_date: datetime

    # 总体指标
    total_conversions: int
    total_revenue: float
    total_cost: float

    # 渠道归因结果
    channel_results: Dict[str, AttributionResult]

    # 归因路径分析
    attribution_paths: List[Dict]

    # 优化建议
    suggestions: List[str]

    # 报告摘要
    summary: Dict


class AttributionEngine:
    """
    归因分析引擎

    支持多种归因模型，计算各渠道的真实贡献度
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.attribution_window = self.config.get(
            "attribution_window", 30
        )  # 归因窗口（天）
        self.confidence_threshold = self.config.get("confidence_threshold", 0.7)

        # 渠道权重配置（位置加权模型使用）
        self.position_weights = {
            "first": 0.4,  # 首次触达权重
            "middle": 0.2,  # 中间触达权重
            "last": 0.4,  # 末次触达权重
        }

        # TimeDecay模型半衰期配置（天）
        self.decay_half_life = self.config.get("decay_half_life", 7)

        # 渠道类型映射
        self.channel_mapping = self._init_channel_mapping()

    def _init_channel_mapping(self) -> Dict[str, ChannelType]:
        """初始化渠道类型映射"""
        return {
            "google": ChannelType.PAID_SEARCH,
            "baidu": ChannelType.PAID_SEARCH,
            "抖音自然": ChannelType.ORGANIC_SEARCH,
            "小红书": ChannelType.SOCIAL_MEDIA,
            "抖音付费": ChannelType.PAID_SEARCH,
            "快手": ChannelType.VIDEO_PLATFORM,
            "B站": ChannelType.VIDEO_PLATFORM,
            "淘宝": ChannelType.ECOMMERCE,
            "天猫": ChannelType.ECOMMERCE,
            "京东": ChannelType.ECOMMERCE,
            "拼多多": ChannelType.ECOMMERCE,
            "微信": ChannelType.SOCIAL_MEDIA,
            "微博": ChannelType.SOCIAL_MEDIA,
            "邮件": ChannelType.EMAIL,
            "短信": ChannelType.EMAIL,
            "KOL": ChannelType.INFLUENCER,
            "网红": ChannelType.INFLUENCER,
            "直访": ChannelType.DIRECT,
            "展示广告": ChannelType.DISPLAY,
            "品牌广告": ChannelType.DISPLAY,
        }

    def analyze(
        self,
        touchpoints: List[TouchPoint],
        model: AttributionModel,
        start_date: datetime,
        end_date: datetime,
    ) -> AttributionReport:
        """
        执行归因分析

        Args:
            touchpoints: 触点数据列表
            model: 归因模型
            start_date: 分析开始日期
            end_date: 分析结束日期

        Returns:
            归因分析报告
        """
        # 按用户/会话分组
        user_journeys = self._group_by_journey(touchpoints)

        # 计算各渠道归因
        channel_attributions = self._calculate_attribution(user_journeys, model)

        # 生成归因结果
        results = self._generate_results(channel_attributions, model)

        # 分析归因路径
        paths = self._analyze_paths(user_journeys)

        # 生成优化建议
        suggestions = self._generate_suggestions(results, paths)

        # 创建报告
        report = AttributionReport(
            report_id=self._generate_report_id(),
            created_at=datetime.now(),
            model=model,
            start_date=start_date,
            end_date=end_date,
            total_conversions=sum(r.conversions for r in results),
            total_revenue=sum(r.revenue for r in results),
            total_cost=sum(r.cost for r in results),
            channel_results={r.channel: r for r in results},
            attribution_paths=paths,
            suggestions=suggestions,
            summary=self._generate_summary(results),
        )

        return report

    def _group_by_journey(
        self, touchpoints: List[TouchPoint]
    ) -> Dict[str, List[TouchPoint]]:
        """按用户/会话分组触点"""
        journeys = {}
        for tp in touchpoints:
            # 使用渠道+时间戳创建唯一标识
            key = f"{tp.channel}_{tp.timestamp.strftime('%Y%m%d%H%M')}"
            if key not in journeys:
                journeys[key] = []
            journeys[key].append(tp)

        # 按时间排序
        for key in journeys:
            journeys[key].sort(key=lambda x: x.timestamp)

        return journeys

    def _calculate_attribution(
        self, journeys: Dict[str, List[TouchPoint]], model: AttributionModel
    ) -> Dict[str, Dict]:
        """根据模型计算归因"""
        if model == AttributionModel.FIRST_TOUCH:
            return self._first_touch_attribution(journeys)
        elif model == AttributionModel.LAST_TOUCH:
            return self._last_touch_attribution(journeys)
        elif model == AttributionModel.LINEAR:
            return self._linear_attribution(journeys)
        elif model == AttributionModel.TIME_DECAY:
            return self._time_decay_attribution(journeys)
        elif model == AttributionModel.POSITION_BASED:
            return self._position_based_attribution(journeys)
        else:
            return self._linear_attribution(journeys)

    def _first_touch_attribution(
        self, journeys: Dict[str, List[TouchPoint]]
    ) -> Dict[str, Dict]:
        """首次触达归因"""
        attributions = {}

        for journey_id, points in journeys.items():
            if not points:
                continue

            # 只归因给第一个触点
            first = points[0]
            channel = first.channel

            if channel not in attributions:
                attributions[channel] = self._init_channel_attribution(channel)

            attributions[channel]["conversions"] += 1
            attributions[channel]["revenue"] += first.value
            attributions[channel]["cost"] += first.cost
            attributions[channel]["touchpoints"].append(first)

        return attributions

    def _last_touch_attribution(
        self, journeys: Dict[str, List[TouchPoint]]
    ) -> Dict[str, Dict]:
        """末次触达归因"""
        attributions = {}

        for journey_id, points in journeys.items():
            if not points:
                continue

            # 只归因给最后一个触点
            last = points[-1]
            channel = last.channel

            if channel not in attributions:
                attributions[channel] = self._init_channel_attribution(channel)

            attributions[channel]["conversions"] += 1
            attributions[channel]["revenue"] += last.value
            attributions[channel]["cost"] += last.cost
            attributions[channel]["touchpoints"].append(last)

        return attributions

    def _linear_attribution(
        self, journeys: Dict[str, List[TouchPoint]]
    ) -> Dict[str, Dict]:
        """线性归因"""
        attributions = {}

        for journey_id, points in journeys.items():
            if not points:
                continue

            # 平均分配权重
            weight = 1.0 / len(points)

            for point in points:
                channel = point.channel

                if channel not in attributions:
                    attributions[channel] = self._init_channel_attribution(channel)

                attributions[channel]["weighted_conversions"] += weight
                attributions[channel]["weighted_revenue"] += point.value * weight
                attributions[channel]["weighted_cost"] += point.cost * weight
                attributions[channel]["touchpoints"].append(point)

        return attributions

    def _time_decay_attribution(
        self, journeys: Dict[str, List[TouchPoint]]
    ) -> Dict[str, Dict]:
        """时间衰减归因"""
        attributions = {}

        for journey_id, points in journeys.items():
            if not points:
                continue

            if len(points) == 1:
                # 只有一个触点，100%归因
                point = points[0]
                channel = point.channel
                if channel not in attributions:
                    attributions[channel] = self._init_channel_attribution(channel)
                attributions[channel]["weighted_conversions"] += 1.0
                attributions[channel]["weighted_revenue"] += point.value
                attributions[channel]["weighted_cost"] += point.cost
                attributions[channel]["touchpoints"].append(point)
            else:
                # 计算时间衰减权重
                first_time = points[0].timestamp
                weights = []

                for point in points:
                    days_diff = (point.timestamp - first_time).total_seconds() / 86400
                    # 使用半衰期公式
                    weight = 0.5 ** (days_diff / self.decay_half_life)
                    weights.append(weight)

                total_weight = sum(weights)
                normalized_weights = [w / total_weight for w in weights]

                for i, point in enumerate(points):
                    channel = point.channel
                    if channel not in attributions:
                        attributions[channel] = self._init_channel_attribution(channel)

                    attributions[channel]["weighted_conversions"] += normalized_weights[
                        i
                    ]
                    attributions[channel]["weighted_revenue"] += (
                        point.value * normalized_weights[i]
                    )
                    attributions[channel]["weighted_cost"] += (
                        point.cost * normalized_weights[i]
                    )
                    attributions[channel]["touchpoints"].append(point)

        return attributions

    def _position_based_attribution(
        self, journeys: Dict[str, List[TouchPoint]]
    ) -> Dict[str, Dict]:
        """位置加权归因"""
        attributions = {}

        for journey_id, points in journeys.items():
            if not points:
                continue

            n = len(points)

            for i, point in enumerate(points):
                channel = point.channel
                if channel not in attributions:
                    attributions[channel] = self._init_channel_attribution(channel)

                # 计算位置权重
                if n == 1:
                    weight = 1.0
                elif n == 2:
                    weight = 0.5 if i in [0, 1] else 0.0
                else:
                    if i == 0:
                        weight = self.position_weights["first"]
                    elif i == n - 1:
                        weight = self.position_weights["last"]
                    else:
                        weight = self.position_weights["middle"] / (n - 2)

                attributions[channel]["weighted_conversions"] += weight
                attributions[channel]["weighted_revenue"] += point.value * weight
                attributions[channel]["weighted_cost"] += point.cost * weight
                attributions[channel]["touchpoints"].append(point)

        return attributions

    def _init_channel_attribution(self, channel: str) -> Dict:
        """初始化渠道归因数据"""
        return {
            "channel": channel,
            "channel_type": self.channel_mapping.get(channel, ChannelType.DIRECT),
            "conversions": 0,
            "revenue": 0.0,
            "cost": 0.0,
            "weighted_conversions": 0.0,
            "weighted_revenue": 0.0,
            "weighted_cost": 0.0,
            "touchpoints": [],
        }

    def _generate_results(
        self, attributions: Dict[str, Dict], model: AttributionModel
    ) -> List[AttributionResult]:
        """生成归因结果列表"""
        results = []

        total_value = (
            sum(max(a["weighted_revenue"], a["revenue"]) for a in attributions.values())
            or 1.0
        )

        for channel, attr in attributions.items():
            conversions = max(attr["weighted_conversions"], attr["conversions"])
            revenue = max(attr["weighted_revenue"], attr["revenue"])
            cost = max(attr["weighted_cost"], attr["cost"])

            # 计算归因权重
            weight = revenue / total_value if total_value > 0 else 0.0

            # 计算ROI指标
            roi = (revenue - cost) / cost if cost > 0 else 0.0
            cpa = cost / conversions if conversions > 0 else 0.0
            roas = revenue / cost if cost > 0 else 0.0

            # 计算效率指标
            touchpoints = attr["touchpoints"]
            total_clicks = sum(tp.clicks for tp in touchpoints)
            total_impressions = sum(tp.impressions for tp in touchpoints)

            conversion_rate = conversions / len(touchpoints) if touchpoints else 0.0
            click_rate = (
                total_clicks / total_impressions if total_impressions > 0 else 0.0
            )
            ctr = total_clicks / total_impressions if total_impressions > 0 else 0.0

            # 计算置信度
            confidence = min(1.0, len(touchpoints) / 10) if touchpoints else 0.0

            result = AttributionResult(
                channel=channel,
                channel_type=attr["channel_type"],
                model=model,
                total_touchpoints=len(touchpoints),
                conversions=attr["conversions"],
                revenue=attr["revenue"],
                cost=attr["cost"],
                attributed_conversions=conversions,
                attributed_revenue=revenue,
                attribution_weight=weight,
                roi=roi,
                cpa=cpa,
                roas=roas,
                conversion_rate=conversion_rate,
                click_rate=click_rate,
                ctr=ctr,
                confidence=confidence,
            )

            results.append(result)

        # 按归因收入排序
        results.sort(key=lambda x: x.attributed_revenue, reverse=True)

        return results

    def _analyze_paths(self, journeys: Dict[str, List[TouchPoint]]) -> List[Dict]:
        """分析归因路径"""
        path_counts = {}

        for journey_id, points in journeys.items():
            if not points:
                continue

            # 生成路径字符串
            path = " -> ".join([p.channel for p in points])

            if path not in path_counts:
                path_counts[path] = {
                    "path": path,
                    "count": 0,
                    "total_value": 0.0,
                    "channels": [p.channel for p in points],
                    "channel_count": len(points),
                }

            path_counts[path]["count"] += 1
            path_counts[path]["total_value"] += sum(p.value for p in points)

        # 转换为列表并排序
        paths = list(path_counts.values())
        paths.sort(key=lambda x: x["count"], reverse=True)

        # 只返回前20条最常见路径
        return paths[:20]

    def _generate_suggestions(
        self, results: List[AttributionResult], paths: List[Dict]
    ) -> List[str]:
        """生成优化建议"""
        suggestions = []

        # 分析高价值渠道
        high_value_channels = [r for r in results if r.attributed_revenue > 0]

        if high_value_channels:
            top_channel = high_value_channels[0]
            suggestions.append(
                f"建议加大对「{top_channel.channel}」渠道的投入，"
                f"当前归因贡献度达 {top_channel.attribution_weight * 100:.1f}%，"
                f"ROI 为 {top_channel.roi:.2f}"
            )

        # 分析低效渠道
        low_roi_channels = [r for r in results if r.cost > 0 and r.roi < 0.5]

        if low_roi_channels:
            channels = "、".join([c.channel for c in low_roi_channels[:3]])
            suggestions.append(
                f"「{channels}」等渠道ROI较低，建议优化投放策略或重新分配预算"
            )

        # 分析归因路径
        if paths:
            avg_touchpoints = sum(p["channel_count"] for p in paths) / len(paths)
            if avg_touchpoints > 3:
                suggestions.append(
                    f"用户平均触达 {avg_touchpoints:.1f} 个渠道后转化，"
                    f"建议优化首触渠道的用户体验，缩短转化路径"
                )

        # 分析渠道多样性
        if len(results) > 5:
            suggestions.append("建议测试新的渠道组合，探索更多获客渠道的可能性")

        # 特定渠道建议
        for result in results:
            if result.channel_type == ChannelType.INFLUENCER:
                if result.roi > 2.0:
                    suggestions.append(
                        f"KOL渠道表现优异（ROI: {result.roi:.2f}），"
                        f"建议建立长期合作关系"
                    )

        return (
            suggestions
            if suggestions
            else ["继续监控各渠道表现，积累更多数据后进行优化"]
        )

    def _generate_summary(self, results: List[AttributionResult]) -> Dict:
        """生成报告摘要"""
        total_revenue = sum(r.attributed_revenue for r in results)
        total_cost = sum(r.cost for r in results)
        total_conversions = sum(r.attributed_conversions for r in results)

        return {
            "total_channels": len(results),
            "total_revenue": total_revenue,
            "total_cost": total_cost,
            "overall_roi": (total_revenue - total_cost) / total_cost
            if total_cost > 0
            else 0,
            "overall_roas": total_revenue / total_cost if total_cost > 0 else 0,
            "total_conversions": total_conversions,
            "avg_cpa": total_cost / total_conversions if total_conversions > 0 else 0,
            "top_channel": results[0].channel if results else None,
            "top_channel_contribution": results[0].attribution_weight if results else 0,
        }

    def _generate_report_id(self) -> str:
        """生成报告ID"""
        import uuid

        return f"ATTR_{uuid.uuid4().hex[:12].upper()}"

    def compare_models(
        self, touchpoints: List[TouchPoint], start_date: datetime, end_date: datetime
    ) -> Dict[AttributionModel, AttributionReport]:
        """对比所有归因模型"""
        reports = {}

        for model in AttributionModel:
            reports[model] = self.analyze(touchpoints, model, start_date, end_date)

        return reports

    def export_report(self, report: AttributionReport, format: str = "json") -> str:
        """导出报告"""
        if format == "json":
            return json.dumps(
                {
                    "report_id": report.report_id,
                    "created_at": report.created_at.isoformat(),
                    "model": report.model.value,
                    "date_range": {
                        "start": report.start_date.isoformat(),
                        "end": report.end_date.isoformat(),
                    },
                    "summary": report.summary,
                    "channel_results": [
                        {
                            "channel": r.channel,
                            "channel_type": r.channel_type.value,
                            "attributed_conversions": r.attributed_conversions,
                            "attributed_revenue": r.attributed_revenue,
                            "attribution_weight": r.attribution_weight,
                            "roi": r.roi,
                            "cpa": r.cpa,
                            "roas": r.roas,
                        }
                        for r in report.channel_results.values()
                    ],
                    "attribution_paths": report.attribution_paths[:10],
                    "suggestions": report.suggestions,
                },
                ensure_ascii=False,
                indent=2,
            )

        return str(report)
