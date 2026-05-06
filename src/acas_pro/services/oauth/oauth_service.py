# -*- coding: utf-8 -*-
"""
ACAS Pro - OAuth Service
Third-party login integration (QQ/WeChat)
"""

import json
import urllib.request
import urllib.parse
import secrets
from typing import Optional, Dict, Tuple
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class OAuthUserInfo:
    """OAuth用户信息"""
    provider: str
    openid: str
    nickname: str
    avatar: str
    email: Optional[str] = None


class OAuthProvider(ABC):
    """OAuth提供者基类"""
    
    @abstractmethod
    def get_authorization_url(self, state: str) -> str:
        """获取授权URL"""
        pass
    
    @abstractmethod
    def get_access_token(self, code: str) -> Optional[str]:
        """通过授权码获取访问令牌"""
        pass
    
    @abstractmethod
    def get_user_info(self, access_token: str) -> Optional[OAuthUserInfo]:
        """获取用户信息"""
        pass


class QQOAuth(OAuthProvider):
    """QQ OAuth"""
    
    # QQ互联配置（从 config.oauth 读取）
    @property
    def APP_ID(self): return self._cfg.qq_app_id
    @property
    def APP_KEY(self): return self._cfg.qq_app_key
    @property
    def REDIRECT_URI(self): return self._cfg.qq_redirect_uri

    def __init__(self, cfg): self._cfg = cfg
    
    AUTH_URL = "https://graph.qq.com/oauth2.0/authorize"
    TOKEN_URL = "https://graph.qq.com/oauth2.0/token"
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
    
    def get_access_token(self, code: str) -> Optional[str]:
        params = {
            "grant_type": "authorization_code",
            "client_id": self.APP_ID,
            "client_secret": self.APP_KEY,
            "code": code,
            "redirect_uri": self.REDIRECT_URI
        }
        try:
            url = f"{self.TOKEN_URL}?{urllib.parse.urlencode(params)}"
            with urllib.request.urlopen(url, timeout=10) as response:
                data = urllib.parse.parse_qs(response.read().decode())
                return data.get("access_token", [None])[0]
        except Exception:
            return None
    
    def get_user_info(self, access_token: str) -> Optional[OAuthUserInfo]:
        # QQ需要先获取openid
        try:
            # 获取openid
            openid_url = f"https://graph.qq.com/oauth2.0/me?access_token={access_token}"
            with urllib.request.urlopen(openid_url, timeout=10) as response:
                # 解析JSONP响应
                text = response.read().decode()
                # 移除callback
                if "callback" in text:
                    text = text[text.index("(")+1:text.rindex(")")]
                data = json.loads(text)
                openid = data.get("openid")
                client_id = data.get("client_id")
            
            if not openid:
                return None
            
            # 获取用户信息
            params = {
                "access_token": access_token,
                "oauth_consumer_key": client_id or self.APP_ID,
                "openid": openid
            }
            url = f"{self.USER_INFO_URL}?{urllib.parse.urlencode(params)}"
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
            
            return OAuthUserInfo(
                provider="qq",
                openid=openid,
                nickname=data.get("nickname", ""),
                avatar=data.get("figureurl_qq_2", data.get("figureurl", "")),
                email=None
            )
        except Exception:
            return None


class WeChatOAuth(OAuthProvider):
    """微信 OAuth"""
    
    # 微信开放平台配置（从 config.oauth 读取）
    @property
    def APP_ID(self): return self._cfg.wechat_app_id
    @property
    def APP_SECRET(self): return self._cfg.wechat_app_secret
    @property
    def REDIRECT_URI(self): return self._cfg.wechat_redirect_uri

    def __init__(self, cfg): self._cfg = cfg
    
    AUTH_URL = "https://open.weixin.qq.com/connect/qrconnect"
    TOKEN_URL = "https://api.weixin.qq.com/sns/oauth2/access_token"
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
    
    def get_access_token(self, code: str) -> Optional[str]:
        params = {
            "appid": self.APP_ID,
            "secret": self.APP_SECRET,
            "code": code,
            "grant_type": "authorization_code"
        }
        try:
            url = f"{self.TOKEN_URL}?{urllib.parse.urlencode(params)}"
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
                return data.get("access_token")
        except Exception:
            return None
    
    def get_user_info(self, access_token: str) -> Optional[OAuthUserInfo]:
        # 微信需要在获取token时保存openid
        # 这里简化处理，实际需要完整流程
        try:
            # 假设我们有openid
            params = {
                "access_token": access_token,
                "openid": "placeholder"  # 实际需要从token响应中获取
            }
            url = f"{self.USER_INFO_URL}?{urllib.parse.urlencode(params)}"
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
            
            return OAuthUserInfo(
                provider="wechat",
                openid=data.get("unionid", data.get("openid", "")),
                nickname=data.get("nickname", ""),
                avatar=data.get("headimgurl", ""),
                email=None
            )
        except Exception:
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
        """处理授权回调"""
        provider_obj = self._providers.get(provider)
        if not provider_obj:
            return None
        
        access_token = provider_obj.get_access_token(code)
        if not access_token:
            return None
        
        return provider_obj.get_user_info(access_token)
    
    def available_providers(self) -> list:
        """获取可用的OAuth提供者"""
        return list(self._providers.keys())
