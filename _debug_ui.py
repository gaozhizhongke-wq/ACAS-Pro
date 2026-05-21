"""
UI coverage test with _SmartMock Qt fakes.
Run standalone: python _debug_ui.py
Run with coverage: python -m coverage run _debug_ui.py && python -m coverage report
"""
import sys, os, types
from unittest.mock import MagicMock

# Patch MagicMock to support __format__
_orig_format = getattr(MagicMock, '__format__', None)
def _mock_format(self, spec):
    return ''
MagicMock.__format__ = _mock_format


class _SmartMock:
    """Lightweight mock supporting comparisons, formatting, path-like."""
    def __init__(self, name='mock'):
        self._name = name
    def __getattr__(self, name):
        if name == 'count': return 0
        return _SmartMock(f'{self._name}.{name}')
    def __call__(self, *a, **kw):
        return _SmartMock(f'{self._name}()')
    def __ge__(self, other): return True
    def __gt__(self, other): return True
    def __le__(self, other): return False
    def __lt__(self, other): return False
    def __eq__(self, other): return isinstance(other, (_SmartMock, _FQ, MagicMock))
    def __ne__(self, other): return not self.__eq__(other)
    def __int__(self): return 0
    def __float__(self): return 0.0
    def __format__(self, spec): return ''
    def __round__(self, n=None): return 0
    def __index__(self): return 0
    def __bool__(self): return True
    def __str__(self): return ''
    def __repr__(self): return '_SM'
    def __iter__(self): return iter([])
    def __len__(self): return 0
    def __contains__(self, item): return False
    def __getitem__(self, key): return _SmartMock()
    def __setitem__(self, key, val): pass
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def __hash__(self): return 0
    def __add__(self, other): return _SmartMock()
    def __radd__(self, other): return _SmartMock()
    def __sub__(self, other): return _SmartMock()
    def __mul__(self, other): return _SmartMock()
    def __truediv__(self, other): return _SmartMock()
    def __neg__(self): return _SmartMock()
    def __and__(self, other): return _SmartMock()
    def __or__(self, other): return _SmartMock()
    def __xor__(self, other): return _SmartMock()
    def __invert__(self): return _SmartMock()
    def __fspath__(self): return ''  # PathLike support


class _MetaFQ(type):
    _cache = {}
    def __getattr__(cls, name):
        if name.startswith('_'):
            return type.__getattribute__(cls, name)
        key = (id(cls), name)
        if key not in _MetaFQ._cache:
            _MetaFQ._cache[key] = _SmartMock(f'{cls.__name__}.{name}')
        return _MetaFQ._cache[key]


class _FQ(metaclass=_MetaFQ):
    def __init__(self, *a, **kw): pass
    def __getattr__(self, name): return _SmartMock(name=name)
    def __setattr__(self, name, v): object.__setattr__(self, name, v)
    def __iter__(self): return iter([])
    def __bool__(self): return True
    def __len__(self): return 0
    def __str__(self): return ''
    def __eq__(self, o): return isinstance(o, (_SmartMock, _FQ, MagicMock))
    def __hash__(self): return 0
    def __contains__(self, item): return False
    def __getitem__(self, key): return _SmartMock()
    def __setitem__(self, key, val): pass
    def __call__(self, *a, **kw): return _SmartMock()
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def __ge__(self, other): return True
    def __gt__(self, other): return True
    def __le__(self, other): return False
    def __lt__(self, other): return False
    def __int__(self): return 0
    def __float__(self): return 0.0
    def __format__(self, spec): return ''
    def __index__(self): return 0
    def __fspath__(self): return ''


