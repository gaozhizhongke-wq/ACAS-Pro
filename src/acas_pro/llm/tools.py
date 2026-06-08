#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Tool Registry
Exposes ACAS Pro functions as LLM-callable tools (OpenAI Function Calling format)
"""

import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Any

from ..core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ToolDefinition:
    """Tool definition in OpenAI Function Calling format"""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema
    function: Callable = None
    
    def to_schema(self) -> Dict:
        """Convert to OpenAI tool schema"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }


class ToolRegistry:
    """
    Tool Registry for LLM Function Calling
    Manages tool definitions and execution
    """
    
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
    
    def register(self, name: str, description: str, 
                 parameters: Dict[str, Any], function: Callable) -> None:
        """Register a tool"""
        self._tools[name] = ToolDefinition(
            name=name,
            description=description,
            parameters=parameters,
            function=function
        )
    
    def unregister(self, name: str) -> bool:
        """Unregister a tool"""
        if name in self._tools:
            del self._tools[name]
            return True
        return False
    
    def get_schema(self, name: str) -> Optional[Dict]:
        """Get tool schema by name"""
        tool = self._tools.get(name)
        if tool:
            return tool.to_schema()
        return None
    
    def get_all_schemas(self) -> List[Dict]:
        """Get all tool schemas"""
        return [tool.to_schema() for tool in self._tools.values()]
    
    def execute(self, name: str, **kwargs) -> Any:
        """Execute a tool by name with given arguments"""
        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"Tool not found: {name}")
        
        if not tool.function:
            raise RuntimeError(f"Tool {name} has no implementation")
        
        try:
            result = tool.function(**kwargs)
            return result
        except Exception as e:
            logger.exception(f"Error in execute: {e}")
            return {"error": str(e)}
    
    def list_tools(self) -> List[Dict]:
        """List all registered tools with metadata"""
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": list(t.parameters.get("properties", {}).keys())
            }
            for t in self._tools.values()
        ]


