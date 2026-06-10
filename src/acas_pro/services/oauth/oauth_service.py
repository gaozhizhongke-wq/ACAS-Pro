# -*- coding: utf-8 -*-
"""
ACAS Pro - OAuth Service
Third-party login integration (QQ/WeChat)
"""

import json
import urllib.request
import urllib.parse
import urllib.error
import secrets
import logging
try:
    import aiohttp
    _HAS_AIOHTTP = True
except ImportError:
    _HAS_AIOHTTP = False
import asyncio
from typing import Optional, Dict, Tuple, NamedTuple
from dataclasses import dataclass
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


@dataclass
class OAuthUserInfo:
    """OAuth用户信息"""
    provider: str
    openid: str
    nickname: str
    avatar: str
    email: Optional[str] = None


class TokenResponse(NamedTuple):
    """OAuth token response"""
    access_token: str
    expires_in: int
    refresh_token: Optional[str] = None
    openid: Optional[str] = None
    scope: Optional[str] = None


class OAuthProvider(ABC):
    """OAuth提供者基类"""
    
    @abstractmethod
    def get_authorization_url(self, state: str) -> str:
        """获取授权URL"""
        pass
    
    @abstractmethod
    def get_token_response(self, code: str) -> Optional[TokenResponse]:
        """通过授权码获取完整token响应"""
        pass
    
    @abstractmethod
    def get_user_info(self, access_token: str, openid: str) -> Optional[OAuthUserInfo]:
        """获取用户信息"""
        pass


class QQOAuth(OAuthProvider):
    """QQ OAuth"""
    
    @property
    def APP_ID(self): return self._cfg.qq_app_id
    @property
    def APP_KEY(self): return self._cfg.qq_app_key
    @property
    def REDIRECT_URI(self): return self._cfg.qq_redirect_uri

    def __init__(self, cfg): self._cfg = cfg
    
    AUTH_URL = "https://graph.qq.com/oauth2.0/authorize"
    TOKEN_URL = "https://graph.qq.com/oauth2.0/token"  # nosec B313  # OAuth endpoint URL, not a password
    OPENID_URL = "https://graph.qq.com/oauth2.0/me"  # nosec B313  # OAuth endpoint URL, not a password
    USER_INFO_URL = "https://graph.qq.com/user/get_user_info"
    
    def get_authorization_url(self, state: str) -> str:
        params = {
            "response_type": "code",
            "client_id": self.APP_ID,
            "redirect_uri": self.REDIRECT_URI,
            "state": state,
            "scope": "get_user_info"
        }
        return f"{self.AUTH_URL}?{urllib.parse.urlencode(params)}"
    
    def get_token_response(self, code: str) -> Optional[TokenResponse]:
        params = {
            "grant_type": "authorization_code",
            "client_id": self.APP_ID,
            "client_secret": self.APP_KEY,
            "code": code,
            "redirect_uri": self.REDIRECT_URI
        }
        try:
            url = f"{self.TOKEN_URL}?{urllib.parse.urlencode(params)}"
            with urllib.request.urlopen(url, timeout=10) as response:  # nosec B310  # hardcoded platform URL
                data = urllib.parse.parse_qs(response.read().decode())
                access_token = data.get("access_token", [None])[0]
                if not access_token:
                    return None
                return TokenResponse(
                    access_token=access_token,
                    expires_in=int(data.get("expires_in", ["7200"])[0]),
                    refresh_token=data.get("refresh_token", [None])[0]
                )
        except urllib.error.HTTPError as e:
            logger.error(f"QQ OAuth HTTP error: {e.code} - {e.reason}")
            return None
        except urllib.error.URLError as e:
            logger.error(f"QQ OAuth URL error: {e.reason}")
            return None
        except Exception as e:
            logger.error(f"QQ OAuth error: {e}")
            return None
    
    def get_openid(self, access_token: str) -> Optional[str]:
        """获取QQ的openid"""
        try:
            url = f"{self.OPENID_URL}?access_token={access_token}"
            with urllib.request.urlopen(url, timeout=10) as response:  # nosec B310  # hardcoded platform URL
                text = response.read().decode()
                # Parse JSONP response
                if "callback" in text:
                    text = text[text.index("(") + 1:text.rindex(")")]
                data = json.loads(text)
                return data.get("openid")
        except Exception as e:
            logger.error(f"QQ openid error: {e}")
            return None
    
    def get_user_info(self, access_token: str, openid: str) -> Optional[OAuthUserInfo]:
        if not openid:
            # Get openid first
            openid = self.get_openid(access_token)
            if not openid:
                return None
        
        try:
            params = {
                "access_token": access_token,
                "oauth_consumer_key": self.APP_ID,
                "openid": openid
            }
            url = f"{self.USER_INFO_URL}?{urllib.parse.urlencode(params)}"
            with urllib.request.urlopen(url, timeout=10) as response:  # nosec B310  # hardcoded platform URL
                data = json.loads(response.read().decode())
            
            return OAuthUserInfo(
                provider="qq",
                openid=openid,
                nickname=data.get("nickname", ""),
                avatar=data.get("figureurl_qq_2", data.get("figureurl", "")),
                email=None
            )
        except Exception as e:
            logger.error(f"QQ user info error: {e}")
            return None
    
    async def get_token_response_async(self, code: str) -> Optional[TokenResponse]:
        """Get token (async)"""
        params = {
            "grant_type": "authorization_code",
            "client_id": self.APP_ID,
            "client_secret": self.APP_KEY,
            "code": code,
            "redirect_uri": self.REDIRECT_URI
        }
        try:
            url = f"{self.TOKEN_URL}?{urllib.parse.urlencode(params)}"
            if _HAS_AIOHTTP:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=10) as resp:
                        data = urllib.parse.parse_qs(await resp.text())
            else:
                data = await asyncio.to_thread(self._blocking_get_token, params)
            
            access_token = data.get("access_token", [None])[0]
            if not access_token:
                return None
            return TokenResponse(
                access_token=access_token,
                expires_in=int(data.get("expires_in", ["7200"])[0]),
                refresh_token=data.get("refresh_token", [None])[0]
            )
        except Exception as e:
            logger.error(f"QQ OAuth async error: {e}")
            return None
    
    def _blocking_get_token(self, params: dict) -> dict:
        """Blocking helper for token (used as fallback)"""
        url = f"{self.TOKEN_URL}?{urllib.parse.urlencode(params)}"
        with urllib.request.urlopen(url, timeout=10) as response:  # nosec B310  # hardcoded platform URL
            return urllib.parse.parse_qs(response.read().decode())


