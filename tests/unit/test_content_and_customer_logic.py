from acas_pro.ui.logic.content_logic import (
    ContentCreationLogic, Platform, ContentStyle, GeneratedScript
)
from acas_pro.ui.logic.customer_logic import (
    CustomerLogic, Customer, CustomerStatus, CustomerSource
)


# ---- ContentCreationLogic Tests ----

class TestFetchTrends:
    def test_fetch_all_platforms(self):
        logic = ContentCreationLogic()
        trends = logic.fetch_trends(limit=5)
        assert len(trends) == 5

    def test_fetch_specific_platform(self):
        logic = ContentCreationLogic()
        trends = logic.fetch_trends(platform=Platform.DOUYIN, limit=3)
        assert all(t.platform == Platform.DOUYIN for t in trends)

    def test_fetch_populates_internal(self):
        logic = ContentCreationLogic()
        trends = logic.fetch_trends(limit=2)  # noqa: F841
        assert len(logic._trends) == 2


class TestAnalyzeTrend:
    def test_analyze_existing(self):
        logic = ContentCreationLogic()
        trends = logic.fetch_trends(limit=1)
        result = logic.analyze_trend(trends[0].id)
        assert 'viral_factors' in result
        assert 'target_audience' in result
        assert 'content_gaps' in result

    def test_analyze_missing(self):
        logic = ContentCreationLogic()
        assert logic.analyze_trend('no-id') == {}


class TestGenerateScript:
    def test_generate_basic(self):
        logic = ContentCreationLogic()
        script = logic.generate_script(
            topic='AI Tools',
            platform=Platform.DOUYIN,
            style=ContentStyle.PROFESSIONAL,
            duration=60
        )
        assert isinstance(script, GeneratedScript)
        assert script.platform == Platform.DOUYIN
        assert script.style == ContentStyle.PROFESSIONAL
        assert script.estimated_duration == 60

    def test_generate_with_keywords(self):
        logic = ContentCreationLogic()
        script = logic.generate_script(
            topic='Test',
            platform=Platform.XIAOHONGSHU,
            style=ContentStyle.CASUAL,
            keywords=['AI', 'tools']
        )
        assert 'AI' in script.keywords

    def test_generate_title_format(self):
        logic = ContentCreationLogic()
        script = logic.generate_script(
            topic='Test',
            platform=Platform.DOUYIN,
            style=ContentStyle.HUMOROUS
        )
        assert 'Test' in script.title
        assert 'humorous' in script.title


class TestGetTemplates:
    def test_get_all(self):
        logic = ContentCreationLogic()
        templates = logic.get_templates()
        assert len(templates) >= 0  # may be empty or preloaded

    def test_get_by_platform(self):
        logic = ContentCreationLogic()
        templates = logic.get_templates(platform=Platform.XIAOHONGSHU)
        assert all(t.platform == Platform.XIAOHONGSHU for t in templates)


class TestOptimizeScript:
    def test_optimize_for_douyin(self):
        logic = ContentCreationLogic()
        script = logic.generate_script('T', Platform.DOUYIN, ContentStyle.PROFESSIONAL, 120)
        optimized = logic.optimize_script(script, Platform.DOUYIN)
        assert optimized.platform == Platform.DOUYIN
        assert optimized.estimated_duration <= 60  # max_duration for douyin

    def test_optimize_for_kuaishou(self):
        logic = ContentCreationLogic()
        script = logic.generate_script('T', Platform.DOUYIN, ContentStyle.EMOTIONAL, 200)
        optimized = logic.optimize_script(script, Platform.KUAISHOU)
        assert optimized.estimated_duration <= 120  # max_duration for kuaishou

    def test_optimize_content_prefix(self):
        logic = ContentCreationLogic()
        script = logic.generate_script('T', Platform.DOUYIN, ContentStyle.PROFESSIONAL, 60)
        optimized = logic.optimize_script(script, Platform.XIAOHONGSHU)
        assert optimized.content.startswith('[Optimized for xiaohongshu]')


# ---- CustomerLogic Tests ----

class TestCreateCustomer:
    def test_create_basic(self):
        logic = CustomerLogic()
        c = logic.create_customer(name='Alice', email='a@test.com', phone='123')
        assert isinstance(c, Customer)
        assert c.name == 'Alice'
        assert c.status == CustomerStatus.NEW
        assert c.source == CustomerSource.ORGANIC

    def test_create_custom_source(self):
        logic = CustomerLogic()
        c = logic.create_customer('B', 'b@test.com', source=CustomerSource.ADS)
        assert c.source == CustomerSource.ADS

    def test_create_adds_to_dict(self):
        logic = CustomerLogic()
        c = logic.create_customer('X', 'x@test.com')
        assert c.id in logic._customers


