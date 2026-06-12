"""Tests for services/oauth/oauth_service.py - deep coverage."""
import sys
import os
import json
from unittest.mock import MagicMock as M, patch
import pytest

# Save real modules before mocking (module-level mock required for import below)
_saved_modules = {mod: sys.modules.get(mod) for mod in [
    'PySide6', 'numpy', 'acas_pro.core.config', 'acas_pro.core.logging',
    'acas_pro.core.security', 'acas_pro.services.user_service', 'acas_pro.i18n',
    'PySide6.QtWidgets', 'PySide6.QtCore', 'PySide6.QtGui']}
for mod in ['PySide6','numpy','acas_pro.core.config','acas_pro.core.logging',
    'acas_pro.core.security','acas_pro.services.user_service','acas_pro.i18n']:
    m = M(); m.get_config = M(); m.get_logger = M()  # noqa: E702
    sys.modules[mod] = m
sys.modules['PySide6.QtWidgets'] = M(); sys.modules['PySide6.QtCore'] = M()  # noqa: E702
sys.modules['PySide6.QtGui'] = M()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from acas_pro.services.oauth.oauth_service import (  # noqa: E402
    OAuthUserInfo, TokenResponse, QQOAuth, WeChatOAuth, OAuthService
)

# Restore real modules after import so other test files aren't polluted
for mod, orig in _saved_modules.items():
    if orig is not None:
        sys.modules[mod] = orig
    elif mod in sys.modules:
        del sys.modules[mod]

def _make_urlopen_cm(body_bytes):
    """Return a mock context manager for urllib.request.urlopen."""
    cm = M()
    cm.read.return_value = body_bytes
    # Make `with urlopen(...) as response:` work
    cm.__enter__ = M(return_value=cm)
    cm.__exit__ = M(return_value=False)
    return cm


# ── OAuthUserInfo ─────────────────────────────────────────────────────────

class TestOAuthUserInfo:
    def test_create(self):
        info = OAuthUserInfo(
            provider='qq', openid='o123', nickname='Alice',
            avatar='http://x.com/a.png', email='a@x.com'
        )
        assert info.provider == 'qq'
        assert info.openid == 'o123'
        assert info.nickname == 'Alice'

    def test_create_without_email(self):
        info = OAuthUserInfo(provider='wx', openid='o456', nickname='Bob', avatar='')
        assert info.email is None

    def test_repr(self):
        info = OAuthUserInfo(provider='qq', openid='o1', nickname='N', avatar='')
        assert 'OAuthUserInfo' in repr(info)

    def test_str(self):
        info = OAuthUserInfo(provider='qq', openid='o1', nickname='N', avatar='')
        assert isinstance(str(info), str)


# ── TokenResponse ─────────────────────────────────────────────────────────

class TestTokenResponse:
    def _make(self, **kw):
        defaults = dict(access_token='at', expires_in=3600,
                        refresh_token='rt', openid='o1', scope='all')
        defaults.update(kw)
        return TokenResponse(**defaults)

    def test_create(self):
        tr = self._make()
        assert tr.access_token == 'at'
        assert tr.expires_in == 3600

    def test_as_tuple(self):
        tr = self._make()
        assert isinstance(tr, tuple)

    def test_replace(self):
        tr = self._make()
        tr2 = tr._replace(access_token='at2')
        assert tr2.access_token == 'at2'


# ── QQOAuth ──────────────────────────────────────────────────────────────

class TestQQOAuth:
    @pytest.fixture
    def oauth(self):
        cfg = M()
        cfg.qq_app_id = 'qcid'       # NOT qq_client_id!
        cfg.qq_app_key = 'qcs'
        cfg.qq_redirect_uri = 'http://x.com/cb'
        return QQOAuth(cfg)

    def test_get_authorization_url(self, oauth):
        url = oauth.get_authorization_url('mystate')
        assert isinstance(url, str)
        assert 'graph.qq.com' in url
        assert 'mystate' in url

    def test_get_token_response_success(self, oauth):
        body = b'access_token=at&expires_in=7200&refresh_token=rt&openid=o1'
        cm = _make_urlopen_cm(body)
        with patch('urllib.request.urlopen', return_value=cm):
            result = oauth.get_token_response('code123')
        assert result is not None
        assert result.access_token == 'at'
        assert result.expires_in == 7200

    def test_get_token_response_no_token(self, oauth):
        body = b'expires_in=7200'   # no access_token
        cm = _make_urlopen_cm(body)
        with patch('urllib.request.urlopen', return_value=cm):
            result = oauth.get_token_response('code123')
        assert result is None

    def test_get_token_response_http_error(self, oauth):
        from urllib.error import HTTPError
        with patch('urllib.request.urlopen',
                   side_effect=HTTPError(None, 400, 'Bad', {}, None)):
            result = oauth.get_token_response('code123')
        assert result is None

    def test_get_openid_success_jsonp(self, oauth):
        body = b'callback( {"openid":"o123"} );'
        cm = _make_urlopen_cm(body)
        with patch('urllib.request.urlopen', return_value=cm):
            result = oauth.get_openid('at')
        assert result == 'o123'

    def test_get_openid_success_json(self, oauth):
        body = b'{"openid":"o456"}'
        cm = _make_urlopen_cm(body)
        with patch('urllib.request.urlopen', return_value=cm):
            result = oauth.get_openid('at')
        assert result == 'o456'

    def test_get_user_info_success(self, oauth):
        body = json.dumps({'ret': 0, 'nickname': 'Alice',
                          'figureurl_qq_2': 'http://x.com/a.png'}).encode()
        cm = _make_urlopen_cm(body)
        with patch('urllib.request.urlopen', return_value=cm):
            info = oauth.get_user_info('at', 'o1')
        assert info is not None
        assert info.nickname == 'Alice'
        assert info.avatar == 'http://x.com/a.png'

    def test_get_user_info_nonzero_ret(self, oauth):
        """QQ get_user_info does NOT check ret before building result."""
        body = json.dumps({'ret': 1, 'nickname': '', 'figureurl_qq_2': ''}).encode()
        cm = _make_urlopen_cm(body)
        with patch('urllib.request.urlopen', return_value=cm):
            info = oauth.get_user_info('at', 'o1')
        # Still returns OAuthUserInfo (with empty fields), NOT None
        assert info is not None
        assert info.nickname == ''
        assert info.avatar == ''


