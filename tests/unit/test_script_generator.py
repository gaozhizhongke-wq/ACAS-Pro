# -*- coding: utf-8 -*-
"""Tests for content/script_generator.py"""

import pytest
from unittest.mock import MagicMock, patch

from acas_pro.content.script_generator import (
    ScriptGenerator,
    ScriptTemplate,
    GeneratedScript,
    ContentStyle,
    Platform,
)


class TestScriptGenerator:
    """Test ScriptGenerator class"""

    @pytest.fixture
    def mock_db(self):
        """Mock DatabaseManager"""
        db = MagicMock()
        db.fetchone.return_value = None
        db.fetchall.return_value = []
        db.execute.return_value = None
        return db

    @pytest.fixture
    def generator(self, mock_db):
        """Create ScriptGenerator with mocked DB"""
        with patch('acas_pro.content.script_generator.DatabaseManager', return_value=mock_db):
            gen = ScriptGenerator(db=mock_db)
            gen.db = mock_db
            return gen

    @pytest.fixture
    def sample_product_info(self):
        """Sample product info for testing"""
        return {
            'name': '黑茶',
            'feature': '传统工艺',
            'benefit': '健康养生',
        }

    # ===== 初始化测试 =====
    def test_init(self, mock_db):
        """Test ScriptGenerator initialization"""
        with patch('acas_pro.content.script_generator.DatabaseManager', return_value=mock_db):
            gen = ScriptGenerator()
            assert gen.db is not None

    def test_init_with_db(self, mock_db):
        """Test initialization with provided DB"""
        gen = ScriptGenerator(db=mock_db)
        assert gen.db == mock_db

    def test_templates_exist(self):
        """Test TEMPLATES constant"""
        assert len(ScriptGenerator.TEMPLATES) > 0
        assert (ContentStyle.BROADCAST, Platform.DOUYIN) in ScriptGenerator.TEMPLATES

    def test_hook_templates_exist(self):
        """Test HOOK_TEMPLATES constant"""
        assert 'question' in ScriptGenerator.HOOK_TEMPLATES
        assert 'shock' in ScriptGenerator.HOOK_TEMPLATES
        assert 'story' in ScriptGenerator.HOOK_TEMPLATES

    def test_cta_templates_exist(self):
        """Test CTA_TEMPLATES constant"""
        assert Platform.DOUYIN in ScriptGenerator.CTA_TEMPLATES
        assert Platform.XIAOHONGSHU in ScriptGenerator.CTA_TEMPLATES

    def test_culture_rules_exist(self):
        """Test CULTURE_RULES constant"""
        assert 'northwest' in ScriptGenerator.CULTURE_RULES
        assert 'middle_east' in ScriptGenerator.CULTURE_RULES

    def test_festival_themes_exist(self):
        """Test FESTIVAL_THEMES constant"""
        assert 'ramadan' in ScriptGenerator.FESTIVAL_THEMES
        assert 'spring_festival' in ScriptGenerator.FESTIVAL_THEMES

    # ===== 意图分析测试 =====
    def test_analyze_intent_basic(self, generator):
        """Test basic intent analysis"""
        intent = generator._analyze_intent('我想推广黑茶')
        assert isinstance(intent, dict)
        assert 'product' in intent

    def test_analyze_intent_with_health(self, generator):
        """Test intent analysis with health keywords"""
        intent = generator._analyze_intent('黑茶可以降脂养胃')
        assert intent.get('benefit') == '健康养生'

    def test_analyze_intent_with_region(self, generator):
        """Test intent analysis with regional keywords"""
        intent = generator._analyze_intent('西北市场的黑茶')
        assert intent.get('target') == '地域市场'

    # ===== 模板选择测试 =====
    def test_select_template_exists(self, generator):
        """Test template selection"""
        template = generator._select_template(ContentStyle.BROADCAST, Platform.DOUYIN)
        assert isinstance(template, ScriptTemplate)
        assert template.style == ContentStyle.BROADCAST

    def test_select_template_default(self, generator):
        """Test default template selection"""
        template = generator._select_template(ContentStyle.PROMOTION, Platform.BILIBILI)
        assert isinstance(template, ScriptTemplate)
        assert template.name == '通用模板'

    # ===== 内容生成测试 =====
    def test_generate_content(self, generator, sample_product_info):
        """Test content generation"""
        template = generator._select_template(ContentStyle.BROADCAST, Platform.DOUYIN)
        intent = {'product': '黑茶', 'benefit': '健康'}
        
        content = generator._generate_content(
            input_text='黑茶养生',
            template=template,
            intent=intent,
            product_info=sample_product_info,
        )
        assert isinstance(content, str)
        assert len(content) > 0

    # ===== 钩子生成测试 =====
    def test_generate_hook(self, generator):
        """Test hook generation"""
        intent = {'benefit': '健康', 'target': '懂生活的人'}
        hook = generator._generate_hook(intent)
        assert isinstance(hook, str)
        assert len(hook) > 0

    # ===== 文化适配测试 =====
    def test_apply_culture_adaptation_northwest(self, generator):
        """Test culture adaptation for northwest"""
        content = '黑茶很好喝'
        adapted = generator._apply_culture_adaptation(content, 'northwest')
        assert isinstance(adapted, str)
        assert len(adapted) >= len(content)

    def test_apply_culture_adaptation_middle_east(self, generator):
        """Test culture adaptation for middle east"""
        content = 'This tea is great'
        adapted = generator._apply_culture_adaptation(content, 'middle_east')
        assert isinstance(adapted, str)

    def test_apply_culture_adaptation_unknown(self, generator):
        """Test culture adaptation for unknown culture"""
        content = 'Test content'
        adapted = generator._apply_culture_adaptation(content, 'unknown')
        assert adapted == content  # Should return unchanged

    # ===== 节日主题测试 =====
    def test_apply_festival_theme_ramadan(self, generator):
        """Test festival theme for ramadan"""
        content = '黑茶适合斋月饮用'
        themed = generator._apply_festival_theme(content, 'ramadan')
        assert isinstance(themed, str)
        assert len(themed) >= len(content)

    def test_apply_festival_theme_spring(self, generator):
        """Test festival theme for spring festival"""
        content = '黑茶是过年送礼好选择'
        themed = generator._apply_festival_theme(content, 'spring_festival')
        assert isinstance(themed, str)

    def test_apply_festival_theme_unknown(self, generator):
        """Test festival theme for unknown festival"""
        content = 'Test content'
        themed = generator._apply_festival_theme(content, 'unknown')
        assert themed == content  # Should return unchanged

    # ===== 标题生成测试 =====
    def test_generate_title(self, generator):
        """Test title generation"""
        content = '黑茶有很多功效'
        title = generator._generate_title(content, Platform.DOUYIN)
        assert isinstance(title, str)
        assert len(title) > 0

    # ===== 标签生成测试 =====
    def test_generate_hashtags(self, generator):
        """Test hashtag generation"""
        content = '黑茶养生'
        hashtags = generator._generate_hashtags(content, Platform.DOUYIN)
        assert isinstance(hashtags, list)
        assert len(hashtags) <= 5  # Limit check

    def test_generate_hashtags_xiaohongshu(self, generator):
        """Test hashtag generation for xiaohongshu"""
        content = '黑茶测评'
        hashtags = generator._generate_hashtags(content, Platform.XIAOHONGSHU)
        assert isinstance(hashtags, list)

    # ===== 钩子提取测试 =====
    def test_extract_hooks(self, generator):
        """Test hook extraction"""
        content = '为什么黑茶这么好？\n因为它有很多功效！\n快来试试看'
        hooks = generator._extract_hooks(content)
        assert isinstance(hooks, list)

    def test_extract_hooks_no_markers(self, generator):
        """Test hook extraction with no markers"""
        content = '黑茶很好喝。我非常喜欢。推荐给大家。'
        hooks = generator._extract_hooks(content)
        assert isinstance(hooks, list)
        assert len(hooks) == 0  # No hooks found

    # ===== CTA生成测试 =====
    def test_generate_cta(self, generator):
        """Test CTA generation"""
        intent = {'benefit': '健康', 'product': '黑茶'}
        cta = generator._generate_cta(Platform.DOUYIN, intent)
        assert isinstance(cta, str)
        assert len(cta) > 0

    # ===== 变体生成测试 =====
    def test_generate_variations(self, generator):
        """Test variation generation"""
        content = '黑茶很好喝。快来买吧！'
        variations = generator._generate_variations(content, ContentStyle.BROADCAST, n=2)
        assert isinstance(variations, list)
        assert len(variations) == 2

    # ===== 文案改写测试 =====
    def test_rewrite_to_knowledge(self, generator):
        """Test rewriting to knowledge style"""
        content = '黑茶很好'
        rewritten = generator.rewrite(content, ContentStyle.KNOWLEDGE, Platform.BILIBILI)
        assert isinstance(rewritten, str)
        assert len(rewritten) > len(content)

    def test_rewrite_to_emotional(self, generator):
        """Test rewriting to emotional style"""
        content = '黑茶很好'
        rewritten = generator.rewrite(content, ContentStyle.EMOTIONAL, Platform.DOUYIN)
        assert isinstance(rewritten, str)
        assert '说实话' in rewritten

    def test_rewrite_no_change(self, generator):
        """Test rewriting with no style change"""
        content = '黑茶很好'
        rewritten = generator.rewrite(content, ContentStyle.BROADCAST, Platform.DOUYIN)
        assert rewritten == content

    # ===== 主流程测试 =====
    def test_generate_basic(self, generator, mock_db, sample_product_info):
        """Test basic script generation"""
        mock_db.execute.return_value = None
        
        script = generator.generate(
            input_text='我想推广黑茶',
            platform=Platform.DOUYIN,
            style=ContentStyle.BROADCAST,
        )
        
        assert isinstance(script, GeneratedScript)
        assert script.input_text == '我想推广黑茶'
        assert script.style == ContentStyle.BROADCAST
        assert script.platform == Platform.DOUYIN
        mock_db.execute.assert_called()  # Verify save was called

    def test_generate_with_culture(self, generator, mock_db):
        """Test script generation with culture adaptation"""
        mock_db.execute.return_value = None
        
        script = generator.generate(
            input_text='黑茶推广',
            platform=Platform.DOUYIN,
            style=ContentStyle.BROADCAST,
            culture='northwest',
        )
        
        assert isinstance(script, GeneratedScript)
        mock_db.execute.assert_called()

    def test_generate_with_festival(self, generator, mock_db):
        """Test script generation with festival theme"""
        mock_db.execute.return_value = None
        
        script = generator.generate(
            input_text='节日促销',
            platform=Platform.DOUYIN,
            style=ContentStyle.PROMOTION,
            festival='spring_festival',
        )
        
        assert isinstance(script, GeneratedScript)
        mock_db.execute.assert_called()

    def test_generate_with_product_info(self, generator, mock_db, sample_product_info):
        """Test script generation with product info"""
        mock_db.execute.return_value = None
        
        script = generator.generate(
            input_text='推广产品',
            platform=Platform.XIAOHONGSHU,
            style=ContentStyle.SEEDING,
            product_info=sample_product_info,
        )
        
        assert isinstance(script, GeneratedScript)
        mock_db.execute.assert_called()


