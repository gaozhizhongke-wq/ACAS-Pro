#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Market Intelligence Engine
Enterprise news aggregation and risk detection
"""

import hashlib
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
from enum import Enum

from ..core.logging import get_logger
from ..sentiment.analyzer import sentiment_analyzer, SentimentResult, SentimentLevel

logger = get_logger(__name__)


class NewsCategory(Enum):
    """News category enumeration"""
    BUSINESS = "business"
    TECHNOLOGY = "technology"
    FINANCE = "finance"
    POLITICS = "politics"
    COMMODITY = "commodity"
    LOGISTICS = "logistics"
    DISASTER = "disaster"
    REGULATION = "regulation"


class RiskLevel(Enum):
    """Risk level enumeration"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class NewsArticle:
    """News article data"""
    id: str
    title: str
    content: str
    summary: str
    source: str
    source_url: str
    category: NewsCategory
    published_at: datetime
    language: str
    sentiment: Optional[SentimentResult] = None
    relevance_score: float = 0.0
    affected_regions: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "source": self.source,
            "category": self.category.value,
            "published_at": self.published_at.isoformat(),
            "sentiment": self.sentiment.to_dict() if self.sentiment else None,
            "relevance_score": self.relevance_score,
            "affected_regions": self.affected_regions
        }


@dataclass
class RiskAlert:
    """Risk alert data"""
    id: str
    level: RiskLevel
    title: str
    description: str
    category: str
    source_articles: List[str]
    affected_regions: List[str]
    detected_at: datetime
    expires_at: Optional[datetime] = None
    recommended_actions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "level": self.level.value,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "affected_regions": self.affected_regions,
            "detected_at": self.detected_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "recommended_actions": self.recommended_actions
        }


