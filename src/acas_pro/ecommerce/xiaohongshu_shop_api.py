#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - 小红书店铺 API Client
基于小红书开放平台接口实现。

文档: https://open.xiaohongshu.com
"""

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


class XiaohongshuShopClient(PlatformAPIClient):
    """小红书店铺API客户端

    接口规范:
    - 签名方法: HMAC-SHA256
    - 请求方式: POST JSON
    - 公共参数: appId, timestamp, sign, version
    - 响应格式: {"success": true, "data": {...}, "errorMsg": ""}
    """

    PLATFORM_NAME = "小红书店铺"
    API_BASE = "https://ark.xiaohongshu.com/api"
    AUTH_URL = "https://ark.xiaohongshu.com/authorize"
    API_VERSION = "1"

    def __init__(self, credentials: PlatformCredentials):
        super().__init__(credentials)

    def _check_business_error(self, result: Dict) -> None:
        """检查小红书业务错误码"""
        if not result.get("success", True):
            error_code = result.get("errorCode", "UNKNOWN")
            message = result.get("errorMsg", "Unknown error")
            if error_code in ("UNAUTHORIZED", "TOKEN_EXPIRED"):
                raise AuthError(f"[{error_code}] {message}")
            raise APIError(f"XHS_{error_code}", message, result)

    def _build_common_params(self, method: str) -> Dict[str, str]:
        """构建公共请求参数"""
        params = {
            "appId": self.credentials.app_key,
            "timestamp": self.get_timestamp(),
            "version": self.API_VERSION,
        }
        params["sign"] = self.sign_hmac_sha256(params, self.credentials.app_secret)
        return params

    def _request_api(self, path: str, biz_data: Optional[Dict] = None) -> Dict:
        """调用小红书API"""
        common = self._build_common_params(path)
        headers = {"Authorization": f"Bearer {self.credentials.access_token}"}
        body = {**common, **(biz_data or {})}
        return self.request("POST", path, data=body, headers=headers)

    # ── Token刷新 ─────────────────────────────────────────────────

    def _do_refresh_token(self) -> Optional[str]:
        params = {
            "appId": self.credentials.app_key,
            "refreshToken": self.credentials.refresh_token,
        }
        result = self.request("POST", "/auth/refreshToken", data=params)
        return result.get("data", {}).get("accessToken")

    # ── 订单接口 ──────────────────────────────────────────────────

    def sync_orders(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        page: int = 1,
    ) -> SyncResult:
        """同步订单列表

        API: /order/list
        """
        if not self.is_authenticated:
            return SyncResult(success=False, errors=["Not authenticated"])

        biz = {"pageNo": page, "pageSize": self.PAGE_SIZE}
        if start_time:
            biz["startTime"] = start_time
        if end_time:
            biz["endTime"] = end_time

        try:
            result = self._request_api("/order/list", biz)
            orders = result.get("data", {}).get("orderList", [])
            total = result.get("data", {}).get("total", 0)
            return SyncResult(
                success=True, total=total, data=orders, created=len(orders)
            )
        except Exception as e:
            logger.exception("[小红书] Order sync failed")
            return SyncResult(success=False, errors=[str(e)])

    # ── 商品接口 ──────────────────────────────────────────────────

    def sync_products(self, page: int = 1) -> SyncResult:
        """同步商品列表

        API: /product/list
        """
        if not self.is_authenticated:
            return SyncResult(success=False, errors=["Not authenticated"])

        biz = {"pageNo": page, "pageSize": self.PAGE_SIZE}

        try:
            result = self._request_api("/product/list", biz)
            products = result.get("data", {}).get("productList", [])
            total = result.get("data", {}).get("total", 0)
            return SyncResult(
                success=True, total=total, data=products, created=len(products)
            )
        except Exception as e:
            logger.exception("[小红书] Product sync failed")
            return SyncResult(success=False, errors=[str(e)])

    # ── 库存接口 ──────────────────────────────────────────────────

    def sync_inventory(self, product_ids: Optional[List[str]] = None) -> SyncResult:
        """同步库存

        API: /product/stock/list
        """
        if not self.is_authenticated:
            return SyncResult(success=False, errors=["Not authenticated"])

        biz = {}
        if product_ids:
            biz["productIds"] = product_ids

        try:
            result = self._request_api("/product/stock/list", biz)
            stocks = result.get("data", {}).get("stockList", [])
            return SyncResult(success=True, total=len(stocks), data=stocks)
        except Exception as e:
            logger.exception("[小红书] Inventory sync failed")
            return SyncResult(success=False, errors=[str(e)])

    # ── 商品上下架 ────────────────────────────────────────────────

    def update_product_status(self, product_id: str, status: str) -> bool:
        """更新商品上下架状态

        API: /product/updateStatus
        """
        if not self.is_authenticated:
            return False

        try:
            biz = {"productId": product_id, "status": status}
            result = self._request_api("/product/updateStatus", biz)
            return result.get("success", False)
        except Exception:
            logger.exception("[小红书] Update product status failed")
            return False

    # ── 物流接口 ──────────────────────────────────────────────────

    def get_logistics_info(self, order_id: str) -> Dict[str, Any]:
        """查询物流信息

        API: /logistics/query
        """
        if not self.is_authenticated:
            return {"error": "Not authenticated"}

        try:
            result = self._request_api("/logistics/query", {"orderId": order_id})
            return result.get("data", {})
        except Exception as e:
            logger.exception("[小红书] Logistics query failed")
            return {"error": str(e)}

    # ── OAuth ─────────────────────────────────────────────────────

    def exchange_token(self, code: str) -> Dict[str, str]:
        """用授权码换取access_token"""
        params = {
            "appId": self.credentials.app_key,
            "code": code,
            "grantType": "authorization_code",
        }
        params["sign"] = self.sign_hmac_sha256(params, self.credentials.app_secret)

        try:
            result = self.request("POST", "/auth/token", data=params)
            token_data = result.get("data", {})
            return {
                "access_token": token_data.get("accessToken", ""),
                "refresh_token": token_data.get("refreshToken", ""),
                "expires_in": str(token_data.get("expiresIn", "")),
                "shop_id": token_data.get("shopId", ""),
            }
        except Exception as e:
            logger.exception("[小红书] Token exchange failed")
            return {"error": str(e)}
