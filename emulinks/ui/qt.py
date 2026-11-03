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
# Uso en el resto de la interfaz:  from emulinks.ui.qt import *
# Nunca importar PySide6/PySide2 directamente fuera de este archivo.
# ══════════════════════════════════════════════════════════════════════════
import sys

from emulinks import APP_NAME


def _import_qt():
    errors = []

    # ── Intento 1: PySide6 ──────────────────────────────────────────────
    try:
        from PySide6.QtWidgets import (
            QApplication, QMainWindow, QWidget, QFrame, QGroupBox,
            QLabel, QPushButton, QToolButton, QLineEdit, QComboBox,
            QScrollArea, QSizePolicy, QSplitter, QStackedWidget,
            QHBoxLayout, QVBoxLayout, QGridLayout,
            QMessageBox, QSpacerItem, QTabWidget, QTabBar,
            QCheckBox, QTextEdit, QPlainTextEdit, QProgressBar, QStatusBar,
            QFileDialog, QListWidget, QListWidgetItem,
            QTableWidget, QTableWidgetItem, QHeaderView,
            QTreeWidget, QTreeWidgetItem,
            QDialog, QDialogButtonBox, QInputDialog,
            QSpinBox, QDoubleSpinBox,
            QRadioButton, QButtonGroup,
            QMenu,
        )
        # PySide6/Qt6: QAction se movió de QtWidgets → QtGui
        from PySide6.QtGui import (
            QAction,
            QColor, QFont, QFontDatabase, QIcon, QPalette,
            QPainter, QPen, QBrush,
            QPixmap, QImage,
            QTextCursor, QCursor,
            QDragEnterEvent, QDropEvent,
        )
        from PySide6.QtCore import (
            Qt, QObject, QEvent, QThread, Signal, QTimer,
            QSettings, QMimeData, QRectF, QPointF,
            QLocale, QTranslator, QLibraryInfo,
        )
        return "PySide6", locals()
    except ImportError as e:
        errors.append(f"PySide6: {e}")

    # ── Intento 2: PySide2 ──────────────────────────────────────────────
    try:
        from PySide2.QtWidgets import (
            QApplication, QMainWindow, QWidget, QFrame, QGroupBox,
            QLabel, QPushButton, QToolButton, QLineEdit, QComboBox,
            QScrollArea, QSizePolicy, QSplitter, QStackedWidget,
            QHBoxLayout, QVBoxLayout, QGridLayout,
            QMessageBox, QSpacerItem, QTabWidget, QTabBar,
            QCheckBox, QTextEdit, QPlainTextEdit, QProgressBar, QStatusBar,
            QFileDialog, QListWidget, QListWidgetItem,
            QTableWidget, QTableWidgetItem, QHeaderView,
            QTreeWidget, QTreeWidgetItem,
            QDialog, QDialogButtonBox, QInputDialog,
            QSpinBox, QDoubleSpinBox,
            QRadioButton, QButtonGroup,
            QMenu, QAction,
        )
        from PySide2.QtGui import (
            QColor, QFont, QFontDatabase, QIcon, QPalette,
            QPainter, QPen, QBrush,
            QPixmap, QImage,
            QTextCursor, QCursor,
            QDragEnterEvent, QDropEvent,
        )
        from PySide2.QtCore import (
            Qt, QObject, QEvent, QThread, Signal, QTimer,
            QSettings, QMimeData, QRectF, QPointF,
            QLocale, QTranslator, QLibraryInfo,
        )
        return "PySide2", locals()
    except ImportError as e:
        errors.append(f"PySide2: {e}")

    print("=" * 65)
    print("ERROR FATAL: No se encontró ningún framework Qt compatible.")
    print("  Windows 10/11 / Linux (Python 3.10+):  pip install PySide6")
    print("  Windows 7 (Python 3.8):                pip install PySide2")
    for e in errors: print(f"  · {e}")
    print("=" * 65)
    input("Presioná Enter para salir...")
    sys.exit(1)


_QT_BACKEND, _qt = _import_qt()
print(f"[{APP_NAME}] Backend Qt: {_QT_BACKEND}")

# ── Exponer todos los nombres Qt en el namespace global (una sola línea) ──
globals().update({k: v for k, v in _qt.items() if k.startswith("Q") or k == "Signal"})


# ── Helper exec() compatible PySide6 / PySide2 ─────────────────────────
def _exec(widget):
    """Llama exec() o exec_() según lo que soporte el widget/app."""
    if hasattr(widget, 'exec') and callable(widget.exec):
        return widget.exec()
    return widget.exec_()


# ── Helper globalPos() compatible PySide6 / PySide2 ────────────────────
# PySide6: e.globalPosition().toPoint()  |  PySide2: e.globalPos()
def _global_pos(event):
    if hasattr(event, 'globalPosition'):
        return event.globalPosition().toPoint()
    return event.globalPos()


# "from emulinks.ui.qt import *" exporta las clases Qt y los helpers.
__all__ = [k for k in _qt if k.startswith("Q") or k == "Signal"] + ["_QT_BACKEND", "_exec", "_global_pos"]