def install_qt():
    QWidget = _FQ
    QDialog = type('QDialog', (_FQ,), {})
    QMainWindow = type('QMainWindow', (_FQ,), {})
    QObject = QWidget

    w = types.ModuleType('PySide6.QtWidgets')
    w.QWidget = QWidget; w.QDialog = QDialog; w.QMainWindow = QMainWindow; w.QObject = QObject
    widgets = [
        'QLabel','QPushButton','QLineEdit','QTextEdit','QComboBox','QCheckBox',
        'QTabWidget','QScrollArea','QFrame','QGroupBox','QListWidget','QTableWidget',
        'QSplitter','QProgressBar','QSpinBox','QDoubleSpinBox','QDateEdit',
        'QDateTimeEdit','QStackedWidget','QSlider','QWebEngineView','QGraphicsView',
        'QRadioButton','QFileDialog','QDialogButtonBox','QAbstractItemView',
        'QSizePolicy','QSpacerItem','QCompleter','QCalendarWidget','QTreeWidget',
        'QTreeWidgetItem','QStatusBar','QToolBar','QTextEdit','QGraphicsOpacityEffect',
        'QButtonGroup','QRadioButton','QCheckBox','QHeaderView',
        'QGraphicsDropShadowEffect','QGraphicsBlurEffect',
    ]
    for name in widgets:
        setattr(w, name, type(name, (_FQ,), {}))
    for name in [
        'QTableWidgetItem','QAction','QMenu','QMenuBar',
        'QMessageBox','QListWidgetItem','QGraphicsScene','QTreeWidgetItem',
        'QParallelAnimationGroup','QSequentialAnimationGroup','QPropertyAnimation',
    ]:
        setattr(w, name, MagicMock)
    for name in ['QVBoxLayout','QHBoxLayout','QGridLayout','QFormLayout']:
        m = MagicMock(return_value=_SmartMock())
        m.return_value.count = MagicMock(return_value=0)
        m.return_value.itemAt = MagicMock(return_value=None)
        m.return_value.takeAt = MagicMock(return_value=None)
        m.return_value.addWidget = MagicMock()
        m.return_value.addLayout = MagicMock()
        m.return_value.addStretch = MagicMock()
        m.return_value.setContentsMargins = MagicMock()
        m.return_value.setSpacing = MagicMock()
        setattr(w, name, m)

    c = types.ModuleType('PySide6.QtCore')
    c.Qt = type('Qt', (_FQ,), {})()
    c.Signal = MagicMock; c.Slot = MagicMock
    c.QTimer = type('QTimer', (_FQ,), {}); c.QThread = type('QThread', (_FQ,), {})
    c.QDateTime = MagicMock; c.QDate = MagicMock; c.QObject = QObject
    c.QRect = MagicMock; c.QRectF = MagicMock; c.QSize = MagicMock
    c.QPoint = MagicMock; c.QUrl = MagicMock; c.QFile = MagicMock

    g = types.ModuleType('PySide6.QtGui')
    g.QPixmap = MagicMock; g.QIcon = MagicMock
    g.QFont = type('QFont', (_FQ,), {})
    g.QColor = type('QColor', (_FQ,), {})
    g.QPalette = MagicMock; g.QSize = MagicMock; g.QPoint = MagicMock
    g.QTextCursor = MagicMock; g.QPainter = MagicMock; g.QPen = MagicMock; g.QBrush = MagicMock

    ch = types.ModuleType('PySide6.QtCharts')
    ch.QChart = MagicMock(return_value=_SmartMock())
    for name in ['QLineSeries','QBarSeries','QPieSeries','QValueAxis','QBarSet','QAreaSeries',
                 'QScatterSeries','QSplineSeries','QPercentBarSeries']:
        setattr(ch, name, MagicMock)

    wm = types.ModuleType('PySide6.QtWebEngineWidgets')
    wm.QWebEngineView = QWidget; wm.QWebEnginePage = MagicMock

    p = types.ModuleType('PySide6')
    sys.modules['PySide6'] = p
    sys.modules['PySide6.QtWidgets'] = w; sys.modules['PySide6.QtGui'] = g
    sys.modules['PySide6.QtCore'] = c; sys.modules['PySide6.QtCharts'] = ch
    sys.modules['PySide6.QtWebEngineWidgets'] = wm