class MarketIntelligenceEngine:
    """
    Enterprise market intelligence engine
    - Multi-source news aggregation
    - Real-time sentiment analysis
    - Automated risk detection
    - Regional impact assessment
    """
    
    # Simulated news sources
    SOURCES = [
        "Reuters", "Bloomberg", "Financial Times", "Wall Street Journal",
        "CNBC", "BBC Business", "TechCrunch", "Supply Chain Dive"
    ]
    
    # Risk detection patterns
    RISK_PATTERNS = {
        "supply_disruption": {
            "keywords": ["shortage", "supply chain", "disruption", "delay", "congestion"],
            "risk_level": RiskLevel.HIGH,
            "category": "supply_chain"
        },
        "price_volatility": {
            "keywords": ["price surge", "volatile", "inflation", "cost increase"],
            "risk_level": RiskLevel.MEDIUM,
            "category": "financial"
        },
        "geopolitical": {
            "keywords": ["sanction", "trade war", "tariff", "embargo", "restriction"],
            "risk_level": RiskLevel.HIGH,
            "category": "political"
        },
        "natural_disaster": {
            "keywords": ["earthquake", "flood", "hurricane", "pandemic", "outbreak"],
            "risk_level": RiskLevel.CRITICAL,
            "category": "disaster"
        },
        "cybersecurity": {
            "keywords": ["cyber attack", "data breach", "hacking", "ransomware"],
            "risk_level": RiskLevel.HIGH,
            "category": "security"
        }
    }
    
    def __init__(self):
        self._cache: List[NewsArticle] = []
        self._cache_time: Optional[datetime] = None
        self._cache_ttl = timedelta(minutes=15)
    
    def fetch_intelligence(
        self,
        categories: Optional[List[NewsCategory]] = None,
        regions: Optional[List[str]] = None,
        max_items: int = 50,
        hours_back: int = 24
    ) -> List[NewsArticle]:
        """
        Fetch market intelligence
        
        Args:
            categories: Filter by categories
            regions: Filter by affected regions
            max_items: Maximum items to return
            hours_back: How many hours back to fetch
        
        Returns:
            List of news articles
        """
        # Check cache
        if self._cache_time and datetime.utcnow() - self._cache_time < self._cache_ttl:
            articles = self._cache
        else:
            # Generate simulated data (in production, this would fetch from APIs)
            articles = self._generate_sample_data(100)
            self._cache = articles
            self._cache_time = datetime.utcnow()
        
        # Apply filters
        filtered = articles
        
        if categories:
            filtered = [a for a in filtered if a.category in categories]
        
        if regions:
            filtered = [
                a for a in filtered 
                if any(r in a.affected_regions for r in regions)
            ]
        
        # Filter by time
        cutoff = datetime.utcnow() - timedelta(hours=hours_back)
        filtered = [a for a in filtered if a.published_at > cutoff]
        
        # Sort by relevance and time
        filtered.sort(key=lambda x: (x.relevance_score, x.published_at), reverse=True)
        
        return filtered[:max_items]
    
    def _generate_sample_data(self, count: int) -> List[NewsArticle]:
        """Generate simulated news data"""
        articles = []
        now = datetime.utcnow()
        
        templates = [
            {
                "title": "Global supply chain faces disruption amid port congestion",
                "content": "Major ports in Asia and Europe are experiencing severe congestion...",
                "category": NewsCategory.LOGISTICS,
                "keywords": ["supply chain", "port", "congestion"]
            },
            {
                "title": "Tech sector shows strong growth in Q3 earnings",
                "content": "Technology companies reported better-than-expected earnings...",
                "category": NewsCategory.TECHNOLOGY,
                "keywords": ["tech", "growth", "earnings"]
            },
            {
                "title": "Oil prices surge amid geopolitical tensions",
                "content": "Crude oil prices have increased by 15% following new sanctions...",
                "category": NewsCategory.COMMODITY,
                "keywords": ["oil", "prices", "sanctions"]
            },
            {
                "title": "E-commerce growth accelerates in Southeast Asia",
                "content": "Online retail sales in SEA markets grew by 25% year-over-year...",
                "category": NewsCategory.BUSINESS,
                "keywords": ["e-commerce", "growth", "SEA"]
            },
            {
                "title": "New trade agreement benefits cross-border commerce",
                "content": "The recently signed trade pact reduces tariffs...",
                "category": NewsCategory.REGULATION,
                "keywords": ["trade", "agreement", "tariffs"]
            },
            {
                "title": "Hurricane disrupts logistics in coastal regions",
                "content": "Severe weather conditions have forced port closures...",
                "category": NewsCategory.DISASTER,
                "keywords": ["hurricane", "logistics", "port"]
            },
            {
                "title": "Currency volatility affects import costs",
                "content": "Exchange rate fluctuations are creating uncertainty...",
                "category": NewsCategory.FINANCE,
                "keywords": ["currency", "volatility", "imports"]
            },
            {
                "title": "Cybersecurity threats target logistics systems",
                "content": "Recent attacks on shipping and logistics IT infrastructure...",
                "category": NewsCategory.TECHNOLOGY,
                "keywords": ["cybersecurity", "logistics", "attacks"]
            }
        ]
        
        regions_pool = ["global", "cn_northwest", "mena", "ssa", "sea"]
        
        for i in range(count):
            template = templates[i % len(templates)]
            
            # Randomize time
            hours_ago = random.randint(0, 48)
            published = now - timedelta(hours=hours_ago)
            
            # Analyze sentiment
            full_text = f"{template['title']}. {template['content']}"
            sentiment = sentiment_analyzer.analyze(full_text)
            
            # Calculate relevance
            relevance = random.uniform(0.5, 1.0)
            if sentiment.overall_sentiment in [SentimentLevel.NEGATIVE, SentimentLevel.VERY_NEGATIVE]:
                relevance += 0.15
            
            # Assign regions
            num_regions = random.randint(1, 3)
            affected = random.sample(regions_pool, num_regions)
            
            article = NewsArticle(
                id=f"news_{i:06d}",
                title=template["title"],
                content=template["content"],
                summary=template["content"][:100] + "...",
                source=random.choice(self.SOURCES),
                source_url=f"https://example.com/news/{i}",
                category=template["category"],
                published_at=published,
                language="en",
                sentiment=sentiment,
                relevance_score=round(relevance, 2),
                affected_regions=affected,
                keywords=template["keywords"]
            )
            articles.append(article)
        
        return articles
    
    def detect_risks(self, articles: List[NewsArticle]) -> List[RiskAlert]:
        """Detect risks from news articles"""
        alerts = []
        
        # Group articles by risk pattern
        pattern_matches = {key: [] for key in self.RISK_PATTERNS.keys()}
        
        for article in articles:
            text = f"{article.title} {article.content}".lower()
            
            for pattern_key, pattern_data in self.RISK_PATTERNS.items():
                if any(kw in text for kw in pattern_data["keywords"]):
                    pattern_matches[pattern_key].append(article)
        
        # Generate alerts for patterns with multiple matches
        for pattern_key, matched_articles in pattern_matches.items():
            if len(matched_articles) >= 2:
                pattern_data = self.RISK_PATTERNS[pattern_key]
                
                # Collect affected regions
                affected_regions = set()
                for article in matched_articles:
                    affected_regions.update(article.affected_regions)
                
                # Create alert
                alert = RiskAlert(
                    id=f"alert_{pattern_key}_{datetime.utcnow().strftime('%Y%m%d%H%M')}",
                    level=pattern_data["risk_level"],
                    title=f"{pattern_key.replace('_', ' ').title()} Risk Detected",
                    description=f"Multiple indicators of {pattern_key.replace('_', ' ')} detected in {len(matched_articles)} reports.",
                    category=pattern_data["category"],
                    source_articles=[a.id for a in matched_articles[:5]],
                    affected_regions=list(affected_regions),
                    detected_at=datetime.utcnow(),
                    expires_at=datetime.utcnow() + timedelta(days=3),
                    recommended_actions=self._get_recommended_actions(pattern_key)
                )
                alerts.append(alert)
        
        # Sort by risk level
        level_order = {
            RiskLevel.CRITICAL: 0,
            RiskLevel.HIGH: 1,
            RiskLevel.MEDIUM: 2,
            RiskLevel.LOW: 3,
            RiskLevel.INFO: 4
        }
        alerts.sort(key=lambda x: level_order.get(x.level, 5))
        
        return alerts
    
    def _get_recommended_actions(self, risk_type: str) -> List[str]:
        """Get recommended actions for risk type"""
        actions = {
            "supply_disruption": [
                "评估替代供应商",
                "增加安全库存",
                "通知客户可能的延迟"
            ],
            "price_volatility": [
                "审查定价策略",
                "考虑对冲策略",
                "与供应商重新谈判"
            ],
            "geopolitical": [
                "监控政策变化",
                "评估替代市场",
                "咨询法律团队"
            ],
            "natural_disaster": [
                "激活应急预案",
                "评估库存位置",
                "联系保险公司"
            ],
            "cybersecurity": [
                "审查安全协议",
                "进行安全审计",
                "通知相关方"
            ]
        }
        return actions.get(risk_type, ["继续监控情况"])
    
    def get_sentiment_summary(self, articles: List[NewsArticle]) -> Dict:
        """Get sentiment summary statistics"""
        if not articles:
            return {
                "total": 0,
                "sentiment_distribution": {},
                "average_score": 0,
                "trend": "neutral"
            }
        
        distribution = {
            "very_positive": 0,
            "positive": 0,
            "neutral": 0,
            "negative": 0,
            "very_negative": 0
        }
        
        total_score = 0
        for article in articles:
            if article.sentiment:
                distribution[article.sentiment.overall_sentiment.value] += 1
                total_score += article.sentiment.sentiment_score
        
        avg_score = total_score / len(articles)
        
        # Determine trend
        if avg_score > 0.3:
            trend = "positive"
        elif avg_score < -0.3:
            trend = "negative"
        else:
            trend = "neutral"
        
        return {
            "total": len(articles),
            "sentiment_distribution": distribution,
            "average_score": round(avg_score, 3),
            "positive_ratio": round((distribution["very_positive"] + distribution["positive"]) / len(articles), 2),
            "negative_ratio": round((distribution["very_negative"] + distribution["negative"]) / len(articles), 2),
            "trend": trend
        }


# Global instance
market_intelligence = MarketIntelligenceEngine()
