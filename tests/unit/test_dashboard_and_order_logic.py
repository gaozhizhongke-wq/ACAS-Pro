from datetime import datetime, timedelta
from acas_pro.ui.logic.dashboard_logic import (
    DashboardLogic, AlertItem
)
from acas_pro.ui.logic.order_logic import (
    OrderLogic, Order, OrderStatus, PaymentStatus
)


# ---- DashboardLogic Tests ----

class TestLoadUser:
    def test_load_user_with_service(self):
        logic = DashboardLogic()
        logic.user_service = type('S', (), {'get_current': lambda self: {'nickname': 'Alice'}})()
        result = logic.load_user()
        assert result is not None
        assert logic._user == result

    def test_load_user_no_service(self):
        logic = DashboardLogic()
        result = logic.load_user()
        assert result is None


class TestWelcomeMessage:
    def test_with_user(self):
        logic = DashboardLogic()
        logic._user = {'nickname': 'Bob'}
        assert 'Bob' in logic.get_welcome_message()

    def test_without_user(self):
        logic = DashboardLogic()
        assert '用户' in logic.get_welcome_message()


class TestSubtitle:
    def test_get_subtitle(self):
        logic = DashboardLogic()
        assert '今日' in logic.get_subtitle()


class TestCalculateKPIs:
    def test_basic(self):
        logic = DashboardLogic()
        data = {
            'revenue': 120000,
            'revenue_prev': 100000,
            'active_orders': 500,
            'orders_prev': 400,
            'inventory_count': 2000,
            'low_stock_count': 5,
            'critical_alerts': 0,
            'high_alerts': 1,
            'medium_alerts': 0,
        }
        kpis = logic.calculate_kpis(data)
        assert len(kpis) == 4
        assert kpis[0].title == '总营收'
        assert kpis[1].title == '活跃订单'
        assert kpis[2].title == '库存商品'
        assert kpis[3].title == '风险预警'

    def test_revenue_trend_positive(self):
        logic = DashboardLogic()
        data = {'revenue': 120000, 'revenue_prev': 100000}
        kpis = logic.calculate_kpis(data)
        assert kpis[0].trend > 0

    def test_low_stock_subtitle(self):
        logic = DashboardLogic()
        data = {'low_stock_count': 10}
        kpis = logic.calculate_kpis(data)
        assert '补货' in kpis[2].subtitle

    def test_no_low_stock(self):
        logic = DashboardLogic()
        data = {'low_stock_count': 0}
        kpis = logic.calculate_kpis(data)
        assert '充足' in kpis[2].subtitle

    def test_critical_alerts(self):
        logic = DashboardLogic()
        data = {'critical_alerts': 2, 'high_alerts': 0, 'medium_alerts': 0}
        kpis = logic.calculate_kpis(data)
        assert kpis[3].color == DashboardLogic.COLORS['danger']

    def test_no_alerts(self):
        logic = DashboardLogic()
        data = {'critical_alerts': 0, 'high_alerts': 0, 'medium_alerts': 0}
        kpis = logic.calculate_kpis(data)
        assert '无风险' in kpis[3].subtitle

    def test_use_default_data(self):
        logic = DashboardLogic()
        kpis = logic.calculate_kpis()  # no data → use _fetch_default_data
        assert len(kpis) == 4


class TestQuickActions:
    def test_get_actions(self):
        logic = DashboardLogic()
        actions = logic.get_quick_actions()
        assert len(actions) == 4
        assert actions[0].id == 'forecast'
        assert actions[3].icon == '⚙️'


class TestAlerts:
    def test_get_alerts(self):
        logic = DashboardLogic()
        logic._alerts = [
            AlertItem(level='critical', message='test', timestamp=datetime.now())
        ]
        alerts = logic.get_alerts(limit=10)
        assert len(alerts) == 1

    def test_get_alerts_limit(self):
        logic = DashboardLogic()
        logic._alerts = [
            AlertItem(level='c', message=f't{i}', timestamp=datetime.now())
            for i in range(5)
        ]
        assert len(logic.get_alerts(limit=3)) == 3


class TestRefreshData:
    def test_refresh(self):
        logic = DashboardLogic()
        logic.user_service = type('S', (), {'get_current': lambda self: {'nickname': 'X'}})()
        result = logic.refresh_data()
        assert 'user' in result
        assert 'kpis' in result
        assert 'alerts' in result


class TestFormatHelpers:
    def test_format_currency_wan(self):
        assert DashboardLogic._format_currency(120000) == '¥12.0万'

    def test_format_currency_small(self):
        assert DashboardLogic._format_currency(9999) == '¥9,999'

    def test_format_number_wan(self):
        assert DashboardLogic._format_number(12000) == '1.2万'

    def test_format_trend_positive(self):
        assert '↑' in DashboardLogic._format_trend(10.5)

    def test_format_trend_negative(self):
        assert '↓' in DashboardLogic._format_trend(-5.0)

    def test_format_trend_zero(self):
        assert '→' in DashboardLogic._format_trend(0.0)


# ---- OrderLogic Tests ----

