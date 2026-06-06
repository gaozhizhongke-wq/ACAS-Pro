"""
Pytest configuration and shared fixtures for ACAS Pro tests
"""
import os
import sys
import tempfile
import platform
import shutil
from pathlib import Path

import pytest
from unittest.mock import MagicMock, patch
from types import ModuleType

# Windows: suppress pytest symlink cleanup PermissionError (WinError 5)
if platform.system() == 'Windows':
    try:
        import _pytest.pathlib as _pl
        _orig_cleanup = getattr(_pl, 'cleanup_dead_symlinks', None)
        if _orig_cleanup:
            def _safe_cleanup(root):
                try:
                    _orig_cleanup(root)
                except PermissionError:
                    pass
            _pl.cleanup_dead_symlinks = _safe_cleanup
    except Exception:
        pass

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# --- Comprehensive PySide6 mock ---
def _make_widget_mock():
    """Create a comprehensive PySide6 module mock with all needed widget classes."""
    pyside6 = ModuleType('mock_pyside6')
    widgets = ModuleType('mock_widgets')
    core = ModuleType('mock_core')
    gui = ModuleType('mock_gui')
    charts = ModuleType('mock_charts')

    widget_names = [
        'QWidget', 'QMainWindow', 'QDialog', 'QDialogButtonBox',
        'QLabel', 'QPushButton', 'QVBoxLayout', 'QHBoxLayout',
        'QStackedWidget', 'QFrame', 'QScrollArea', 'QMessageBox',
        'QLineEdit', 'QTableWidget', 'QTableWidgetItem', 'QHeaderView',
        'QGroupBox', 'QComboBox', 'QSpinBox', 'QDoubleSpinBox',
        'QTextEdit', 'QCheckBox', 'QSlider', 'QSpacerItem', 'QSizePolicy',
        'QTabWidget', 'QTabBar', 'QListWidget', 'QListWidgetItem',
        'QProgressBar', 'QSplitter', 'QMenu', 'QMenuBar', 'QToolBar',
        'QStatusBar', 'QAction', 'QTimer', 'QGraphicsView',
        'QGraphicsScene', 'QGraphicsPixmapItem', 'QGraphicsTextItem',
        'QGraphicsEffect', 'QGraphicsOpacityEffect', 'QGraphicsBlurEffect',
        'QPointF', 'QLineF', 'QRectF', 'QSize', 'QPoint',
        'QGridLayout', 'QFormLayout', 'QRadioButton', 'QButtonGroup',
        'QPropertyAnimation', 'QEasingCurve', 'QPalette', 'QColor',
        'QFont', 'QFontMetrics', 'QPixmap', 'QImage', 'QByteArray',
        'QBuffer', 'QIODevice', 'QDateEdit', 'QDateTimeEdit', 'QDate',
        'QTime', 'QDateTime', 'QUrl', 'QFileDialog', 'QInputDialog',
        'QPainter', 'QPen', 'QBrush', 'QLinearGradient', 'QRadialGradient',
        'QPolygonF', 'QAbstractItemView', 'QTextCursor', 'QTextBlock',
        'QTextCharFormat', 'QSyntaxHighlighter', 'QStandardItemModel',
        'QStandardItem', 'QTreeView', 'QTreeWidget', 'QTreeWidgetItem',
        'QAbstractSpinBox', 'QCompleter', 'QToolButton', 'QTextEdit',
        'QWebEngineView', 'QWebEnginePage', 'QCalendarWidget',
        'QTextBrowser', 'QPlainTextEdit',
    ]

    for name in widget_names:
        setattr(widgets, name, MagicMock(return_value=MagicMock()))

    mock_qt = MagicMock()
    for attr in ['AlignLeft', 'AlignRight', 'AlignCenter', 'AlignTop', 'AlignBottom',
                 'Horizontal', 'Vertical', 'Window', 'Dialog', 'Tool', 'Sheet',
                 'DisplayRole', 'EditRole', 'CheckStateRole', 'UserRole',
                 'LeftToRight', 'NoFocus', 'NoFrame']:
        setattr(mock_qt, attr, 1)
    mock_qt.AlignmentFlag = type('AlignmentFlag', (), {
        'AlignLeft': 1, 'AlignRight': 2, 'AlignCenter': 4, 'AlignHCenter': 8
    })
    mock_qt.ItemDataRole = type('ItemDataRole', (), {'DisplayRole': 0, 'EditRole': 1})
    mock_qt.Orientation = type('Orientation', (), {'Horizontal': 0, 'Vertical': 1})
    mock_qt.WindowType = type('WindowType', (), {'Window': 1, 'Dialog': 2})
    mock_qt.CheckState = type('CheckState', (), {'Checked': 2, 'Unchecked': 0})
    mock_qt.GlobalColor = type('GlobalColor', (), {
        'white': 0, 'black': 1, 'red': 2, 'green': 3, 'blue': 4,
        'cyan': 5, 'magenta': 6, 'yellow': 7, 'gray': 8, 'lightGray': 9
    })
    mock_qt.SizePolicy = type('SizePolicy', (), {
        'Fixed': 0, 'Minimum': 1, 'Maximum': 4, 'Preferred': 5,
        'Expanding': 7, 'MinimumExpanding': 3, 'Ignored': 13,
    })
    core.Qt = mock_qt
    core.Signal = MagicMock
    core.Slot = MagicMock
    core.Property = MagicMock
    core.QSize = MagicMock(return_value=MagicMock())
    core.QTimer = MagicMock(return_value=MagicMock())
    core.QThread = MagicMock
    core.QObject = MagicMock
    core.QCoreApplication = MagicMock
    core.QDate = MagicMock
    core.QDateTime = MagicMock
    core.QUrl = MagicMock

    gui.QFont = MagicMock(return_value=MagicMock())
    gui.QIcon = MagicMock(return_value=MagicMock())
    gui.QPixmap = MagicMock(return_value=MagicMock())
    gui.QImage = MagicMock(return_value=MagicMock())
    gui.QColor = MagicMock(return_value=MagicMock())
    gui.QPalette = MagicMock(return_value=MagicMock())
    gui.QPainter = MagicMock()
    gui.QPen = MagicMock(return_value=MagicMock())
    gui.QBrush = MagicMock(return_value=MagicMock())
    gui.QLinearGradient = MagicMock(return_value=MagicMock())
    gui.QFontMetrics = MagicMock(return_value=MagicMock())
    gui.QCursor = MagicMock
    gui.QPolygonF = MagicMock
    gui.QTextCursor = MagicMock
    gui.QSyntaxHighlighter = MagicMock
    gui.QTextCharFormat = MagicMock
    gui.QAction = MagicMock

    # Attach sub-modules to main module for proper import resolution
    pyside6.QtWidgets = widgets
    pyside6.QtCore = core
    pyside6.QtGui = gui
    pyside6.QtCharts = charts

    sys.modules['PySide6'] = pyside6
    sys.modules['PySide6.QtWidgets'] = widgets
    sys.modules['PySide6.QtCore'] = core
    sys.modules['PySide6.QtGui'] = gui
    sys.modules['PySide6.QtCharts'] = charts
    # Clear any stale sub-modules
    for key in list(sys.modules.keys()):
        if 'PySide6.Qt' in key and key not in ['PySide6.QtWidgets', 'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtCharts']:
            del sys.modules[key]
    
    return pyside6


