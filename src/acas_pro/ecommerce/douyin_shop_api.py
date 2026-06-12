#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - 抖音小店 API Client
基于抖音开放平台 v2 接口实现。

文档: https://op.jinritemai.com/docs
"""

import json
import sqlite3
from typing import Any, Dict, List, Optional
from .platform_api_base import (
    PlatformAPIClient,
    PlatformCredentials,
    SyncResult,
    APIError,
    AuthError,
)

from ..core.logging import get_logger

logger = get_logger(__name__)


class DouyinShopClient(PlatformAPIClient):
    """抖音小店API客户端

    接口规范:
    - 签名方法: HMAC-SHA256
    - 请求方式: POST JSON
    - 公共参数: app_key, timestamp, sign, method, v
    - 响应格式: {"err_no": 0, "message": "success", "data": {...}}
    """

    PLATFORM_NAME = "抖音小店"
    API_BASE = "https://openapi-fxg.jinritemai.com"
    AUTH_URL = "https://fxg.jinritemai.com/open/authorize"
    API_VERSION = "2"

    def __init__(self, credentials: PlatformCredentials):
        super().__init__(credentials)

    def _check_business_error(self, result: Dict) -> None:
        """检查抖音业务错误码"""
        err_no = result.get("err_no", 0)
        if err_no != 0:
            message = result.get("message", "Unknown error")
            if err_no in (40001, 40002, 40003):
                raise AuthError(f"[{err_no}] {message}")
            raise APIError(f"DOUYIN_{err_no}", message, result)

    def _build_common_params(self, method: str) -> Dict[str, str]:
        """构建公共请求参数"""
        timestamp = self.get_timestamp()
        params = {
            "app_key": self.credentials.app_key,
            "method": method,
            "timestamp": timestamp,
            "v": self.API_VERSION,
            "sign_method": "hmac-sha256",
        }
        params["sign"] = self.sign_hmac_sha256(params, self.credentials.app_secret)
        return params

    def _request_api(self, method: str, biz_data: Optional[Dict] = None) -> Dict:
        """调用抖音API"""
        common = self._build_common_params(method)
        headers = {"Access-Token": self.credentials.access_token}

        body = {
            **common,
            "param_json": json.dumps(biz_data or {}),
        }

        return self.request("POST", "/api", params=body, headers=headers)

    # ── Token刷新 ─────────────────────────────────────────────────

    def _do_refresh_token(self) -> Optional[str]:
        """刷新抖音access_token

        API: /oauth/refresh_token
        """
        params = {
            "app_key": self.credentials.app_key,
            "refresh_token": self.credentials.refresh_token,
            "grant_type": "refresh_token",
        }
        params["sign"] = self.sign_hmac_sha256(params, self.credentials.app_secret)
        result = self.request("POST", "/oauth/refresh_token", data=params)
        return result.get("data", {}).get("access_token")

    # ── 订单接口 ──────────────────────────────────────────────────

    def sync_orders(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        page: int = 1,
    ) -> SyncResult:
        """同步订单列表

        API: order/list (method: order.list)
        """
        if not self.is_authenticated:
            return SyncResult(success=False, errors=["Not authenticated"])

        biz = {
            "page": page,
            "size": self.PAGE_SIZE,
        }
        if start_time:
            biz["start_time"] = start_time
        if end_time:
            biz["end_time"] = end_time

        try:
            result = self._request_api("order.list", biz)
            orders = result.get("data", {}).get("list", [])
            total = result.get("data", {}).get("total", 0)

            return SyncResult(
                success=True,
                total=total,
                data=orders,
                created=len(orders),
            )
        except (sqlite3.Error, ValueError, RuntimeError, json.JSONDecodeError) as e:
            logger.exception("[抖音小店] Order sync failed")
            return SyncResult(success=False, errors=[str(e)])

    # ── 商品接口 ──────────────────────────────────────────────────

    def sync_products(
        self,
        page: int = 1,
    ) -> SyncResult:
        """同步商品列表

        API: product/list (method: product.list)
        """
        if not self.is_authenticated:
            return SyncResult(success=False, errors=["Not authenticated"])

        biz = {
            "page": page,
            "size": self.PAGE_SIZE,
        }

        try:
            result = self._request_api("product.list", biz)
            products = result.get("data", {}).get("list", [])
            total = result.get("data", {}).get("total", 0)

            return SyncResult(
                success=True,
                total=total,
                data=products,
                created=len(products),
            )
        except (sqlite3.Error, ValueError, RuntimeError, json.JSONDecodeError) as e:
            logger.exception("[抖音小店] Product sync failed")
            return SyncResult(success=False, errors=[str(e)])

    # ── 库存接口 ──────────────────────────────────────────────────

    def sync_inventory(
        self,
        product_ids: Optional[List[str]] = None,
    ) -> SyncResult:
        """同步库存

        API: product/stock (method: product.stock)
        """
        if not self.is_authenticated:
            return SyncResult(success=False, errors=["Not authenticated"])

        biz = {}
        if product_ids:
            biz["product_ids"] = product_ids

        try:
            result = self._request_api("product.stock", biz)
            stocks = result.get("data", {}).get("list", [])

            return SyncResult(
                success=True,
                total=len(stocks),
                data=stocks,
            )
        except (sqlite3.Error, ValueError, RuntimeError, json.JSONDecodeError) as e:
            logger.exception("[抖音小店] Inventory sync failed")
            return SyncResult(success=False, errors=[str(e)])

    # ── 商品上下架 ────────────────────────────────────────────────

    def update_product_status(self, product_id: str, status: str) -> bool:
        """更新商品上下架状态

        API: product/setStatus (method: product.setStatus)
        status: "online" / "offline"
        """
        if not self.is_authenticated:
            return False

        try:
            biz = {
                "product_id": product_id,
                "status": 1 if status == "online" else 0,
            }
            result = self._request_api("product.setStatus", biz)
            return result.get("err_no", -1) == 0
        except (sqlite3.Error, ValueError, RuntimeError, json.JSONDecodeError):
            logger.exception("[抖音小店] Update product status failed")
            return False

    # ── 物流接口 ──────────────────────────────────────────────────

    def get_logistics_info(self, order_id: str) -> Dict[str, Any]:
        """查询物流信息

        API: logistics/byOrder (method: logistics.byOrder)
        """
        if not self.is_authenticated:
            return {"error": "Not authenticated"}

        try:
            result = self._request_api("logistics.byOrder", {"order_id": order_id})
            return result.get("data", {})
        except (sqlite3.Error, ValueError, RuntimeError, json.JSONDecodeError) as e:
            logger.exception("[抖音小店] Logistics query failed")
            return {"error": str(e)}

    # ── OAuth回调 ─────────────────────────────────────────────────

    def exchange_token(self, code: str) -> Dict[str, str]:
        """用授权码换取access_token

        API: /oauth/access_token
        """
        params = {
            "app_key": self.credentials.app_key,
            "code": code,
            "grant_type": "authorization_code",
        }
        params["sign"] = self.sign_hmac_sha256(params, self.credentials.app_secret)

        try:
            result = self.request("POST", "/oauth/access_token", data=params)
            token_data = result.get("data", {})
            return {
                "access_token": token_data.get("access_token", ""),
                "refresh_token": token_data.get("refresh_token", ""),
                "expires_in": str(token_data.get("expires_in", "")),
                "shop_id": token_data.get("shop_id", ""),
            }
        except (sqlite3.Error, ValueError, RuntimeError, json.JSONDecodeError) as e:
            logger.exception("[抖音小店] Token exchange failed")
            return {"error": str(e)}


