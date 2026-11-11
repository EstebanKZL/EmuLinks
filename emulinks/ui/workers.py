"""Threads: nunca tocan widgets, solo emiten señales."""

from pathlib import Path
from typing import Any, Dict, List

from emulinks.core import LOG_ERROR, LOG_INFO, LOG_OK, LOG_WARN
from emulinks.core.detection import detect_installations
from emulinks.core.fs import sync_emulator
from emulinks.i18n import tr
from emulinks.ui.qt import *  # noqa: F401,F403


class SyncWorker(QThread):
    log_message   = Signal(str, str)      # (texto, nivel)
    progress_step = Signal(int, int)
    finished_ok   = Signal(dict)

    def __init__(self, emulator_names: List[str], config: Dict[str, Any]):
        super().__init__()
        self.emulator_names = emulator_names
        self.config = config
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        self.log_message.emit(tr("log.sync_header"), LOG_INFO)

        shared_dir = Path(self.config["shared_dir"])
        options = self.config["options"]
        if not shared_dir.exists() and not options.get("dry_run"):
            shared_dir.mkdir(parents=True, exist_ok=True)

        total = len(self.emulator_names)
        summary = {"ok": [], "failed": [], "cancelled": False}

        for idx, name in enumerate(self.emulator_names):
            if self._is_cancelled:
                break
            self.log_message.emit(tr("log.processing", name=name, current=idx + 1, total=total), LOG_INFO)
            emu_config = self.config["emulators"].get(name, {})
            try:
                result = sync_emulator(
                    name, emu_config, shared_dir, options,
                    log=lambda text, level=LOG_INFO: self.log_message.emit(text, level),
                    is_cancelled=lambda: self._is_cancelled,
                )
            except Exception as e:
                # Un error inesperado en un emulador no corta el hilo: si no,
                # la UI se queda en "Sincronizando…" para siempre.
                self.log_message.emit(tr("log.sync_error", name=name, error=e), LOG_ERROR)
                result = False
            (summary["ok"] if result else summary["failed"]).append(name)
            self.progress_step.emit(idx + 1, total)

        summary["cancelled"] = self._is_cancelled
        key = "log.sync_cancelled" if self._is_cancelled else "log.sync_finished"
        level = LOG_WARN if (self._is_cancelled or summary["failed"]) else LOG_OK
        self.log_message.emit(tr(key, ok=len(summary["ok"]), failed=len(summary["failed"])), level)
        self.finished_ok.emit(summary)


class DetectWorker(QThread):
    progress = Signal(str)
    done     = Signal(dict)

    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        self.config = config
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            result = detect_installations(self.config, progress=self.progress.emit,
                                          is_cancelled=lambda: self._is_cancelled)
        except Exception as e:
            result = {"installs": [], "without_data": [], "cancelled": False, "error": str(e)}
        self.done.emit(result)
