import sys, importlib, inspect
from unittest.mock import MagicMock
if 'numpy' not in sys.modules:
    sys.modules['numpy'] = MagicMock()

# Check what UI page classes exist and their init signatures
for modpath in [
    'acas_pro.ui.pages.settings',
    'acas_pro.ui.pages.advanced_analytics',
    'acas_pro.ui.pages.ad_manager',
    'acas_pro.ui.pages.avatar_studio',
    'acas_pro.ui.pages.intelligence',
    'acas_pro.ui.pages.blockchain_settlement',
    'acas_pro.ui.pages.video_maker',
    'acas_pro.ui.pages.llm_chat',
    'acas_pro.ui.pages.publish_manager',
    'acas_pro.ui.pages.account_management',
    'acas_pro.ui.pages.ecommerce_manager',
    'acas_pro.ui.pages.content_creation',
    'acas_pro.ui.pages.festival_calendar',
    'acas_pro.ui.auth.login_dialog',
    'acas_pro.ui.main_window',
]:
    try:
        mod = importlib.import_module(modpath)
        classes = [n for n in dir(mod) if n[0].isupper() and isinstance(getattr(mod,n,None), type) and n not in ('QDialog','QWidget','QMainWindow','QObject','QThread','QTimer','QLabel','QPushButton','QLineEdit','QTextEdit','QComboBox','QCheckBox','QTabWidget','QVBoxLayout','QHBoxLayout','QGridLayout','QScrollArea','QFrame','QGroupBox','QListWidget','QTableWidget','QTableWidgetItem','QSplitter','QProgressBar','QSpinBox','QDoubleSpinBox','QDateEdit','QHeaderView','QAction','QMenu','QMenuBar','QStatusBar','QToolBar','QFormLayout','QStackedWidget','QWebView','QWebEngineView','QPixmap','QIcon','QFont','QColor','QSize','QPoint','QRect','QByteArray','QUrl','QSignalMapper','QPropertyAnimation','QEasingCurve','QGraphicsView','QGraphicsScene','QGraphicsItem','QGraphicsDropShadowEffect','QParallelAnimationGroup','QSequentialAnimationGroup','QGraphicsOpacityEffect','QGraphicsBlurEffect')]
        methods = [n for n in dir(mod) if not n.startswith('_') and callable(getattr(mod,n,None)) and not n[0].isupper()]
        print(f'{modpath}')
        if classes: print(f'  classes: {classes}')
        if methods: print(f'  funcs: {methods[:8]}')
        # Get init sig for first class
        for cls_name in classes[:3]:
            cls = getattr(mod, cls_name)
            try:
                sig = inspect.signature(cls)
                print(f'  {cls_name}.__init__{sig}')
            except:
                pass
        print()
    except Exception as e:
        print(f'{modpath}: ERR {e}')
