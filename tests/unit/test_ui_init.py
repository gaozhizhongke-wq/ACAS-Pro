#!/usr/bin/env python3
"""UI pages instantiation test with real-class Qt fakes.
Run: python tests/unit/test_ui_init.py
"""
import sys, os, types, importlib
from unittest.mock import MagicMock


class _FQ:
    """Fake Qt widget that accepts any attribute access."""
    def __init__(self, *a, **kw):
        pass
    def __getattr__(self, n):
        return MagicMock()
    def __setattr__(self, n, v):
        object.__setattr__(self, n, v)
    def __iter__(self):
        return iter([])
    def __bool__(self):
        return True
    def __len__(self):
        return 0
    def __str__(self):
        return ''
    def __eq__(self, o):
        return isinstance(o, _FQ)
    def __hash__(self):
        return 0
    def __contains__(self, item):
        return False
    def __getitem__(self, key):
        return MagicMock()
    def __setitem__(self, key, val):
        pass
    def __call__(self, *a, **kw):
        return MagicMock()


def install_qt():
    """Must be called before any acas_pro import."""
    QWidget = type('QWidget', (_FQ,), {})
    QMainWindow = type('QMainWindow', (QWidget,), {})
    QDialog = type('QDialog', (QWidget,), {})
    QObject = QWidget

    w = types.ModuleType('PySide6.QtWidgets')
    w.QWidget = QWidget
    w.QDialog = QDialog
    w.QMainWindow = QMainWindow
    w.QObject = QObject

    widget_names = [
        'QLabel', 'QPushButton', 'QLineEdit', 'QTextEdit', 'QComboBox',
        'QCheckBox', 'QTabWidget', 'QScrollArea', 'QFrame', 'QGroupBox',
        'QListWidget', 'QTableWidget', 'QSplitter', 'QProgressBar',
        'QSpinBox', 'QDoubleSpinBox', 'QDateEdit', 'QStackedWidget',
        'QSlider', 'QWebEngineView', 'QGraphicsView', 'QRadioButton',
        'QFileDialog', 'QDialogButtonBox', 'QAbstractItemView',
        'QSizePolicy', 'QSpacerItem', 'QCompleter', 'QCalendarWidget',
        'QTreeWidget', 'QTreeWidgetItem', 'QStatusBar', 'QToolBar',
        'QTextEdit', 'QGraphicsOpacityEffect',
    ]
    for name in widget_names:
        setattr(w, name, QWidget)

    mock_names = [
        'QTableWidgetItem', 'QHeaderView', 'QAction', 'QMenu', 'QMenuBar',
        'QMessageBox', 'QListWidgetItem', 'QGraphicsScene', 'QTreeWidgetItem',
        'QGraphicsDropShadowEffect', 'QGraphicsBlurEffect',
        'QParallelAnimationGroup', 'QSequentialAnimationGroup', 'QPropertyAnimation',
    ]
    for name in mock_names:
        setattr(w, name, MagicMock)

    layout_names = ['QVBoxLayout', 'QHBoxLayout', 'QGridLayout', 'QFormLayout']
    for name in layout_names:
        setattr(w, name, MagicMock(return_value=MagicMock()))

    c = types.ModuleType('PySide6.QtCore')
    c.Qt = MagicMock()
    c.Qt.FontWeight = type('FW', (), {'Bold': 75, 'Normal': 50})
    c.Qt.GlobalColor = type('GC', (), {'red': 0, 'green': 1, 'blue': 2, 'black': 3, 'white': 4, 'gray': 5, 'lightGray': 6})
    c.Signal = MagicMock
    c.Slot = MagicMock
    c.QTimer = MagicMock
    c.QThread = MagicMock
    c.QDateTime = MagicMock
    c.QDate = MagicMock
    c.QObject = QObject
    c.QRect = MagicMock
    c.QRectF = MagicMock
    c.QSize = MagicMock
    c.QPoint = MagicMock
    c.QUrl = MagicMock
    c.QFile = MagicMock

    g = types.ModuleType('PySide6.QtGui')
    g.QPixmap = MagicMock
    g.QIcon = MagicMock
    g.QFont = MagicMock
    g.QColor = MagicMock
    g.QPalette = MagicMock
    g.QSize = MagicMock
    g.QPoint = MagicMock
    g.QTextCursor = MagicMock
    g.QPainter = MagicMock
    g.QPen = MagicMock
    g.QBrush = MagicMock

    ch = types.ModuleType('PySide6.QtCharts')
    ch.QChart = MagicMock(return_value=MagicMock())
    for name in ['QLineSeries', 'QBarSeries', 'QPieSeries', 'QValueAxis', 'QBarSet', 'QAreaSeries']:
        setattr(ch, name, MagicMock)

    wm = types.ModuleType('PySide6.QtWebEngineWidgets')
    wm.QWebEngineView = QWidget
    wm.QWebEnginePage = MagicMock

    p = types.ModuleType('PySide6')
    sys.modules['PySide6'] = p
    sys.modules['PySide6.QtWidgets'] = w
    sys.modules['PySide6.QtGui'] = g
    sys.modules['PySide6.QtCore'] = c
    sys.modules['PySide6.QtCharts'] = ch
    sys.modules['PySide6.QtWebEngineWidgets'] = wm


