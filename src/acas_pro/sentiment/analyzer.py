#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Sentiment Analysis Engine
Enterprise-grade sentiment analysis for market intelligence
"""

import re
from dataclasses import dataclass
from typing import List, Dict, Optional, Set
from enum import Enum
from collections import Counter

from ..core.logging import get_logger

logger = get_logger(__name__)


class SentimentLevel(Enum):
    """Sentiment level enumeration"""
    VERY_NEGATIVE = "very_negative"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    POSITIVE = "positive"
    VERY_POSITIVE = "very_positive"


@dataclass
class AspectSentiment:
    """Aspect-based sentiment"""
    aspect: str
    sentiment: float  # -1 to 1
    mentions: int
    keywords: List[str]


@dataclass
class SentimentResult:
    """Complete sentiment analysis result"""
    text: str
    overall_sentiment: SentimentLevel
    sentiment_score: float  # -1 to 1
    confidence: float  # 0 to 1
    aspects: List[AspectSentiment]
    key_phrases: List[str]
    entities: List[str]
    language: str
    analyzed_at: str
    
    def to_dict(self) -> Dict:
        return {
            "overall_sentiment": self.overall_sentiment.value,
            "sentiment_score": round(self.sentiment_score, 3),
            "confidence": round(self.confidence, 3),
            "aspects": [
                {
                    "aspect": a.aspect,
                    "sentiment": round(a.sentiment, 3),
                    "mentions": a.mentions,
                    "keywords": a.keywords
                }
                for a in self.aspects
            ],
            "key_phrases": self.key_phrases,
            "entities": self.entities,
            "language": self.language
        }


class SentimentAnalyzer:
    """
    Enterprise sentiment analyzer
    - Multi-language support
    - Aspect-based analysis
    - Domain-specific lexicons
    - Confidence scoring
    """
    
    # Supply chain and business-specific lexicons
    POSITIVE_WORDS = {
        'en': [
            'growth', 'increase', 'boom', 'surge', 'strong', 'positive', 'optimistic',
            'expansion', 'profit', 'success', 'recovery', 'improvement', 'breakthrough',
            'milestone', 'partnership', 'innovation', 'efficiency', 'sustainable',
            'growth', 'increase', 'rise', 'gain', 'boost', 'advance', 'progress'
        ],
        'zh': [
            '增长', '上升', '繁荣', '强劲', '乐观', '扩张', '盈利', '成功',
            '复苏', '改善', '突破', '里程碑', '合作', '创新', '高效', '可持续'
        ]
    }
    
    NEGATIVE_WORDS = {
        'en': [
            'decline', 'decrease', 'drop', 'weak', 'negative', 'pessimistic',
            'contraction', 'loss', 'failure', 'crisis', 'risk', 'concern',
            'warning', 'threat', 'disruption', 'shortfall', 'bankruptcy',
            'recession', 'downturn', 'slump', 'crash', 'collapse'
        ],
        'zh': [
            '下降', '衰退', '疲软', '悲观', '收缩', '亏损', '失败', '危机',
            '风险', '担忧', '警告', '威胁', '中断', '短缺', '破产', '萧条'
        ]
    }
    
    RISK_ASPECTS = {
        'supply_chain': {
            'keywords': ['supply', 'shortage', 'inventory', 'stock', 'warehouse', 'logistics'],
            'zh_keywords': ['供应', '短缺', '库存', '仓储', '物流']
        },
        'market': {
            'keywords': ['market', 'demand', 'consumer', 'competition', 'price'],
            'zh_keywords': ['市场', '需求', '消费者', '竞争', '价格']
        },
        'financial': {
            'keywords': ['revenue', 'profit', 'cost', 'investment', 'funding'],
            'zh_keywords': ['收入', '利润', '成本', '投资', '资金']
        },
        'operational': {
            'keywords': ['operation', 'production', 'manufacturing', 'quality', 'efficiency'],
            'zh_keywords': ['运营', '生产', '制造', '质量', '效率']
        },
        'regulatory': {
            'keywords': ['regulation', 'compliance', 'policy', 'government', 'legal'],
            'zh_keywords': ['监管', '合规', '政策', '政府', '法律']
        }
    }
    
    INTENSIFIERS = ['very', 'extremely', 'highly', 'significantly', 'severely', '非常', '极其', '严重']
    NEGATORS = ['not', 'no', 'never', 'neither', 'nor', 'hardly', 'barely', '不', '没', '无', '未']
    
    def __init__(self):
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for efficiency"""
        self.patterns = {}
        for lang in ['en', 'zh']:
            pos_pattern = '|'.join(self.POSITIVE_WORDS[lang])
            neg_pattern = '|'.join(self.NEGATIVE_WORDS[lang])
            self.patterns[f'{lang}_pos'] = re.compile(pos_pattern, re.IGNORECASE)
            self.patterns[f'{lang}_neg'] = re.compile(neg_pattern, re.IGNORECASE)
    
    def analyze(self, text: str, context: str = None) -> SentimentResult:
        """
        Analyze sentiment of text
        
        Args:
            text: Text to analyze
            context: Optional context for domain-specific analysis
        
        Returns:
            SentimentResult with detailed analysis
        """
        # Detect language
        language = self._detect_language(text)
        
        # Tokenize into sentences
        sentences = self._tokenize_sentences(text, language)
        
        # Analyze each sentence
        sentence_scores = []
        for sentence in sentences:
            score = self._analyze_sentence(sentence, language)
            sentence_scores.append(score)
        
        # Calculate overall sentiment
        if sentence_scores:
            avg_score = sum(sentence_scores) / len(sentence_scores)
            # Weight by sentence length for confidence
            confidence = min(0.95, 0.4 + len(sentence_scores) * 0.05)
        else:
            avg_score = 0
            confidence = 0.3
        
        # Determine sentiment level
        sentiment_level = self._score_to_level(avg_score)
        
        # Extract aspects
        aspects = self._extract_aspects(text, language)
        
        # Extract key phrases
        key_phrases = self._extract_key_phrases(text, language)
        
        # Extract entities
        entities = self._extract_entities(text)
        
        return SentimentResult(
            text=text[:200] + "..." if len(text) > 200 else text,
            overall_sentiment=sentiment_level,
            sentiment_score=avg_score,
            confidence=confidence,
            aspects=aspects,
            key_phrases=key_phrases,
            entities=entities,
            language=language,
            analyzed_at=datetime.now(timezone.utc).isoformat()
        )
    
    def _detect_language(self, text: str) -> str:
        """Detect text language"""
        # Simple detection based on character ranges
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        total_chars = len(text)
        
        if chinese_chars / max(total_chars, 1) > 0.3:
            return 'zh'
        return 'en'
    
    def _tokenize_sentences(self, text: str, language: str) -> List[str]:
        """Tokenize text into sentences"""
        if language == 'zh':
            # Chinese sentence delimiters
            sentences = re.split(r'[。！？；]', text)
        else:
            # English sentence delimiters
            sentences = re.split(r'[.!?;]', text)
        
        return [s.strip() for s in sentences if s.strip()]
    
    def _analyze_sentence(self, sentence: str, language: str) -> float:
        """Analyze single sentence sentiment"""
        text_lower = sentence.lower()
        
        # Check for negation
        has_negation = any(neg in text_lower for neg in self.NEGATORS)
        
        # Count positive and negative words
        pos_matches = len(self.patterns[f'{language}_pos'].findall(sentence))
        neg_matches = len(self.patterns[f'{language}_neg'].findall(sentence))
        
        # Check for intensifiers
        intensifier_count = sum(1 for i in self.INTENSIFIERS if i in text_lower)
        intensity = 1 + 0.2 * intensifier_count
        
        # Calculate score
        pos_score = pos_matches * intensity
        neg_score = neg_matches * intensity
        
        # Apply negation
        if has_negation and pos_score > neg_score:
            pos_score, neg_score = neg_score, pos_score
        
        total = pos_score + neg_score
        if total == 0:
            return 0
        
        return (pos_score - neg_score) / total
    
    def _score_to_level(self, score: float) -> SentimentLevel:
        """Convert score to sentiment level"""
        if score > 0.6:
            return SentimentLevel.VERY_POSITIVE
        elif score > 0.2:
            return SentimentLevel.POSITIVE
        elif score < -0.6:
            return SentimentLevel.VERY_NEGATIVE
        elif score < -0.2:
            return SentimentLevel.NEGATIVE
        else:
            return SentimentLevel.NEUTRAL
    
    def _extract_aspects(self, text: str, language: str) -> List[AspectSentiment]:
        """Extract aspect-based sentiment"""
        aspects = []
        text_lower = text.lower()
        
        for aspect_name, aspect_data in self.RISK_ASPECTS.items():
            keywords = aspect_data['keywords']
            if language == 'zh':
                keywords = aspect_data['zh_keywords']
            
            # Count mentions
            mentions = sum(text_lower.count(kw.lower()) for kw in keywords)
            
            if mentions > 0:
                # Analyze sentiment in context of mentions
                aspect_sentiment = 0
                for keyword in keywords:
                    idx = text_lower.find(keyword.lower())
                    if idx >= 0:
                        # Get context window
                        start = max(0, idx - 50)
                        end = min(len(text), idx + 50)
                        context = text[start:end]
                        aspect_sentiment += self._analyze_sentence(context, language)
                
                avg_aspect_sentiment = aspect_sentiment / mentions if mentions > 0 else 0
                
                aspects.append(AspectSentiment(
                    aspect=aspect_name,
                    sentiment=avg_aspect_sentiment,
                    mentions=mentions,
                    keywords=[k for k in keywords if k.lower() in text_lower][:5]
                ))
        
        return aspects
    
    def _extract_key_phrases(self, text: str, language: str) -> List[str]:
        """Extract key phrases"""
        # Simple extraction of noun phrases
        if language == 'zh':
            # Extract 2-4 character phrases
            phrases = re.findall(r'[\u4e00-\u9fff]{2,4}', text)
        else:
            # Extract capitalized phrases
            phrases = re.findall(r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*', text)
        
        # Count and filter
        phrase_counts = Counter(phrases)
        return [phrase for phrase, count in phrase_counts.most_common(5) if count > 0]
    
    def _extract_entities(self, text: str) -> List[str]:
        """Extract named entities"""
        # Simple entity extraction
        # Company names (capitalized words)
        companies = re.findall(r'[A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)+', text)
        
        # Numbers and percentages
        numbers = re.findall(r'\d+(?:\.\d+)?%?', text)
        
        return list(set(companies[:5] + numbers[:5]))
    
    def batch_analyze(self, texts: List[str]) -> List[SentimentResult]:
        """Analyze multiple texts"""
        return [self.analyze(text) for text in texts]


from datetime import datetime, timezone

# Global instance
sentiment_analyzer = SentimentAnalyzer()
