"""Test individual UI pages with timeout. Usage: python _test_one_page.py <page>"""
import sys, os, types
from unittest.mock import MagicMock

MagicMock.__format__ = lambda self, spec: ''


def _noop(*a, **kw): return None


class _Count:
    """layout.count() value: callable returning 0, comparable > 1."""
    def __call__(self): return 0
    def __ge__(self, o): return True
    def __gt__(self, o): return True
    def __le__(self, o): return False
    def __lt__(self, o): return False
    def __int__(self): return 0
    def __index__(self): return 0
    def __bool__(self): return False
    def __eq__(self, o): return isinstance(o, _Count)
    def __repr__(self): return '0'


class _SM:
    def __init__(self, n='m'): self._n = n
    def __getattr__(self, n):
        if n == 'count': return _Count()
        if n == 'connect': return _noop
        return _SM(f'{self._n}.{n}')
    def __call__(self, *a, **kw): return _SM(f'{self._n}()')
    def __ge__(self, o): return True
    def __gt__(self, o): return True
    def __le__(self, o): return False
    def __lt__(self, o): return False
    def __eq__(self, o): return isinstance(o, (_SM, _FQ, MagicMock))
    def __ne__(self, o): return not self.__eq__(o)
    def __int__(self): return 0
    def __float__(self): return 0.0
    def __format__(self, s): return ''
    def __round__(self, n=None): return 0
    def __index__(self): return 0
    def __bool__(self): return True
    def __str__(self): return ''
    def __repr__(self): return '_SM'
    def __iter__(self): return iter([])
    def __len__(self): return 0
    def __contains__(self, x): return False
    def __getitem__(self, k): return _SM()
    def __setitem__(self, k, v): pass
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def __hash__(self): return 0
    def __add__(self, o): return _SM()
    def __radd__(self, o): return _SM()
    def __sub__(self, o): return _SM()
    def __mul__(self, o): return _SM()
    def __truediv__(self, o): return _SM()
    def __and__(self, o): return _SM()
    def __or__(self, o): return _SM()
    def __xor__(self, o): return _SM()
    def __invert__(self): return _SM()
    def __neg__(self): return _SM()
    def __pos__(self): return _SM()
    def __fspath__(self): return ''


class _MF(type):
    _c = {}
    def __getattr__(cls, n):
        if n.startswith('_'): return type.__getattribute__(cls, n)
        k = (id(cls), n)
        if k not in _MF._c: _MF._c[k] = _SM(f'{cls.__name__}.{n}')
        return _MF._c[k]


class _FQ(metaclass=_MF):
    def __init__(self, *a, **kw): pass
    def __getattr__(self, n):
        if n == 'count': return _Count()
        if n == 'connect': return _noop
        return _SM(n=n)
    def __setattr__(self, n, v): object.__setattr__(self, n, v)
    def __iter__(self): return iter([])
    def __bool__(self): return True
    def __len__(self): return 0
    def __str__(self): return ''
    def __eq__(self, o): return isinstance(o, (_SM, _FQ, MagicMock))
    def __hash__(self): return 0
    def __contains__(self, x): return False
    def __getitem__(self, k): return _SM()
    def __setitem__(self, k, v): pass
    def __call__(self, *a, **kw): return _SM()
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def __ge__(self, o): return True
    def __gt__(self, o): return True
    def __le__(self, o): return False
    def __lt__(self, o): return False
    def __int__(self): return 0
    def __float__(self): return 0.0
    def __format__(self, s): return ''
    def __index__(self): return 0
    def __fspath__(self): return ''


# ── Qt Setup ─────────────────────────────────────────────────
QWidget = _FQ
w = types.ModuleType('PySide6.QtWidgets')
w.QWidget = QWidget
w.QDialog = type('QD', (_FQ,), {})
w.QMainWindow = type('QMW', (_FQ,), {})
w.QObject = QWidget

for n in ['QLabel','QPushButton','QLineEdit','QTextEdit','QComboBox','QCheckBox',
          'QTabWidget','QScrollArea','QFrame','QGroupBox','QListWidget','QTableWidget',
          'QSplitter','QProgressBar','QSpinBox','QDoubleSpinBox','QDateEdit',
          'QDateTimeEdit','QStackedWidget','QSlider','QGraphicsView','QRadioButton',
          'QFileDialog','QDialogButtonBox','QAbstractItemView','QSizePolicy',
          'QSpacerItem','QCompleter','QCalendarWidget','QTreeWidget','QTreeWidgetItem',
          'QStatusBar','QToolBar','QGraphicsOpacityEffect','QHeaderView','QButtonGroup']:
    setattr(w, n, type(n, (_FQ,), {}))

for n in ['QTableWidgetItem','QAction','QMenu','QMenuBar','QMessageBox',
          'QListWidgetItem','QGraphicsScene','QTreeWidgetItem',
          'QGraphicsDropShadowEffect','QGraphicsBlurEffect',
          'QParallelAnimationGroup','QSequentialAnimationGroup','QPropertyAnimation']:
    m = MagicMock()
    m.setFlags = _noop
    setattr(w, n, m)

