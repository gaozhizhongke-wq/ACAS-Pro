"""UI page tests - instantiate each UI page class to cover their __init__ code paths."""
import sys
from unittest.mock import MagicMock
from types import ModuleType
import pytest


# Module paths to clear between tests to prevent cross-contamination
_UI_MODULES = [
    'acas_pro.ui.pages.dashboard',
    'acas_pro.ui.pages.inventory',
    'acas_pro.ui.pages.forecast',
    'acas_pro.ui.pages.account_management',
    'acas_pro.ui.pages.ad_manager',
    'acas_pro.ui.pages.advanced_analytics',
    'acas_pro.ui.pages.avatar_studio',
    'acas_pro.ui.pages.blockchain_settlement',
    'acas_pro.ui.pages.content_creation',
    'acas_pro.ui.pages.ecommerce_manager',
    'acas_pro.ui.pages.festival_calendar',
    'acas_pro.ui.pages.intelligence',
    'acas_pro.ui.pages.llm_chat',
    'acas_pro.ui.pages.publish_manager',
    'acas_pro.ui.pages.settings',
    'acas_pro.ui.pages.video_maker',
    'acas_pro.ui.auth.login_dialog',
    'acas_pro.ui.auth',
    'acas_pro.ui.main_window',
    'acas_pro.ui.pages',
    'acas_pro.ui',
    'acas_pro.services.user_service',
    'acas_pro.ml.inventory_optimizer',
    'acas_pro.ml.timesfm_engine',
    'acas_pro.publisher.publish_manager',
    'acas_pro.llm.llm_client',
    'acas_pro.llm',
    'acas_pro.i18n',
    'acas_pro.i18n.translator',
]


def _clear_ui_modules():
    for mod in list(sys.modules.keys()):
        if mod in _UI_MODULES:
            del sys.modules[mod]
        elif mod.startswith('acas_pro.ui.') or mod == 'acas_pro.ui':
            del sys.modules[mod]


def _ensure_service_mocks():
    """Ensure service singletons exist in sys.modules. Returns saved originals."""
    saved = {}
    for mod_name in ['acas_pro.services.user_service', 'numpy']:
        if mod_name in sys.modules:
            saved[mod_name] = sys.modules.pop(mod_name)
        else:
            saved[mod_name] = None

    mod = MagicMock()
    mod.user_service = MagicMock()
    sys.modules['acas_pro.services.user_service'] = mod

    if 'numpy' not in sys.modules:
        sys.modules['numpy'] = MagicMock()

    return saved


def _restore_service_mocks(saved):
    """Restore modules that were mocked by _ensure_service_mocks()."""
    for mod_name, original in saved.items():
        if original is None:
            sys.modules.pop(mod_name, None)
        else:
            sys.modules[mod_name] = original

    # Ensure acas_pro.i18n has required translation functions
    # (settings.py imports: t, set_language, get_language, available_languages)
    try:
        import acas_pro.i18n as i18n_mod
    except ImportError:
        i18n_mod = type(sys)('acas_pro.i18n')
        sys.modules['acas_pro.i18n'] = i18n_mod
    if not hasattr(i18n_mod, 't'):
        i18n_mod.t = lambda key: key
    if not hasattr(i18n_mod, 'set_language'):
        i18n_mod.set_language = MagicMock()
    if not hasattr(i18n_mod, 'get_language'):
        i18n_mod.get_language = MagicMock(return_value='zh_CN')
    if not hasattr(i18n_mod, 'available_languages'):
        i18n_mod.available_languages = ['zh_CN', 'en_US']


class _UIPageTestBase:
    """Base for UI page tests. Override _module_path and _class_name."""
    _module_path = None
    _class_name = None

    _saved_services = None

    def setup_method(self):
        _clear_ui_modules()
        self._saved_services = _ensure_service_mocks()

    def teardown_method(self):
        if self._saved_services is not None:
            _restore_service_mocks(self._saved_services)
            self._saved_services = None

    def test_instantiation(self):
        if not self._module_path or not self._class_name:
            return
        mod = __import__(self._module_path, fromlist=[self._class_name])
        cls = getattr(mod, self._class_name)
        instance = cls()
        assert instance is not None


class TestDashboardPage(_UIPageTestBase):
    _module_path = 'acas_pro.ui.pages.dashboard'
    _class_name = 'DashboardPage'


class TestInventoryPage(_UIPageTestBase):
    _module_path = 'acas_pro.ui.pages.inventory'
    _class_name = 'InventoryPage'


class TestForecastPage(_UIPageTestBase):
    _module_path = 'acas_pro.ui.pages.forecast'
    _class_name = 'ForecastPage'


class TestAccountManagementPage(_UIPageTestBase):
    _module_path = 'acas_pro.ui.pages.account_management'
    _class_name = 'AccountManagementPage'


class TestAdManagerPage(_UIPageTestBase):
    _module_path = 'acas_pro.ui.pages.ad_manager'
    _class_name = 'AdManagerPage'


class TestAdvancedAnalyticsPage(_UIPageTestBase):
    _module_path = 'acas_pro.ui.pages.advanced_analytics'
    _class_name = 'AdvancedAnalyticsPage'


class TestAvatarStudioPage(_UIPageTestBase):
    _module_path = 'acas_pro.ui.pages.avatar_studio'
    _class_name = 'AvatarStudioPage'


class TestBlockchainSettlementPage(_UIPageTestBase):
    _module_path = 'acas_pro.ui.pages.blockchain_settlement'
    _class_name = 'BlockchainSettlementPage'


class TestContentCreationPage(_UIPageTestBase):
    _module_path = 'acas_pro.ui.pages.content_creation'
    _class_name = 'ContentCreationPage'


class TestEcommerceManagerPage(_UIPageTestBase):
    _module_path = 'acas_pro.ui.pages.ecommerce_manager'
    _class_name = 'EcommerceManagerPage'


class TestFestivalCalendarPage(_UIPageTestBase):
    _module_path = 'acas_pro.ui.pages.festival_calendar'
    _class_name = 'FestivalCalendarPage'


class TestIntelligencePage(_UIPageTestBase):
    _module_path = 'acas_pro.ui.pages.intelligence'
    _class_name = 'IntelligencePage'


class TestLLMChatPage(_UIPageTestBase):
    _module_path = 'acas_pro.ui.pages.llm_chat'
    _class_name = 'LLMChatPage'


class TestPublishManagerPage(_UIPageTestBase):
    _module_path = 'acas_pro.ui.pages.publish_manager'
    _class_name = 'PublishManagerPage'


class TestSettingsPage(_UIPageTestBase):
    _module_path = 'acas_pro.ui.pages.settings'
    _class_name = 'SettingsPage'


class TestVideoMakerPage(_UIPageTestBase):
    _module_path = 'acas_pro.ui.pages.video_maker'
    _class_name = 'VideoMakerPage'


class TestLoginDialog(_UIPageTestBase):
    _module_path = 'acas_pro.ui.auth.login_dialog'
    _class_name = 'LoginDialog'


class TestMainWindow(_UIPageTestBase):
    _module_path = 'acas_pro.ui.main_window'
    _class_name = 'MainWindow'
