"""Inspect UI pages to understand method signatures."""
import sys
from unittest.mock import MagicMock
import inspect

# Mock PySide6
pyside6 = MagicMock()
widgets = MagicMock()
core = MagicMock()
gui = MagicMock()
charts = MagicMock()
for cls_name in [
    'QWidget', 'QMainWindow', 'QDialog', 'QVBoxLayout', 'QHBoxLayout', 'QFormLayout',
    'QGridLayout', 'QLabel', 'QPushButton', 'QLineEdit', 'QTextEdit', 'QComboBox',
    'QCheckBox', 'QSpinBox', 'QDoubleSpinBox', 'QTableWidget', 'QTableWidgetItem',
    'QTabWidget', 'QListWidget', 'QListWidgetItem', 'QTreeWidget', 'QTreeWidgetItem',
    'QSplitter', 'QScrollArea', 'QGroupBox', 'QProgressBar', 'QSlider', 'QRadioButton',
    'QDateEdit', 'QTimeEdit', 'QCalendarWidget', 'QMenu', 'QMenuBar', 'QStatusBar',
    'QToolBar', 'QAction', 'QActionGroup', 'QWebView', 'QWebEngineView', 'QStackedWidget',
    'QFrame', 'QGraphicsView', 'QGraphicsScene', 'QDockWidget', 'QMdiArea',
    'QHeaderView', 'QAbstractItemView', 'QDialogButtonBox', 'QFileDialog',
    'QMessageBox', 'QInputDialog', 'QPainter', 'QColor', 'QFont', 'QIcon', 'QPixmap',
    'QTimer', 'QThread', 'QThreadPool', 'QRunnable', 'QMutex', 'QSemaphore',
    'QApplication', 'QSize', 'QPoint', 'QRect', 'QRectF', 'QMargins',
    'QSizePolicy', 'QPalette', 'QBrush', 'QPen', 'QCursor', 'QPolygonF',
    'QTextCursor', 'QTextCharFormat', 'QSyntaxHighlighter', 'QCompleter',
    'QScrollArea', 'QToolButton', 'QToolBox', 'QStandardItemModel', 'QStandardItem',
    'QSortFilterProxyModel', 'QGraphicsPixmapItem', 'QGraphicsTextItem',
    'QPainterPath', 'QLinearGradient', 'QFontMetrics', 'QGraphicsOpacityEffect',
    'QPropertyAnimation', 'QEasingCurve', 'QParallelAnimationGroup', 'QSequentialAnimationGroup',
    'QJsonDocument', 'QJsonObject', 'QJsonArray', 'QJsonValue', 'QFile', 'QFileInfo',
    'QFileSystemModel', 'QStyledItemDelegate', 'QGraphicsEffect', 'QOpacityEffect',
]:
    setattr(widgets, cls_name, MagicMock(return_value=MagicMock()))
for attr_name in ['QTimer', 'QThread', 'QDateTime', 'QDate', 'QTime', 'Qt', 'Signal',
                  'Slot', 'Property', 'QModelIndex', 'QVariant', 'QSize', 'QPoint',
                  'QRect', 'QRectF', 'QUrl', 'QIODevice', 'QByteArray', 'QEmitInterval',
                  'QObject', 'pyqtSignal', 'pyqtSlot']:
    setattr(core, attr_name, MagicMock())
setattr(gui, 'QPainter', MagicMock())
setattr(gui, 'QPen', MagicMock())
setattr(gui, 'QBrush', MagicMock())
setattr(gui, 'QColor', MagicMock())
setattr(gui, 'QFont', MagicMock())
setattr(gui, 'QIcon', MagicMock())
setattr(gui, 'QPixmap', MagicMock())
setattr(gui, 'QCursor', MagicMock())
setattr(gui, 'QPolygonF', MagicMock())
setattr(gui, 'QTextCursor', MagicMock())
setattr(gui, 'QSyntaxHighlighter', MagicMock())
setattr(gui, 'QTextCharFormat', MagicMock())
setattr(gui, 'QAction', MagicMock())
setattr(gui, 'QPainterPath', MagicMock())
setattr(gui, 'QLinearGradient', MagicMock())
setattr(gui, 'QFontMetrics', MagicMock())
sys.modules['PySide6'] = pyside6
sys.modules['PySide6.QtWidgets'] = widgets
sys.modules['PySide6.QtCore'] = core
sys.modules['PySide6.QtGui'] = gui
sys.modules['PySide6.QtCharts'] = charts
for key in list(sys.modules.keys()):
    if 'PySide6.Qt' in key and key not in ['PySide6.QtWidgets', 'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtCharts']:
        del sys.modules[key]

import os  # noqa: E402
os.environ['ACAS_PRO_ENV'] = 'test'

from acas_pro.ui.pages.ad_manager import AdManagerPage  # noqa: E402

cls = AdManagerPage
print(f"Class: {cls.__name__}")
print(f"Bases: {[b.__name__ for b in cls.__mro__[:4]]}")
print()
print("=== Public Methods ===")
for name in sorted(dir(cls)):
    if name.startswith('_'):
        continue
    attr = getattr(cls, name, None)
    if attr and callable(attr):
        try:
            sig = inspect.signature(attr)
            params = list(sig.parameters.keys())
            params_no_self = [p for p in params if p != 'self']
            defaults = sum(1 for p in params if sig.parameters[p].default != inspect.Parameter.empty)
            req = len(params_no_self) - defaults
            if req > 0:
                print(f"  {name}({', '.join(params_no_self)}) [{req} required, {defaults} default]")
        except Exception as e:
            print(f"  {name}(...) [err: {e}]")
