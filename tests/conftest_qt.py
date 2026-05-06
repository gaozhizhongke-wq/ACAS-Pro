#!/usr/bin/env python3
"""Qt mock for testing UI modules without PySide6"""
import sys
from unittest.mock import MagicMock

# Create mock PySide6 module
class QtMockMeta(type):
    def __getattr__(cls, name):
        return MagicMock()

class MockWidget(metaclass=QtMockMeta):
    def __init__(self, *args, **kwargs):
        for key, val in kwargs.items():
            setattr(self, key, val)
    def __getattr__(self, name):
        return MagicMock()
    def setLayout(self, *a): pass
    def addWidget(self, *a): pass
    def addLayout(self, *a): pass
    def setText(self, t): self._text = t
    def text(self): return getattr(self, '_text', '')
    def setChecked(self, c): self._checked = c
    def isChecked(self): return getattr(self, '_checked', False)
    def setValue(self, v): self._value = v
    def value(self): return getattr(self, '_value', 0)
    def setCurrentIndex(self, i): self._idx = i
    def currentIndex(self): return getattr(self, '_idx', 0)
    def count(self): return 0
    def addItem(self, *a): pass
    def addTab(self, *a): pass
    def addRow(self, *a): pass
    def setLayout(self, l): self._layout = l
    def layout(self): return getattr(self, '_layout', MagicMock())
    def children(self): return []
    def findChild(self, *a): return None
    def findChildren(self, *a): return []
    def setObjectName(self, n): self._objname = n
    def objectName(self): return getattr(self, '_objname', '')
    def show(self): pass
    def hide(self): pass
    def close(self): pass
    def resize(self, *a): pass
    def setWindowTitle(self, t): pass
    def setToolTip(self, t): pass
    def setEnabled(self, e): pass
    def setSizePolicy(self, *a): pass
    def setMinimumSize(self, *a): pass
    def setMaximumSize(self, *a): pass
    def connect(self, *a): pass
    def emit(self, *a): pass
    def clicked(self): return MagicMock()
    def textChanged(self): return MagicMock()
    def currentIndexChanged(self): return MagicMock()
    def returnPressed(self): return MagicMock()
    def triggered(self): return MagicMock()
    def toggled(self): return MagicMock()
    def accepted(self): return MagicMock()
    def rejected(self): return MagicMock()
    def finished(self): return MagicMock()

class MockApplication(MockWidget):
    instance = None
    def __init__(self, *a, **kw):
        MockApplication.instance = self
    @classmethod
    def exec(cls): return 0
    @classmethod
    def processEvents(cls): pass

class MockSignal:
    def connect(self, *a): pass
    def disconnect(self, *a): pass
    def emit(self, *a): pass

# Setup mock modules
mock_pyside6 = MagicMock()
mock_pyside6.QtWidgets = MagicMock()
mock_pyside6.QtCore = MagicMock()
mock_pyside6.QtGui = MagicMock()

# Key classes
for name in ['QApplication', 'QWidget', 'QMainWindow', 'QDialog', 
             'QPushButton', 'QLabel', 'QLineEdit', 'QTextEdit', 'QComboBox',
             'QCheckBox', 'QRadioButton', 'QSpinBox', 'QDoubleSpinBox',
             'QSlider', 'QProgressBar', 'QTabWidget', 'QStackedWidget',
             'QListWidget', 'QTreeWidget', 'QTableWidget', 'QGroupBox',
             'QScrollArea', 'QSplitter', 'QFrame', 'QToolBar',
             'QMenuBar', 'QStatusBar', 'QFileDialog', 'QMessageBox',
             'QVBoxLayout', 'QHBoxLayout', 'QGridLayout', 'QFormLayout',
             'QSizePolicy', 'QAction', 'QMenu', 'QSystemTrayIcon']:
    setattr(mock_pyside6.QtWidgets, name, type(name, (MockWidget,), {}))

setattr(mock_pyside6.QtWidgets, 'QApplication', MockApplication)

for name in ['QObject', 'Qt', 'Signal', 'Slot', 'QTimer', 'QThread',
             'QSize', 'QPoint', 'QRect', 'QSettings', 'QModelIndex',
             'QUrl', 'QDateTime', 'QDate', 'QTime']:
    setattr(mock_pyside6.QtCore, name, type(name, (MockWidget,), {}))
setattr(mock_pyside6.QtCore, 'Signal', lambda *a: MagicMock())
setattr(mock_pyside6.QtCore, 'Slot', lambda *a: (lambda f: f))

for name in ['QIcon', 'QPixmap', 'QPainter', 'QColor', 'QFont', 
             'QPen', 'QBrush', 'QCursor', 'QKeySequence', 'QPalette',
             'QClipboard', 'QDesktopServices']:
    setattr(mock_pyside6.QtGui, name, type(name, (MockWidget,), {}))

# Install mock
sys.modules['PySide6'] = mock_pyside6
sys.modules['PySide6.QtWidgets'] = mock_pyside6.QtWidgets
sys.modules['PySide6.QtCore'] = mock_pyside6.QtCore
sys.modules['PySide6.QtGui'] = mock_pyside6.QtGui
