#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for platform-specific shop API clients (Xiaohongshu, Douyin, Taobao).

Covers: _check_business_error, _build_common_params, _request_api, _do_refresh_token,
        sync_orders, sync_products, sync_inventory, update_product_status,
        get_logistics_info, exchange_token for all three platforms.
Results: 87 tests, all passing, 100% coverage on each client module.
"""

import json
import pytest
from unittest.mock import MagicMock

from acas_pro.ecommerce.platform_api_base import (
    PlatformCredentials,
    APIError,
    AuthError,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def valid_creds():
    return PlatformCredentials(
        app_key="test_key",
        app_secret="test_secret",
        access_token="test_token",
        refresh_token="test_refresh",
        shop_id="shop_001",
    )


# ============================================================
# XiaohongshuShopClient
# ============================================================

class TestXiaohongshuShopClient:
    """Tests for XiaohongshuShopClient."""

    def _make_client(self, creds, request_mock=None):
        from acas_pro.ecommerce.xiaohongshu_shop_api import XiaohongshuShopClient
        client = XiaohongshuShopClient(credentials=creds)
        if request_mock is not None:
            client.request = request_mock
        return client

    # ── _check_business_error ───────────────────────────────────

    def test_check_business_error_success(self, valid_creds):
        client = self._make_client(valid_creds)
        client._check_business_error({"success": True, "data": {}})

    def test_check_business_error_unauthorized(self, valid_creds):
        client = self._make_client(valid_creds)
        with pytest.raises(AuthError, match="UNAUTHORIZED"):
            client._check_business_error({"success": False, "errorCode": "UNAUTHORIZED", "errorMsg": "Token invalid"})

    def test_check_business_error_token_expired(self, valid_creds):
        client = self._make_client(valid_creds)
        with pytest.raises(AuthError, match="TOKEN_EXPIRED"):
            client._check_business_error({"success": False, "errorCode": "TOKEN_EXPIRED", "errorMsg": "Expired"})

    def test_check_business_error_api(self, valid_creds):
        client = self._make_client(valid_creds)
        with pytest.raises(APIError, match="XHS_PARAM_ERROR"):
            client._check_business_error({"success": False, "errorCode": "PARAM_ERROR", "errorMsg": "Bad"})

    def test_check_business_error_missing_fields(self, valid_creds):
        client = self._make_client(valid_creds)
        with pytest.raises(APIError, match="XHS_UNKNOWN"):
            client._check_business_error({"success": False})

    # ── _build_common_params ────────────────────────────────────

    def test_build_common_params(self, valid_creds):
        client = self._make_client(valid_creds)
        params = client._build_common_params("/order/list")
        assert params["appId"] == "test_key"
        assert "timestamp" in params
        assert params["version"] == "1"
        assert "sign" in params

    # ── _request_api ────────────────────────────────────────────

    def test_request_api(self, valid_creds):
        mock_request = MagicMock(return_value={"success": True, "data": {}})
        client = self._make_client(valid_creds, request_mock=mock_request)
        result = client._request_api("/order/list", {"pageNo": 1})  # noqa: F841
        args, kwargs = mock_request.call_args
        assert args[0] == "POST"
        assert args[1] == "/order/list"
        assert kwargs["headers"]["Authorization"] == "Bearer test_token"
        assert kwargs["data"]["pageNo"] == 1

    def test_request_api_no_biz_data(self, valid_creds):
        mock_request = MagicMock(return_value={"success": True})
        client = self._make_client(valid_creds, request_mock=mock_request)
        assert client._request_api("/order/list") == {"success": True}

    # ── _do_refresh_token ───────────────────────────────────────

    def test_do_refresh_token_success(self, valid_creds):
        mock_request = MagicMock(return_value={"data": {"accessToken": "new_token"}})
        client = self._make_client(valid_creds, request_mock=mock_request)
        assert client._do_refresh_token() == "new_token"

    def test_do_refresh_token_empty_data(self, valid_creds):
        mock_request = MagicMock(return_value={"data": {}})
        client = self._make_client(valid_creds, request_mock=mock_request)
        # .get("accessToken") on {} returns None
        assert client._do_refresh_token() is None

    def test_do_refresh_token_no_data(self, valid_creds):
        mock_request = MagicMock(return_value={})
        client = self._make_client(valid_creds, request_mock=mock_request)
        assert client._do_refresh_token() is None

    # ── sync_orders ─────────────────────────────────────────────

    def test_sync_orders_success(self, valid_creds):
        mock_request = MagicMock(return_value={
            "success": True, "data": {"orderList": [{"orderId": "o1"}], "total": 1}
        })
        client = self._make_client(valid_creds, request_mock=mock_request)
        r = client.sync_orders()
        assert r.success and r.total == 1 and len(r.data) == 1 and r.created == 1

    def test_sync_orders_with_dates(self, valid_creds):
        mock_request = MagicMock(return_value={
            "success": True, "data": {"orderList": [], "total": 0}
        })
        client = self._make_client(valid_creds, request_mock=mock_request)
        r = client.sync_orders(start_time="2026-01-01", end_time="2026-01-31", page=2)
        assert r.success
        d = mock_request.call_args.kwargs["data"]
        assert d["startTime"] == "2026-01-01" and d["endTime"] == "2026-01-31" and d["pageNo"] == 2

    def test_sync_orders_not_authenticated(self, valid_creds):
        empty = PlatformCredentials(app_key="k", app_secret="s")
        client = self._make_client(empty)
        r = client.sync_orders()
        assert not r.success and "Not authenticated" in r.errors[0]

    def test_sync_orders_api_error(self, valid_creds):
        mock_request = MagicMock(side_effect=Exception("Connection error"))
        client = self._make_client(valid_creds, request_mock=mock_request)
        r = client.sync_orders()
        assert not r.success and "Connection error" in r.errors[0]

    # ── sync_products ───────────────────────────────────────────

    def test_sync_products_success(self, valid_creds):
        mock_request = MagicMock(return_value={
            "success": True, "data": {"productList": [{"id": "p1"}], "total": 1}
        })
        client = self._make_client(valid_creds, request_mock=mock_request)
        r = client.sync_products()
        assert r.success and r.total == 1

    def test_sync_products_not_authenticated(self, valid_creds):
        empty = PlatformCredentials(app_key="k", app_secret="s")
        client = self._make_client(empty)
        assert not client.sync_products().success

    def test_sync_products_api_error(self, valid_creds):
        mock_request = MagicMock(side_effect=Exception("API down"))
        client = self._make_client(valid_creds, request_mock=mock_request)
        r = client.sync_products()
        assert not r.success and "API down" in r.errors[0]

    # ── sync_inventory ──────────────────────────────────────────

    def test_sync_inventory_success(self, valid_creds):
        mock_request = MagicMock(return_value={
            "success": True, "data": {"stockList": [{"pid": "p1", "qty": 50}]}
        })
        client = self._make_client(valid_creds, request_mock=mock_request)
        r = client.sync_inventory()
        assert r.success and r.total == 1

    def test_sync_inventory_with_ids(self, valid_creds):
        mock_request = MagicMock(return_value={
            "success": True, "data": {"stockList": []}
        })
        client = self._make_client(valid_creds, request_mock=mock_request)
        client.sync_inventory(product_ids=["p1"])
        assert mock_request.call_args.kwargs["data"]["productIds"] == ["p1"]

    def test_sync_inventory_not_authenticated(self, valid_creds):
        empty = PlatformCredentials(app_key="k", app_secret="s")
        assert not self._make_client(empty).sync_inventory().success

    def test_sync_inventory_api_error(self, valid_creds):
        mock_request = MagicMock(side_effect=Exception("Timeout"))
        client = self._make_client(valid_creds, request_mock=mock_request)
        assert not client.sync_inventory().success

    # ── update_product_status ───────────────────────────────────

    def test_update_product_status_success(self, valid_creds):
        mock_request = MagicMock(return_value={"success": True})
        client = self._make_client(valid_creds, request_mock=mock_request)
        assert client.update_product_status("p1", "ONLINE") is True
        d = mock_request.call_args.kwargs["data"]
        assert d["productId"] == "p1" and d["status"] == "ONLINE"

    def test_update_product_status_not_authenticated(self, valid_creds):
        empty = PlatformCredentials(app_key="k", app_secret="s")
        assert self._make_client(empty).update_product_status("p1", "ON") is False

    def test_update_product_status_api_error(self, valid_creds):
        mock_request = MagicMock(side_effect=Exception("Fail"))
        client = self._make_client(valid_creds, request_mock=mock_request)
        assert client.update_product_status("p1", "ON") is False

    def test_update_product_status_business_fail(self, valid_creds):
        mock_request = MagicMock(side_effect=APIError("XHS_500", "err", {}))
        client = self._make_client(valid_creds, request_mock=mock_request)
        assert client.update_product_status("p1", "ON") is False

    # ── get_logistics_info ──────────────────────────────────────

    def test_get_logistics_info_success(self, valid_creds):
        mock_request = MagicMock(return_value={
            "success": True, "data": {"company": "SF", "trackingNo": "SF123"}
        })
        client = self._make_client(valid_creds, request_mock=mock_request)
        r = client.get_logistics_info("order_1")
        assert r.get("company") == "SF"

    def test_get_logistics_info_not_authenticated(self, valid_creds):
        empty = PlatformCredentials(app_key="k", app_secret="s")
        r = self._make_client(empty).get_logistics_info("order_1")
        assert r == {"error": "Not authenticated"}

    def test_get_logistics_info_api_error(self, valid_creds):
        mock_request = MagicMock(side_effect=Exception("Log fail"))
        client = self._make_client(valid_creds, request_mock=mock_request)
        r = client.get_logistics_info("order_1")
        assert "Log fail" in r.get("error", "")

    # ── exchange_token ──────────────────────────────────────────

    def test_exchange_token_success(self, valid_creds):
        mock_request = MagicMock(return_value={
            "data": {"accessToken": "at", "refreshToken": "rt", "expiresIn": 7200, "shopId": "s2"}
        })
        client = self._make_client(valid_creds, request_mock=mock_request)
        r = client.exchange_token("code")
        assert r["access_token"] == "at"
        assert r["refresh_token"] == "rt"
        assert r["expires_in"] == "7200"
        assert r["shop_id"] == "s2"

    def test_exchange_token_error(self, valid_creds):
        mock_request = MagicMock(side_effect=Exception("Exchange fail"))
        client = self._make_client(valid_creds, request_mock=mock_request)
        r = client.exchange_token("code")
        assert "error" in r


# ============================================================
# DouyinShopClient
# ============================================================

class TestDouyinShopClient:
    """Tests for DouyinShopClient.

    Note: try/except in Douyin methods catches specific exception types:
    sqlite3.Error, ValueError, RuntimeError, json.JSONDecodeError.
    APIError/AuthError from _check_business_error will propagate up.
    """

    def _make_client(self, creds, request_mock=None):
        from acas_pro.ecommerce.douyin_shop_api import DouyinShopClient
        client = DouyinShopClient(credentials=creds)
        if request_mock is not None:
            client.request = request_mock
        return client

    # ── _check_business_error ───────────────────────────────────

    def test_check_business_error_success(self, valid_creds):
        client = self._make_client(valid_creds)
        client._check_business_error({"err_no": 0, "message": "success"})

    def test_check_business_error_auth(self, valid_creds):
        client = self._make_client(valid_creds)
        with pytest.raises(AuthError, match="40001"):
            client._check_business_error({"err_no": 40001, "message": "auth fail"})

    def test_check_business_error_api(self, valid_creds):
        client = self._make_client(valid_creds)
        with pytest.raises(APIError, match="DOUYIN_50001"):
            client._check_business_error({"err_no": 50001, "message": "server err"})

    # ── _build_common_params ────────────────────────────────────

    def test_build_common_params(self, valid_creds):
        client = self._make_client(valid_creds)
        p = client._build_common_params("order.list")
        assert p["app_key"] == "test_key"
        assert p["method"] == "order.list"
        assert p["v"] == "2"
        assert p["sign_method"] == "hmac-sha256"
        assert "timestamp" in p
        assert "sign" in p

    # ── _request_api ────────────────────────────────────────────

    def test_request_api(self, valid_creds):
        mock_request = MagicMock(return_value={"err_no": 0, "data": {}})
        client = self._make_client(valid_creds, request_mock=mock_request)
        r = client._request_api("order.list", {"page": 1})
        assert r == {"err_no": 0, "data": {}}
        args, kwargs = mock_request.call_args
        # Douyin passes body as params= (not data=)
        assert "param_json" in kwargs.get("params", {})
        assert "Access-Token" in kwargs.get("headers", {})

    # ── _do_refresh_token ───────────────────────────────────────

    def test_do_refresh_token_success(self, valid_creds):
        mock_request = MagicMock(return_value={"data": {"access_token": "new_at"}})
        client = self._make_client(valid_creds, request_mock=mock_request)
        assert client._do_refresh_token() == "new_at"

    # ── sync_orders ─────────────────────────────────────────────

    def test_sync_orders_success(self, valid_creds):
        mock_request = MagicMock(return_value={
            "err_no": 0, "data": {"list": [{"order_id": "o1"}], "total": 1}
        })
        client = self._make_client(valid_creds, request_mock=mock_request)
        r = client.sync_orders()
        assert r.success and r.total == 1 and len(r.data) == 1

    def test_sync_orders_with_time_range(self, valid_creds):
        mock_request = MagicMock(return_value={
            "err_no": 0, "data": {"list": [], "total": 0}
        })
        client = self._make_client(valid_creds, request_mock=mock_request)
        r = client.sync_orders(start_time="2026-01-01", end_time="2026-01-31")
        assert r.success
        p = mock_request.call_args.kwargs["params"]
        biz = json.loads(p["param_json"])
        assert "start_time" in biz and "end_time" in biz

    def test_sync_orders_not_authenticated(self, valid_creds):
        empty = PlatformCredentials(app_key="k", app_secret="s")
        assert not self._make_client(empty).sync_orders().success

    def test_sync_orders_request_error(self, valid_creds):
        """Douyin catches sqlite3/Value/Runtime/JSON errors, not generic Exception"""
        mock_request = MagicMock(side_effect=ValueError("network"))
        client = self._make_client(valid_creds, request_mock=mock_request)
        r = client.sync_orders()
        assert not r.success and "network" in r.errors[0]

    # ── sync_products ───────────────────────────────────────────

    def test_sync_products_success(self, valid_creds):
        mock_request = MagicMock(return_value={
            "err_no": 0, "data": {"list": [{"product_id": "p1"}], "total": 1}
        })
        client = self._make_client(valid_creds, request_mock=mock_request)
        r = client.sync_products()
        assert r.success and r.total == 1

    def test_sync_products_not_authenticated(self, valid_creds):
        empty = PlatformCredentials(app_key="k", app_secret="s")
        assert not self._make_client(empty).sync_products().success

    def test_sync_products_error(self, valid_creds):
        mock_request = MagicMock(side_effect=ValueError("fail"))
        client = self._make_client(valid_creds, request_mock=mock_request)
        assert not client.sync_products().success

    # ── sync_inventory ──────────────────────────────────────────

    def test_sync_inventory_success(self, valid_creds):
        mock_request = MagicMock(return_value={
            "err_no": 0, "data": {"list": [{"pid": "p1", "stock_num": 50}]}
        })
        client = self._make_client(valid_creds, request_mock=mock_request)
        r = client.sync_inventory()
        assert r.success and r.total == 1

    def test_sync_inventory_with_ids(self, valid_creds):
        mock_request = MagicMock(return_value={
            "err_no": 0, "data": {"list": []}
        })
        client = self._make_client(valid_creds, request_mock=mock_request)
        r = client.sync_inventory(product_ids=["p1"])
        assert r.success
        p = mock_request.call_args.kwargs["params"]
        biz = json.loads(p["param_json"])
        assert biz["product_ids"] == ["p1"]

    def test_sync_inventory_not_authenticated(self, valid_creds):
        empty = PlatformCredentials(app_key="k", app_secret="s")
        assert not self._make_client(empty).sync_inventory().success

    def test_sync_inventory_error(self, valid_creds):
        """Douyin sync_inventory catches sqlite3/Value/Runtime/JSON errors"""
        mock_request = MagicMock(side_effect=ValueError("stock err"))
        client = self._make_client(valid_creds, request_mock=mock_request)
        r = client.sync_inventory()
        assert not r.success and "stock err" in r.errors[0]

    # ── update_product_status ───────────────────────────────────

    def test_update_product_status_online(self, valid_creds):
        mock_request = MagicMock(return_value={"err_no": 0})
        client = self._make_client(valid_creds, request_mock=mock_request)
        assert client.update_product_status("p1", "online") is True
        p = mock_request.call_args.kwargs["params"]
        biz = json.loads(p["param_json"])
        assert biz["status"] == 1  # online → 1

    def test_update_product_status_offline(self, valid_creds):
        mock_request = MagicMock(return_value={"err_no": 0})
        client = self._make_client(valid_creds, request_mock=mock_request)
        assert client.update_product_status("p1", "offline") is True
        p = mock_request.call_args.kwargs["params"]
        biz = json.loads(p["param_json"])
        assert biz["status"] == 0  # offline → 0

    def test_update_product_status_not_auth(self, valid_creds):
        empty = PlatformCredentials(app_key="k", app_secret="s")
        assert self._make_client(empty).update_product_status("p1", "online") is False

    def test_update_product_status_exception(self, valid_creds):
        """Douyin update_product_status catches sqlite3/Value/Runtime/JSON errors"""
        mock_request = MagicMock(side_effect=ValueError("status err"))
        client = self._make_client(valid_creds, request_mock=mock_request)
        assert client.update_product_status("p1", "online") is False

    def test_update_product_status_business_fail(self, valid_creds):
        mock_request = MagicMock(return_value={"err_no": 50001})
        client = self._make_client(valid_creds, request_mock=mock_request)
        # Mocked request() bypasses _check_business_error; update_product_status
        # does result.get("err_no", -1) == 0 → False
        assert client.update_product_status("p1", "online") is False

    # ── get_logistics_info ──────────────────────────────────────

    def test_get_logistics_info_success(self, valid_creds):
        mock_request = MagicMock(return_value={
            "err_no": 0, "data": {"company": "Yunda"}
        })
        client = self._make_client(valid_creds, request_mock=mock_request)
        assert client.get_logistics_info("o1").get("company") == "Yunda"

    def test_get_logistics_info_not_auth(self, valid_creds):
        empty = PlatformCredentials(app_key="k", app_secret="s")
        r = self._make_client(empty).get_logistics_info("o1")
        assert "error" in r

    def test_get_logistics_info_error(self, valid_creds):
        mock_request = MagicMock(side_effect=ValueError("fail"))
        client = self._make_client(valid_creds, request_mock=mock_request)
        r = client.get_logistics_info("o1")
        assert "error" in r

    # ── exchange_token ──────────────────────────────────────────

    def test_exchange_token_success(self, valid_creds):
        mock_request = MagicMock(return_value={
            "data": {"access_token": "at_dy", "refresh_token": "rt_dy", "expires_in": 86400}
        })
        client = self._make_client(valid_creds, request_mock=mock_request)
        r = client.exchange_token("code")
        assert r["access_token"] == "at_dy"
        assert r["refresh_token"] == "rt_dy"
        assert r["expires_in"] == "86400"

    def test_exchange_token_error(self, valid_creds):
        mock_request = MagicMock(side_effect=ValueError("X"))
        client = self._make_client(valid_creds, request_mock=mock_request)
        assert "error" in client.exchange_token("code")


# ============================================================
# TaobaoShopClient
# ============================================================

class TestTaobaoShopClient:
    """Tests for TaobaoShopClient."""

    def _make_client(self, creds, request_mock=None):
        from acas_pro.ecommerce.taobao_shop_api import TaobaoShopClient
        client = TaobaoShopClient(credentials=creds)
        if request_mock is not None:
            client.request = request_mock
        return client

    # ── _check_business_error ───────────────────────────────────

    def test_check_business_error_success(self, valid_creds):
        client = self._make_client(valid_creds)
        client._check_business_error({"trades_sold_get_response": {}})

    def test_check_business_error_auth(self, valid_creds):
        client = self._make_client(valid_creds)
        with pytest.raises(AuthError, match="27"):
            client._check_business_error({"error_response": {"code": 27, "msg": "auth fail"}})

    def test_check_business_error_api(self, valid_creds):
        client = self._make_client(valid_creds)
        with pytest.raises(APIError, match="TAOBAO_15"):
            client._check_business_error({"error_response": {"code": 15, "msg": "ISP err"}})

    # ── _build_common_params ────────────────────────────────────

    def test_build_common_params(self, valid_creds):
        client = self._make_client(valid_creds)
        p = client._build_common_params("taobao.item.get")
        assert p["app_key"] == "test_key"
        assert p["method"] == "taobao.item.get"
        assert p["format"] == "json"
        assert p["v"] == "2.0"
        assert p["sign_method"] == "md5"
        assert p["session"] == "test_token"
        assert "timestamp" in p
        assert "sign" in p

    # ── _request_api ────────────────────────────────────────────

    def test_request_api(self, valid_creds):
        mock_request = MagicMock(return_value={"code": 0})
        client = self._make_client(valid_creds, request_mock=mock_request)
        r = client._request_api("taobao.item.get", {"num_iid": "123"})
        assert r == {"code": 0}
        d = mock_request.call_args.kwargs["data"]
        assert d.get("session") == "test_token"
        assert d.get("num_iid") == "123"

    def test_request_api_no_biz_params(self, valid_creds):
        mock_request = MagicMock(return_value={})
        client = self._make_client(valid_creds, request_mock=mock_request)
        client._request_api("taobao.item.get")
        d = mock_request.call_args.kwargs["data"]
        assert "session" in d  # always included

    # ── _do_refresh_token ───────────────────────────────────────

    def test_do_refresh_token_success(self, valid_creds):
        mock_request = MagicMock(return_value={
            "top_auth_token_refresh_response": {
                "top_auth_token": {"access_token": "new_tb"}
            }
        })
        client = self._make_client(valid_creds, request_mock=mock_request)
        assert client._do_refresh_token() == "new_tb"

    # ── sync_orders ─────────────────────────────────────────────

    def test_sync_orders_success(self, valid_creds):
        mock_request = MagicMock(return_value={
            "trades_sold_get_response": {
                "trades": {"trade": [{"tid": "o1"}, {"tid": "o2"}]},
                "total_results": 2,
            }
        })
        client = self._make_client(valid_creds, request_mock=mock_request)
        r = client.sync_orders()
        assert r.success and r.total == 2 and len(r.data) == 2

    def test_sync_orders_not_authenticated(self, valid_creds):
        empty = PlatformCredentials(app_key="k", app_secret="s")
        assert not self._make_client(empty).sync_orders().success

    def test_sync_orders_with_dates(self, valid_creds):
        """Covers start_created / end_created branches"""
        mock_request = MagicMock(return_value={
            "trades_sold_get_response": {
                "trades": {"trade": []},
                "total_results": 0,
            }
        })
        client = self._make_client(valid_creds, request_mock=mock_request)
        r = client.sync_orders(start_time="2026-01-01", end_time="2026-01-31")
        assert r.success
        d = mock_request.call_args.kwargs["data"]
        assert d["start_created"] == "2026-01-01"
        assert d["end_created"] == "2026-01-31"

    def test_sync_orders_api_error(self, valid_creds):
        mock_request = MagicMock(side_effect=Exception("TB error"))
        client = self._make_client(valid_creds, request_mock=mock_request)
        r = client.sync_orders()
        assert not r.success and "TB error" in r.errors[0]

    # ── sync_products ───────────────────────────────────────────

    def test_sync_products_success(self, valid_creds):
        mock_request = MagicMock(return_value={
            "items_onsale_get_response": {
                "items": {"item": [{"num_iid": "p1"}]},
                "total_results": 1,
            }
        })
        client = self._make_client(valid_creds, request_mock=mock_request)
        r = client.sync_products()
        assert r.success and r.total == 1 and len(r.data) == 1

    def test_sync_products_not_auth(self, valid_creds):
        empty = PlatformCredentials(app_key="k", app_secret="s")
        assert not self._make_client(empty).sync_products().success

    def test_sync_products_error(self, valid_creds):
        mock_request = MagicMock(side_effect=Exception("fail"))
        client = self._make_client(valid_creds, request_mock=mock_request)
        assert not client.sync_products().success

    # ── sync_inventory ──────────────────────────────────────────

    def test_sync_inventory_success(self, valid_creds):
        mock_request = MagicMock(return_value={
            "skus_custom_get_response": {
                "skus": {"sku": [{"sku_id": "s1", "quantity": 100}]}
            }
        })
        client = self._make_client(valid_creds, request_mock=mock_request)
        r = client.sync_inventory()
        assert r.success and r.total == 1

    def test_sync_inventory_with_ids(self, valid_creds):
        mock_request = MagicMock(return_value={
            "skus_custom_get_response": {"skus": {"sku": []}}
        })
        client = self._make_client(valid_creds, request_mock=mock_request)
        client.sync_inventory(product_ids=["p1", "p2"])
        d = mock_request.call_args.kwargs["data"]
        assert d["num_iids"] == "p1,p2"

    def test_sync_inventory_not_auth(self, valid_creds):
        empty = PlatformCredentials(app_key="k", app_secret="s")
        assert not self._make_client(empty).sync_inventory().success

    def test_sync_inventory_error(self, valid_creds):
        """Taobao sync_inventory catches general Exception"""
        mock_request = MagicMock(side_effect=Exception("inv err"))
        client = self._make_client(valid_creds, request_mock=mock_request)
        r = client.sync_inventory()
        assert not r.success and "inv err" in r.errors[0]

    # ── update_product_status ───────────────────────────────────

    def test_update_product_status_online(self, valid_creds):
        mock_request = MagicMock(return_value={
            "item_update_listing_response": {"item": {"num_iid": "p1"}}
        })
        client = self._make_client(valid_creds, request_mock=mock_request)
        assert client.update_product_status("p1", "online") is True
        d = mock_request.call_args.kwargs["data"]
        assert d["num_iid"] == "p1" and d["num"] == "1"

    def test_update_product_status_offline(self, valid_creds):
        mock_request = MagicMock(return_value={
            "item_update_delisting_response": {"item": {"num_iid": "p1"}}
        })
        client = self._make_client(valid_creds, request_mock=mock_request)
        assert client.update_product_status("p1", "offline") is True
        d = mock_request.call_args.kwargs["data"]
        assert "num" not in d  # offline has no 'num' param

    def test_update_product_status_fail(self, valid_creds):
        mock_request = MagicMock(return_value={"error_response": {"code": 15}})
        client = self._make_client(valid_creds, request_mock=mock_request)
        assert client.update_product_status("p1", "online") is False

    def test_update_product_status_not_auth(self, valid_creds):
        empty = PlatformCredentials(app_key="k", app_secret="s")
        assert self._make_client(empty).update_product_status("p1", "online") is False

    def test_update_product_status_exception(self, valid_creds):
        mock_request = MagicMock(side_effect=Exception("fail"))
        client = self._make_client(valid_creds, request_mock=mock_request)
        assert client.update_product_status("p1", "online") is False

    # ── get_logistics_info ──────────────────────────────────────

    def test_get_logistics_info_success(self, valid_creds):
        mock_request = MagicMock(return_value={
            "logistics_orders_get_response": {
                "shipments": {"logistics_order": [{"company_name": "ZTO"}]}
            }
        })
        client = self._make_client(valid_creds, request_mock=mock_request)
        r = client.get_logistics_info("o1")
        assert r.get("company_name") == "ZTO"

    def test_get_logistics_info_empty(self, valid_creds):
        mock_request = MagicMock(return_value={
            "logistics_orders_get_response": {
                "shipments": {"logistics_order": []}
            }
        })
        client = self._make_client(valid_creds, request_mock=mock_request)
        r = client.get_logistics_info("o1")
        assert r == {}

    def test_get_logistics_info_not_auth(self, valid_creds):
        empty = PlatformCredentials(app_key="k", app_secret="s")
        assert "error" in self._make_client(empty).get_logistics_info("o1")

    def test_get_logistics_info_error(self, valid_creds):
        """Taobao get_logistics_info catches general Exception"""
        mock_request = MagicMock(side_effect=Exception("log err"))
        client = self._make_client(valid_creds, request_mock=mock_request)
        r = client.get_logistics_info("o1")
        assert "log err" in r.get("error", "")

    # ── exchange_token ──────────────────────────────────────────

    def test_exchange_token_success(self, valid_creds):
        mock_request = MagicMock(return_value={
            "top_auth_token_create_response": {
                "top_auth_token": {
                    "access_token": "at_tb",
                    "refresh_token": "rt_tb",
                    "expires_in": 86400,
                    "taobao_user_id": "12345",
                }
            }
        })
        client = self._make_client(valid_creds, request_mock=mock_request)
        r = client.exchange_token("code")
        assert r["access_token"] == "at_tb"
        assert r["refresh_token"] == "rt_tb"
        assert r["expires_in"] == "86400"
        # Taobao maps taobao_user_id → shop_id
        assert r["shop_id"] == "12345"

    def test_exchange_token_error(self, valid_creds):
        mock_request = MagicMock(side_effect=Exception("X"))
        client = self._make_client(valid_creds, request_mock=mock_request)
        assert "error" in client.exchange_token("code")