class TestScriptTemplate:
    """Test ScriptTemplate dataclass"""

    def test_template_creation(self):
        """Test ScriptTemplate creation"""
        template = ScriptTemplate(
            id='test_001',
            name='测试模板',
            style=ContentStyle.BROADCAST,
            platform=Platform.DOUYIN,
            structure=['开场', '正文', '结尾'],
            min_length=300,
            max_length=800,
            example='测试示例',
            tags=['测试'],
        )
        assert template.id == 'test_001'
        assert template.min_length == 300
        assert template.max_length == 800


class TestGeneratedScript:
    """Test GeneratedScript dataclass"""

    def test_script_creation(self):
        """Test GeneratedScript creation"""
        script = GeneratedScript(
            id='script_001',
            input_text='测试输入',
            title='测试标题',
            content='测试内容',
            style=ContentStyle.BROADCAST,
            platform=Platform.DOUYIN,
            word_count=100,
            hashtags=['#测试'],
            hooks=['钩子1'],
            cta='点击了解更多',
            variations=['变体1', '变体2'],
        )
        assert script.id == 'script_001'
        assert script.word_count == 100
        assert len(script.hashtags) == 1


class TestEnums:
    """Test enums"""

    def test_content_style_values(self):
        """Test ContentStyle enum values"""
        assert ContentStyle.BROADCAST.value == 'broadcast'
        assert ContentStyle.DRAMA.value == 'drama'
        assert ContentStyle.KNOWLEDGE.value == 'knowledge'
        assert ContentStyle.SEEDING.value == 'seeding'
        assert ContentStyle.EMOTIONAL.value == 'emotional'
        assert ContentStyle.PROMOTION.value == 'promotion'

    def test_platform_values(self):
        """Test Platform enum values"""
        assert Platform.DOUYIN.value == 'douyin'
        assert Platform.XIAOHONGSHU.value == 'xiaohongshu'
        assert Platform.KUAISHOU.value == 'kuaishou'
        assert Platform.BILIBILI.value == 'bilibili'
