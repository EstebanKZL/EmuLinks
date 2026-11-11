# ══════════════════════════════════════════════════════════════════════════
# CAPA DE COMPATIBILIDAD AUTOMÁTICA: PySide6 / PySide2
# ══════════════════════════════════════════════════════════════════════════
# Orden de prioridad:
#   1. PySide6  → Python 3.10+, Windows 10/11, Linux
#   2. PySide2  → Python 3.8/3.9, Windows 7/8/10, Linux
#
# Instalación según entorno:
#   Windows 10/11 / Linux (Python 3.10+):  pip install PySide6
#   Windows 7       (Python 3.8):          pip install PySide2
#
# Cada nombre se busca en QtWidgets, QtGui y QtCore: así se resuelven solas las
# clases que Qt6 movió de módulo (QAction, QShortcut, QFileSystemModel → QtGui).
#
# Nota: los módulos se importan con sentencias literales
# (no importlib) para que Nuitka los vea y empaquete QtSvg.
# Uso en el resto de la interfaz:  from emulinks.ui.qt import *
# Nunca importar PySide6/PySide2 directamente fuera de este archivo.
# ══════════════════════════════════════════════════════════════════════════
import sys

from emulinks import APP_NAME

_QT_NAMES = (
    # ── Widgets ──
    "QApplication", "QMainWindow", "QWidget", "QFrame", "QGroupBox", "QLabel",
    "QPushButton", "QToolButton", "QToolBar", "QLineEdit", "QComboBox",
    "QScrollArea", "QSizePolicy", "QSplitter", "QStackedWidget", "QStackedLayout",
    "QHBoxLayout", "QVBoxLayout", "QGridLayout", "QFormLayout",
    "QMessageBox", "QSpacerItem", "QTabWidget", "QTabBar",
    "QCheckBox", "QTextEdit", "QPlainTextEdit", "QProgressBar", "QStatusBar",
    "QFileDialog", "QListWidget", "QListWidgetItem",
    "QTableWidget", "QTableWidgetItem", "QTableView", "QTreeView", "QListView",
    "QHeaderView", "QAbstractItemView", "QTreeWidget", "QTreeWidgetItem",
    "QDialog", "QDialogButtonBox", "QInputDialog", "QSpinBox", "QDoubleSpinBox",
    "QRadioButton", "QButtonGroup", "QMenu", "QFileIconProvider",
    "QGraphicsOpacityEffect",
    # ── Gui ──
    "QAction", "QShortcut", "QFileSystemModel", "QKeySequence",
    "QColor", "QFont", "QFontDatabase", "QIcon", "QPalette",
    "QPainter", "QPen", "QBrush", "QPixmap", "QImage", "QTextCursor",
    "QDragEnterEvent", "QDropEvent", "QStandardItemModel", "QStandardItem",
    "QDesktopServices", "QGuiApplication",
    "QCursor",                                   # EmuLinks: clic en filas de la lista
    # ── Core ──
    "Qt", "QObject", "QEvent", "QThread", "QTimer", "QSettings", "QMimeData",
    "QRectF", "QPointF", "QPoint", "QSize", "QRect", "QByteArray", "QUrl",
    "QLocale", "QTranslator", "QLibraryInfo", "QFile", "QFileInfo", "QDir",
    "QStandardPaths", "QStorageInfo", "QMimeDatabase", "QSortFilterProxyModel",
    "QModelIndex", "QPropertyAnimation", "QEasingCurve",
)


def _load_pyside6():
    from PySide6 import QtCore, QtGui, QtWidgets
    try:
        from PySide6 import QtSvg
    except ImportError:
        QtSvg = None
    return (QtWidgets, QtGui, QtCore), QtSvg


def _load_pyside2():
    from PySide2 import QtCore, QtGui, QtWidgets
    try:
        from PySide2 import QtSvg
    except ImportError:
        QtSvg = None
    return (QtWidgets, QtGui, QtCore), QtSvg


def _import_qt():
    errors = []
    for backend, loader in (("PySide6", _load_pyside6), ("PySide2", _load_pyside2)):
        try:
            mods, svg = loader()
        except ImportError as e:
            errors.append(f"{backend}: {e}")
            continue
        ns, missing = {}, []
        for name in _QT_NAMES:
            obj = next((getattr(m, name) for m in mods if hasattr(m, name)), None)
            if obj is None:
                missing.append(name)
            ns[name] = obj
        ns["Signal"] = mods[2].Signal
        # QtSvg es opcional: sin él los íconos quedan vacíos pero el programa funciona.
        ns["QSvgRenderer"] = svg.QSvgRenderer if svg is not None else None
        if svg is None:
            missing.append("QSvgRenderer (íconos desactivados)")
        if missing:
            print(f"[Qt] Aviso: no disponibles en {backend}: {', '.join(missing)}")
        return backend, ns

    print("=" * 65)
    print("ERROR FATAL: No se encontró ningún framework Qt compatible.")
    print("  Windows 10/11 / Linux (Python 3.10+):  pip install PySide6")
    print("  Windows 7 (Python 3.8):                pip install PySide2")
    for e in errors:
        print(f"  · {e}")
    print("=" * 65)
    input("Presioná Enter para salir...")
    sys.exit(1)


_QT_BACKEND, _qt = _import_qt()
globals().update(_qt)            # expone QApplication, QWidget, Qt, Signal, etc.
print(f"[{APP_NAME}] Backend Qt: {_QT_BACKEND}")


def _exec(obj, *args):
    """exec() / exec_() compatible PySide6 / PySide2 (QApplication, QDialog, QMenu…)."""
    fn = getattr(obj, "exec", None)
    if not callable(fn):
        fn = obj.exec_
    return fn(*args)


def _global_pos(event):
    """PySide6: globalPosition().toPoint()  |  PySide2: globalPos()."""
    if hasattr(event, "globalPosition"):
        return event.globalPosition().toPoint()
    return event.globalPos()


def _event_pos(event):
    """Posición local del mouse. PySide6: position().toPoint() | PySide2: pos()."""
    if hasattr(event, "position"):
        return event.position().toPoint()
    return event.pos()


# "from emulinks.ui.qt import *" exporta las clases Qt y los helpers.
__all__ = list(_qt) + ["_QT_BACKEND", "_exec", "_global_pos", "_event_pos"]