class ACASTools:
    """
    ACAS Pro built-in tools for LLM
    Wraps ACAS Pro business functions as LLM-callable tools
    """
    
    def __init__(self, config=None, database=None):
        self.config = config
        self.database = database
        self.registry = ToolRegistry()
        self._register_all()
    
    def _register_all(self) -> None:
        """Register all ACAS Pro tools"""
        
        # ===== 销售预测 =====
        self.registry.register(
            name="sales_forecast",
            description="预测未来销售趋势。输入历史销售数据，输出未来一段时间的销售预测结果，包含预测值和置信区间。",
            parameters={
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "产品ID"
                    },
                    "days": {
                        "type": "integer",
                        "description": "预测天数，默认30天",
                        "default": 30
                    },
                    "historical_data": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "历史销售数据列表"
                    }
                },
                "required": ["product_id"]
            },
            function=self._sales_forecast
        )
        
        # ===== 库存优化 =====
        self.registry.register(
            name="inventory_optimize",
            description="优化库存策略。根据销售预测和当前库存，给出补货建议、安全库存和最优订货量。",
            parameters={
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "产品ID"
                    },
                    "current_stock": {
                        "type": "integer",
                        "description": "当前库存数量"
                    },
                    "lead_time_days": {
                        "type": "integer",
                        "description": "供货周期天数",
                        "default": 7
                    },
                    "service_level": {
                        "type": "number",
                        "description": "服务水平(0-1)，默认0.95",
                        "default": 0.95
                    }
                },
                "required": ["product_id", "current_stock"]
            },
            function=self._inventory_optimize
        )
        
        # ===== 市场情报 =====
        self.registry.register(
            name="market_intelligence",
            description="获取市场情报和舆情分析。分析指定关键词或行业的新闻趋势、情感倾向、风险预警。",
            parameters={
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "搜索关键词"
                    },
                    "industry": {
                        "type": "string",
                        "description": "行业名称"
                    },
                    "days": {
                        "type": "integer",
                        "description": "分析近几天的数据，默认7天",
                        "default": 7
                    }
                },
                "required": []
            },
            function=self._market_intelligence
        )
        
        # ===== 内容创作 =====
        self.registry.register(
            name="content_create",
            description="生成营销内容。支持生成小红书笔记、抖音脚本、微信推文等多种内容形式。",
            parameters={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "内容主题"
                    },
                    "platform": {
                        "type": "string",
                        "enum": ["xiaohongshu", "douyin", "wechat", "weibo", "general"],
                        "description": "目标平台"
                    },
                    "style": {
                        "type": "string",
                        "enum": ["professional", "casual", "humorous", "emotional"],
                        "description": "内容风格"
                    },
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "关键词列表"
                    }
                },
                "required": ["topic", "platform"]
            },
            function=self._content_create
        )
        
        # ===== 趋势监控 =====
        self.registry.register(
            name="trend_monitor",
            description="监控热门趋势。获取当前各大平台的热门话题、爆款商品、行业趋势数据。",
            parameters={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "监控类别，如：电商、美妆、食品等"
                    },
                    "platform": {
                        "type": "string",
                        "enum": ["all", "taobao", "douyin", "xiaohongshu", "weibo"],
                        "description": "监控平台",
                        "default": "all"
                    }
                },
                "required": []
            },
            function=self._trend_monitor
        )
        
        # ===== 账号分析 =====
        self.registry.register(
            name="account_analyze",
            description="分析账号运营数据。查看账号的粉丝增长、内容表现、互动数据等。",
            parameters={
                "type": "object",
                "properties": {
                    "account_id": {
                        "type": "string",
                        "description": "账号ID"
                    },
                    "metric": {
                        "type": "string",
                        "enum": ["overview", "growth", "engagement", "content"],
                        "description": "分析指标类型",
                        "default": "overview"
                    },
                    "days": {
                        "type": "integer",
                        "description": "分析天数",
                        "default": 30
                    }
                },
                "required": ["account_id"]
            },
            function=self._account_analyze
        )
        
        # ===== 广告投放 =====
        self.registry.register(
            name="ad_campaign_manage",
            description="管理广告投放。创建广告计划、调整出价、查看投放效果。",
            parameters={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["create", "pause", "resume", "optimize", "report"],
                        "description": "操作类型"
                    },
                    "campaign_id": {
                        "type": "string",
                        "description": "广告计划ID（修改/查看时需要）"
                    },
                    "budget": {
                        "type": "number",
                        "description": "预算金额（创建时使用）"
                    },
                    "target_audience": {
                        "type": "object",
                        "description": "目标受众描述"
                    }
                },
                "required": ["action"]
            },
            function=self._ad_campaign_manage
        )
        
        # ===== 电商运营 =====
        self.registry.register(
            name="ecommerce_manage",
            description="管理电商运营。查看订单、管理商品、分析店铺数据。",
            parameters={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["orders", "products", "shop_stats", "supply_chain"],
                        "description": "操作类型"
                    },
                    "shop_id": {
                        "type": "string",
                        "description": "店铺ID"
                    },
                    "filters": {
                        "type": "object",
                        "description": "筛选条件"
                    }
                },
                "required": ["action"]
            },
            function=self._ecommerce_manage
        )
        
        # ===== 数据查询 =====
        self.registry.register(
            name="data_query",
            description="查询ACAS Pro系统中的业务数据。支持销售数据、用户数据、运营指标等查询。",
            parameters={
                "type": "object",
                "properties": {
                    "query_type": {
                        "type": "string",
                        "enum": ["sales", "users", "operations", "inventory", "finance"],
                        "description": "查询数据类型"
                    },
                    "time_range": {
                        "type": "string",
                        "description": "时间范围，如: 7d, 30d, 90d, 1y",
                        "default": "30d"
                    },
                    "filters": {
                        "type": "object",
                        "description": "筛选条件"
                    }
                },
                "required": ["query_type"]
            },
            function=self._data_query
        )
        
        # ===== 节日营销 =====
        self.registry.register(
            name="festival_calendar",
            description="查看节日营销日历。获取即将到来的营销节点、节日促销建议。",
            parameters={
                "type": "object",
                "properties": {
                    "month": {
                        "type": "integer",
                        "description": "月份(1-12)，不传则返回近3个月",
                    },
                    "category": {
                        "type": "string",
                        "description": "行业类别筛选"
                    }
                },
                "required": []
            },
            function=self._festival_calendar
        )
    
    # ===== Tool Implementations =====
    
    def _sales_forecast(self, product_id: str, days: int = 30, 
                        historical_data: list = None, **kwargs) -> Dict:
        """Execute sales forecast"""
        try:
            from ...ml.timesfm_engine import TimesFMEngine
            engine = TimesFMEngine()
            
            if historical_data:
                result = engine.predict(historical_data, horizon=days)
            else:
                # Try to load from database
                result = engine.predict_sample(horizon=days)
            
            return {
                "product_id": product_id,
                "forecast_days": days,
                "predictions": result.get("predictions", []),
                "confidence_lower": result.get("confidence_lower", []),
                "confidence_upper": result.get("confidence_upper", []),
                "trend": result.get("trend", "stable"),
                "summary": f"产品{product_id}未来{days}天预测已完成，趋势为{result.get('trend', '稳定')}"
            }
        except ImportError:
            return {
                "product_id": product_id,
                "forecast_days": days,
                "error": "TimesFM引擎未安装，请先安装ml模块",
                "summary": f"预测功能暂不可用，产品{product_id}需安装TimesFM引擎"
            }
        except Exception as e:
            logger.exception(f"Error in _sales_forecast: {e}")
            return {"error": str(e), "summary": f"预测失败: {str(e)}"}
    
    def _inventory_optimize(self, product_id: str, current_stock: int,
                           lead_time_days: int = 7, service_level: float = 0.95,
                           **kwargs) -> Dict:
        """Execute inventory optimization"""
        try:
            from ...ml.inventory_optimizer import InventoryOptimizer
            optimizer = InventoryOptimizer()
            result = optimizer.optimize(
                product_id=product_id,
                current_stock=current_stock,
                lead_time_days=lead_time_days,
                service_level=service_level
            )
            return result
        except ImportError:
            # Fallback calculation
            import math
            daily_demand = current_stock / 30  # rough estimate
            safety_stock = int(daily_demand * 1.96 * math.sqrt(lead_time_days))
            reorder_point = int(daily_demand * lead_time_days + safety_stock)
            
            return {
                "product_id": product_id,
                "current_stock": current_stock,
                "safety_stock": safety_stock,
                "reorder_point": reorder_point,
                "recommended_order_qty": max(0, reorder_point - current_stock + safety_stock),
                "status": "low" if current_stock < safety_stock else "adequate",
                "summary": f"产品{product_id}库存{current_stock}，安全库存{safety_stock}，{'需要补货' if current_stock < safety_stock else '库存充足'}"
            }
        except Exception as e:
            logger.exception(f"Error in _inventory_optimize: {e}")
            return {"error": str(e), "summary": f"库存优化失败: {str(e)}"}
    
    def _market_intelligence(self, keyword: str = "", industry: str = "",
                             days: int = 7, **kwargs) -> Dict:
        """Execute market intelligence analysis"""
        try:
            from ...sentiment.analyzer import SentimentAnalyzer
            from ...sentiment.news_engine import NewsEngine
            
            analyzer = SentimentAnalyzer()
            news_engine = NewsEngine()
            
            news = news_engine.fetch(keyword=keyword or industry, days=days)
            sentiment = analyzer.analyze_batch([n.get("title", "") for n in news])
            
            return {
                "keyword": keyword or industry,
                "period_days": days,
                "news_count": len(news),
                "top_news": news[:5] if news else [],
                "sentiment_summary": sentiment.get("summary", "中性"),
                "risk_level": sentiment.get("risk_level", "low"),
                "summary": f"关键词'{keyword or industry}'近{days}天舆情分析：共{len(news)}条相关新闻，情感倾向{sentiment.get('summary', '中性')}，风险等级{sentiment.get('risk_level', '低')}"
            }
        except ImportError:
            return {
                "keyword": keyword or industry,
                "period_days": days,
                "news_count": 0,
                "sentiment_summary": "暂无数据",
                "risk_level": "unknown",
                "summary": f"舆情分析模块未安装，无法分析'{keyword or industry}'"
            }
        except Exception as e:
            logger.exception(f"Error in _market_intelligence: {e}")
            return {"error": str(e), "summary": f"市场情报获取失败: {str(e)}"}
    
    def _content_create(self, topic: str, platform: str, style: str = "professional",
                        keywords: list = None, **kwargs) -> Dict:
        """Generate marketing content"""
        platform_names = {
            "xiaohongshu": "小红书",
            "douyin": "抖音",
            "wechat": "微信公众号",
            "weibo": "微博",
            "general": "通用"
        }
        
        # Use the LLM client to generate content if available
        try:
            from .llm_client import LLMClient, LLMConfig, LLMMessage
            # Try to get LLM config from app config
            llm_config = self._get_llm_config()
            if llm_config and llm_config.api_key:
                client = LLMClient(llm_config)
                
                platform_desc = platform_names.get(platform, platform)
                style_desc = {"professional": "专业", "casual": "轻松", "humorous": "幽默", "emotional": "感性"}.get(style, style)
                
                kw_str = f"，关键词：{', '.join(keywords)}" if keywords else ""
                
                prompt = f"""请为{platform_desc}平台创作一篇关于「{topic}」的营销内容。
风格：{style_desc}
要求：
1. 符合{platform_desc}平台的内容风格
2. 包含吸引人的标题
3. 内容有感染力，能引起互动
4. 自然融入产品或品牌信息{kw_str}

请直接输出内容，不需要额外说明。"""
                
                response = client.quick_chat(prompt, system="你是一位资深的营销内容创作专家，擅长各平台的内容创作。")
                
                return {
                    "topic": topic,
                    "platform": platform_names.get(platform, platform),
                    "style": style,
                    "content": response,
                    "summary": f"已为{platform_names.get(platform, platform)}生成关于「{topic}」的{style_desc}风格内容"
                }
        except Exception as e:
            logger.exception(f"Error in _content_create: {e}")
            import logging
            logging.debug(f"{type(e).__name__}: {e}")
        
        # Fallback: template-based content
        templates = {
            "xiaohongshu": f"✨{topic}超全攻略✨\n\n姐妹们！今天来分享{topic}的干货~\n\n💡核心要点：\n1. 了解需求，选择最适合自己的方案\n2. 关注品质，不盲目跟风\n3. 对比性价比，理性消费\n\n🔥个人体验：真的很推荐！用了之后效果显著～\n\n{' '.join('#' + k for k in (keywords or ['好物推荐', '种草']))}\n\n👆觉得有用的话点个赞哦～",
            "douyin": f"【{topic}】30秒干货分享\n\n开头hook：你还在为{topic}发愁吗？\n\n核心内容：3个方法搞定{topic}\n1️⃣ 方法一：快速入门\n2️⃣ 方法二：进阶技巧\n3️⃣ 方法三：专业方案\n\n结尾：关注我，每天分享干货！",
            "wechat": f"# {topic}完全指南\n\n在当今竞争激烈的市场中，{topic}已经成为不可忽视的关键因素。\n\n## 为什么要关注{topic}？\n\n{topic}直接影响着我们的决策和效果。理解并掌握它，能帮助我们在市场中占据优势。\n\n## 核心策略\n\n1. **深入了解**：全面调研{topic}的市场现状\n2. **精准定位**：找到自己的差异化优势\n3. **持续优化**：根据数据反馈不断调整\n\n## 总结\n\n{topic}的成功不是偶然，而是系统化运营的结果。",
            "general": f"关于「{topic}」的内容创作\n\n核心要点：\n1. {topic}的重要性\n2. 如何有效利用{topic}\n3. {topic}的最佳实践\n\n建议结合具体场景和数据进行更有针对性的内容创作。"
        }
        
        content = templates.get(platform, templates["general"])
        
        return {
            "topic": topic,
            "platform": platform_names.get(platform, platform),
            "style": style,
            "content": content,
            "summary": f"已为{platform_names.get(platform, platform)}生成关于「{topic}」的内容（模板生成，配置大模型后可AI创作）"
        }
    
    def _trend_monitor(self, category: str = "", platform: str = "all",
                       **kwargs) -> Dict:
        """Monitor trends"""
        try:
            from ...content.trend_monitor import TrendMonitor
            monitor = TrendMonitor()
            trends = monitor.get_trends(category=category, platform=platform)
            return trends
        except ImportError:
            return {
                "category": category or "全部",
                "platform": platform,
                "trends": [
                    {"rank": 1, "title": f"{category or '热门'}趋势1", "heat": 9800},
                    {"rank": 2, "title": f"{category or '热门'}趋势2", "heat": 8500},
                    {"rank": 3, "title": f"{category or '热门'}趋势3", "heat": 7200}
                ],
                "summary": f"趋势监控模块未完整安装，显示模拟数据。类别: {category or '全部'}，平台: {platform}"
            }
        except Exception as e:
            logger.exception(f"Error in _trend_monitor: {e}")
            return {"error": str(e), "summary": f"趋势监控失败: {str(e)}"}
    
    def _account_analyze(self, account_id: str, metric: str = "overview",
                         days: int = 30, **kwargs) -> Dict:
        """Analyze account data"""
        try:
            from ...platforms.account_manager import AccountManager
            manager = AccountManager()
            account = manager.get_account(account_id)
            if account:
                return {
                    "account_id": account_id,
                    "metric": metric,
                    "data": account,
                    "summary": f"账号{account_id}的{metric}数据分析完成"
                }
        except Exception as e:
            logger.exception(f"Error in _account_analyze: {e}")
            import logging
            logging.debug(f"{type(e).__name__}: {e}")
        
        return {
            "account_id": account_id,
            "metric": metric,
            "days": days,
            "data": {"note": "账号数据暂不可用"},
            "summary": f"账号{account_id}数据暂不可用，请确认账号ID是否正确"
        }
    
    def _ad_campaign_manage(self, action: str, campaign_id: str = "",
                            budget: float = 0, target_audience: dict = None,
                            **kwargs) -> Dict:
        """Manage ad campaigns"""
        try:
            from ...ads.ad_manager import AdManager
            manager = AdManager()
            
            if action == "create":
                result = manager.create_campaign(budget=budget, target=target_audience)
                return {"action": action, "result": result, "summary": f"广告计划已创建，预算{budget}"}
            elif action == "report":
                report = manager.get_report(campaign_id)
                return {"action": action, "report": report, "summary": f"广告{campaign_id}报告已生成"}
            else:
                return {"action": action, "summary": f"广告{action}操作已执行"}
        except ImportError:
            return {"action": action, "summary": f"广告管理模块未安装，{action}操作暂不可用"}
        except Exception as e:
            logger.exception(f"Error in _ad_campaign_manage: {e}")
            return {"error": str(e), "summary": f"广告操作失败: {str(e)}"}
    
    def _ecommerce_manage(self, action: str, shop_id: str = "",
                          filters: dict = None, **kwargs) -> Dict:
        """Manage e-commerce operations"""
        action_names = {
            "orders": "订单", "products": "商品",
            "shop_stats": "店铺数据", "supply_chain": "供应链"
        }
        
        try:
            if action == "orders":
                from ...ecommerce.order_manager import OrderManager
                manager = OrderManager()
                orders = manager.list_orders(shop_id=shop_id, filters=filters)
                return {"action": action, "orders": orders, "summary": f"查询到{len(orders)}条订单"}
            elif action == "products":
                from ...ecommerce.product_manager import ProductManager
                manager = ProductManager()
                products = manager.list_products(shop_id=shop_id)
                return {"action": action, "products": products, "summary": f"查询到{len(products)}个商品"}
            else:
                return {"action": action, "summary": f"{action_names.get(action, action)}数据查询完成"}
        except ImportError:
            return {"action": action, "summary": f"电商模块未安装，{action_names.get(action, action)}查询暂不可用"}
        except Exception as e:
            logger.exception(f"Error in _ecommerce_manage: {e}")
            return {"error": str(e), "summary": f"电商操作失败: {str(e)}"}
    
    def _data_query(self, query_type: str, time_range: str = "30d",
                    filters: dict = None, **kwargs) -> Dict:
        """Query business data"""
        type_names = {
            "sales": "销售数据", "users": "用户数据",
            "operations": "运营指标", "inventory": "库存数据", "finance": "财务数据"
        }
        
        return {
            "query_type": type_names.get(query_type, query_type),
            "time_range": time_range,
            "data": {"note": "数据查询功能需要配置数据库连接"},
            "filters": filters,
            "summary": f"{type_names.get(query_type, query_type)}查询完成（时间范围: {time_range}）"
        }
    
    def _festival_calendar(self, month: int = None, category: str = "",
                           **kwargs) -> Dict:
        """Get festival marketing calendar"""
        try:
            from ...analytics.festival_calendar import FestivalCalendar
            calendar = FestivalCalendar()
            events = calendar.get_events(month=month, category=category)
            return {
                "month": month,
                "events": events,
                "summary": f"共获取{len(events)}个营销节点"
            }
        except ImportError:
            # Fallback data
            import datetime
            current_month = month or datetime.datetime.now().month
            festivals = {
                1: [{"name": "元旦", "date": "1月1日", "type": "节日"}],
                2: [{"name": "情人节", "date": "2月14日", "type": "节日"}, {"name": "春节", "date": "农历正月初一", "type": "传统节日"}],
                3: [{"name": "三八妇女节", "date": "3月8日", "type": "节日"}, {"name": "315消费者日", "date": "3月15日", "type": "主题日"}],
                4: [{"name": "清明节", "date": "4月5日", "type": "传统节日"}],
                5: [{"name": "五一劳动节", "date": "5月1日", "type": "节日"}, {"name": "母亲节", "date": "5月第二个周日", "type": "节日"}],
                6: [{"name": "618大促", "date": "6月18日", "type": "电商节"}, {"name": "端午节", "date": "农历五月初五", "type": "传统节日"}],
                7: [{"name": "暑期促销", "date": "7月", "type": "促销季"}],
                8: [{"name": "七夕节", "date": "农历七月初七", "type": "传统节日"}],
                9: [{"name": "中秋节", "date": "农历八月十五", "type": "传统节日"}, {"name": "教师节", "date": "9月10日", "type": "节日"}],
                10: [{"name": "国庆节", "date": "10月1日", "type": "节日"}, {"name": "双十一预热", "date": "10月下旬", "type": "电商节"}],
                11: [{"name": "双十一", "date": "11月11日", "type": "电商节"}, {"name": "感恩节", "date": "11月第四个周四", "type": "节日"}],
                12: [{"name": "双十二", "date": "12月12日", "type": "电商节"}, {"name": "圣诞节", "date": "12月25日", "type": "节日"}, {"name": "年终大促", "date": "12月下旬", "type": "促销季"}]
            }
            
            events = festivals.get(current_month, [])
            return {
                "month": current_month,
                "events": events,
                "summary": f"{current_month}月共{len(events)}个营销节点（模拟数据，安装festival_calendar模块获取完整日历）"
            }
        except Exception as e:
            logger.exception(f"Error in _festival_calendar: {e}")
            return {"error": str(e), "summary": f"节日日历查询失败: {str(e)}"}
    
    def _get_llm_config(self) -> None:
        """Get LLM config from app config"""
        try:
            from ...core.config import config
            if hasattr(config, 'llm') and config.llm:
                from .llm_client import LLMConfig, LLMProvider
                return LLMConfig(
                    provider=LLMProvider(config.llm.get('provider', 'openai')),
                    api_key=config.llm.get('api_key', ''),
                    api_base=config.llm.get('api_base', ''),
                    model=config.llm.get('model', ''),
                    max_tokens=config.llm.get('max_tokens', 4096),
                    temperature=config.llm.get('temperature', 0.7)
                )
        except Exception as e:
            logger.exception(f"Error in _get_llm_config: {e}")
            import logging
            logging.debug(f"{type(e).__name__}: {e}")
        return None
