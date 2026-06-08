#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - 淘宝/天猫 API Client
基于淘宝开放平台(TOP)接口实现。

文档: https://open.taobao.com/api
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


class TaobaoShopClient(PlatformAPIClient):
    """淘宝/天猫API客户端
    
    接口规范:
    - 签名方法: MD5 (hmac-md5)
    - 请求方式: POST (application/x-www-form-urlencoded)
    - 公共参数: app_key, method, timestamp, format, v, sign, session
    - 响应格式: {"{method}_response": {...}, "error_response": {...}}
    """
    
    PLATFORM_NAME = "淘宝/天猫"
    API_BASE = "https://eco.taobao.com/router/rest"
    AUTH_URL = "https://oauth.taobao.com/authorize"
    API_VERSION = "2.0"
    
    def __init__(self, credentials: PlatformCredentials):
        super().__init__(credentials)
    
    def _check_business_error(self, result: Dict) -> None:
        """检查淘宝业务错误码"""
        if "error_response" in result:
            err = result["error_response"]
            code = err.get("code", "UNKNOWN")
            msg = err.get("msg", err.get("sub_msg", "Unknown error"))
            if code in (27, 28, 29):
                raise AuthError(f"[{code}] {msg}")
            raise APIError(f"TAOBAO_{code}", msg, result)
    
    def _build_common_params(self, method: str) -> Dict[str, str]:
        """构建淘宝TOP公共参数"""
        from datetime import datetime
        params = {
            "app_key": self.credentials.app_key,
            "method": method,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "format": "json",
            "v": self.API_VERSION,
            "sign_method": "md5",
            "session": self.credentials.access_token,
        }
        params["sign"] = self.sign_md5(params, self.credentials.app_secret)
        return params
    
    def _request_api(self, method: str, biz_params: Optional[Dict] = None) -> Dict:
        """调用淘宝TOP API"""
        params = self._build_common_params(method)
        if biz_params:
            params.update(biz_params)
        return self.request("POST", "", data=params)
    
    # ── Token刷新 ─────────────────────────────────────────────────
    
    def _do_refresh_token(self) -> Optional[str]:
        params = {
            "app_key": self.credentials.app_key,
            "method": "taobao.top.auth.token.refresh",
            "refresh_token": self.credentials.refresh_token,
            "grant_type": "refresh_token",
        }
        params["sign"] = self.sign_md5(params, self.credentials.app_secret)
        result = self.request("POST", "", data=params)
        token_data = result.get("top_auth_token_refresh_response", {}).get("top_auth_token", {})
        return token_data.get("access_token")
    
    # ── 订单接口 ──────────────────────────────────────────────────
    
    def sync_orders(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        page: int = 1,
    ) -> SyncResult:
        """同步订单列表
        
        API: taobao.trades.sold.get
        """
        if not self.is_authenticated:
            return SyncResult(success=False, errors=["Not authenticated"])
        
        biz = {
            "fields": "tid,status,created,payment,orders",
            "page_no": str(page),
            "page_size": str(self.PAGE_SIZE),
        }
        if start_time:
            biz["start_created"] = start_time
        if end_time:
            biz["end_created"] = end_time
        
        try:
            result = self._request_api("taobao.trades.sold.get", biz)
            trades = result.get("trades_sold_get_response", {}).get("trades", {}).get("trade", [])
            total = result.get("trades_sold_get_response", {}).get("total_results", 0)
            return SyncResult(success=True, total=total, data=trades, created=len(trades))
        except Exception as e:
            logger.exception(f"[淘宝] Order sync failed")
            return SyncResult(success=False, errors=[str(e)])
    
    # ── 商品接口 ──────────────────────────────────────────────────
    
    def sync_products(self, page: int = 1) -> SyncResult:
        """同步商品列表
        
        API: taobao.items.onsale.get
        """
        if not self.is_authenticated:
            return SyncResult(success=False, errors=["Not authenticated"])
        
        biz = {
            "fields": "num_iid,title,nick,price,num",
            "page_no": str(page),
            "page_size": str(self.PAGE_SIZE),
        }
        
        try:
            result = self._request_api("taobao.items.onsale.get", biz)
            items = result.get("items_onsale_get_response", {}).get("items", {}).get("item", [])
            total = result.get("items_onsale_get_response", {}).get("total_results", 0)
            return SyncResult(success=True, total=total, data=items, created=len(items))
        except Exception as e:
            logger.exception(f"[淘宝] Product sync failed")
            return SyncResult(success=False, errors=[str(e)])
    
    # ── 库存接口 ──────────────────────────────────────────────────
    
    def sync_inventory(self, product_ids: Optional[List[str]] = None) -> SyncResult:
        """同步库存
        
        API: taobao.skus.custom.get
        """
        if not self.is_authenticated:
            return SyncResult(success=False, errors=["Not authenticated"])
        
        biz = {"fields": "num_iid,sku_id,quantity,price"}
        if product_ids:
            biz["num_iids"] = ",".join(product_ids)
        
        try:
            result = self._request_api("taobao.skus.custom.get", biz)
            skus = result.get("skus_custom_get_response", {}).get("skus", {}).get("sku", [])
            return SyncResult(success=True, total=len(skus), data=skus)
        except Exception as e:
            logger.exception(f"[淘宝] Inventory sync failed")
            return SyncResult(success=False, errors=[str(e)])
    
    # ── 商品上下架 ────────────────────────────────────────────────
    
    def update_product_status(self, product_id: str, status: str) -> bool:
        """更新商品上下架状态
        
        上架: taobao.item.update.listing
        下架: taobao.item.update.delisting
        """
        if not self.is_authenticated:
            return False
        
        try:
            if status == "online":
                method = "taobao.item.update.listing"
                biz = {"num_iid": product_id, "num": "1"}
            else:
                method = "taobao.item.update.delisting"
                biz = {"num_iid": product_id}
            
            result = self._request_api(method, biz)
            return "error_response" not in result
        except Exception as e:
            logger.exception(f"[淘宝] Update product status failed")
            return False
    
    # ── 物流接口 ──────────────────────────────────────────────────
    
    def get_logistics_info(self, order_id: str) -> Dict[str, Any]:
        """查询物流信息
        
        API: taobao.logistics.orders.get
        """
        if not self.is_authenticated:
            return {"error": "Not authenticated"}
        
        try:
            biz = {
                "fields": "tid,company_name,logistics_code,status",
                "tid": order_id,
            }
            result = self._request_api("taobao.logistics.orders.get", biz)
            shipments = result.get("logistics_orders_get_response", {}).get("shipments", {}).get("logistics_order", [])
            return shipments[0] if shipments else {}
        except Exception as e:
            logger.exception(f"[淘宝] Logistics query failed")
            return {"error": str(e)}
    
    # ── OAuth ─────────────────────────────────────────────────────
    
    def exchange_token(self, code: str) -> Dict[str, str]:
        """用授权码换取access_token"""
        params = {
            "app_key": self.credentials.app_key,
            "method": "taobao.top.auth.token.create",
            "code": code,
            "grant_type": "authorization_code",
        }
        params["sign"] = self.sign_md5(params, self.credentials.app_secret)
        
        try:
            result = self.request("POST", "", data=params)
            token_data = result.get("top_auth_token_create_response", {}).get("top_auth_token", {})
            return {
                "access_token": token_data.get("access_token", ""),
                "refresh_token": token_data.get("refresh_token", ""),
                "expires_in": str(token_data.get("expires_in", "")),
                "shop_id": token_data.get("taobao_user_id", ""),
            }
        except Exception as e:
            logger.exception(f"[淘宝] Token exchange failed")
            return {"error": str(e)}
