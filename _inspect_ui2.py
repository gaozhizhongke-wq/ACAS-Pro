import sys, importlib
from unittest.mock import MagicMock
if 'numpy' not in sys.modules:
    sys.modules['numpy'] = MagicMock()

# Simulate conftest PySide6 mock
import types
pyside6 = types.ModuleType('PySide6')
widgets = types.ModuleType('PySide6.QtWidgets')
gui = types.ModuleType('PySide6.QtGui')
core = types.ModuleType('PySide6.QtCore')
charts = types.ModuleType('PySide6.QtCharts')

for mod in [pyside6, widgets, gui, core, charts]:
    sys.modules[mod.__name__] = mod
pyside6.QtWidgets = widgets
pyside6.QtGui = gui
pyside6.QtCore = core
pyside6.QtCharts = charts

Qt = types.ModuleType('PySide6.QtCore.Qt')
Signal = MagicMock
Slot = MagicMock
sys.modules['PySide6.QtCore.Qt'] = Qt

for name in ['QWidget','QDialog','QMainWindow','QLabel','QPushButton','QLineEdit',
             'QTextEdit','QComboBox','QCheckBox','QTabWidget','QVBoxLayout','QHBoxLayout',
             'QGridLayout','QScrollArea','QFrame','QGroupBox','QListWidget','QTableWidget',
             'QTableWidgetItem','QSplitter','QProgressBar','QSpinBox','QDoubleSpinBox',
             'QDateEdit','QHeaderView','QAction','QMenu','QMenuBar','QStatusBar','QToolBar',
             'QFormLayout','QStackedWidget','QWebView','QWebEngineView','QGraphicsView',
             'QGraphicsScene','QGraphicsDropShadowEffect','QGraphicsOpacityEffect',
             'QGraphicsBlurEffect','QParallelAnimationGroup','QSequentialAnimationGroup',
             'QPropertyAnimation','QEasingCurve','QGraphicsItem']:
    setattr(widgets, name, MagicMock(return_value=MagicMock()))

for name in ['QPixmap','QIcon','QFont','QColor','QSize','QPoint','QRect','QByteArray','QUrl']:
    setattr(gui, name, MagicMock)

for name in ['QTimer','QThread','QDateTime','QDate','QTime','Signal','Slot','Property','QObject']:
    setattr(core, name, MagicMock)

setattr(charts, 'QChart', MagicMock(return_value=MagicMock()))
setattr(charts, 'QLineSeries', MagicMock)
setattr(charts, 'QBarSeries', MagicMock)
setattr(charts, 'QPieSeries', MagicMock)
setattr(charts, 'QValueAxis', MagicMock)
setattr(charts, 'QBarSet', MagicMock)

# Now try importing UI pages
for modpath in [
    'acas_pro.ui.pages.settings',
    'acas_pro.ui.pages.advanced_analytics',
    'acas_pro.ui.pages.ad_manager',
    'acas_pro.ui.pages.avatar_studio',
    'acas_pro.ui.pages.intelligence',
    'acas_pro.ui.pages.video_maker',
    'acas_pro.ui.pages.llm_chat',
    'acas_pro.ui.pages.publish_manager',
    'acas_pro.ui.pages.account_management',
    'acas_pro.ui.pages.ecommerce_manager',
    'acas_pro.ui.pages.content_creation',
    'acas_pro.ui.pages.festival_calendar',
    'acas_pro.ui.pages.blockchain_settlement',
    'acas_pro.ui.auth.login_dialog',
    'acas_pro.ui.main_window',
]:
    try:
        mod = importlib.import_module(modpath)
        classes = [n for n in dir(mod) if n[0].isupper() and isinstance(getattr(mod,n,None), type)
                   and n not in ('QWidget','QDialog','QMainWindow','QObject','QThread','QTimer')]
        if classes:
            print(f'{modpath}: OK - {classes}')
        else:
            print(f'{modpath}: OK (no classes)')
    except Exception as e:
        print(f'{modpath}: ERR {str(e)[:80]}')
