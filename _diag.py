"""Diagnostic for AvatarStudioPage failure."""
import sys, os, types
from unittest.mock import MagicMock
sys.modules['numpy'] = MagicMock()

MagicMock.__format__ = lambda self, spec: ''

def _noop(*a, **kw): return None

class _SM:
    def __init__(self, n='m'): self._n = n
    def __getattr__(self, n):
        if n == 'connect': return _noop
        return _SM(f'{self._n}.{n}')
    def __call__(self, *a, **kw): return _SM(f'{self._n}()')
    def __ge__(self, o): return True
    def __gt__(self, o): return True

class _FQ:
    def __init__(self, *a, **kw): pass
    def __getattr__(self, n):
        if n == 'connect': return _noop
        return _SM(n=n)
    def __call__(self, *a, **kw): return _FQ()
    def __ge__(self, o): return True

# Minimal QtWidgets
w = types.ModuleType('PySide6.QtWidgets')
w.QWidget = _FQ
for n in ['QAction','QMenu','QToolBar','QPushButton','QLabel',
          'QVBoxLayout','QHBoxLayout','QGridLayout','QFormLayout','QGroupBox',
          'QLineEdit','QTextEdit','QComboBox','QCheckBox','QTabWidget',
          'QScrollArea','QFrame','QListWidget','QTableWidget','QSplitter',
          'QProgressBar','QSpinBox','QDoubleSpinBox','QDateEdit','QDateTimeEdit',
          'QStackedWidget','QSlider','QGraphicsView','QRadioButton','QFileDialog',
          'QDialogButtonBox','QAbstractItemView','QSizePolicy','QSpacerItem',
          'QCompleter','QCalendarWidget','QTreeWidget','QStatusBar','QToolBar',
          'QGraphicsOpacityEffect','QButtonGroup','QHeaderView']:
    setattr(w, n, type(n, (_FQ,), {}))

# QTableWidgetItem etc as MagicMock
for n in ['QTableWidgetItem','QAction','QMenu','QMenuBar','QMessageBox',
          'QListWidgetItem','QGraphicsScene',
          'QGraphicsDropShadowEffect','QGraphicsBlurEffect',
          'QParallelAnimationGroup','QSequentialAnimationGroup','QPropertyAnimation']:
    m = MagicMock()
    m.setFlags = _noop
    setattr(w, n, m)

w.QDialog = type('QDialog', (_FQ,), {})
w.QMainWindow = type('QMainWindow', (_FQ,), {})
w.QObject = _FQ
sys.modules['PySide6.QtWidgets'] = w

# QtCore
c = types.ModuleType('PySide6.QtCore')
c.Qt = type('Qt', (_FQ,), {})()
c.Signal = MagicMock; c.Slot = MagicMock
c.QTimer = type('QTimer', (_FQ,), {})
c.QThread = type('QThread', (_FQ,), {})
c.QDate = type('QDate', (), {'currentDate': staticmethod(lambda: MagicMock())})
c.QDateTime = type('QDateTime', (), {'currentDateTime': staticmethod(lambda: MagicMock())})
c.QRect = MagicMock; c.QUrl = MagicMock; c.QFile = MagicMock
c.QSize = type('QSize', (_FQ,), {})()
sys.modules['PySide6.QtCore'] = c

# QtGui
g = types.ModuleType('PySide6.QtGui')
g.QPixmap = MagicMock; g.QIcon = MagicMock
g.QFont = type('QFont', (_FQ,), {}); g.QColor = type('QColor', (_FQ,), {})
g.QPalette = MagicMock; g.QTextCursor = MagicMock; g.QPainter = MagicMock
g.QAction = MagicMock
sys.modules['PySide6.QtGui'] = g

sys.modules['PySide6'] = types.ModuleType('PySide6')
sys.modules['numpy'] = MagicMock()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import logging
logging.basicConfig(level=logging.CRITICAL)

try:
    from acas_pro.ui.pages import avatar_studio
    print('Import OK', flush=True)
    try:
        page = avatar_studio.AvatarStudioPage()
        print('Instantiate OK', flush=True)
    except Exception as e:
        import traceback
        traceback.print_exc()
except Exception as e:
    import traceback
    traceback.print_exc()