_make_widget_mock()

# NOTE: Flask, flask_cors, flask_limiter are NOT mocked globally - web route tests need real Flask

# Mock psycopg2 for database_pg tests
if 'psycopg2' not in sys.modules:
    _psycopg2 = MagicMock()
    _psycopg2.pool = MagicMock()
    _psycopg2.pool.ThreadedConnectionPool = MagicMock
    _psycopg2.extras = MagicMock()
    _psycopg2.extras.RealDictCursor = MagicMock
    _psycopg2.sql = MagicMock()
    sys.modules['psycopg2'] = _psycopg2
    sys.modules['psycopg2.pool'] = _psycopg2.pool
    sys.modules['psycopg2.extras'] = _psycopg2.extras
    sys.modules['psycopg2.sql'] = _psycopg2.sql

# NOTE: Do NOT globally mock requests - E2E tests need real HTTP calls
# If specific tests need mocked requests, use local fixtures instead

# Mock psutil for monitoring
if 'psutil' not in sys.modules:
    sys.modules['psutil'] = MagicMock()

# Mock ML/data science libraries
# NOTE: numpy/pandas/scipy are NOT mocked globally - forecast engine needs real np.array()
#       Tests that can't import these should use local fixtures/mock instead
# NOTE: Removed 'playwright' from global mock - tests needing real playwright should import it directly
for _ml_mod in ['torch', 'transformers', 'scikit-learn', 'sklearn',
                 'matplotlib', 'PIL', 'pillow', 'cv2',
                 'feedparser', 'bs4', 'beautifulsoup4', 'lxml',
                 'openai', 'anthropic', 'google.generativeai',
                 'tqdm', 'aiohttp', 'httpx', 'boto3',
                 'schedule', 'apscheduler', 'celery',
                 'qrcode', 'Pillow', 'moviepy', 'pydub',
                 'selenium', 'undetected_chromedriver',
                 'praw', 'tweepy', 'weibo', 'douban',
                 'timesfm', 'prophet', 'statsmodels',
                 'sqlalchemy', 'alembic']:
    if _ml_mod not in sys.modules:
        sys.modules[_ml_mod] = MagicMock()