for n in ['QVBoxLayout','QHBoxLayout','QGridLayout','QFormLayout']:
    m = MagicMock(return_value=_SM())
    m.return_value.count = _Count()
    m.return_value.itemAt = lambda *a, **kw: None
    m.return_value.takeAt = lambda *a, **kw: None
    m.return_value.addWidget = _noop
    m.return_value.addLayout = _noop
    m.return_value.addStretch = _noop
    m.return_value.setContentsMargins = _noop
    m.return_value.setSpacing = _noop
    setattr(w, n, m)

c = types.ModuleType('PySide6.QtCore')
c.Qt = type('Qt', (_FQ,), {})()
c.Signal = MagicMock; c.Slot = MagicMock
c.QTimer = type('QT', (_FQ,), {}); c.QThread = type('QTh', (_FQ,), {})
c.QDate = type('QDate', (), {'currentDate': classmethod(lambda cls: MagicMock())})
c.QDateTime = type('QDateTime', (), {'currentDateTime': classmethod(lambda cls: MagicMock())})
c.QRect = MagicMock; c.QUrl = MagicMock; c.QFile = MagicMock
c.QSize = type('QSize', (_FQ,), {})()

g = types.ModuleType('PySide6.QtGui')
g.QPixmap = MagicMock; g.QIcon = MagicMock
g.QFont = type('QF', (_FQ,), {}); g.QColor = type('QC', (_FQ,), {})
g.QPalette = MagicMock; g.QTextCursor = MagicMock; g.QPainter = MagicMock
g.QAction = MagicMock

ch = types.ModuleType('PySide6.QtCharts')
ch.QChart = MagicMock(return_value=_SM())
for n in ['QLineSeries','QBarSeries','QPieSeries','QValueAxis','QBarSet','QAreaSeries']:
    setattr(ch, n, MagicMock)

wm = types.ModuleType('PySide6.QtWebEngineWidgets')
wm.QWebEngineView = QWidget; wm.QWebEnginePage = MagicMock

sys.modules['PySide6'] = types.ModuleType('PySide6')
sys.modules['PySide6.QtWidgets'] = w; sys.modules['PySide6.QtGui'] = g
sys.modules['PySide6.QtCore'] = c; sys.modules['PySide6.QtCharts'] = ch
sys.modules['PySide6.QtWebEngineWidgets'] = wm
sys.modules['numpy'] = MagicMock()
sys.path.insert(0, 'src')

cfg = types.ModuleType('acas_pro.core.config')
cfg.config = _SM(); cfg.config.ui = _SM(); cfg.config.ui.font_family = 'Arial'
cfg.config.api = _SM(); cfg.config.database = _SM(); cfg.config.security = _SM()
cfg.config.security.secret_key = 'test-key'; cfg.config.logging = _SM()
cfg.get_config = MagicMock(return_value=cfg.config)
sys.modules['acas_pro.core.config'] = cfg

for m in ['acas_pro.core.logging','acas_pro.services.user_service','acas_pro.i18n',
    'acas_pro.services.oauth','acas_pro.services.publish','acas_pro.services.ad_service',
    'acas_pro.services.avatar','acas_pro.services.video','acas_pro.services.blockchain',
    'acas_pro.services.llm','acas_pro.services.forecast','acas_pro.services.inventory',
    'acas_pro.services.content','acas_pro.services.account','acas_pro.services.ecommerce',
    'acas_pro.services.analytics','acas_pro.services.festival','acas_pro.collectors.weibo_api',
    'acas_pro.collectors.rss_collector','acas_pro.collectors.data_collector','acas_pro.llm.client',
    'acas_pro.llm.claude_engine','acas_pro.llm.gemini_engine','acas_pro.llm.base_engine',
    'acas_pro.ml.timesfm_engine','acas_pro.sentiment.news_engine','acas_pro.sentiment.analyzer',
    'acas_pro.sentiment.analyzer_v2','acas_pro.core.logging_v2','acas_pro.ui.pages.main_window']:
    mod_mock = MagicMock()
    mod_mock.get_logger = MagicMock()
    mod_mock.get_config = MagicMock()
    sys.modules[m] = mod_mock


CLS_MAP = {
    'content_creation': 'ContentCreationPage',
    'festival_calendar': 'FestivalCalendarPage',
    'intelligence': 'IntelligencePage',
    'ad_manager': 'AdManagerPage',
    'avatar_studio': 'AvatarStudioPage',
    'video_maker': 'VideoMakerPage',
    'publish_manager': 'PublishManagerPage',
    'account_management': 'AccountManagementPage',
    'ecommerce_manager': 'EcommerceManagerPage',
    'blockchain_settlement': 'BlockchainSettlementPage',
    'llm_chat': 'LLMChatPage',
    'advanced_analytics': 'AdvancedAnalyticsPage',
    'settings': 'SettingsPage',
    'dashboard': 'DashboardPage',
    'forecast': 'ForecastPage',
    'inventory': 'InventoryPage',
}

page = sys.argv[1] if len(sys.argv) > 1 else 'content_creation'
cls_name = CLS_MAP.get(page, page)
mod_path = f'acas_pro.ui.pages.{page}'

print(f'Testing {page} / {cls_name}...', flush=True)
try:
    mod = __import__(mod_path, fromlist=[cls_name])
    C = getattr(mod, cls_name)
    obj = C()
    print('OK', flush=True)
except Exception as e:
    print(f'FAIL: {type(e).__name__}: {e}', flush=True)
