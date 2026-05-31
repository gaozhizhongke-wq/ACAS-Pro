#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Platform API Factory
平台API客户端工厂，根据平台类型创建对应的API客户端实例。
"""

from typing import Optional

from .platform_api_base import PlatformAPIClient, PlatformCredentials
from .douyin_shop_api import DouyinShopClient
from .kuaishou_shop_api import KuaishouShopClient
from .xiaohongshu_shop_api import XiaohongshuShopClient
from .taobao_shop_api import TaobaoShopClient

from ..core.logging import get_logger

logger = get_logger(__name__)

# 平台枚举到客户端类的映射
_PLATFORM_CLIENT_MAP = {
    "douyin_shop": DouyinShopClient,
    "kuaishou_shop": KuaishouShopClient,
    "xiaohongshu_shop": XiaohongshuShopClient,
    "taobao": TaobaoShopClient,
    "tmall": TaobaoShopClient,  # 天猫共用淘宝API
}


def create_platform_client(
    platform: str,
    credentials: PlatformCredentials,
) -> Optional[PlatformAPIClient]:
    """创建平台API客户端
    
    Args:
        platform: 平台标识（如 douyin_shop, kuaishou_shop）
        credentials: 平台API凭证
        
    Returns:
        PlatformAPIClient 实例，或 None（如果平台不支持）
    """
    client_class = _PLATFORM_CLIENT_MAP.get(platform)
    if not client_class:
        logger.warning(f"[PlatformAPIFactory] Unsupported platform: {platform}")
        return None
    
    client = client_class(credentials)
    logger.info(
        f"[PlatformAPIFactory] Created {client.PLATFORM_NAME} API client "
        f"(configured={client.is_configured}, authenticated={client.is_authenticated})"
    )
    return client


def get_supported_platforms() -> list:
    """获取支持的平台列表"""
    return list(_PLATFORM_CLIENT_MAP.keys())


__all__ = [
    "create_platform_client",
    "get_supported_platforms",
    "PlatformAPIClient",
    "PlatformCredentials",
    "SyncResult",
    "APIError",
    "DouyinShopClient",
    "KuaishouShopClient",
    "XiaohongshuShopClient",
    "TaobaoShopClient",
]