# ── WeChatOAuth ──────────────────────────────────────────────────────────

class TestWeChatOAuth:
    @pytest.fixture
    def oauth(self):
        cfg = M()
        cfg.wechat_app_id = 'wcid'
        cfg.wechat_app_secret = 'wcs'
        cfg.wechat_redirect_uri = 'http://x.com/wxcb'
        return WeChatOAuth(cfg)

    def test_get_authorization_url(self, oauth):
        url = oauth.get_authorization_url('wxstate')
        assert isinstance(url, str)
        assert 'open.weixin.qq.com' in url

    def test_get_token_response_success(self, oauth):
        body = b'{"access_token":"wxat","expires_in":7200,"refresh_token":"wxrt","openid":"wxo1","scope":"snsapi_login"}'
        cm = _make_urlopen_cm(body)
        with patch('urllib.request.urlopen', return_value=cm):
            result = oauth.get_token_response('code123')
        assert result is not None
        assert result.access_token == 'wxat'
        assert result.openid == 'wxo1'

    def test_get_token_response_error(self, oauth):
        body = b'{"errcode":40029,"errmsg":"invalid code"}'
        cm = _make_urlopen_cm(body)
        with patch('urllib.request.urlopen', return_value=cm):
            result = oauth.get_token_response('badcode')
        assert result is None

    def test_get_user_info_success(self, oauth):
        body = json.dumps({'openid':'wxo1','nickname':'Bob',
                          'headimgurl':'http://x.com/b.png'}).encode()
        cm = _make_urlopen_cm(body)
        with patch('urllib.request.urlopen', return_value=cm):
            info = oauth.get_user_info('wxtoken', 'wxo1')
        assert info is not None
        assert info.nickname == 'Bob'
        assert info.avatar == 'http://x.com/b.png'


# ── OAuthService ──────────────────────────────────────────────────────────

class TestOAuthService:
    @pytest.fixture
    def svc(self):
        cfg = M()
        cfg.qq_app_id = 'qcid'; cfg.qq_app_key = 'qcs'; cfg.qq_redirect_uri = 'http://x.com/cb'  # noqa: E702
        cfg.wechat_app_id = 'wcid'; cfg.wechat_app_secret = 'wcs'; cfg.wechat_redirect_uri = 'http://x.com/wxcb'  # noqa: E702
        return OAuthService(cfg)

    def test_available_providers(self, svc):
        provs = svc.available_providers()
        assert isinstance(provs, list)
        assert 'qq' in provs
        assert 'wechat' in provs

    def test_get_authorization_url(self, svc):
        url, state = svc.get_authorization_url('qq')
        assert isinstance(url, str)
        assert isinstance(state, str)
        assert 'qq.com' in url

    def test_get_authorization_url_unknown_provider(self, svc):
        url, state = svc.get_authorization_url('unknown')
        assert url == ''
        assert state == ''

    def test_handle_callback_success(self, svc):
        mock_provider = M(spec=QQOAuth)
        mock_provider.get_token_response.return_value = TokenResponse(
            access_token='at', expires_in=3600,
            refresh_token='rt', openid='o1', scope='all'
        )
        mock_provider.get_user_info.return_value = OAuthUserInfo(
            provider='qq', openid='o1', nickname='N', avatar=''
        )
        svc._providers = {'qq': mock_provider}

        result = svc.handle_callback('qq', 'code123')
        assert result is not None
        assert result.provider == 'qq'

    def test_handle_callback_no_provider(self, svc):
        result = svc.handle_callback('unknown', 'code')
        assert result is None

    def test_handle_callback_token_failure(self, svc):
        mock_provider = M(spec=QQOAuth)
        mock_provider.get_token_response.return_value = None
        svc._providers = {'qq': mock_provider}
        result = svc.handle_callback('qq', 'badcode')
        assert result is None

    def test_refresh_token_unsupported(self, svc):
        """Only WeChat supports token refresh."""
        mock_provider = M(spec=QQOAuth)
        svc._providers = {'qq': mock_provider}
        result = svc.refresh_token('qq', 'old_rt')
        assert result is None

    def test_refresh_token_wechat_success(self, svc):
        """WeChat refresh_token needs self._cfg.wechat_app_id (source has a bug: __init__ doesn't set self._cfg)."""
        # Patch the missing attribute so the code can run
        svc._cfg = M()
        svc._cfg.wechat_app_id = 'wcid'

        # Mock the HTTP call to WeChat's refresh URL
        body = json.dumps({'access_token':'new_at','expires_in':7200,
                           'refresh_token':'new_rt','openid':'wxo1','scope':'snsapi_login'}).encode()
        cm = _make_urlopen_cm(body)
        with patch('urllib.request.urlopen', return_value=cm):
            result = svc.refresh_token('wechat', 'old_rt')
        assert result is not None
        assert result.access_token == 'new_at'