class WeChatOAuth(OAuthProvider):
    """微信 OAuth"""
    
    @property
    def APP_ID(self): return self._cfg.wechat_app_id
    @property
    def APP_SECRET(self): return self._cfg.wechat_app_secret
    @property
    def REDIRECT_URI(self): return self._cfg.wechat_redirect_uri

    def __init__(self, cfg): self._cfg = cfg
    
    AUTH_URL = "https://open.weixin.qq.com/connect/qrconnect"
    TOKEN_URL = "https://api.weixin.qq.com/sns/oauth2/access_token"
    REFRESH_URL = "https://api.weixin.qq.com/sns/oauth2/refresh_token"  # nosec B313  # OAuth endpoint URL, not a password
    USER_INFO_URL = "https://api.weixin.qq.com/sns/userinfo"
    
    def get_authorization_url(self, state: str) -> str:
        params = {
            "appid": self.APP_ID,
            "redirect_uri": self.REDIRECT_URI,
            "response_type": "code",
            "scope": "snsapi_login",
            "state": state
        }
        return f"{self.AUTH_URL}?{urllib.parse.urlencode(params)}#wechat_redirect"
    
    def get_token_response(self, code: str) -> Optional[TokenResponse]:
        """
        获取微信token响应
        微信的token响应包含: access_token, expires_in, refresh_token, openid, scope
        """
        params = {
            "appid": self.APP_ID,
            "secret": self.APP_SECRET,
            "code": code,
            "grant_type": "authorization_code"
        }
        try:
            url = f"{self.TOKEN_URL}?{urllib.parse.urlencode(params)}"
            with urllib.request.urlopen(url, timeout=10) as response:  # nosec B310  # hardcoded platform URL
                data = json.loads(response.read().decode())
                
            # Check for error response from WeChat
            if "errcode" in data and data["errcode"] != 0:
                logger.error(f"WeChat token error: {data.get('errmsg', 'unknown')}")
                return None
            
            access_token = data.get("access_token")
            if not access_token:
                logger.error("WeChat token response missing access_token")
                return None
            
            return TokenResponse(
                access_token=access_token,
                expires_in=data.get("expires_in", 7200),
                refresh_token=data.get("refresh_token"),
                openid=data.get("openid"),  # Critical: WeChat returns openid here!
                scope=data.get("scope")
            )
        except urllib.error.HTTPError as e:
            logger.error(f"WeChat OAuth HTTP error: {e.code} - {e.reason}")
            return None
        except urllib.error.URLError as e:
            logger.error(f"WeChat OAuth URL error: {e.reason}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"WeChat OAuth JSON decode error: {e}")
            return None
        except Exception as e:
            logger.error(f"WeChat OAuth error: {e}")
            return None
    
    def get_user_info(self, access_token: str, openid: str) -> Optional[OAuthUserInfo]:
        """
        获取微信用户信息
        必须传入从token响应中获取的openid
        """
        if not openid:
            logger.error("WeChat get_user_info called without openid")
            return None
        
        try:
            params = {
                "access_token": access_token,
                "openid": openid  # Use the openid from token response
            }
            url = f"{self.USER_INFO_URL}?{urllib.parse.urlencode(params)}"
            with urllib.request.urlopen(url, timeout=10) as response:  # nosec B310  # hardcoded platform URL
                data = json.loads(response.read().decode())
            
            # Check for WeChat API errors
            if "errcode" in data and data["errcode"] != 0:
                logger.error(f"WeChat userinfo error: {data.get('errmsg', 'unknown')}")
                return None
            
            # Use unionid if available (for cross-app linking), fallback to openid
            user_openid = data.get("unionid") or data.get("openid", openid)
            
            return OAuthUserInfo(
                provider="wechat",
                openid=user_openid,
                nickname=data.get("nickname", ""),
                avatar=data.get("headimgurl", ""),
                email=None
            )
        except urllib.error.HTTPError as e:
            logger.error(f"WeChat user info HTTP error: {e.code} - {e.reason}")
            return None
        except urllib.error.URLError as e:
            logger.error(f"WeChat user info URL error: {e.reason}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"WeChat user info JSON decode error: {e}")
            return None
        except Exception as e:
            logger.error(f"WeChat user info error: {e}")
            return None


class OAuthService:
    """OAuth服务管理"""
    
    def __init__(self, oauth_config):
        self._providers: Dict[str, OAuthProvider] = {
            "qq": QQOAuth(oauth_config),
            "wechat": WeChatOAuth(oauth_config)
        }
    
    def get_authorization_url(self, provider: str) -> Tuple[str, str]:
        """获取授权URL和state"""
        provider_obj = self._providers.get(provider)
        if not provider_obj:
            return "", ""
        
        state = secrets.token_urlsafe(16)
        url = provider_obj.get_authorization_url(state)
        return url, state
    
    def handle_callback(self, provider: str, code: str) -> Optional[OAuthUserInfo]:
        """
        处理授权回调
        
        微信流程:
        1. get_token_response(code) -> TokenResponse(access_token, openid, ...)
        2. get_user_info(access_token, openid) -> OAuthUserInfo
        
        返回完整的用户信息
        """
        provider_obj = self._providers.get(provider)
        if not provider_obj:
            logger.error(f"Unknown OAuth provider: {provider}")
            return None
        
        # Step 1: Get token response (contains openid for WeChat)
        token_resp = provider_obj.get_token_response(code)
        if not token_resp:
            logger.error(f"Failed to get token for {provider}")
            return None
        
        # Step 2: Get user info using access_token and openid from token response
        user_info = provider_obj.get_user_info(token_resp.access_token, token_resp.openid)
        if not user_info:
            logger.error(f"Failed to get user info for {provider}")
            return None
        
        logger.info(f"OAuth login success: {provider}/{user_info.openid}")
        return user_info
    
    def refresh_token(self, provider: str, refresh_token: str) -> Optional[TokenResponse]:
        """刷新access_token"""
        if provider != "wechat":
            logger.warning(f"Token refresh not supported for {provider}")
            return None
        
        try:
            params = {
                "appid": self._cfg.wechat_app_id,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token
            }
            url = f"{WeChatOAuth.REFRESH_URL}?{urllib.parse.urlencode(params)}"
            with urllib.request.urlopen(url, timeout=10) as response:  # nosec B310  # hardcoded platform URL
                data = json.loads(response.read().decode())
            
            if "errcode" in data and data["errcode"] != 0:
                logger.error(f"WeChat refresh error: {data.get('errmsg')}")
                return None
            
            return TokenResponse(
                access_token=data.get("access_token"),
                expires_in=data.get("expires_in", 7200),
                refresh_token=data.get("refresh_token"),
                openid=data.get("openid"),
                scope=data.get("scope")
            )
        except Exception as e:
            logger.error(f"WeChat token refresh error: {e}")
            return None
    
    def available_providers(self) -> list:
        """获取可用的OAuth提供者"""
        return list(self._providers.keys())