# Setup PySide6 mock BEFORE any test runs
_make_widget_mock()


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for tests"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_home(tmp_path):
    """Mock Path.home() to return a temporary directory"""
    with patch.object(Path, 'home', return_value=tmp_path):
        yield tmp_path


@pytest.fixture
def clean_env():
    """Clean environment variables for tests"""
    original_env = os.environ.copy()
    # Clear sensitive env vars
    for key in list(os.environ.keys()):
        if any(x in key.upper() for x in ['SECRET', 'KEY', 'TOKEN', 'PASSWORD']):
            del os.environ[key]
    yield
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def sample_config_data():
    """Sample configuration data for tests"""
    return {
        "name": "Test Config",
        "version": "1.0.0",
        "environment": "development",
        "debug": True,
        "database": {
            "type": "sqlite",
            "name": "test.db"
        },
        "security": {
            "secret_key": "test_secret_key_32_chars_long!!",
            "password_min_length": 8
        },
        "llm": {
            "enabled": False
        }
    }


# --- Test isolation: reset singletons WITHOUT deleting modules ---
# Deleting acas_pro modules from sys.modules breaks monkeypatch.setattr:
#   auth.py does `import acas_pro.core.security as _sec` at import time.
#   After module deletion + re-import, `_sec` still points to the OLD module
#   object, so patches on the new module have no effect.
# Fix: use the official _reset_lazy_instances() from security.py.


@pytest.fixture(autouse=True, scope="function")
def _reset_lazy_singletons():
    """Reset lazy singletons between tests without deleting module objects."""
    # Use the official reset function provided by security.py
    import acas_pro.core.security as _sec
    _sec._reset_lazy_instances()

    # Also reset user_service.py lazy singletons
    import acas_pro.services.user_service as _us
    _us._reset_lazy()

    # If jwt was fully replaced by a MagicMock, restore the real module
    if 'jwt' in sys.modules:
        import jwt as _jwt_check
        if not hasattr(_jwt_check, 'decode'):
            del sys.modules['jwt']

    yield

    # After test: only clean up jwt if it's still a non-real mock
    if 'jwt' in sys.modules:
        import jwt as _jwt_check2
        if not hasattr(_jwt_check2, 'decode'):
            del sys.modules['jwt']

    # Do NOT delete acas_pro.* — see comment above.


# --- Flask test fixtures ---
@pytest.fixture
def app():
    """Create and configure a Flask app for testing."""
    from acas_pro.web import create_app
    test_config = {
        'TESTING': True,
        'SECRET_KEY': 'test-secret-key-32-chars-long!!',
        'DATABASE': 'test.db',
        'ENVIRONMENT': 'development'
    }
    app = create_app(test_config)
    return app


@pytest.fixture
def client(app):
    """Create a test client for the app."""
    return app.test_client()




# Windows: clean up pytest-current on exit to prevent stale junction next run
if platform.system() == 'Windows':
    @pytest.hookimpl(trylast=True)
    def pytest_unconfigure(config):
        """Clean up pytest-current on exit to prevent PermissionError on next run."""
        try:
            pytest_current = Path(tempfile.gettempdir()) / f'pytest-of-{os.getlogin()}' / 'pytest-current'
            # Use os.path.exists which doesn't raise PermissionError on Windows
            if os.path.exists(str(pytest_current)) or os.path.islink(str(pytest_current)):
                try:
                    if os.path.isdir(str(pytest_current)):
                        shutil.rmtree(str(pytest_current), ignore_errors=True)
                    else:
                        os.unlink(str(pytest_current))
                except (OSError, PermissionError):
                    pass
        except (OSError, PermissionError):
            pass
    pytest_unconfigure.hookimpl = pytest.hookimpl(trylast=True)(pytest_unconfigure)

