"""Arranque de la aplicación (Prompt de Diseño v5.3, sección 19)."""

import io
import sys

from emulinks import APP_NAME, APP_VERSION
from emulinks.core.system import IS_WINDOWS
from emulinks.i18n import check_translations


def main() -> None:
    if IS_WINDOWS and hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    # Qt y el tema se importan acá: theme resuelve THEME e idioma al importarse.
    from emulinks.ui.qt import _QT_BACKEND, _exec, QApplication, Qt
    from emulinks.ui.theme import setup_appearance

    if IS_WINDOWS:
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                f"estebancasales.{APP_NAME.lower()}.v{APP_VERSION.replace('.', '')}"
            )
        except Exception:
            pass

    # HighDPI — ANTES de crear QApplication
    if _QT_BACKEND == "PySide6":
        import warnings
        if hasattr(Qt, "AA_UseHighDpiPixmaps"):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    else:
        if hasattr(Qt, "AA_EnableHighDpiScaling"):
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        if hasattr(Qt, "AA_UseHighDpiPixmaps"):
            QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    if not getattr(sys, "frozen", False):
        check_translations()       # solo en desarrollo: avisa claves faltantes

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    setup_appearance(app)          # ← fuente + paleta + íconos + QSS + cursor + traducciones Qt

    from emulinks.ui.main_window import EmuLinksWindow
    win = EmuLinksWindow()
    win.show()
    sys.exit(_exec(app))
