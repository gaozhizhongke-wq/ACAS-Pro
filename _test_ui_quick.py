import sys, os, types
from unittest.mock import MagicMock

class _FQ:
    def __init__(self, *a, **kw): pass
    def __getattr__(self, n): return MagicMock()
    def __setattr__(self, n, v): object.__setattr__(self, n, v)
    def __iter__(self): return iter([])
    def __bool__(self): return True

QWidget = type('QWidget', (_FQ,), {})
QDialog = type('QDialog', (QWidget,), {})
QMainWindow = type('QMainWindow', (QWidget,), {})
QObject = QWidget

w = types.ModuleType('PySide6.QtWidgets')
w.QWidget = QWidget; w.QDialog = QDialog; w.QMainWindow = QMainWindow; w.QObject = QObject
for name in ['QLabel','QPushButton','QLineEdit','QTextEdit','QComboBox','QCheckBox','QTabWidget','QScrollArea','QFrame','QGroupBox','QListWidget','QTableWidget','QSplitter','QProgressBar','QSpinBox','QDoubleSpinBox','QDateEdit','QStackedWidget','QSlider','QGraphicsView','QRadioButton','QFileDialog','QDialogButtonBox','QSizePolicy','QSpacerItem','QCompleter','QCalendarWidget','QTreeWidget','QTreeWidgetItem','QStatusBar','QToolBar','QGraphicsOpacityEffect']:
    setattr(w, name, QWidget)
for name in ['QTableWidgetItem','QHeaderView','QAction','QMenu','QMenuBar','QMessageBox','QListWidgetItem','QGraphicsScene','QTreeWidgetItem','QGraphicsDropShadowEffect','QGraphicsBlurEffect','QParallelAnimationGroup','QSequentialAnimationGroup','QPropertyAnimation']:
    setattr(w, name, MagicMock)
for name in ['QVBoxLayout','QHBoxLayout','QGridLayout','QFormLayout']:
    setattr(w, name, MagicMock(return_value=MagicMock()))

c = types.ModuleType('PySide6.QtCore')
c.Qt = MagicMock()
c.Qt.FontWeight = type('FW', (), {'Bold': 75, 'Normal': 50})
c.Qt.GlobalColor = type('GC', (), {'red': 0, 'green': 1, 'blue': 2, 'black': 3, 'white': 4})
c.Signal = MagicMock; c.Slot = MagicMock; c.QTimer = MagicMock; c.QThread = MagicMock
c.QDateTime = MagicMock; c.QDate = MagicMock; c.QObject = QObject; c.QRect = MagicMock
c.QUrl = MagicMock; c.QFile = MagicMock

g = types.ModuleType('PySide6.QtGui')
g.QPixmap = MagicMock; g.QIcon = MagicMock; g.QFont = MagicMock; g.QColor = MagicMock
g.QPalette = MagicMock; g.QSize = MagicMock; g.QPoint = MagicMock; g.QTextCursor = MagicMock

sys.modules['PySide6'] = types.ModuleType('PySide6')
sys.modules['PySide6.QtWidgets'] = w; sys.modules['PySide6.QtGui'] = g; sys.modules['PySide6.QtCore'] = c
sys.modules['numpy'] = MagicMock()
sys.path.insert(0, 'src')
sys.modules['acas_pro.core.config'] = MagicMock()

for k in [k for k in sys.modules if k.startswith('acas_pro')]:
    del sys.modules[k]

pages = [
    ('acas_pro.ui.pages.settings', 'SettingsPage'),
    ('acas_pro.ui.pages.dashboard', 'DashboardPage'),
    ('acas_pro.ui.pages.forecast', 'ForecastPage'),
    ('acas_pro.ui.pages.inventory', 'InventoryPage'),
    ('acas_pro.ui.pages.festival_calendar', 'FestivalCalendarPage'),
    ('acas_pro.ui.pages.content_creation', 'ContentCreationPage'),
    ('acas_pro.ui.pages.intelligence', 'IntelligencePage'),
]

for mod_path, cls_name in pages:
    try:
        print(f'  Testing {cls_name}...', flush=True)
        mod = __import__(mod_path, fromlist=[cls_name])
        cls = getattr(mod, cls_name)
        methods = [m for m in dir(cls) if not m.startswith('_') and callable(getattr(cls, m, None))]
        try:
            obj = cls()
            print(f'    OK: instantiated ({len(methods)} methods)')
        except Exception as e:
            print(f'    INIT FAIL: {type(e).__name__}: {str(e)[:60]}')
    except Exception as e:
        print(f'    IMPORT FAIL: {type(e).__name__}: {str(e)[:60]}')
    # Clear cache
    for k in [k for k in sys.modules if k.startswith('acas_pro')]:
        del sys.modules[k]
