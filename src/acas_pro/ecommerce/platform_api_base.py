#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Platform API Base Client
电商平台API客户端基类，提供通用认证、签名、请求重试等功能。
"""

import hashlib
import hmac
import json
import asyncio
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False

from ..core.logging import get_logger
from ..core.config import config

logger = get_logger(__name__)


class APIError(Exception):
    """API调用异常"""
    def __init__(self, code: str, message: str, response: Optional[Dict] = None):
        self.code = code
        self.message = message
        self.response = response or {}
        super().__init__(f"[{code}] {message}")


class RateLimitError(APIError):
    """API限流异常"""
    def __init__(self, retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__("RATE_LIMITED", f"API rate limited, retry after {retry_after}s")


class AuthError(APIError):
    """认证异常"""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__("AUTH_ERROR", message)


@dataclass
class PlatformCredentials:
    """平台API凭证"""
    app_key: str = ""
    app_secret: str = ""
    access_token: str = ""
    refresh_token: str = ""
    token_expires_at: str = ""  # ISO format
    shop_id: str = ""  # 平台侧店铺ID


@dataclass
class SyncResult:
    """同步操作结果"""
    success: bool
    total: int = 0
    created: int = 0
    updated: int = 0
    failed: int = 0
    errors: List[str] = field(default_factory=list)
    data: List[Dict] = field(default_factory=list)


class PlatformAPIClient(ABC):
    """电商平台API客户端基类
    
    提供以下通用能力：
    1. HTTP 请求（GET/POST）带自动重试
    2. 签名生成（HMAC-SHA256 / MD5）
    3. Token 管理（自动刷新）
    4. 限流处理
    5. 统一日志
    """
    
    # 子类必须定义
    PLATFORM_NAME: str = ""
    API_BASE: str = ""
    AUTH_URL: str = ""
    
    # 请求配置
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # 秒
    REQUEST_TIMEOUT = 30  # 秒
    PAGE_SIZE = 50
    
    def __init__(self, credentials: PlatformCredentials):
        self.credentials = credentials
        self._session = None
    
    @property
    def is_configured(self) -> bool:
        """检查是否已配置API凭证"""
        return bool(self.credentials.app_key and self.credentials.app_secret)
    
    @property
    def is_authenticated(self) -> bool:
        """检查是否已认证"""
        return bool(self.credentials.access_token)
    
    # ── 签名方法 ──────────────────────────────────────────────────
    
    def sign_md5(self, params: Dict[str, Any], secret: str) -> str:
        """MD5签名（淘宝/天猫/京东通用）
        
        规则: 将所有参数按key排序拼接为 key1value1key2value2... + secret，取MD5
        """
        sorted_keys = sorted(params.keys())
        sign_str = secret + ''.join(f'{k}{params[k]}' for k in sorted_keys) + secret
        return hashlib.md5(sign_str.encode('utf-8')).hexdigest().upper()
    
    def sign_hmac_sha256(self, params: Dict[str, Any], secret: str) -> str:
        """HMAC-SHA256签名（抖音小店通用）"""
        sorted_keys = sorted(params.keys())
        sign_str = '&'.join(f'{k}={params[k]}' for k in sorted_keys)
        return hmac.new(
            secret.encode('utf-8'),
            sign_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    # ── 通用HTTP请求 ──────────────────────────────────────────────
    
    def _get_session(self):
        """获取HTTP session（延迟初始化）"""
        if self._session is None:
            import requests
            self._session = requests.Session()
            self._session.headers.update({
                'Content-Type': 'application/json',
                'User-Agent': 'ACAS-Pro/4.0.0',
            })
        return self._session

    def _get_async_client(self):
        """获取异步HTTP client（延迟初始化）"""
        if self._async_client is None:
            if not _HAS_HTTPX:
                raise RuntimeError("httpx not installed")
            self._async_client = httpx.AsyncClient(
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'ACAS-Pro/4.0.0',
                },
                timeout=self.REQUEST_TIMEOUT,
            )
        return self._async_client
    
    def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """通用API请求，带自动重试
        
        Args:
            method: GET / POST
            path: API路径（相对于API_BASE）
            params: URL查询参数
            data: POST body
            headers: 额外请求头
            timeout: 超时秒数
            
        Returns:
            API响应JSON
            
        Raises:
            APIError: API错误
            RateLimitError: 限流
            AuthError: 认证失败
        """
        url = f"{self.API_BASE}{path}"
        timeout = timeout or self.REQUEST_TIMEOUT
        
        last_error = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                session = self._get_session()
                
                if method.upper() == 'GET':
                    resp = session.get(
                        url,
                        params=params,
                        headers=headers,
                        timeout=timeout,
                    )
                else:
                    resp = session.post(
                        url,
                        params=params,
                        json=data,
                        headers=headers,
                        timeout=timeout,
                    )
                
                # 处理HTTP状态码
                if resp.status_code == 401:
                    raise AuthError(f"Token expired or invalid: {resp.text[:200]}")
                elif resp.status_code == 429:
                    retry_after = int(resp.headers.get('Retry-After', 60))
                    raise RateLimitError(retry_after)
                elif resp.status_code >= 500:
                    raise APIError(
                        f"SERVER_{resp.status_code}",
                        f"Server error: {resp.text[:200]}"
                    )
                elif resp.status_code >= 400:
                    raise APIError(
                        f"CLIENT_{resp.status_code}",
                        f"Client error: {resp.text[:200]}"
                    )
                
                result = resp.json()
                
                # 子类可覆盖此方法检查业务级错误码
                self._check_business_error(result)
                
                return result
                
            except (APIError, AuthError, RateLimitError):
                raise
            except Exception as e:
                last_error = e
                if attempt < self.MAX_RETRIES:
                    wait = self.RETRY_DELAY * attempt
                    logger.warning(
                        f"[{self.PLATFORM_NAME}] Request failed (attempt {attempt}/{self.MAX_RETRIES}), "
                        f"retrying in {wait}s: {e}"
                    )
                    time.sleep(wait)
                else:
                    logger.error(
                        f"[{self.PLATFORM_NAME}] Request failed after {self.MAX_RETRIES} attempts: {e}"
                    )
        
        raise APIError("REQUEST_FAILED", f"Request failed: {last_error}")
    
    async def request_async(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        retry: bool = True,
        token_refresh: bool = True,
    ) -> Dict:
        """异步HTTP请求（requests封装，支持重试和token刷新）"""
        last_error = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                return await self._do_request_async(method, endpoint, params, data)
            except UnauthorizedError:
                logger.error(f"[{self.PLATFORM_NAME}] Unauthorized (401)")
                if retry and token_refresh and attempt == 1:
                    if not self.refresh_access_token():
                        raise
                else:
                    raise
            except (RateLimitError, APIError) as e:
                last_error = e
                wait = min(self.RETRY_BASE_DELAY * (2 ** (attempt - 1)), self.RETRY_MAX_DELAY)
                if attempt < self.MAX_RETRIES:
                    logger.warning(
                        f"[{self.PLATFORM_NAME}] Request failed (attempt {attempt}/{self.MAX_RETRIES}), "
                        f"retrying in {wait}s: {e}"
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.error(
                        f"[{self.PLATFORM_NAME}] Request failed after {self.MAX_RETRIES} attempts: {e}"
                    )
            except Exception as e:
                last_error = e
                if retry and attempt < self.MAX_RETRIES:
                    wait = min(self.RETRY_BASE_DELAY * (2 ** (attempt - 1)), self.RETRY_MAX_DELAY)
                    logger.warning(
                        f"[{self.PLATFORM_NAME}] Request failed (attempt {attempt}/{self.MAX_RETRIES}), "
                        f"retrying in {wait}s: {e}"
                    )
                    await asyncio.sleep(wait)
                else:
                    raise
        raise APIError("REQUEST_FAILED", f"Request failed: {last_error}")

    async def _do_request_async(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
    ) -> Dict:
        """执行实际HTTP请求（异步版本，使用httpx）"""
        if not _HAS_HTTPX:
            raise RuntimeError("httpx not installed")
        
        url = f"{self.API_BASE}{endpoint}"
        client = self._get_async_client()
        
        try:
            if method.upper() == 'GET':
                resp = await client.get(url, params=params)
            else:
                resp = await client.post(url, params=params, json=data)
            
            # 处理HTTP状态码
            if resp.status_code == 401:
                raise AuthError(f"Token expired or invalid: {resp.text[:200]}")
            elif resp.status_code == 429:
                retry_after = int(resp.headers.get('Retry-After', 60))
                raise RateLimitError(retry_after)
            elif resp.status_code >= 500:
                raise APIError(
                    f"SERVER_{resp.status_code}",
                    f"Server error: {resp.text[:200]}"
                )
            elif resp.status_code >= 400:
                raise APIError(
                    f"CLIENT_{resp.status_code}",
                    f"Client error: {resp.text[:200]}"
                )
            
            result = resp.json()
            
            # 子类可覆盖此方法检查业务级错误码
            self._check_business_error(result)
            
            return result
            
        except (APIError, AuthError, RateLimitError):
            raise
        except Exception as e:
            raise APIError("REQUEST_FAILED", f"Async request failed: {e}")


    def _check_business_error(self, result: Dict):
        """检查业务级错误码，子类可覆盖"""
        pass
    
    # ── Token管理 ─────────────────────────────────────────────────
    
    def refresh_access_token(self) -> bool:
        """刷新access_token，子类实现具体逻辑"""
        if not self.credentials.refresh_token:
            logger.warning(f"[{self.PLATFORM_NAME}] No refresh_token available")
            return False
        try:
            new_token = self._do_refresh_token()
            if new_token:
                self.credentials.access_token = new_token
                logger.info(f"[{self.PLATFORM_NAME}] Token refreshed successfully")
                return True
        except Exception as e:
            logger.exception(f"[{self.PLATFORM_NAME}] Token refresh failed")
        return False
    
    def _do_refresh_token(self) -> Optional[str]:
        """子类实现token刷新逻辑"""
        raise NotImplementedError(f"{self.PLATFORM_NAME} token refresh not implemented")
    
    # ── 抽象方法：子类必须实现 ─────────────────────────────────────
    
    @abstractmethod
    def sync_orders(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        page: int = 1,
    ) -> SyncResult:
        """同步订单"""
        ...
    
    @abstractmethod
    def sync_products(
        self,
        page: int = 1,
    ) -> SyncResult:
        """同步商品"""
        ...
    
    @abstractmethod
    def sync_inventory(
        self,
        product_ids: Optional[List[str]] = None,
    ) -> SyncResult:
        """同步库存"""
        ...
    
    @abstractmethod
    def update_product_status(
        self,
        product_id: str,
        status: str,
    ) -> bool:
        """更新商品上下架状态"""
        ...
    
    @abstractmethod
    def get_logistics_info(
        self,
        order_id: str,
    ) -> Dict[str, Any]:
        """查询物流信息"""
        ...
    
    # ── 通用工具方法 ──────────────────────────────────────────────
    
    @staticmethod
    def generate_nonce() -> str:
        """生成随机字符串"""
        return uuid.uuid4().hex[:16]
    
    @staticmethod
    def get_timestamp() -> str:
        """获取当前时间戳（秒）"""
        return str(int(time.time()))
