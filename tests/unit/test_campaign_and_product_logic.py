from datetime import datetime, timedelta
from acas_pro.ui.logic.campaign_logic import (
    CampaignLogic, Campaign, CampaignStatus, CampaignType
)
from acas_pro.ui.logic.product_logic import (
    ProductLogic, Product, ProductStatus
)


# ---- CampaignLogic Tests ----

class TestCreateCampaign:
    def test_create_basic(self):
        logic = CampaignLogic()
        c = logic.create_campaign(
            name='Test Campaign',
            campaign_type=CampaignType.EMAIL,
            subject='Hello',
            content='Content here',
            target_audience={'tags': ['vip']}
        )
        assert isinstance(c, Campaign)
        assert c.name == 'Test Campaign'
        assert c.status == CampaignStatus.DRAFT
        assert c.sent_count == 0

    def test_create_adds_to_dict(self):
        logic = CampaignLogic()
        c = logic.create_campaign(
            name='X',
            campaign_type=CampaignType.ADS,
            subject='S',
            content='C',
            target_audience={}
        )
        assert c.id in logic._campaigns


class TestScheduleCampaign:
    def test_schedule_draft(self):
        logic = CampaignLogic()
        c = logic.create_campaign('X', CampaignType.EMAIL, 'S', 'C', {})
        future = datetime.now() + timedelta(days=1)
        assert logic.schedule_campaign(c.id, future) is True
        assert c.status == CampaignStatus.SCHEDULED
        assert c.schedule == future

    def test_schedule_non_draft_fails(self):
        logic = CampaignLogic()
        c = logic.create_campaign('X', CampaignType.EMAIL, 'S', 'C', {})
        logic.launch_campaign(c.id)
        future = datetime.now() + timedelta(days=1)
        assert logic.schedule_campaign(c.id, future) is False

    def test_schedule_missing(self):
        logic = CampaignLogic()
        assert logic.schedule_campaign('no-id', datetime.now()) is False


class TestLaunchCampaign:
    def test_launch_draft(self):
        logic = CampaignLogic()
        c = logic.create_campaign('X', CampaignType.EMAIL, 'S', 'C', {})
        assert logic.launch_campaign(c.id) is True
        assert c.status == CampaignStatus.RUNNING
        assert c.started_at is not None

    def test_launch_scheduled(self):
        logic = CampaignLogic()
        c = logic.create_campaign('X', CampaignType.EMAIL, 'S', 'C', {})
        logic.schedule_campaign(c.id, datetime.now())
        assert logic.launch_campaign(c.id) is True

    def test_launch_not_draft_or_scheduled(self):
        logic = CampaignLogic()
        c = logic.create_campaign('X', CampaignType.EMAIL, 'S', 'C', {})
        logic.launch_campaign(c.id)
        logic.pause_campaign(c.id)
        assert logic.launch_campaign(c.id) is False  # PAUSED → not in [DRAFT, SCHEDULED]


class TestPauseResume:
    def test_pause_running(self):
        logic = CampaignLogic()
        c = logic.create_campaign('X', CampaignType.EMAIL, 'S', 'C', {})
        logic.launch_campaign(c.id)
        assert logic.pause_campaign(c.id) is True
        assert c.status == CampaignStatus.PAUSED

    def test_pause_not_running(self):
        logic = CampaignLogic()
        c = logic.create_campaign('X', CampaignType.EMAIL, 'S', 'C', {})
        assert logic.pause_campaign(c.id) is False

    def test_resume_paused(self):
        logic = CampaignLogic()
        c = logic.create_campaign('X', CampaignType.EMAIL, 'S', 'C', {})
        logic.launch_campaign(c.id)
        logic.pause_campaign(c.id)
        assert logic.resume_campaign(c.id) is True
        assert c.status == CampaignStatus.RUNNING

    def test_resume_not_paused(self):
        logic = CampaignLogic()
        c = logic.create_campaign('X', CampaignType.EMAIL, 'S', 'C', {})
        assert logic.resume_campaign(c.id) is False


