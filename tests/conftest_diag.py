"""Temp conftest for pollution diagnostics - replace conftest.py with this"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from unittest.mock import MagicMock

# ── PySide6 mock (from original conftest) ──
from types import ModuleType

def _make_widget_mock():
    pyside6 = ModuleType('mock_pyside6')
    widgets = ModuleType('mock_widgets')
    core = ModuleType('mock_core')
    gui = ModuleType('mock_gui')
    charts = ModuleType('mock_charts')
    for name in ['QWidget','QMainWindow','QDialog','QDialogButtonBox','QLabel','QPushButton','QVBoxLayout','QHBoxLayout','QStackedWidget','QFrame','QScrollArea','QMessageBox','QLineEdit','QTableWidget','QTableWidgetItem','QHeaderView','QGroupBox','QComboBox','QSpinBox','QDoubleSpinBox','QTextEdit','QCheckBox','QSlider','QSpacerItem','QSizePolicy','QTabWidget','QTabBar','QListWidget','QListWidgetItem','QProgressBar','QSplitter','QMenu','QMenuBar','QToolBar','QStatusBar','QAction','QTimer','QGraphicsView','QGraphicsScene','QGraphicsPixmapItem','QGraphicsTextItem','QGraphicsEffect','QGraphicsOpacityEffect','QGraphicsBlurEffect','QPointF','QLineF','QRectF','QSize','QPoint','QGridLayout','QFormLayout','QRadioButton','QButtonGroup']:
        setattr(widgets, name, MagicMock(return_value=MagicMock()))
    mock_qt = MagicMock()
    for attr in ['AlignLeft','AlignRight','AlignCenter','Horizontal','Vertical']:
        setattr(mock_qt, attr, 1)
    core.Qt = mock_qt
    core.Signal = MagicMock
    core.Slot = MagicMock
    core.Property = MagicMock
    core.QSize = MagicMock(return_value=MagicMock())
    core.QTimer = MagicMock(return_value=MagicMock())
    core.QThread = MagicMock
    core.QObject = MagicMock
    sys.modules['PySide6'] = pyside6
    sys.modules['PySide6.QtWidgets'] = widgets
    sys.modules['PySide6.QtCore'] = core
    sys.modules['PySide6.QtGui'] = gui
    sys.modules['PySide6.QtCharts'] = charts
_make_widget_mock()

sys.modules['flask'] = MagicMock()
sys.modules['flask_cors'] = MagicMock()
sys.modules['flask_limiter'] = MagicMock()
sys.modules['psutil'] = MagicMock()
for _m in ['numpy','torch','transformers','scikit-learn','sklearn','pandas','scipy','matplotlib','PIL','pillow','feedparser','bs4','openai','anthropic','tqdm','aiohttp','httpx','boto3','qrcode','Pillow','sqlalchemy','alembic']:
    if _m not in sys.modules:
        sys.modules[_m] = MagicMock()

import tempfile  # noqa: E402

@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
def mock_home(tmp_path):
    with patch.object(Path, 'home', return_value=tmp_path):  # noqa: F821
        yield tmp_path

# ── Pollution diagnostics ──

def pytest_collection_finish(session):
    try:
        import acas_pro.core.security as sec
        gc = sec.__dict__.get('get_config')
        is_mock = isinstance(gc, MagicMock)
        if is_mock:
            print("\n[COLLECTION] POLLUTED! security.get_config is MagicMock")
        else:
            print(f"\n[COLLECTION] OK: security.get_config type={type(gc).__name__}")
    except Exception as e:
        print(f"\n[COLLECTION] Error: {e}")

def pytest_runtest_teardown(item, nextitem):
    try:
        import acas_pro.core.security as sec
        gc = sec.__dict__.get('get_config')
        if gc is not None and isinstance(gc, MagicMock):
            print(f"\n[POLLUTED] After {item.nodeid}")
    except:  # noqa: E722
        pass

def pytest_sessionfinish(session, exitstatus):
    try:
        import acas_pro.core.security as sec
        gc = sec.__dict__.get('get_config')
        is_mock = isinstance(gc, MagicMock)
        result = sec._cfg()
        alg = result.security.jwt_algorithm
        alg_is_mock = isinstance(alg, MagicMock)
        print(f"\n[FINAL] security.get_config is MagicMock: {is_mock}")
        print(f"[FINAL] _cfg().security.jwt_algorithm is MagicMock: {alg_is_mock}")
    except Exception as e:
        print(f"\n[FINAL] Error: {e}")