class TestUpdateCustomer:
    def test_update_email(self):
        logic = CustomerLogic()
        c = logic.create_customer('X', 'old@test.com')
        assert logic.update_customer(c.id, email='new@test.com') is True
        assert c.email == 'new@test.com'

    def test_update_missing(self):
        logic = CustomerLogic()
        assert logic.update_customer('no-id', email='x') is False


class TestGetCustomer:
    def test_get_exists(self):
        logic = CustomerLogic()
        c = logic.create_customer('X', 'x@test.com')
        assert logic.get_customer(c.id) is c

    def test_get_missing(self):
        logic = CustomerLogic()
        assert logic.get_customer('no-id') is None


class TestFindByEmail:
    def test_find_exists(self):
        logic = CustomerLogic()
        c = logic.create_customer('X', 'findme@test.com')
        assert logic.find_by_email('findme@test.com') is c

    def test_find_case_insensitive(self):
        logic = CustomerLogic()
        logic.create_customer('X', 'Case@Test.com')
        assert logic.find_by_email('case@test.com') is not None

    def test_find_missing(self):
        logic = CustomerLogic()
        assert logic.find_by_email('no@test.com') is None


class TestListCustomers:
    def test_list_all(self):
        logic = CustomerLogic()
        logic.create_customer('A', 'a@test.com')
        logic.create_customer('B', 'b@test.com')
        assert len(logic.list_customers()) == 2

    def test_list_by_status(self):
        logic = CustomerLogic()
        c = logic.create_customer('A', 'a@test.com')
        logic.update_purchase_history(c.id, 15000)
        result = logic.list_customers(status=CustomerStatus.VIP)
        assert len(result) == 1

    def test_list_by_source(self):
        logic = CustomerLogic()
        logic.create_customer('A', 'a@test.com', source=CustomerSource.ADS)
        logic.create_customer('B', 'b@test.com')
        result = logic.list_customers(source=CustomerSource.ADS)
        assert len(result) == 1

    def test_list_by_search(self):
        logic = CustomerLogic()
        logic.create_customer('Alice Smith', 'alice@test.com')
        logic.create_customer('Bob Jones', 'bob@test.com')
        result = logic.list_customers(search='alice')
        assert len(result) == 1


class TestUpdatePurchaseHistory:
    def test_first_purchase(self):
        logic = CustomerLogic()
        c = logic.create_customer('X', 'x@test.com')
        assert logic.update_purchase_history(c.id, 500.0) is True
        assert c.total_orders == 1
        assert c.total_spent == 500.0
        assert c.status == CustomerStatus.ACTIVE  # was NEW

    def test_vip_threshold(self):
        logic = CustomerLogic()
        c = logic.create_customer('X', 'x@test.com')
        logic.update_purchase_history(c.id, 15000.0)
        assert c.status == CustomerStatus.VIP

    def test_missing_customer(self):
        logic = CustomerLogic()
        assert logic.update_purchase_history('no-id', 100.0) is False


class TestCreateSegment:
    def test_create_basic(self):
        logic = CustomerLogic()
        seg = logic.create_segment('High Value', {'min_spent': 10000})
        assert seg.name == 'High Value'
        assert seg.criteria == {'min_spent': 10000}
        assert seg.id in logic._segments


class TestGetSegmentCustomers:
    def test_filter_by_min_spent(self):
        logic = CustomerLogic()
        c1 = logic.create_customer('A', 'a@test.com')
        c2 = logic.create_customer('B', 'b@test.com')
        logic.update_purchase_history(c1.id, 15000)
        seg = logic.create_segment('VIP', {'min_spent': 10000})
        result = logic.get_segment_customers(seg.id)
        ids = [c.id for c in result]
        assert c1.id in ids
        assert c2.id not in ids

    def test_empty_segment(self):
        logic = CustomerLogic()
        seg = logic.create_segment('Empty', {'min_spent': 99999})
        assert logic.get_segment_customers(seg.id) == []


class TestGetCustomerStats:
    def test_with_customers(self):
        logic = CustomerLogic()
        c1 = logic.create_customer('A', 'a@test.com')
        c2 = logic.create_customer('B', 'b@test.com')
        logic.update_purchase_history(c1.id, 500)
        logic.update_purchase_history(c2.id, 300)
        stats = logic.get_customer_stats()
        assert stats['total'] == 2
        assert stats['vip_count'] == 0

    def test_empty(self):
        logic = CustomerLogic()
        stats = logic.get_customer_stats()
        assert stats['total'] == 0
        assert stats['avg_order_value'] == 0


class TestGetChurnedCustomers:
    def test_no_customers(self):
        logic = CustomerLogic()
        assert logic.get_churned_customers() == []

    def test_no_churned(self):
        logic = CustomerLogic()
        c = logic.create_customer('A', 'a@test.com')
        logic.update_purchase_history(c.id, 100)
        assert logic.get_churned_customers(days=90) == []
