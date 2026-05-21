"""Introspect oauth_service.py real signatures."""
import sys, os, types, inspect
from unittest.mock import MagicMock as M

# Mock heavy dependencies
for mod in ['PySide6','numpy','acas_pro.core.config','acas_pro.core.logging',
    'acas_pro.core.security','acas_pro.services.user_service','acas_pro.i18n']:
    m = M(); m.get_config = M(); m.get_logger = M()
    sys.modules[mod] = m

sys.modules['PySide6.QtWidgets'] = M(); sys.modules['PySide6.QtCore'] = M()
sys.modules['PySide6.QtGui'] = M(); sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from acas_pro.services.oauth.oauth_service import OAuthUserInfo, TokenResponse, OAuthProvider, QQOAuth, WeChatOAuth, OAuthService

for cls in [OAuthUserInfo, OAuthProvider, QQOAuth, WeChatOAuth, OAuthService]:
    print(f'\n=== {cls.__name__} ===')
    if hasattr(cls, '__dataclass_fields__'):
        print(f'  dataclass fields: {list(cls.__dataclass_fields__.keys())}')
    if hasattr(cls, '__init__'):
        try:
            sig = inspect.signature(cls.__init__)
            print(f'  __init__{sig}')
        except: pass
    for n, m in inspect.getmembers(cls, predicate=callable):
        if not n.startswith('_') or n in ('__init__', '__str__', '__repr__'):
            try:
                sig = inspect.signature(m)
                print(f'  {n}{sig}')
            except: pass