class TestCreateOrder:
    def _make_item(self, product_id='p1', product_name='Item', qty=1, price=10.0):
        return {
            'product_id': product_id,
            'product_name': product_name,
            'quantity': qty,
            'unit_price': price,
        }

    def test_create_basic(self):
        logic = OrderLogic()
        items = [self._make_item()]
        order = logic.create_order('cust1', 'Alice', items, 'Shanghai')
        assert isinstance(order, Order)
        assert order.customer_id == 'cust1'
        assert order.status == OrderStatus.PENDING
        assert order.payment_status == PaymentStatus.PENDING
        assert order.total_amount == 10.0

    def test_create_multi_items(self):
        logic = OrderLogic()
        items = [
            self._make_item(qty=2, price=10.0),
            self._make_item(product_id='p2', product_name='Item2', qty=1, price=25.0),
        ]
        order = logic.create_order('c1', 'Bob', items, 'Addr')
        assert order.total_amount == 2 * 10.0 + 25.0

    def test_create_adds_to_dict(self):
        logic = OrderLogic()
        order = logic.create_order('c1', 'X', [self._make_item()], 'Addr')
        assert order.id in logic._orders


class TestUpdateStatus:
    def test_update_success(self):
        logic = OrderLogic()
        order = logic.create_order('c1', 'X', [{'product_id': 'p1', 'product_name': 'X', 'quantity': 1, 'unit_price': 10}], 'Addr')
        assert logic.update_status(order.id, OrderStatus.CONFIRMED) is True
        assert order.status == OrderStatus.CONFIRMED

    def test_update_missing(self):
        logic = OrderLogic()
        assert logic.update_status('no-id', OrderStatus.CONFIRMED) is False


class TestUpdatePayment:
    def test_update_success(self):
        logic = OrderLogic()
        order = logic.create_order('c1', 'X', [{'product_id': 'p1', 'product_name': 'X', 'quantity': 1, 'unit_price': 10}], 'Addr')
        assert logic.update_payment(order.id, PaymentStatus.PAID) is True
        assert order.payment_status == PaymentStatus.PAID

    def test_update_missing(self):
        logic = OrderLogic()
        assert logic.update_payment('no-id', PaymentStatus.PAID) is False


class TestGetOrder:
    def test_get_exists(self):
        logic = OrderLogic()
        order = logic.create_order('c1', 'X', [{'product_id': 'p1', 'product_name': 'X', 'quantity': 1, 'unit_price': 10}], 'Addr')
        assert logic.get_order(order.id) is order

    def test_get_missing(self):
        logic = OrderLogic()
        assert logic.get_order('no-id') is None


class TestListOrders:
    def test_list_all(self):
        logic = OrderLogic()
        logic.create_order('c1', 'X', [{'product_id': 'p1', 'product_name': 'X', 'quantity': 1, 'unit_price': 10}], 'Addr')
        logic.create_order('c2', 'Y', [{'product_id': 'p1', 'product_name': 'X', 'quantity': 1, 'unit_price': 10}], 'Addr')
        assert len(logic.list_orders()) == 2

    def test_list_by_status(self):
        logic = OrderLogic()
        o1 = logic.create_order('c1', 'X', [{'product_id': 'p1', 'product_name': 'X', 'quantity': 1, 'unit_price': 10}], 'Addr')
        logic.update_status(o1.id, OrderStatus.SHIPPED)
        result = logic.list_orders(status=OrderStatus.SHIPPED)
        assert len(result) == 1

    def test_list_by_customer(self):
        logic = OrderLogic()
        logic.create_order('c1', 'X', [{'product_id': 'p1', 'product_name': 'X', 'quantity': 1, 'unit_price': 10}], 'Addr')
        logic.create_order('c2', 'Y', [{'product_id': 'p1', 'product_name': 'X', 'quantity': 1, 'unit_price': 10}], 'Addr')
        result = logic.list_orders(customer_id='c1')
        assert len(result) == 1


class TestCalculateRevenue:
    def test_with_orders(self):
        logic = OrderLogic()
        now = datetime.now()
        o1 = logic.create_order('c1', 'X', [{'product_id': 'p1', 'product_name': 'X', 'quantity': 1, 'unit_price': 100}], 'Addr')
        logic.update_payment(o1.id, PaymentStatus.PAID)
        o1.created_at = now - timedelta(days=1)
        o2 = logic.create_order('c2', 'Y', [{'product_id': 'p1', 'product_name': 'X', 'quantity': 1, 'unit_price': 50}], 'Addr')
        logic.update_payment(o2.id, PaymentStatus.PAID)
        o2.created_at = now - timedelta(days=1)
        result = logic.calculate_revenue(now - timedelta(days=2), now)
        assert result['total_revenue'] == 150.0
        assert result['order_count'] == 2

    def test_empty(self):
        logic = OrderLogic()
        now = datetime.now()
        result = logic.calculate_revenue(now - timedelta(days=1), now)
        assert result['total_revenue'] == 0.0
        assert result['order_count'] == 0


class TestGetStatusSummary:
    def test_summary(self):
        logic = OrderLogic()
        logic.create_order('c1', 'X', [{'product_id': 'p1', 'product_name': 'X', 'quantity': 1, 'unit_price': 10}], 'Addr')
        summary = logic.get_status_summary()
        assert summary['pending'] == 1
        assert summary['confirmed'] == 0