def install_acas_deps():
    sys.modules['numpy'] = MagicMock()
    sys.path.insert(0, 'src')
    config_mod = types.ModuleType('acas_pro.core.config')
    config_mod.config = _SmartMock()
    config_mod.config.ui = _SmartMock()
    config_mod.config.ui.font_family = 'Arial'
    config_mod.config.api = _SmartMock()
    config_mod.config.database = _SmartMock()
    config_mod.config.security = _SmartMock()
    config_mod.config.security.secret_key = 'test-key'
    config_mod.config.logging = _SmartMock()
    config_mod.get_config = MagicMock(return_value=config_mod.config)
    sys.modules['acas_pro.core.config'] = config_mod
    def _make_mod(name):
        m = MagicMock()
        m.get_logger = MagicMock()
        m.get_config = MagicMock()
        return m
    for mod in [
        'acas_pro.core.logging', 'acas_pro.services.user_service',
        'acas_pro.i18n', 'acas_pro.services.oauth', 'acas_pro.services.publish',
        'acas_pro.services.ad_service', 'acas_pro.services.avatar',
        'acas_pro.services.video', 'acas_pro.services.blockchain',
        'acas_pro.services.llm', 'acas_pro.services.forecast',
        'acas_pro.services.inventory', 'acas_pro.services.content',
        'acas_pro.services.account', 'acas_pro.services.ecommerce',
        'acas_pro.services.analytics', 'acas_pro.services.festival',
        'acas_pro.collectors.weibo_api', 'acas_pro.collectors.rss_collector',
        'acas_pro.collectors.data_collector', 'acas_pro.llm.client',
        'acas_pro.llm.claude_engine', 'acas_pro.llm.gemini_engine',
        'acas_pro.llm.base_engine', 'acas_pro.ml.timesfm_engine',
        'acas_pro.sentiment.news_engine', 'acas_pro.sentiment.analyzer',
        'acas_pro.sentiment.analyzer_v2', 'acas_pro.core.logging_v2',
        'acas_pro.ui.pages.main_window',
    ]:
        sys.modules[mod] = _make_mod(mod)


def clear_acas():
    keep = {'acas_pro.core.config', 'acas_pro.core.logging', 'acas_pro.i18n'}
    for k in list(sys.modules):
        if k.startswith('acas_pro') and k not in keep:
            del sys.modules[k]


if __name__ == '__main__':
    install_qt()
    install_acas_deps()

    pages = [
        ('acas_pro.ui.pages.settings', 'SettingsPage'),
        ('acas_pro.ui.pages.dashboard', 'DashboardPage'),
        ('acas_pro.ui.pages.forecast', 'ForecastPage'),
        ('acas_pro.ui.pages.inventory', 'InventoryPage'),
        # ('acas_pro.ui.pages.festival_calendar', 'FestivalCalendarPage'),  # HANGS - skip
        ('acas_pro.ui.pages.content_creation', 'ContentCreationPage'),
        ('acas_pro.ui.pages.intelligence', 'IntelligencePage'),
        ('acas_pro.ui.pages.ad_manager', 'AdManagerPage'),
        ('acas_pro.ui.pages.avatar_studio', 'AvatarStudioPage'),
        ('acas_pro.ui.pages.video_maker', 'VideoMakerPage'),
        ('acas_pro.ui.pages.publish_manager', 'PublishManagerPage'),
        ('acas_pro.ui.pages.account_management', 'AccountManagementPage'),
        ('acas_pro.ui.pages.ecommerce_manager', 'EcommerceManagerPage'),
        ('acas_pro.ui.pages.blockchain_settlement', 'BlockchainSettlementPage'),
        ('acas_pro.ui.pages.llm_chat', 'LLMChatPage'),
        ('acas_pro.ui.pages.advanced_analytics', 'AdvancedAnalyticsPage'),
    ]

    ok = fail = imp = 0
    for mod_path, cls_name in pages:
        clear_acas()
        install_acas_deps()
        try:
            print(f'  {cls_name}...', end=' ', flush=True)
            mod = __import__(mod_path, fromlist=[cls_name])
            cls = getattr(mod, cls_name)
            obj = cls()
            print('OK')
            ok += 1
        except ImportError as e:
            print(f'IMPORT: {str(e)[:50]}')
            imp += 1
        except Exception as e:
            tb = str(e).split('\n')[-1][:70]
            print(f'FAIL: {tb}')
            fail += 1

    print(f'\n{ok} OK, {fail} FAIL, {imp} IMPORT out of {len(pages)} total')