class TestCompleteCampaign:
    def test_complete_running(self):
        logic = CampaignLogic()
        c = logic.create_campaign('X', CampaignType.EMAIL, 'S', 'C', {})
        logic.launch_campaign(c.id)
        assert logic.complete_campaign(c.id) is True
        assert c.status == CampaignStatus.COMPLETED
        assert c.completed_at is not None

    def test_complete_missing(self):
        logic = CampaignLogic()
        assert logic.complete_campaign('no-id') is False


class TestUpdateStats:
    def test_update_stats(self):
        logic = CampaignLogic()
        c = logic.create_campaign('X', CampaignType.EMAIL, 'S', 'C', {})
        logic.update_stats(c.id, sent=100, opened=50, clicked=10)
        assert c.sent_count == 100
        assert c.open_count == 50
        assert c.click_count == 10

    def test_update_stats_missing(self):
        logic = CampaignLogic()
        assert logic.update_stats('no-id', sent=1) is False


class TestGetCampaign:
    def test_get_exists(self):
        logic = CampaignLogic()
        c = logic.create_campaign('X', CampaignType.EMAIL, 'S', 'C', {})
        assert logic.get_campaign(c.id) is c

    def test_get_missing(self):
        logic = CampaignLogic()
        assert logic.get_campaign('no-id') is None


class TestListCampaigns:
    def test_list_all(self):
        logic = CampaignLogic()
        logic.create_campaign('A', CampaignType.EMAIL, 'S', 'C', {})
        logic.create_campaign('B', CampaignType.SMS, 'S', 'C', {})
        assert len(logic.list_campaigns()) == 2

    def test_list_by_status(self):
        logic = CampaignLogic()
        c = logic.create_campaign('A', CampaignType.EMAIL, 'S', 'C', {})
        logic.launch_campaign(c.id)
        result = logic.list_campaigns(status=CampaignStatus.RUNNING)
        assert len(result) == 1
        assert result[0].id == c.id

    def test_list_by_type(self):
        logic = CampaignLogic()
        logic.create_campaign('A', CampaignType.EMAIL, 'S', 'C', {})
        logic.create_campaign('B', CampaignType.SMS, 'S', 'C', {})
        result = logic.list_campaigns(campaign_type=CampaignType.EMAIL)
        assert len(result) == 1


class TestPerformanceMetrics:
    def test_metrics(self):
        logic = CampaignLogic()
        c = logic.create_campaign('X', CampaignType.EMAIL, 'S', 'C', {})
        logic.update_stats(c.id, sent=100, opened=50, clicked=10)
        m = logic.get_performance_metrics(c.id)
        assert m['sent'] == 100
        assert m['open_rate'] == 50.0
        assert m['click_rate'] == 10.0
        assert m['ctr'] == 20.0  # 10/50*100

    def test_metrics_missing(self):
        logic = CampaignLogic()
        assert logic.get_performance_metrics('no-id') == {}

    def test_metrics_zero_sent(self):
        logic = CampaignLogic()
        c = logic.create_campaign('X', CampaignType.EMAIL, 'S', 'C', {})
        m = logic.get_performance_metrics(c.id)
        assert m['open_rate'] == 0.0


class TestDuplicateCampaign:
    def test_duplicate(self):
        logic = CampaignLogic()
        c = logic.create_campaign('Orig', CampaignType.EMAIL, 'S', 'C', {'x': 1})
        dup = logic.duplicate_campaign(c.id)
        assert dup is not None
        assert dup.name == 'Orig (Copy)'
        assert dup.subject == 'S'
        assert dup.target_audience == {'x': 1}

    def test_duplicate_missing(self):
        logic = CampaignLogic()
        assert logic.duplicate_campaign('no-id') is None


# ---- ProductLogic Tests ----

class TestCreateProduct:
    def test_create_basic(self):
        logic = ProductLogic()
        p = logic.create_product(
            name='Test Product',
            description='Desc',
            price=99.99,
            cost=50.0,
            stock=10,
            category='electronics',
            tags=['new']
        )
        assert isinstance(p, Product)
        assert p.price == 99.99
        assert p.status == ProductStatus.ACTIVE

    def test_create_zero_stock(self):
        logic = ProductLogic()
        p = logic.create_product('X', 'D', price=10.0, stock=0)
        assert p.status == ProductStatus.OUT_OF_STOCK

    def test_create_adds_to_dict(self):
        logic = ProductLogic()
        p = logic.create_product('X', 'D', price=10.0)
        assert p.id in logic._products


