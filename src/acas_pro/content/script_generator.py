#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Script Generator
AI文案生成与改写系统
"""

import json
import sqlite3
import random
import time
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from ..core.logging import get_logger
from ..core.database import DatabaseManager

logger = get_logger(__name__)


class ContentStyle(Enum):
    """内容风格"""

    BROADCAST = "broadcast"  # 口播风格
    DRAMA = "drama"  # 剧情风格
    KNOWLEDGE = "knowledge"  # 知识风格
    SEEDING = "seeding"  # 种草风格
    EMOTIONAL = "emotional"  # 情感风格
    PROMOTION = "promotion"  # 促销风格


class Platform(Enum):
    """平台类型"""

    DOUYIN = "douyin"
    XIAOHONGSHU = "xiaohongshu"
    KUAISHOU = "kuaishou"
    BILIBILI = "bilibili"


@dataclass
class ScriptTemplate:
    """文案模板"""

    id: str
    name: str
    style: ContentStyle
    platform: Platform
    structure: List[str]  # 结构段落
    min_length: int
    max_length: int
    example: str
    tags: List[str]


@dataclass
class GeneratedScript:
    """生成的文案"""

    id: str
    input_text: str
    title: str
    content: str
    style: ContentStyle
    platform: Platform
    word_count: int
    hashtags: List[str]
    hooks: List[str]  # 钩子/卖点
    cta: str  # 行动号召
    variations: List[str]  # 变体版本


class ScriptGenerator:
    """
    AI文案生成与改写系统

    功能：
    1. 单段输入智能扩写
    2. 多风格改写矩阵
    3. 地域文化适配
    4. 节日时令主题生成
    """

    # 文案结构模板库
    TEMPLATES = {
        (ContentStyle.BROADCAST, Platform.DOUYIN): ScriptTemplate(
            id="douyin_broadcast_001",
            name="抖音口播-痛点解决型",
            style=ContentStyle.BROADCAST,
            platform=Platform.DOUYIN,
            structure=["钩子开场", "痛点共鸣", "解决方案", "行动号召"],
            min_length=300,
            max_length=800,
            example="姐妹们，天天外卖奶茶的看过来！这个黑茶我喝了三个月...",
            tags=["口播", "种草", "痛点"],
        ),
        (ContentStyle.SEEDING, Platform.XIAOHONGSHU): ScriptTemplate(
            id="xhs_seeding_001",
            name="小红书-场景种草型",
            style=ContentStyle.SEEDING,
            platform=Platform.XIAOHONGSHU,
            structure=["场景引入", "产品展示", "使用体验", "购买引导"],
            min_length=500,
            max_length=1500,
            example="周末宅家，泡一杯暖暖的黑茶...",
            tags=["种草", "生活方式", "测评"],
        ),
        (ContentStyle.KNOWLEDGE, Platform.BILIBILI): ScriptTemplate(
            id="bili_knowledge_001",
            name="B站-知识科普型",
            style=ContentStyle.KNOWLEDGE,
            platform=Platform.BILIBILI,
            structure=["背景铺垫", "知识密度", "观点输出", "互动提问"],
            min_length=800,
            max_length=2000,
            example="黑茶，为什么被称为'边疆的生命之饮'？今天我们来聊聊...",
            tags=["科普", "历史", "文化"],
        ),
    }

    # 钩子模板库
    HOOK_TEMPLATES = {
        "question": [
            "还有谁想{benefit}?",
            "为什么{target}都在{action}?",
            "{problem}怎么办?",
        ],
        "shock": [
            "千万不要{action}!",
            "{number}%的人不知道{fact}",
            "{action}的{number}个真相",
        ],
        "story": [
            "从{before}到{after},我只做对了这一件事",
            "{time}前,我还是{status}...",
        ],
    }

    # CTA模板库
    CTA_TEMPLATES = {
        Platform.DOUYIN: [
            "点击左下角链接，{benefit}",
            "评论区告诉我{question}",
            "关注我看更多{topic}",
        ],
        Platform.XIAOHONGSHU: [
            "戳主页看更多{topic}",
            "同款在左下角，{benefit}",
            "{question}评论区见",
        ],
    }

    # 文化适配规则
    CULTURE_RULES = {
        "northwest": {  # 中国西北
            "keywords": ["酥油茶", "高原", "牦牛", "丝路"],
            "phrases": ["西北人的养生智慧", "高原上的黑金"],
            "avoid": ["过于精致的包装"],
        },
        "middle_east": {  # 中东
            "keywords": ["纯净", "恩赐", "分享", "家庭"],
            "phrases": ["Insha'Allah", "Mashallah"],
            "avoid": ["酒精", "猪肉", "女性形象", "日间饮食场景"],
        },
        "mongolia": {  # 蒙古
            "keywords": ["草原", "游牧", "苏台柴", "马头琴"],
            "phrases": ["草原的味道", "游牧民族的智慧"],
            "avoid": ["过于现代化的表达"],
        },
    }

    # 节日主题库
    FESTIVAL_THEMES = {
        "ramadan": {  # 斋月
            "name": "斋月",
            "keywords": ["封斋", "开斋", "能量补充", "健康斋月"],
            "phrases": ["封斋期间的能量补充", "开斋宴上的待客之道"],
            "visual": ["金色", "深绿色", "新月"],
        },
        "eid_al_fitr": {  # 开斋节
            "name": "开斋节",
            "keywords": ["感恩", "分享", "团聚", "礼物"],
            "phrases": ["把这份祝福带回家", "与家人共享"],
        },
        "spring_festival": {  # 春节
            "name": "春节",
            "keywords": ["团圆", "年货", "送礼", "健康"],
            "phrases": ["过年送礼送健康", "团圆时刻的好茶"],
            "visual": ["红色", "金色", "福字"],
        },
    }

    # Tables managed by core/schema.py — do not add CREATE TABLE here

    def __init__(self, db: "DatabaseManager" = None):
        self.db = db or DatabaseManager()

    def generate(
        self,
        input_text: str,
        platform: Platform = Platform.DOUYIN,
        style: ContentStyle = ContentStyle.BROADCAST,
        culture: Optional[str] = None,
        festival: Optional[str] = None,
        product_info: Optional[Dict] = None,
    ) -> GeneratedScript:
        """
        生成文案

        Args:
            input_text: 用户输入的简短描述
            platform: 目标平台
            style: 内容风格
            culture: 文化适配 (northwest/middle_east/mongolia)
            festival: 节日主题 (ramadan/eid_al_fitr/spring_festival)
            product_info: 产品信息
        """
        # 1. 意图理解
        intent = self._analyze_intent(input_text)

        # 2. 选择模板
        template = self._select_template(style, platform)

        # 3. 生成内容
        content = self._generate_content(
            input_text=input_text,
            template=template,
            intent=intent,
            product_info=product_info,
        )

        # 4. 文化适配
        if culture:
            content = self._apply_culture_adaptation(content, culture)

        # 5. 节日主题
        if festival:
            content = self._apply_festival_theme(content, festival)

        # 6. 生成标题和标签
        title = self._generate_title(content, platform)
        hashtags = self._generate_hashtags(content, platform)

        # 7. 提取钩子和CTA
        hooks = self._extract_hooks(content)
        cta = self._generate_cta(platform, intent)

        # 8. 生成变体
        variations = self._generate_variations(content, style, n=2)

        script = GeneratedScript(
            id=f"script_{int(time.time() * 1000)}",
            input_text=input_text,
            title=title,
            content=content,
            style=style,
            platform=platform,
            word_count=len(content),
            hashtags=hashtags,
            hooks=hooks,
            cta=cta,
            variations=variations,
        )

        # 保存到数据库
        self._save_script(script)

        return script

    def _analyze_intent(self, input_text: str) -> Dict:
        """分析用户意图"""
        intent = {
            "product": None,
            "benefit": None,
            "target": None,
            "scenario": None,
            "emotion": None,
        }

        # 简单关键词匹配（实际应使用NLP模型）
        if "黑茶" in input_text:
            intent["product"] = "黑茶"
        if any(word in input_text for word in ["降脂", "养胃", "健康"]):
            intent["benefit"] = "健康养生"
        if any(word in input_text for word in ["西北", "中东", "蒙古"]):
            intent["target"] = "地域市场"

        return intent

    def _select_template(
        self, style: ContentStyle, platform: Platform
    ) -> ScriptTemplate:
        """选择文案模板"""
        key = (style, platform)
        if key in self.TEMPLATES:
            return self.TEMPLATES[key]

        # 默认模板
        return ScriptTemplate(
            id="default_001",
            name="通用模板",
            style=style,
            platform=platform,
            structure=["开场", "正文", "结尾"],
            min_length=300,
            max_length=1000,
            example="",
            tags=["通用"],
        )

    def _generate_content(
        self,
        input_text: str,
        template: ScriptTemplate,
        intent: Dict,
        product_info: Optional[Dict],
    ) -> str:
        """生成文案内容"""
        # 基于模板结构生成内容
        sections = []

        for section_name in template.structure:
            if section_name in ["钩子开场", "开场"]:
                section = self._generate_hook(intent)
            elif section_name in ["痛点共鸣", "背景铺垫"]:
                section = self._generate_context(input_text, intent)
            elif section_name in ["解决方案", "产品展示"]:
                section = self._generate_solution(input_text, product_info)
            elif section_name in ["行动号召", "购买引导"]:
                section = self._generate_cta_section(intent)
            else:
                section = input_text

            sections.append(section)

        content = "\n\n".join(sections)

        # 控制长度
        if len(content) > template.max_length:
            content = content[: template.max_length] + "..."

        return content

    def _generate_hook(self, intent: Dict) -> str:
        """生成钩子开场"""
        hook_type = random.choice(list(self.HOOK_TEMPLATES.keys()))
        template = random.choice(self.HOOK_TEMPLATES[hook_type])

        # 填充变量
        hook = template.format(
            benefit=intent.get("benefit", "变得更健康"),
            target=intent.get("target", "懂生活的人"),
            action="喝黑茶",
            problem="肠胃不适",
            number="90",
            fact="黑茶的养生功效",
            before="亚健康",
            after="精力充沛",
            time="三个月",
            status="熬夜党",
        )

        return hook

    def _generate_context(self, input_text: str, intent: Dict) -> str:
        """生成背景/痛点段落"""
        contexts = [
            f"现代人生活节奏快，{intent.get('benefit', '健康')}问题越来越受关注。",
            f"很多人不知道，{input_text}其实是一个很好的选择。",
            f"说到{intent.get('product', '养生')}，你可能有很多疑问。",
        ]
        return random.choice(contexts)

    def _generate_solution(self, input_text: str, product_info: Optional[Dict]) -> str:
        """生成解决方案段落"""
        if product_info:
            solution = f"{product_info.get('name', '这款产品')}采用{product_info.get('feature', '传统工艺')}，"
            solution += f"{product_info.get('benefit', '品质有保障')}。"
        else:
            solution = f"{input_text}，经过科学验证，效果显著。"

        return solution

    def _generate_cta_section(self, intent: Dict) -> str:
        """生成CTA段落"""
        ctas = [
            f"想要{intent.get('benefit', '改善')}?现在就开始行动!",
            "别犹豫了，点击下方链接了解更多!",
            "评论区告诉我你的想法!",
        ]
        return random.choice(ctas)

    def _apply_culture_adaptation(self, content: str, culture: str) -> str:
        """应用文化适配"""
        if culture not in self.CULTURE_RULES:
            return content

        rules = self.CULTURE_RULES[culture]

        # 添加文化关键词
        keywords = rules.get("keywords", [])
        if keywords and random.random() > 0.5:
            content = random.choice(rules.get("phrases", [""])) + "\n" + content

        # 避免敏感内容
        for avoid in rules.get("avoid", []):
            # 简单替换（实际应使用更复杂的NLP）
            pass

        return content

    def _apply_festival_theme(self, content: str, festival: str) -> str:
        """应用节日主题"""
        if festival not in self.FESTIVAL_THEMES:
            return content

        theme = self.FESTIVAL_THEMES[festival]

        # 添加节日元素
        phrases = theme.get("phrases", [])
        if phrases:
            content = random.choice(phrases) + "\n" + content

        return content

    def _generate_title(self, content: str, platform: Platform) -> str:
        """生成标题"""
        # 提取关键信息生成标题
        titles = [
            "这个秘密，90%的人都不知道",
            "为什么聪明人都在喝这个?",
            "从亚健康到精力充沛，我只做对了这一件事",
            "千万不要这样喝!",
        ]
        return random.choice(titles)

    def _generate_hashtags(self, content: str, platform: Platform) -> List[str]:
        """生成标签"""
        base_tags = ["黑茶", "养生", "健康", "茶文化"]

        platform_tags = {
            Platform.DOUYIN: ["#黑茶养生", "#健康生活方式", "#茶饮推荐"],
            Platform.XIAOHONGSHU: ["#黑茶", "#养生茶", "#健康饮品", "#种草"],
            Platform.KUAISHOU: ["#黑茶", "#养生", "#好物推荐"],
            Platform.BILIBILI: ["#茶文化", "#知识科普", "#黑茶"],
        }

        tags = base_tags + platform_tags.get(platform, [])
        return tags[:5]  # 限制标签数量

    def _extract_hooks(self, content: str) -> List[str]:
        """提取钩子/卖点"""
        hooks = []
        lines = content.split("\n")

        for line in lines[:3]:  # 只看前3行
            if any(marker in line for marker in ["?", "!", "为什么", "千万不要"]):
                hooks.append(line.strip())

        return hooks[:3]

    def _generate_cta(self, platform: Platform, intent: Dict) -> str:
        """生成CTA"""
        templates = self.CTA_TEMPLATES.get(platform, ["了解更多"])
        template = random.choice(templates)

        return template.format(
            benefit=intent.get("benefit") or "改善健康",
            question=(intent.get("product") or "这个产品") + "怎么样",
            topic="养生知识",
        )

    def _generate_variations(
        self, content: str, style: ContentStyle, n: int = 2
    ) -> List[str]:
        """生成变体版本"""
        variations = []

        # 简单变体：调整语气和用词
        for i in range(n):
            if i == 0:
                # 更口语化
                var = content.replace("。", "!").replace("，", " ")
            else:
                # 更正式
                var = content.replace("!", "。")
            variations.append(var)

        return variations

    def _save_script(self, script: GeneratedScript) -> None:
        """保存生成的文案"""
        try:
            self.db.execute(
                """
                INSERT INTO generated_scripts (
                    id, input_text, title, content, style, platform,
                    word_count, hashtags, hooks, cta, variations
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    script.id,
                    script.input_text,
                    script.title,
                    script.content,
                    script.style.value,
                    script.platform.value,
                    script.word_count,
                    json.dumps(script.hashtags, ensure_ascii=False),
                    json.dumps(script.hooks, ensure_ascii=False),
                    script.cta,
                    json.dumps(script.variations, ensure_ascii=False),
                ),
            )
        except (
            sqlite3.Error,
            ValueError,
            RuntimeError,
            json.JSONDecodeError,
            Exception,
        ) as e:
            logger.error(f"Failed to save script: {e}")

    def rewrite(
        self, content: str, target_style: ContentStyle, target_platform: Platform
    ) -> str:
        """
        改写文案风格

        Args:
            content: 原始文案
            target_style: 目标风格
            target_platform: 目标平台
        """
        # 基于目标风格调整
        if target_style == ContentStyle.KNOWLEDGE:
            # 添加数据支撑
            rewritten = f"研究表明，{content}\n\n数据支持这一观点。"
        elif target_style == ContentStyle.EMOTIONAL:
            # 情感化表达
            rewritten = f"说实话，{content}\n\n这是我真实的感受。"
        else:
            rewritten = content

        return rewritten
