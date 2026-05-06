"""
智能决策引擎 - AI驱动的营销决策推荐系统
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import json
import random


class DecisionType(Enum):
    """决策类型"""
    CONTENT_OPTIMIZATION = "content_optimization"   # 内容优化
    BID_ADJUSTMENT = "bid_adjustment"               # 出价调整
    BUDGET_REALLOCATION = "budget_reallocation"     # 预算再分配
    INVENTORY_DECISION = "inventory_decision"       # 库存决策
    CAMPAIGN_LAUNCH = "campaign_launch"             # 活动启动
    AUDIENCE_EXPANSION = "audience_expansion"       # 人群扩展
    CHANNEL_SELECTION = "channel_selection"         # 渠道选择
    CREATIVE_TEST = "creative_test"                # 创意测试
    PRICING_STRATEGY = "pricing_strategy"           # 定价策略
    SEASONAL_PLANNING = "seasonal_planning"         # 季节性规划


class DecisionPriority(Enum):
    """决策优先级"""
    P0_CRITICAL = ("P0", 0, "紧急")      # 立即执行，影响核心指标
    P1_HIGH = ("P1", 1, "重要")          # 24小时内执行
    P2_MEDIUM = ("P2", 2, "常规")        # 72小时内执行
    P3_LOW = ("P3", 3, "优化")           # 可延迟的优化项


class DecisionStatus(Enum):
    """决策状态"""
    PENDING = "pending"           # 待执行
    APPROVED = "approved"         # 已批准
    EXECUTING = "executing"       # 执行中
    COMPLETED = "completed"       # 已完成
    SKIPPED = "skipped"           # 已跳过
    FAILED = "failed"             # 执行失败


@dataclass
class Decision:
    """决策数据"""
    decision_id: str
    decision_type: DecisionType
    title: str
    description: str
    priority: DecisionPriority
    
    # 决策详情
    target_metric: str           # 目标指标
    current_value: float         # 当前值
    target_value: float          # 目标值
    expected_impact: float       # 预期影响
    confidence: float            # 置信度 0-1
    
    # 执行计划
    action_plan: List[str]        # 具体行动步骤
    resource_requirements: Dict   # 资源需求
    estimated_cost: float        # 预估成本
    estimated_time: str          # 预估时间
    
    # 关联数据
    related_channels: List[str]   # 关联渠道
    related_campaigns: List[str]  # 关联活动
    related_products: List[str]   # 关联产品
    
    # 状态追踪
    status: DecisionStatus = DecisionStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    executed_at: Optional[datetime] = None
    
    # 结果评估
    actual_impact: Optional[float] = None
    result_notes: str = ""


@dataclass
class DecisionReport:
    """决策分析报告"""
    report_id: str
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    
    # 决策统计
    total_decisions: int
    pending_decisions: int
    completed_decisions: int
    skipped_decisions: int
    
    # 决策类型分布
    decisions_by_type: Dict[str, int]
    
    # 优先级分布
    decisions_by_priority: Dict[str, int]
    
    # 执行效果
    avg_confidence: float
    avg_expected_impact: float
    avg_actual_impact: Optional[float]
    impact_achievement_rate: float  # 实际影响/预期影响
    
    # 待处理决策
    pending_decisions_list: List[Decision]
    
    # 历史决策效果
    recent_decisions: List[Decision]


class SmartDecider:
    """
    智能决策引擎
    
    基于数据分析和AI算法，自动生成营销决策建议
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.confidence_threshold = self.config.get('confidence_threshold', 0.6)
        self.impact_threshold = self.config.get('impact_threshold', 0.05)
        
        # 决策历史
        self.decision_history: List[Decision] = []
        
        # 决策模板
        self._init_decision_templates()
    
    def _init_decision_templates(self):
        """初始化决策模板"""
        self.templates = {
            DecisionType.CONTENT_OPTIMIZATION: {
                'default_title': "内容优化建议",
                'action_plan_template': [
                    "分析当前内容表现数据",
                    "识别高互动内容特征",
                    "调整内容策略",
                    "A/B测试验证效果"
                ],
                'resource_requirements_template': {
                    'time': "2-3天",
                    'cost': 500,
                    'tools': ["内容分析工具"]
                }
            },
            DecisionType.BID_ADJUSTMENT: {
                'default_title': "出价优化建议",
                'action_plan_template': [
                    "分析当前出价效果",
                    "识别高效关键词",
                    "调整出价策略",
                    "监控转化率变化"
                ],
                'resource_requirements_template': {
                    'time': "1-2天",
                    'cost': 0,
                    'tools': ["广告平台"]
                }
            },
            DecisionType.BUDGET_REALLOCATION: {
                'default_title': "预算优化建议",
                'action_plan_template': [
                    "分析各渠道ROI",
                    "识别高效渠道",
                    "制定预算调整方案",
                    "分阶段执行"
                ],
                'resource_requirements_template': {
                    'time': "3-5天",
                    'cost': 0,
                    'tools': ["数据分析平台"]
                }
            },
            DecisionType.INVENTORY_DECISION: {
                'default_title': "库存调整建议",
                'action_plan_template': [
                    "分析库存周转率",
                    "预测需求变化",
                    "制定补货计划",
                    "执行采购订单"
                ],
                'resource_requirements_template': {
                    'time': "1-3天",
                    'cost': 1000,
                    'tools': ["库存管理系统"]
                }
            },
            DecisionType.CAMPAIGN_LAUNCH: {
                'default_title': "新活动启动建议",
                'action_plan_template': [
                    "确定活动目标",
                    "设计活动方案",
                    "准备营销素材",
                    "执行活动计划"
                ],
                'resource_requirements_template': {
                    'time': "5-7天",
                    'cost': 5000,
                    'tools': ["营销平台"]
                }
            },
            DecisionType.AUDIENCE_EXPANSION: {
                'default_title': "人群扩展建议",
                'action_plan_template': [
                    "分析现有受众特征",
                    "识别相似人群",
                    "测试新人群效果",
                    "逐步扩大覆盖"
                ],
                'resource_requirements_template': {
                    'time': "3-5天",
                    'cost': 2000,
                    'tools': ["广告平台"]
                }
            }
        }
    
    def analyze_and_decide(
        self,
        metrics: Dict[str, Any],
        historical_data: Optional[Dict] = None
    ) -> List[Decision]:
        """
        分析数据并生成决策建议
        
        Args:
            metrics: 当前指标数据
            historical_data: 历史数据（可选）
        
        Returns:
            决策建议列表
        """
        decisions = []
        
        # 1. 内容优化决策
        content_decisions = self._analyze_content_metrics(metrics)
        decisions.extend(content_decisions)
        
        # 2. 投放优化决策
        bid_decisions = self._analyze_bid_metrics(metrics)
        decisions.extend(bid_decisions)
        
        # 3. 预算优化决策
        budget_decisions = self._analyze_budget_metrics(metrics)
        decisions.extend(budget_decisions)
        
        # 4. 库存决策
        inventory_decisions = self._analyze_inventory_metrics(metrics)
        decisions.extend(inventory_decisions)
        
        # 5. 渠道选择决策
        channel_decisions = self._analyze_channel_metrics(metrics)
        decisions.extend(channel_decisions)
        
        # 6. 创意测试决策
        creative_decisions = self._analyze_creative_metrics(metrics)
        decisions.extend(creative_decisions)
        
        # 7. 季节性规划决策
        seasonal_decisions = self._analyze_seasonal_metrics(metrics)
        decisions.extend(seasonal_decisions)
        
        # 按优先级排序
        decisions.sort(key=lambda x: (x.priority.value[1], -x.confidence))
        
        # 过滤低置信度决策
        decisions = [
            d for d in decisions 
            if d.confidence >= self.confidence_threshold
        ]
        
        # 更新历史
        self.decision_history.extend(decisions)
        
        return decisions
    
    def _analyze_content_metrics(self, metrics: Dict) -> List[Decision]:
        """分析内容指标并生成决策"""
        decisions = []
        
        content_metrics = metrics.get('content', {})
        if not content_metrics:
            return decisions
        
        # 检查内容表现
        engagement_rate = content_metrics.get('engagement_rate', 0.5)
        avg_views = content_metrics.get('avg_views', 0)
        conversion_rate = content_metrics.get('conversion_rate', 0)
        
        # 低互动率优化
        if engagement_rate < 0.03:
            decision = Decision(
                decision_id=self._generate_decision_id(),
                decision_type=DecisionType.CONTENT_OPTIMIZATION,
                title="提升内容互动率",
                description=f"当前互动率为 {engagement_rate*100:.1f}%，低于目标值3%",
                priority=DecisionPriority.P1_HIGH,
                target_metric="内容互动率",
                current_value=engagement_rate,
                target_value=0.05,
                expected_impact=0.02,
                confidence=0.75,
                action_plan=[
                    "分析高互动内容的共同特征",
                    "优化标题和封面设计",
                    "增加互动引导",
                    "在黄金时段发布"
                ],
                resource_requirements={
                    'time': "2-3天",
                    'cost': 500,
                    'tools': ["内容分析工具"]
                },
                estimated_cost=500,
                estimated_time="2-3天",
                related_channels=['小红书', '抖音', 'B站'],
                related_campaigns=[],
                related_products=[]
            )
            decisions.append(decision)
        
        # 高播放低转化
        if avg_views > 10000 and conversion_rate < 0.005:
            decision = Decision(
                decision_id=self._generate_decision_id(),
                decision_type=DecisionType.CONTENT_OPTIMIZATION,
                title="优化高播放内容转化",
                description=f"平均播放{avg_views}次但转化率仅{conversion_rate*100:.2f}%",
                priority=DecisionPriority.P0_CRITICAL,
                target_metric="内容转化率",
                current_value=conversion_rate,
                target_value=0.01,
                expected_impact=0.005,
                confidence=0.85,
                action_plan=[
                    "分析观看人群画像",
                    "优化行动号召(CTA)",
                    "添加购买链接",
                    "设计专属优惠"
                ],
                resource_requirements={
                    'time': "1-2天",
                    'cost': 300,
                    'tools': ["转化分析工具"]
                },
                estimated_cost=300,
                estimated_time="1-2天",
                related_channels=['抖音', '快手'],
                related_campaigns=[],
                related_products=content_metrics.get('top_products', [])
            )
            decisions.append(decision)
        
        return decisions
    
    def _analyze_bid_metrics(self, metrics: Dict) -> List[Decision]:
        """分析出价指标并生成决策"""
        decisions = []
        
        bid_metrics = metrics.get('bidding', {})
        if not bid_metrics:
            return decisions
        
        # 检查CPA
        current_cpa = bid_metrics.get('avg_cpa', 100)
        target_cpa = bid_metrics.get('target_cpa', 50)
        
        if current_cpa > target_cpa * 1.3:
            decision = Decision(
                decision_id=self._generate_decision_id(),
                decision_type=DecisionType.BID_ADJUSTMENT,
                title=f"CPA过高需优化",
                description=f"当前CPA {current_cpa:.2f}元，超过目标 {target_cpa:.2f}元 的30%",
                priority=DecisionPriority.P0_CRITICAL,
                target_metric="CPA",
                current_value=current_cpa,
                target_value=target_cpa,
                expected_impact=-0.2,
                confidence=0.82,
                action_plan=[
                    "识别高CPA关键词",
                    "优化关键词匹配模式",
                    "调整出价策略",
                    "优化落地页"
                ],
                resource_requirements={
                    'time': "1天",
                    'cost': 0,
                    'tools': ["广告平台"]
                },
                estimated_cost=0,
                estimated_time="1天",
                related_channels=bid_metrics.get('channels', []),
                related_campaigns=[],
                related_products=[]
            )
            decisions.append(decision)
        
        # 检查关键词效率
        keyword_metrics = bid_metrics.get('keywords', [])
        high_cpc_keywords = [k for k in keyword_metrics if k.get('cpc', 0) > 5]
        
        if len(high_cpc_keywords) > 5:
            decision = Decision(
                decision_id=self._generate_decision_id(),
                decision_type=DecisionType.BID_ADJUSTMENT,
                title="关键词成本优化",
                description=f"发现{len(high_cpc_keywords)}个高CPC关键词需要优化",
                priority=DecisionPriority.P1_HIGH,
                target_metric="CPC",
                current_value=3.5,
                target_value=2.5,
                expected_impact=-0.2,
                confidence=0.70,
                action_plan=[
                    "分析高CPC关键词转化",
                    "降低无效词出价",
                    "添加长尾词",
                    "优化质量分"
                ],
                resource_requirements={
                    'time': "2天",
                    'cost': 0,
                    'tools': ["广告平台"]
                },
                estimated_cost=0,
                estimated_time="2天",
                related_channels=['百度', 'Google'],
                related_campaigns=[],
                related_products=[]
            )
            decisions.append(decision)
        
        return decisions
    
    def _analyze_budget_metrics(self, metrics: Dict) -> List[Decision]:
        """分析预算指标并生成决策"""
        decisions = []
        
        budget_metrics = metrics.get('budget', {})
        if not budget_metrics:
            return decisions
        
        # 检查渠道ROI
        channel_rois = budget_metrics.get('channel_roi', {})
        
        low_roi_channels = [
            ch for ch, roi in channel_rois.items() 
            if roi < 1.0
        ]
        
        high_roi_channels = [
            ch for ch, roi in channel_rois.items() 
            if roi > 2.5
        ]
        
        # 发现低效渠道
        if len(low_roi_channels) >= 2:
            decision = Decision(
                decision_id=self._generate_decision_id(),
                decision_type=DecisionType.BUDGET_REALLOCATION,
                title="预算重新分配建议",
                description=f"{len(low_roi_channels)}个渠道ROI低于1，建议减少投入",
                priority=DecisionPriority.P1_HIGH,
                target_metric="整体ROI",
                current_value=1.5,
                target_value=2.0,
                expected_impact=0.3,
                confidence=0.78,
                action_plan=[
                    f"从{low_roi_channels}减少30%预算",
                    f"增加{high_roi_channels[0] if high_roi_channels else '高效渠道'}预算",
                    "监控调整后效果",
                    "持续优化"
                ],
                resource_requirements={
                    'time': "3-5天",
                    'cost': 0,
                    'tools': ["数据分析平台"]
                },
                estimated_cost=0,
                estimated_time="3-5天",
                related_channels=low_roi_channels + high_roi_channels,
                related_campaigns=[],
                related_products=[]
            )
            decisions.append(decision)
        
        return decisions
    
    def _analyze_inventory_metrics(self, metrics: Dict) -> List[Decision]:
        """分析库存指标并生成决策"""
        decisions = []
        
        inventory_metrics = metrics.get('inventory', {})
        if not inventory_metrics:
            return decisions
        
        # 检查库存周转
        turnover_rate = inventory_metrics.get('turnover_rate', 0)
        stockout_rate = inventory_metrics.get('stockout_rate', 0)
        dead_stock_ratio = inventory_metrics.get('dead_stock_ratio', 0)
        
        # 缺货预警
        if stockout_rate > 0.15:
            decision = Decision(
                decision_id=self._generate_decision_id(),
                decision_type=DecisionType.INVENTORY_DECISION,
                title="库存缺货风险",
                description=f"缺货率{stockout_rate*100:.1f}%，需紧急补货",
                priority=DecisionPriority.P0_CRITICAL,
                target_metric="缺货率",
                current_value=stockout_rate,
                target_value=0.05,
                expected_impact=-0.1,
                confidence=0.90,
                action_plan=[
                    "识别缺货商品",
                    "联系供应商紧急补货",
                    "调整营销投放优先级",
                    "设置库存预警"
                ],
                resource_requirements={
                    'time': "1-2天",
                    'cost': 5000,
                    'tools': ["库存系统", "采购系统"]
                },
                estimated_cost=5000,
                estimated_time="1-2天",
                related_channels=[],
                related_campaigns=[],
                related_products=inventory_metrics.get('low_stock_products', [])
            )
            decisions.append(decision)
        
        # 死库存清理
        if dead_stock_ratio > 0.2:
            decision = Decision(
                decision_id=self._generate_decision_id(),
                decision_type=DecisionType.INVENTORY_DECISION,
                title="清理死库存",
                description=f"死库存占比{dead_stock_ratio*100:.1f}%，需促销清理",
                priority=DecisionPriority.P2_MEDIUM,
                target_metric="死库存率",
                current_value=dead_stock_ratio,
                target_value=0.1,
                expected_impact=-0.1,
                confidence=0.75,
                action_plan=[
                    "识别死库存商品",
                    "制定促销方案",
                    "调整价格策略",
                    "清理后复盘"
                ],
                resource_requirements={
                    'time': "7-14天",
                    'cost': 2000,
                    'tools': ["库存系统", "促销工具"]
                },
                estimated_cost=2000,
                estimated_time="7-14天",
                related_channels=['淘宝', '天猫', '京东', '拼多多'],
                related_campaigns=['死库存清仓'],
                related_products=inventory_metrics.get('dead_stock_products', [])
            )
            decisions.append(decision)
        
        return decisions
    
    def _analyze_channel_metrics(self, metrics: Dict) -> List[Decision]:
        """分析渠道指标并生成决策"""
        decisions = []
        
        channel_metrics = metrics.get('channels', {})
        if not channel_metrics:
            return decisions
        
        # 检查新渠道机会
        new_channels = channel_metrics.get('new_opportunities', [])
        
        if new_channels:
            decision = Decision(
                decision_id=self._generate_decision_id(),
                decision_type=DecisionType.CHANNEL_SELECTION,
                title="开拓新渠道",
                description=f"发现{len(new_channels)}个潜在高效渠道",
                priority=DecisionPriority.P2_MEDIUM,
                target_metric="渠道覆盖率",
                current_value=0.6,
                target_value=0.8,
                expected_impact=0.2,
                confidence=0.65,
                action_plan=[
                    f"测试{new_channels[0] if new_channels else '新渠道'}",
                    "小预算A/B测试",
                    "评估测试效果",
                    "逐步扩大投入"
                ],
                resource_requirements={
                    'time': "14-30天",
                    'cost': 10000,
                    'tools': ["广告平台"]
                },
                estimated_cost=10000,
                estimated_time="14-30天",
                related_channels=new_channels,
                related_campaigns=[],
                related_products=[]
            )
            decisions.append(decision)
        
        return decisions
    
    def _analyze_creative_metrics(self, metrics: Dict) -> List[Decision]:
        """分析创意指标并生成决策"""
        decisions = []
        
        creative_metrics = metrics.get('creative', {})
        if not creative_metrics:
            return decisions
        
        # 检查创意疲劳
        impression_fatigue = creative_metrics.get('impression_fatigue', 0)
        
        if impression_fatigue > 0.3:
            decision = Decision(
                decision_id=self._generate_decision_id(),
                decision_type=DecisionType.CREATIVE_TEST,
                title="创意疲劳需更新",
                description=f"用户看过{impression_fatigue*100:.1f}%创意超过5次",
                priority=DecisionPriority.P1_HIGH,
                target_metric="创意疲劳度",
                current_value=impression_fatigue,
                target_value=0.1,
                expected_impact=-0.2,
                confidence=0.80,
                action_plan=[
                    "分析高疲劳创意",
                    "设计新创意方案",
                    "A/B测试验证",
                    "替换低效创意"
                ],
                resource_requirements={
                    'time': "3-5天",
                    'cost': 2000,
                    'tools': ["创意工具"]
                },
                estimated_cost=2000,
                estimated_time="3-5天",
                related_channels=creative_metrics.get('fatigue_channels', []),
                related_campaigns=[],
                related_products=[]
            )
            decisions.append(decision)
        
        return decisions
    
    def _analyze_seasonal_metrics(self, metrics: Dict) -> List[Decision]:
        """分析季节性指标并生成决策"""
        decisions = []
        
        seasonal_metrics = metrics.get('seasonal', {})
        if not seasonal_metrics:
            return decisions
        
        # 检查节日/活动准备
        upcoming_events = seasonal_metrics.get('upcoming_events', [])
        
        for event in upcoming_events:
            days_until = event.get('days_until', 0)
            
            if days_until <= 7:
                priority = DecisionPriority.P0_CRITICAL
            elif days_until <= 14:
                priority = DecisionPriority.P1_HIGH
            else:
                priority = DecisionPriority.P2_MEDIUM
            
            decision = Decision(
                decision_id=self._generate_decision_id(),
                decision_type=DecisionType.SEASONAL_PLANNING,
                title=f"活动准备：{event.get('name', '未知活动')}",
                description=f"距活动开始还有{days_until}天，需提前准备",
                priority=priority,
                target_metric="活动GMV",
                current_value=seasonal_metrics.get('avg_gmv', 0),
                target_value=event.get('target_gmv', 0),
                expected_impact=event.get('expected_growth', 0.5),
                confidence=0.85,
                action_plan=[
                    "确定活动方案",
                    "准备营销素材",
                    "预热推广",
                    "活动执行"
                ],
                resource_requirements={
                    'time': f"{days_until}天",
                    'cost': event.get('budget', 5000),
                    'tools': ["营销平台"]
                },
                estimated_cost=event.get('budget', 5000),
                estimated_time=f"{days_until}天",
                related_channels=event.get('channels', []),
                related_campaigns=[event.get('name', '未知活动')],
                related_products=event.get('products', [])
            )
            decisions.append(decision)
        
        return decisions
    
    def _generate_decision_id(self) -> str:
        """生成决策ID"""
        import hashlib
        timestamp = datetime.now().isoformat()
        random_str = str(random.random())
        hash_input = f"{timestamp}_{random_str}"
        return f"DEC_{hashlib.md5(hash_input.encode()).hexdigest()[:10].upper()}"
    
    def approve_decision(self, decision_id: str) -> bool:
        """批准决策"""
        for decision in self.decision_history:
            if decision.decision_id == decision_id:
                decision.status = DecisionStatus.APPROVED
                decision.updated_at = datetime.now()
                return True
        return False
    
    def execute_decision(self, decision_id: str) -> bool:
        """标记决策为执行中"""
        for decision in self.decision_history:
            if decision.decision_id == decision_id:
                decision.status = DecisionStatus.EXECUTING
                decision.updated_at = datetime.now()
                return True
        return False
    
    def complete_decision(
        self, 
        decision_id: str, 
        actual_impact: float,
        notes: str = ""
    ) -> bool:
        """完成决策"""
        for decision in self.decision_history:
            if decision.decision_id == decision_id:
                decision.status = DecisionStatus.COMPLETED
                decision.executed_at = datetime.now()
                decision.actual_impact = actual_impact
                decision.result_notes = notes
                decision.updated_at = datetime.now()
                return True
        return False
    
    def skip_decision(self, decision_id: str, reason: str = "") -> bool:
        """跳过决策"""
        for decision in self.decision_history:
            if decision.decision_id == decision_id:
                decision.status = DecisionStatus.SKIPPED
                decision.result_notes = reason
                decision.updated_at = datetime.now()
                return True
        return False
    
    def get_pending_decisions(
        self,
        max_results: int = 10,
        min_priority: Optional[DecisionPriority] = None
    ) -> List[Decision]:
        """获取待处理决策"""
        pending = [
            d for d in self.decision_history
            if d.status == DecisionStatus.PENDING
        ]
        
        if min_priority:
            pending = [
                d for d in pending 
                if d.priority.value[1] <= min_priority.value[1]
            ]
        
        # 按优先级和置信度排序
        pending.sort(key=lambda x: (x.priority.value[1], -x.confidence))
        
        return pending[:max_results]
    
    def generate_report(
        self,
        period_start: datetime,
        period_end: datetime
    ) -> DecisionReport:
        """生成决策报告"""
        # 筛选期间内的决策
        period_decisions = [
            d for d in self.decision_history
            if period_start <= d.created_at <= period_end
        ]
        
        # 统计
        decisions_by_type = {}
        decisions_by_priority = {}
        
        for d in period_decisions:
            type_key = d.decision_type.value
            priority_key = d.priority.value[0]
            
            decisions_by_type[type_key] = decisions_by_type.get(type_key, 0) + 1
            decisions_by_priority[priority_key] = decisions_by_priority.get(priority_key, 0) + 1
        
        completed = [d for d in period_decisions if d.status == DecisionStatus.COMPLETED]
        completed_with_impact = [d for d in completed if d.actual_impact is not None]
        
        # 计算效果
        avg_actual_impact = None
        impact_achievement_rate = 0.0
        
        if completed_with_impact:
            total_expected = sum(d.expected_impact for d in completed_with_impact)
            total_actual = sum(d.actual_impact for d in completed_with_impact)
            avg_actual_impact = total_actual / len(completed_with_impact)
            impact_achievement_rate = total_actual / total_expected if total_expected > 0 else 0
        
        # 获取待处理决策
        pending_decisions = self.get_pending_decisions(max_results=10)
        
        return DecisionReport(
            report_id=self._generate_report_id(),
            generated_at=datetime.now(),
            period_start=period_start,
            period_end=period_end,
            total_decisions=len(period_decisions),
            pending_decisions=len([d for d in period_decisions if d.status == DecisionStatus.PENDING]),
            completed_decisions=len(completed),
            skipped_decisions=len([d for d in period_decisions if d.status == DecisionStatus.SKIPPED]),
            decisions_by_type=decisions_by_type,
            decisions_by_priority=decisions_by_priority,
            avg_confidence=sum(d.confidence for d in period_decisions) / len(period_decisions) if period_decisions else 0,
            avg_expected_impact=sum(d.expected_impact for d in period_decisions) / len(period_decisions) if period_decisions else 0,
            avg_actual_impact=avg_actual_impact,
            impact_achievement_rate=impact_achievement_rate,
            pending_decisions_list=pending_decisions,
            recent_decisions=period_decisions[-10:] if period_decisions else []
        )
    
    def _generate_report_id(self) -> str:
        """生成报告ID"""
        import hashlib
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        hash_input = f"{timestamp}_report"
        return f"RPT_{hashlib.md5(hash_input.encode()).hexdigest()[:8].upper()}"
    
    def export_decisions(self, decisions: List[Decision], format: str = 'json') -> str:
        """导出决策列表"""
        if format == 'json':
            return json.dumps([
                {
                    'decision_id': d.decision_id,
                    'type': d.decision_type.value,
                    'title': d.title,
                    'description': d.description,
                    'priority': d.priority.value[0],
                    'priority_label': d.priority.value[2],
                    'status': d.status.value,
                    'confidence': d.confidence,
                    'expected_impact': d.expected_impact,
                    'target_metric': d.target_metric,
                    'action_plan': d.action_plan,
                    'estimated_cost': d.estimated_cost,
                    'estimated_time': d.estimated_time,
                    'related_channels': d.related_channels,
                    'created_at': d.created_at.isoformat()
                }
                for d in decisions
            ], ensure_ascii=False, indent=2)
        
        return str(decisions)