class TestUpdateProduct:
    def test_update_price(self):
        logic = ProductLogic()
        p = logic.create_product('X', 'D', price=10.0)
        assert logic.update_product(p.id, price=20.0) is True
        assert p.price == 20.0

    def test_update_missing(self):
        logic = ProductLogic()
        assert logic.update_product('no-id', price=20.0) is False


class TestGetProduct:
    def test_get_exists(self):
        logic = ProductLogic()
        p = logic.create_product('X', 'D', price=10.0)
        assert logic.get_product(p.id) is p

    def test_get_missing(self):
        logic = ProductLogic()
        assert logic.get_product('no-id') is None


class TestListProducts:
    def test_list_all(self):
        logic = ProductLogic()
        logic.create_product('A', 'D', price=10.0, category='cat1')
        logic.create_product('B', 'D', price=20.0, category='cat2')
        assert len(logic.list_products()) == 2

    def test_list_by_category(self):
        logic = ProductLogic()
        logic.create_product('A', 'D', price=10.0, category='cat1')
        logic.create_product('B', 'D', price=20.0, category='cat2')
        result = logic.list_products(category='cat1')
        assert len(result) == 1
        assert result[0].category == 'cat1'

    def test_list_by_status(self):
        logic = ProductLogic()
        p = logic.create_product('A', 'D', price=10.0, stock=0)  # noqa: F841
        logic.create_product('B', 'D', price=20.0, stock=5)
        result = logic.list_products(status=ProductStatus.OUT_OF_STOCK)
        assert len(result) == 1

    def test_list_by_search(self):
        logic = ProductLogic()
        logic.create_product('iPhone 15', 'Apple phone', price=999.0)
        logic.create_product('Galaxy S24', 'Samsung phone', price=899.0)
        result = logic.list_products(search='iphone')
        assert len(result) == 1


class TestUpdateStock:
    def test_update_stock_active(self):
        logic = ProductLogic()
        p = logic.create_product('X', 'D', price=10.0, stock=10)
        assert logic.update_stock(p.id, 5) is True
        assert p.stock_quantity == 5

    def test_update_stock_to_zero(self):
        logic = ProductLogic()
        p = logic.create_product('X', 'D', price=10.0, stock=10)
        logic.update_stock(p.id, 0)
        assert p.status == ProductStatus.OUT_OF_STOCK

    def test_update_stock_from_zero(self):
        logic = ProductLogic()
        p = logic.create_product('X', 'D', price=10.0, stock=0)
        logic.update_stock(p.id, 10)
        assert p.status == ProductStatus.ACTIVE

    def test_update_stock_missing(self):
        logic = ProductLogic()
        assert logic.update_stock('no-id', 5) is False


class TestProfitMargin:
    def test_positive_margin(self):
        logic = ProductLogic()
        p = logic.create_product('X', 'D', price=100.0, cost=60.0)
        assert logic.calculate_profit_margin(p.id) == 40.0

    def test_zero_price(self):
        logic = ProductLogic()
        p = logic.create_product('X', 'D', price=0.0, cost=0.0)
        assert logic.calculate_profit_margin(p.id) == 0.0

    def test_missing_product(self):
        logic = ProductLogic()
        assert logic.calculate_profit_margin('no-id') == 0.0


class TestLowStock:
    def test_low_stock(self):
        logic = ProductLogic()
        p1 = logic.create_product('A', 'D', price=10.0, stock=5)
        p2 = logic.create_product('B', 'D', price=20.0, stock=20)
        logic.create_product('C', 'D', price=30.0, stock=0, category='x')
        # C is out_of_stock but not discontinued → included
        result = logic.get_low_stock_products(threshold=10)
        ids = [p.id for p in result]
        assert p1.id in ids
        assert p2.id not in ids


class TestCategorySummary:
    def test_summary(self):
        logic = ProductLogic()
        logic.create_product('A', 'D', price=10.0, category='cat1')
        logic.create_product('B', 'D', price=20.0, category='cat1')
        logic.create_product('C', 'D', price=30.0, category='cat2')
        summary = logic.get_category_summary()
        assert summary['cat1'] == 2
        assert summary['cat2'] == 1
