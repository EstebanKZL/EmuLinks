"""Arranque de la aplicación: HighDPI, logging, captura de errores y ventana."""

import io
import logging
import logging.handlers
import os
import platform
import sys
import tempfile
import traceback
from pathlib import Path

from emulinks import APP_NAME, APP_VERSION
from emulinks.core import config as core_config
from emulinks.core.system import IS_WINDOWS
from emulinks.i18n import check_translations, tr

# Prueba de humo de los builds (el workflow la corre sobre el ejecutable compilado):
# arranca la ventana, dispara señales conectadas a lambdas —lo que falla con Nuitka
# + PySide2 sin parchear—, revisa que QtSvg dibuje los íconos y sale con 0 si todo
# anduvo. Usa una config temporal: nunca toca la del usuario.
SMOKE_TEST = os.environ.get("EMULINKS_SMOKE_TEST") == "1"


def _is_compiled() -> bool:
    """True en el ejecutable de Nuitka (define __compiled__) o de otro empaquetador."""
    return "__compiled__" in globals() or getattr(sys, "frozen", False)


def _isolate_config_for_smoke_test() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="emulinks-smoke-"))
    core_config.CONFIG_PATH = tmp / "config.json"
    core_config.LOG_DIR = tmp


def _schedule_smoke_test(app, win, QTimer) -> None:
    result = {"ok": False, "detail": ""}

    def poke():
        from emulinks.ui.icons import icon_pixmap
        from emulinks.ui.qt import QSvgRenderer
        win.dry_run_cb.setChecked(not win.dry_run_cb.isChecked())  # toggled(bool) -> lambda
        win.max_backups_spin.setValue(win.max_backups_spin.value() + 1)  # valueChanged(int) -> lambda
        img = icon_pixmap("save", 16, "ok").toImage()
        drawn = any(img.pixelColor(x, y).alpha() for x in range(16) for y in range(16))
        saved = core_config.load_config().get("options", {})
        checks = {
            "QtSvg": QSvgRenderer is not None and drawn,
            "señal->lambda": saved.get("dry_run") == win.dry_run_cb.isChecked()
                             and saved.get("max_backups") == win.max_backups_spin.value(),
        }
        result["ok"] = all(checks.values())
        result["detail"] = ", ".join(f"{k}={'ok' if v else 'FALLO'}" for k, v in checks.items())

    def finish():
        print(f"[smoke] {'OK' if result['ok'] else 'FALLO'} ({result['detail']})", flush=True)
        app.exit(0 if result["ok"] else 2)

    QTimer.singleShot(800, poke)
    QTimer.singleShot(2500, finish)


def fix_windows_console_encoding() -> None:
    if IS_WINDOWS and hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def set_windows_app_id() -> None:
    """Ícono propio en la barra de tareas de Windows (en vez del de Python)."""
    if IS_WINDOWS:
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                f"estebankzl.{APP_NAME.lower()}.v{APP_VERSION.replace('.', '')}")
        except (AttributeError, OSError):
            pass


def setup_logging() -> str:
    """Log rotativo en la carpeta de logs de EmuLinks (2 MB × 3). Devuelve la ruta del archivo.
    Se guarda junto a config.json, en la carpeta de datos de EmuLinks."""
    from emulinks.ui.qt import _QT_BACKEND
    log_path = Path(core_config.LOG_DIR) / f"{APP_NAME}.log"
    handler = logging.handlers.RotatingFileHandler(str(log_path), maxBytes=2_000_000, backupCount=3,
                                                   encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    logging.info("Inicio %s v%s (%s, Python %s, %s)", APP_NAME, APP_VERSION, _QT_BACKEND,
                 platform.python_version(), platform.platform())
    return str(log_path)


def install_excepthook() -> None:
    """Cualquier error no controlado se registra y se muestra en un diálogo con detalles,
    en vez de cerrar el programa sin aviso."""
    from emulinks.ui.qt import QApplication
    from emulinks.ui.widgets import show_message

    def _hook(exc_type, exc, tb):
        details = "".join(traceback.format_exception(exc_type, exc, tb))
        logging.error("Error no controlado:\n%s", details)
        if SMOKE_TEST:                  # sin pantalla: un diálogo modal colgaría la prueba
            print(details, flush=True)
            os._exit(3)
        if QApplication.instance() is not None:
            show_message("error", None, tr("msg.unexpected_title"),
                         tr("msg.unexpected_text", detail=str(exc)), details=details)
    sys.excepthook = _hook


def main() -> None:
    fix_windows_console_encoding()
    set_windows_app_id()

    if SMOKE_TEST:
        _isolate_config_for_smoke_test()

    # Qt y el tema se importan acá: theme resuelve THEME e idioma al importarse.
    from emulinks.ui.qt import _QT_BACKEND, _exec, QApplication, QIcon, QTimer, Qt
    from emulinks.ui.theme import setup_appearance

    # HighDPI — ANTES de crear QApplication (Qt6 ya escala bien por defecto)
    if _QT_BACKEND != "PySide6":
        for attr in ("AA_EnableHighDpiScaling", "AA_UseHighDpiPixmaps"):
            if hasattr(Qt, attr):
                QApplication.setAttribute(getattr(Qt, attr), True)

    if not _is_compiled():
        check_translations()       # solo en desarrollo: avisa claves faltantes

    app = QApplication(sys.argv)
    icon_path = Path(__file__).resolve().parent / "assets" / "emulinks.png"
    if icon_path.exists():         # ícono de ventana y barra de tareas
        app.setWindowIcon(QIcon(str(icon_path)))
    setup_appearance(app)          # fuente + paleta + glifos + QSS + cursor + traducciones Qt
    setup_logging()
    install_excepthook()

    from emulinks.ui.main_window import EmuLinksWindow
    win = EmuLinksWindow()
    win.show()
    if SMOKE_TEST:
        _schedule_smoke_test(app, win, QTimer)
    sys.exit(_exec(app))
