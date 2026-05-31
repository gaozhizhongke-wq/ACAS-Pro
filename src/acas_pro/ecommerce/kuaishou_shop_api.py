#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - 快手小店 API Client
基于快手开放平台接口实现。

文档: https://open.kuaishou.com/document
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


class KuaishouShopClient(PlatformAPIClient):
    """快手小店API客户端
    
    接口规范:
    - 签名方法: MD5
    - 请求方式: POST JSON
    - 公共参数: app_key, timestamp, sign, method, version
    - 响应格式: {"result": 1, "error_msg": "", "data": {...}}
    """
    
    PLATFORM_NAME = "快手小店"
    API_BASE = "https://openapi.kwaixiaodian.com"
    AUTH_URL = "https://s.kwaixiaodian.com/authorize"
    API_VERSION = "1"
    
    def __init__(self, credentials: PlatformCredentials):
        super().__init__(credentials)
    
    def _check_business_error(self, result: Dict):
        """检查快手业务错误码"""
        error_code = result.get("result", 1)
        if error_code != 1:
            message = result.get("error_msg", "Unknown error")
            if error_code in (401, 403):
                raise AuthError(f"[{error_code}] {message}")
            raise APIError(f"KUAISHOU_{error_code}", message, result)
    
    def _build_common_params(self, method: str) -> Dict[str, str]:
        """构建公共请求参数"""
        params = {
            "app_key": self.credentials.app_key,
            "method": method,
            "timestamp": self.get_timestamp(),
            "version": self.API_VERSION,
            "sign_method": "MD5",
        }
        params["sign"] = self.sign_md5(params, self.credentials.app_secret)
        return params
    
    def _request_api(self, method: str, biz_data: Optional[Dict] = None) -> Dict:
        """调用快手API"""
        common = self._build_common_params(method)
        headers = {"Access-Token": self.credentials.access_token}
        body = {**common, "param_json": biz_data or {}}
        return self.request("POST", "/api", data=body, headers=headers)
    
    # ── Token刷新 ─────────────────────────────────────────────────
    
    def _do_refresh_token(self) -> Optional[str]:
        params = {
            "app_key": self.credentials.app_key,
            "refresh_token": self.credentials.refresh_token,
            "grant_type": "refresh_token",
        }
        params["sign"] = self.sign_md5(params, self.credentials.app_secret)
        result = self.request("POST", "/oauth2/refresh_token", data=params)
        return result.get("data", {}).get("access_token")
    
    # ── 订单接口 ──────────────────────────────────────────────────
    
    def sync_orders(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        page: int = 1,
    ) -> SyncResult:
        """同步订单列表
        
        API: open.order.list
        """
        if not self.is_authenticated:
            return SyncResult(success=False, errors=["Not authenticated"])
        
        biz = {"page_no": page, "page_size": self.PAGE_SIZE}
        if start_time:
            biz["begin_time"] = start_time
        if end_time:
            biz["end_time"] = end_time
        
        try:
            result = self._request_api("open.order.list", biz)
            orders = result.get("data", {}).get("order_list", [])
            total = result.get("data", {}).get("total", 0)
            return SyncResult(success=True, total=total, data=orders, created=len(orders))
        except Exception as e:
            logger.exception(f"[快手小店] Order sync failed")
            return SyncResult(success=False, errors=[str(e)])
    
    # ── 商品接口 ──────────────────────────────────────────────────
    
    def sync_products(self, page: int = 1) -> SyncResult:
        """同步商品列表
        
        API: open.item.list
        """
        if not self.is_authenticated:
            return SyncResult(success=False, errors=["Not authenticated"])
        
        biz = {"page_no": page, "page_size": self.PAGE_SIZE}
        
        try:
            result = self._request_api("open.item.list", biz)
            products = result.get("data", {}).get("item_list", [])
            total = result.get("data", {}).get("total", 0)
            return SyncResult(success=True, total=total, data=products, created=len(products))
        except Exception as e:
            logger.exception(f"[快手小店] Product sync failed")
            return SyncResult(success=False, errors=[str(e)])
    
    # ── 库存接口 ──────────────────────────────────────────────────
    
    def sync_inventory(self, product_ids: Optional[List[str]] = None) -> SyncResult:
        """同步库存
        
        API: open.item.stock.list
        """
        if not self.is_authenticated:
            return SyncResult(success=False, errors=["Not authenticated"])
        
        biz = {}
        if product_ids:
            biz["item_ids"] = product_ids
        
        try:
            result = self._request_api("open.item.stock.list", biz)
            stocks = result.get("data", {}).get("stock_list", [])
            return SyncResult(success=True, total=len(stocks), data=stocks)
        except Exception as e:
            logger.exception(f"[快手小店] Inventory sync failed")
            return SyncResult(success=False, errors=[str(e)])
    
    # ── 商品上下架 ────────────────────────────────────────────────
    
    def update_product_status(self, product_id: str, status: str) -> bool:
        """更新商品上下架状态
        
        API: open.item.updateListingState
        """
        if not self.is_authenticated:
            return False
        
        try:
            biz = {"item_id": product_id, "listing_state": 1 if status == "online" else 0}
            result = self._request_api("open.item.updateListingState", biz)
            return result.get("result", 0) == 1
        except Exception as e:
            logger.exception(f"[快手小店] Update product status failed")
            return False
    
    # ── 物流接口 ──────────────────────────────────────────────────
    
    def get_logistics_info(self, order_id: str) -> Dict[str, Any]:
        """查询物流信息
        
        API: open.logistics.query
        """
        if not self.is_authenticated:
            return {"error": "Not authenticated"}
        
        try:
            result = self._request_api("open.logistics.query", {"order_id": order_id})
            return result.get("data", {})
        except Exception as e:
            logger.exception(f"[快手小店] Logistics query failed")
            return {"error": str(e)}
    
    # ── OAuth ─────────────────────────────────────────────────────
    
    def exchange_token(self, code: str) -> Dict[str, str]:
        """用授权码换取access_token"""
        params = {
            "app_key": self.credentials.app_key,
            "code": code,
            "grant_type": "authorization_code",
        }
        params["sign"] = self.sign_md5(params, self.credentials.app_secret)
        
        try:
            result = self.request("POST", "/oauth2/access_token", data=params)
            token_data = result.get("data", {})
            return {
                "access_token": token_data.get("access_token", ""),
                "refresh_token": token_data.get("refresh_token", ""),
                "expires_in": str(token_data.get("expires_in", "")),
                "shop_id": token_data.get("shop_id", ""),
            }
        except Exception as e:
            logger.exception(f"[快手小店] Token exchange failed")
            return {"error": str(e)}