if __name__ == '__main__':
    install_qt()
    if 'numpy' not in sys.modules:
        sys.modules['numpy'] = MagicMock()

    # Remove cached acas_pro modules
    to_remove = [k for k in sys.modules if k.startswith('acas_pro')]
    for k in to_remove:
        del sys.modules[k]

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

    # Mock config to avoid DB
    cfg_mock = MagicMock()
    sys.modules['acas_pro.core.config'] = cfg_mock

    pages = [
        ('acas_pro.ui.pages.settings', 'SettingsPage'),
        ('acas_pro.ui.pages.ad_manager', 'AdManagerPage'),
        ('acas_pro.ui.pages.avatar_studio', 'AvatarStudioPage'),
        ('acas_pro.ui.pages.video_maker', 'VideoMakerPage'),
        ('acas_pro.ui.pages.intelligence', 'IntelligencePage'),
        ('acas_pro.ui.pages.publish_manager', 'PublishManagerPage'),
        ('acas_pro.ui.pages.account_management', 'AccountManagementPage'),
        ('acas_pro.ui.pages.ecommerce_manager', 'EcommerceManagerPage'),
        ('acas_pro.ui.pages.content_creation', 'ContentCreationPage'),
        ('acas_pro.ui.pages.festival_calendar', 'FestivalCalendarPage'),
        ('acas_pro.ui.pages.blockchain_settlement', 'BlockchainSettlementPage'),
        ('acas_pro.ui.pages.llm_chat', 'LLMChatPage'),
        ('acas_pro.ui.pages.advanced_analytics', 'AdvancedAnalyticsPage'),
        ('acas_pro.ui.pages.dashboard', 'DashboardPage'),
        ('acas_pro.ui.pages.forecast', 'ForecastPage'),
        ('acas_pro.ui.pages.inventory', 'InventoryPage'),
        ('acas_pro.ui.auth.login_dialog', 'LoginDialog'),
    ]

    results = []
    for mod_path, cls_name in pages:
        try:
            mod = importlib.import_module(mod_path)
            cls = getattr(mod, cls_name, None)
            if cls is None:
                results.append(f'SKIP {mod_path}: {cls_name} not found')
                continue
            # Remove from cache for clean import
            if mod_path in sys.modules:
                del sys.modules[mod_path]
            mod = importlib.import_module(mod_path)
            cls = getattr(mod, cls_name)
            try:
                obj = cls()
                results.append(f'OK   {mod_path}: {cls_name} instantiated')
            except Exception as e:
                err = str(e)[:80]
                results.append(f'FAIL {mod_path}: {cls_name} - {type(e).__name__}: {err}')
        except Exception as e:
            results.append(f'IMP  {mod_path}: {type(e).__name__}: {str(e)[:60]}')

    for r in results:
        print(r)
    ok = sum(1 for r in results if r.startswith('OK'))
    fail = sum(1 for r in results if r.startswith('FAIL'))
    imp = sum(1 for r in results if r.startswith('IMP'))
    print(f'\n{ok} OK, {fail} FAIL, {imp} IMPORT')
