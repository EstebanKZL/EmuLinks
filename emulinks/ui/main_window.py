"""Ventana principal: encabezado → tarjetas → barra de estado."""

import html
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from emulinks import APP_DEVELOPER, APP_EMAIL, APP_NAME, APP_URL, APP_VERSION
from emulinks.core import LOG_ERROR, LOG_INFO, LOG_OK, LOG_WARN
from emulinks.core.config import CONFIG_PATH, BASE_DATA_DIR, _default_config, load_config, save_config
from emulinks.core.detection import apply_detection
from emulinks.core.fs import check_status
from emulinks.core.system import PLATFORM_KEY
from emulinks.i18n import tr
from emulinks.ui.dialogs import (
    AboutDialog, DetectDialog, EmulatorDialog, RestoreBackupDialog, SearchRootsPage, SettingsDialog,
)
from emulinks.ui.filetypes import file_icon
from emulinks.ui.icons import icon, set_button_icon
from emulinks.ui.qt import *  # noqa: F401,F403
from emulinks.ui.theme import ICON_SIZE, SP, THEME
from emulinks.ui.widgets import (
    Banner, DotGripWidget, PathSelector, Toast, ask_confirm, make_badge, make_card,
    make_empty_state, make_icon_button, make_kpi, make_log_view, open_with_system,
    restore_window_state, save_window_state, set_badge, set_help, show_message,
)
from emulinks.ui.workers import SyncWorker

# Estados de check_status() → color del tema y grupo de KPI.
STATE_COLOR_KEYS = {
    "linked": "ok", "file_ok": "ok",
    "pending_link": "ip", "pending_migration": "counter", "file_pending": "counter",
    "file_outdated": "counter", "missing_local": "error", "missing_both": "text_muted",
    "broken": "error", "placeholder": "error", "stale_shared": "counter",
    "no_path": "text_muted", "file_missing": "text_muted",
}
OK_STATES = {"linked", "file_ok"}
PROBLEM_STATES = {"broken", "placeholder", "stale_shared", "no_path", "missing_local"}
PENDING_STATES = set(STATE_COLOR_KEYS) - OK_STATES - PROBLEM_STATES - {"file_missing", "missing_both"}

LOG_COLOR_KEYS = {LOG_OK: "ok", LOG_ERROR: "error", LOG_WARN: "counter", LOG_INFO: "text"}
# El log de pantalla es para el usuario; avisos y errores también van al archivo.
LOG_FILE_LEVELS = {LOG_ERROR: logging.ERROR, LOG_WARN: logging.WARNING}


class EmuLinksWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.worker: Optional[SyncWorker] = None
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.resize(1280, 720)
        self.setMinimumSize(1280, 720)
        self._build_ui()
        self._splitters_restored = restore_window_state(
            self, splitters={"main": self._main_splitter, "right": self._right_splitter})
        # La geometría guardada (otro monitor/escala de DPI, ventana "snappeada")
        # puede quedar más chica que el mínimo: se refuerza acá.
        if self.width() < 1280 or self.height() < 720:
            self.resize(max(self.width(), 1280), max(self.height(), 720))
        # Escaneo de solo lectura al abrir: los KPIs y la tabla arrancan con datos.
        QTimer.singleShot(0, self._check_status)

    # ------------------------------------------------------------------
    # Construcción de la interfaz
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_header())

        body = QWidget()
        body_lay = QHBoxLayout(body)
        body_lay.setContentsMargins(SP["lg"], SP["lg"], SP["lg"], SP["lg"])
        body_lay.setSpacing(SP["lg"])
        root.addWidget(body, 1)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_left_column())
        splitter.addWidget(self._build_right_column())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        body_lay.addWidget(splitter)
        self._main_splitter = splitter

        self._build_menus()
        self._build_status_bar()
        self._populate_emu_list()
        self._load_options_into_ui()
        self._update_shared_banner()

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("headerBar")
        lay = QHBoxLayout(header)
        lay.setContentsMargins(SP["lg"] + 4, SP["md"], SP["lg"] + 4, SP["md"])
        lay.setSpacing(SP["md"])

        titles = QVBoxLayout()
        titles.setSpacing(0)
        t = QLabel(APP_NAME);           t.setObjectName("lblAppTitle")
        s = QLabel(tr("app.subtitle")); s.setObjectName("lblAppSubtitle")
        titles.addWidget(t); titles.addWidget(s)
        lay.addLayout(titles)
        lay.addStretch(1)

        self.badge_estado = make_badge(tr("status.ready"), "neutral")
        set_help(self.badge_estado, "badge_status")
        lay.addWidget(self.badge_estado, 0, Qt.AlignVCenter)
        settings_btn = make_icon_button("settings", "settings", "Ctrl+,")
        settings_btn.clicked.connect(self._open_settings)
        lay.addWidget(settings_btn, 0, Qt.AlignVCenter)
        return header

    def _build_left_column(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(420)
        scroll.setMaximumWidth(480)

        column = QWidget()
        lay = QVBoxLayout(column)
        lay.setContentsMargins(0, 0, SP["sm"], 0)
        lay.setSpacing(SP["lg"])
        lay.addWidget(self._build_shared_dir_card())
        lay.addWidget(self._build_emulators_card(), 1)
        lay.addWidget(self._build_options_card())
        scroll.setWidget(column)
        return scroll

    def _build_shared_dir_card(self) -> QFrame:
        open_btn = QPushButton(tr("btn.open"))
        open_btn.setObjectName("btnSecondary")
        set_button_icon(open_btn, "open")
        set_help(open_btn, "open_shared")
        open_btn.clicked.connect(self._open_shared_folder)
        card, lay = make_card(tr("section.shared"), header_widget=open_btn)
        hint = QLabel(tr("lbl.shared_hint"))
        hint.setObjectName("lblHint")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        # No tiene que existir todavía: se crea al sincronizar.
        self.shared_selector = PathSelector("folder", key="shared", must_exist=False,
                                            help_key="shared_dir", browse_help_key="browse_shared")
        self.shared_selector.edit.setPlaceholderText(tr("ph.shared_dir"))
        self.shared_selector.edit.setText(self.config.get("shared_dir", ""))
        self.shared_selector.edit.setCursorPosition(0)        # se lee el comienzo de la ruta
        self.shared_selector.pathChanged.connect(self._on_shared_dir_changed)
        lay.addWidget(self.shared_selector)
        return card

    def _build_emulators_card(self) -> QFrame:
        card, lay = make_card(tr("section.emulators"))

        chip_row = QHBoxLayout()
        chip_row.setSpacing(SP["xs"])
        self.emu_selection_label = QLabel()
        self.emu_selection_label.setObjectName("lblHint")
        chip_row.addWidget(self.emu_selection_label)
        chip_row.addStretch()
        all_btn = QPushButton(tr("btn.select_all"))
        set_help(all_btn, "select_all")
        all_btn.clicked.connect(self._select_all_emulators)
        chip_row.addWidget(all_btn)
        none_btn = QPushButton(tr("btn.select_none"))
        set_help(none_btn, "select_none")
        none_btn.clicked.connect(self._deselect_all_emulators)
        chip_row.addWidget(none_btn)
        lay.addLayout(chip_row)

        self.emu_list = QListWidget()
        self.emu_list.setMinimumHeight(120)
        set_help(self.emu_list, "emu_list")
        # Clic en cualquier parte de la fila tilda/destilda (no solo el
        # cuadradito), así lo que se ve tildado es siempre lo que se va a
        # operar con Eliminar/Sincronizar — sin sorpresas.
        self.emu_list.itemClicked.connect(self._on_emu_item_clicked)
        self.emu_list.itemChanged.connect(self._on_emu_item_changed)
        self.emu_list.itemDoubleClicked.connect(self._on_emu_double_clicked)
        self.emu_stack = QStackedWidget()
        self.emu_stack.addWidget(make_empty_state(tr("empty.emulators"), "app"))
        self.emu_stack.addWidget(self.emu_list)
        lay.addWidget(self.emu_stack, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(SP["sm"])
        add_btn = QPushButton(tr("btn.add"))
        set_button_icon(add_btn, "plus")
        set_help(add_btn, "add_emulator")
        add_btn.clicked.connect(self._add_emulator)
        btn_row.addWidget(add_btn)
        edit_btn = QPushButton(tr("btn.edit"))
        set_button_icon(edit_btn, "edit")
        set_help(edit_btn, "edit_emulator")
        edit_btn.clicked.connect(self._edit_emulator)
        btn_row.addWidget(edit_btn)
        del_btn = QPushButton(tr("btn.delete"))
        del_btn.setObjectName("btnDanger")
        set_button_icon(del_btn, "trash")
        set_help(del_btn, "delete_emulator")
        del_btn.clicked.connect(self._delete_emulator)
        btn_row.addWidget(del_btn)
        btn_row.addStretch()
        lay.addLayout(btn_row)

        detect_btn = QPushButton(tr("btn.detect"))
        detect_btn.setObjectName("btnPrimary")
        set_button_icon(detect_btn, "search")
        set_help(detect_btn, "detect", shortcut="Ctrl+D")
        detect_btn.setShortcut("Ctrl+D")
        detect_btn.clicked.connect(self._auto_detect)
        lay.addWidget(detect_btn)
        return card

    def _build_options_card(self) -> QFrame:
        card, lay = make_card(tr("section.options"), spacing=SP["sm"])
        self.backup_cb = QCheckBox(tr("opt.backup"))
        self.zip_backup_cb = QCheckBox(tr("opt.zip_backup"))
        self.copy_missing_cb = QCheckBox(tr("opt.copy_missing"))
        self.dry_run_cb = QCheckBox(tr("opt.dry_run"))
        for cb, key in ((self.backup_cb, "opt_backup"), (self.zip_backup_cb, "opt_zip_backup"),
                        (self.copy_missing_cb, "opt_copy_missing"), (self.dry_run_cb, "opt_dry_run")):
            set_help(cb, key)
            cb.toggled.connect(lambda _checked: self._persist_config(quiet=True))
            lay.addWidget(cb)

        max_row = QHBoxLayout()
        max_row.setSpacing(SP["sm"])
        lbl = QLabel(tr("lbl.max_backups"))
        max_row.addWidget(lbl)
        self.max_backups_spin = QSpinBox()
        self.max_backups_spin.setRange(0, 50)
        self.max_backups_spin.setMinimumWidth(76)
        set_help(self.max_backups_spin, "max_backups")
        self.max_backups_spin.valueChanged.connect(lambda _v: self._persist_config(quiet=True))
        max_row.addWidget(self.max_backups_spin)
        max_row.addStretch()
        lay.addLayout(max_row)
        return card

    def _build_right_column(self) -> QWidget:
        column = QWidget()
        lay = QVBoxLayout(column)
        lay.setContentsMargins(SP["sm"], 0, 0, 0)
        lay.setSpacing(SP["lg"])

        self.banner = Banner()
        self.banner.actionClicked.connect(self._on_banner_action)
        self._banner_action = None
        lay.addWidget(self.banner)

        kpis = QHBoxLayout()
        kpis.setSpacing(SP["lg"])
        self.kpi = {}
        for key in ("emulators", "ok", "pending", "problems"):
            card, value = make_kpi("–", tr(f"kpi.{key}"))
            set_help(card, f"kpi_{key}")
            kpis.addWidget(card, 1)
            self.kpi[key] = value
        lay.addLayout(kpis)

        splitter = QSplitter(Qt.Vertical)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_status_card())
        splitter.addWidget(self._build_activity_card())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        lay.addWidget(splitter, 1)
        self._right_splitter = splitter
        return column

    def _build_status_card(self) -> QFrame:
        self.verify_btn = QPushButton(tr("btn.verify"))
        self.verify_btn.setObjectName("btnSecondary")
        set_button_icon(self.verify_btn, "refresh")
        set_help(self.verify_btn, "verify", shortcut="F5")
        self.verify_btn.setShortcut("F5")
        self.verify_btn.clicked.connect(self._check_status)
        card, lay = make_card(tr("section.status"), header_widget=self.verify_btn)

        actions = QHBoxLayout()
        actions.setSpacing(SP["sm"])
        self.status_hint = QLabel()
        self.status_hint.setObjectName("lblHint")
        actions.addWidget(self.status_hint, 1)
        self.sync_selected_btn = QPushButton(tr("btn.sync_selected"))
        self.sync_selected_btn.setObjectName("btnStart")
        set_button_icon(self.sync_selected_btn, "play")
        set_help(self.sync_selected_btn, "sync_selected", shortcut="Ctrl+E")
        self.sync_selected_btn.setShortcut("Ctrl+E")
        self.sync_selected_btn.clicked.connect(self._sync_selected)
        actions.addWidget(self.sync_selected_btn)
        self.sync_all_btn = QPushButton(tr("btn.sync_all"))
        self.sync_all_btn.setObjectName("btnStart")
        set_button_icon(self.sync_all_btn, "play")
        set_help(self.sync_all_btn, "sync_all")
        self.sync_all_btn.clicked.connect(self._sync_all)
        actions.addWidget(self.sync_all_btn)
        self.cancel_btn = QPushButton(tr("btn.stop"))
        self.cancel_btn.setObjectName("btnStop")
        set_button_icon(self.cancel_btn, "stop")
        set_help(self.cancel_btn, "stop")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel_sync)
        actions.addWidget(self.cancel_btn)
        lay.addLayout(actions)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        lay.addWidget(self.progress_bar)

        self.status_table = QTableWidget(0, 3)
        for col, key in enumerate(("col.emulator", "col.item", "col.state")):
            item = QTableWidgetItem(tr(key))
            item.setToolTip(tr(f"tip.{key.replace('.', '_')}"))
            self.status_table.setHorizontalHeaderItem(col, item)
        header = self.status_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setHighlightSections(False)
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.status_table.setColumnWidth(0, 180)
        self.status_table.setColumnWidth(1, 260)
        self.status_table.verticalHeader().setVisible(False)
        self.status_table.verticalHeader().setDefaultSectionSize(32)
        self.status_table.setIconSize(QSize(ICON_SIZE["sm"], ICON_SIZE["sm"]))
        self.status_table.setWordWrap(False)
        self.status_table.setShowGrid(False)
        self.status_table.setAlternatingRowColors(True)
        self.status_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.status_table.setSelectionBehavior(QTableWidget.SelectRows)

        self.status_stack = QStackedWidget()
        self.status_stack.addWidget(make_empty_state(tr("empty.status"), "list"))
        self.status_stack.addWidget(self.status_table)
        lay.addWidget(self.status_stack, 1)
        return card

    def _build_activity_card(self) -> QFrame:
        # "Limpiar log" a la derecha del título: así la tarjeta puede achicarse
        # y dejarle el alto a la tabla de estado.
        clear_btn = QPushButton(tr("btn.clear_log"))
        clear_btn.setObjectName("btnSecondary")
        set_help(clear_btn, "clear_log")
        card, lay = make_card(tr("section.activity"), header_widget=clear_btn)
        self.console = make_log_view()
        self.console.setMinimumHeight(64)
        self.console.setPlaceholderText(tr("empty.log"))      # log vacío con frase útil
        clear_btn.clicked.connect(self.console.clear)
        lay.addWidget(self.console, 1)
        return card

    def _build_menus(self) -> None:
        bar = self.menuBar()
        menu_file = bar.addMenu(tr("menu.file"))
        menu_view = bar.addMenu(tr("menu.view"))
        menu_help = bar.addMenu(tr("menu.help"))
        for m in (menu_file, menu_view, menu_help):
            m.setToolTipsVisible(True)               # sin esto, QMenu no muestra tooltips

        act = menu_file.addAction(icon("open"), tr("action.open_config_dir"))
        set_help(act, "open_config_dir")
        act.triggered.connect(lambda: open_with_system(BASE_DATA_DIR))
        act = menu_file.addAction(tr("action.restore_defaults"))
        set_help(act, "restore_defaults")
        act.triggered.connect(self._restore_default_emulators)
        menu_file.addSeparator()
        act = menu_file.addAction(icon("exit"), tr("action.exit"))
        act.setShortcut(QKeySequence("Ctrl+Q"))
        set_help(act, "exit", "Ctrl+Q")
        act.triggered.connect(self.close)

        act = menu_view.addAction(icon("settings"), tr("action.settings"))
        act.setShortcut(QKeySequence("Ctrl+,"))
        set_help(act, "settings", "Ctrl+,")
        act.triggered.connect(self._open_settings)

        act = menu_help.addAction(icon("external"), tr("action.project"))
        set_help(act, "project")
        act.triggered.connect(lambda: QDesktopServices.openUrl(QUrl(APP_URL)))
        menu_help.addSeparator()
        act = menu_help.addAction(icon("help"), tr("action.about"))
        act.setShortcut(QKeySequence("F1"))
        set_help(act, "about", "F1")
        act.triggered.connect(lambda: _exec(AboutDialog(self, tr("about.description"))))

    def _build_status_bar(self) -> None:
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(tr("status.ready"))

        sep = '&nbsp;&nbsp;│&nbsp;&nbsp;'
        self.os_label = QLabel()
        self.os_label.setTextFormat(Qt.RichText)
        self.os_label.setText(
            f'<span style="font-weight:400;">{html.escape(tr("status.platform", platform=PLATFORM_KEY))}'
            f'{sep}v{APP_VERSION}{sep}{APP_DEVELOPER}&nbsp;&mdash;&nbsp;{APP_EMAIL}</span>'
        )
        self.os_label.setContentsMargins(0, 0, 24, 0)          # lugar para el grip
        self.status_bar.addPermanentWidget(self.os_label)

        self._grip = DotGripWidget(self, bg_color=THEME["status_bg"])
        self._reposition_grip()

    # ------------------------------------------------------------------
    # Configuración y avisos
    # ------------------------------------------------------------------
    def _open_settings(self):
        self._sync_options_from_ui()
        dlg = SettingsDialog(self)
        SearchRootsPage(dlg, self.config)
        if _exec(dlg) == QDialog.Accepted:
            self._persist_config(quiet=True)

    def _update_shared_banner(self):
        """Sin carpeta compartida no se puede sincronizar: se avisa arriba, sin bloquear."""
        if self.shared_selector.path():
            if self._banner_action == "shared":
                self.banner.hide()
                self._banner_action = None
            return
        self._banner_action = "shared"
        self.banner.show_message("warning", tr("banner.no_shared"), tr("btn.browse"))

    def _on_banner_action(self):
        if self._banner_action == "shared":
            self.shared_selector.btn.click()

    def _restore_default_emulators(self):
        defaults = _default_config()["emulators"]
        added = [name for name in defaults if name not in self.config["emulators"]]
        if not added:
            show_message("info", self, tr("action.restore_defaults").rstrip("…"),
                         tr("msg.defaults_present", names=", ".join(defaults)))
            return
        for name in added:
            self.config["emulators"][name] = defaults[name]
        self._populate_emu_list()
        self._persist_config()
        show_message("success", self, tr("action.restore_defaults").rstrip("…"),
                     tr("msg.defaults_added", names=", ".join(added)))

    # ------------------------------------------------------------------
    # Config <-> UI
    # ------------------------------------------------------------------
    def _load_options_into_ui(self):
        options = self.config.get("options", {})
        widgets = (self.backup_cb, self.zip_backup_cb, self.copy_missing_cb,
                   self.dry_run_cb, self.max_backups_spin)
        for w in widgets:
            w.blockSignals(True)
        self.backup_cb.setChecked(bool(options.get("backup", True)))
        self.zip_backup_cb.setChecked(bool(options.get("zip_backup", True)))
        self.copy_missing_cb.setChecked(bool(options.get("copy_missing", False)))
        self.dry_run_cb.setChecked(bool(options.get("dry_run", False)))
        self.max_backups_spin.setValue(int(options.get("max_backups", 5)))
        for w in widgets:
            w.blockSignals(False)

    def _sync_options_from_ui(self):
        self.config["shared_dir"] = self.shared_selector.path()
        # update() y no reemplazo: hay opciones sin control en la UI
        # (search_roots) que no se deben perder.
        self.config.setdefault("options", {}).update({
            "backup": self.backup_cb.isChecked(),
            "zip_backup": self.zip_backup_cb.isChecked(),
            "copy_missing": self.copy_missing_cb.isChecked(),
            "dry_run": self.dry_run_cb.isChecked(),
            "max_backups": self.max_backups_spin.value(),
        })

    def _persist_config(self, quiet: bool = False):
        """Guarda en disco después de cada cambio. Antes los emuladores
        añadidos/editados/borrados solo se guardaban al sincronizar, y se
        perdían si cerrabas el programa sin hacerlo."""
        self._sync_options_from_ui()
        if save_config(self.config):
            if not quiet:
                Toast.show_text(self, tr("toast.saved"))
        else:
            logging.error("No se pudo guardar %s", CONFIG_PATH)
            show_message("error", self, tr("msg.error_title"), tr("msg.config_save_failed", path=CONFIG_PATH))

    # ------------------------------------------------------------------
    # Lista de emuladores
    # ------------------------------------------------------------------
    def _populate_emu_list(self):
        self.emu_list.blockSignals(True)
        self.emu_list.clear()
        for name in sorted(self.config.get("emulators", {}).keys()):
            emu = self.config["emulators"][name]
            n_folders = len(emu.get("important_folders", []))
            n_files = len(emu.get("important_files", []))
            key = "lbl.emu_item_files" if n_files else "lbl.emu_item"
            item = QListWidgetItem(tr(key, name=name, folders=n_folders, files=n_files))
            item.setData(Qt.UserRole, name)
            item.setToolTip(emu.get(PLATFORM_KEY) or tr("status.no_path"))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.emu_list.addItem(item)
        self.emu_list.blockSignals(False)
        self.emu_stack.setCurrentIndex(1 if self.emu_list.count() else 0)
        self._update_selection_label()

    def _select_all_emulators(self):
        for i in range(self.emu_list.count()):
            self.emu_list.item(i).setCheckState(Qt.Checked)

    def _deselect_all_emulators(self):
        for i in range(self.emu_list.count()):
            self.emu_list.item(i).setCheckState(Qt.Unchecked)

    def _get_selected_emulators(self) -> List[str]:
        return [self.emu_list.item(i).data(Qt.UserRole) for i in range(self.emu_list.count())
                if self.emu_list.item(i).checkState() == Qt.Checked]

    def _get_current_emulator(self) -> Optional[str]:
        item = self.emu_list.currentItem()
        return item.data(Qt.UserRole) if item else None

    def _update_selection_label(self):
        self.emu_selection_label.setText(
            tr("lbl.selection", selected=len(self._get_selected_emulators()), total=self.emu_list.count()))

    def _on_emu_item_changed(self, item: QListWidgetItem):
        # La fila tildada queda resaltada: lo que ves tildado es exactamente
        # lo que se va a borrar/sincronizar.
        checked = item.checkState() == Qt.Checked
        item.setBackground(QColor(THEME["selection"]) if checked else QBrush())
        self._update_selection_label()

    def _on_emu_item_clicked(self, item: QListWidgetItem):
        # Si el clic fue sobre el cuadradito, Qt ya cambió el estado solo.
        # Si fue en otro punto de la fila, alternamos el tilde nosotros.
        rect = self.emu_list.visualItemRect(item)
        click_x = self.emu_list.viewport().mapFromGlobal(QCursor.pos()).x()
        if click_x > rect.x() + SP["xl"]:
            item.setCheckState(Qt.Unchecked if item.checkState() == Qt.Checked else Qt.Checked)

    def _on_emu_double_clicked(self, item: QListWidgetItem):
        _exec(RestoreBackupDialog(self, self.config, item.data(Qt.UserRole)))

    # ------------------------------------------------------------------
    # CRUD de emuladores
    # ------------------------------------------------------------------
    def _add_emulator(self):
        self._show_emulator_dialog(None)

    def _edit_emulator(self):
        selected = self._get_selected_emulators()
        if len(selected) > 1:
            show_message("info", self, tr("btn.edit"), tr("msg.edit_one", count=len(selected)))
            return
        name = selected[0] if selected else self._get_current_emulator()
        if not name:
            show_message("info", self, tr("btn.edit"), tr("msg.pick_emulator"))
            return
        self._show_emulator_dialog(name)

    def _delete_emulator(self):
        # Opera sobre TODO lo tildado, no solo sobre el último que tocaste.
        names = self._get_selected_emulators()
        if not names:
            current = self._get_current_emulator()
            names = [current] if current else []
        if not names:
            show_message("info", self, tr("btn.delete"), tr("msg.pick_emulators"))
            return
        listado = "\n".join(f"  · {n}" for n in names)
        if ask_confirm(self, tr("msg.confirm_delete_title"),
                       tr("msg.confirm_delete", count=len(names), names=listado),
                       confirm_text=tr("btn.delete"), danger=True):
            for name in names:
                self.config["emulators"].pop(name, None)
            self._populate_emu_list()
            self._persist_config()

    def _show_emulator_dialog(self, emu_name: Optional[str]):
        dialog = EmulatorDialog(self, emu_name, self.config.get("emulators", {}).get(emu_name, {}))
        if _exec(dialog) == QDialog.Accepted:
            new_name, new_config = dialog.get_data()
            self.config["emulators"][new_name] = new_config
            if emu_name and emu_name != new_name:
                del self.config["emulators"][emu_name]
            self._populate_emu_list()
            self._persist_config()

    def _auto_detect(self):
        self._sync_options_from_ui()
        dialog = DetectDialog(self, self.config)
        if _exec(dialog) != QDialog.Accepted:
            self._persist_config(quiet=True)  # conserva las carpetas de búsqueda agregadas
            return

        results: Dict[str, List[str]] = {"added": [], "updated": [], "unchanged": []}
        for inst, folders, files in dialog.selected():
            results[apply_detection(self.config, inst, folders, files)].append(inst["id"])
        self._populate_emu_list()
        self._persist_config()

        parts = [tr(f"msg.detect_{kind}", names=", ".join(ids)) for kind, ids in results.items() if ids]
        show_message("success" if parts else "info", self, tr("btn.detect"),
                     tr("msg.detect_result", details="\n".join(parts) if parts else tr("msg.detect_none")))
        self._check_status()

    # ------------------------------------------------------------------
    # Carpeta compartida
    # ------------------------------------------------------------------
    def _on_shared_dir_changed(self, _path: str):
        self._persist_config()
        self._update_shared_banner()

    def _open_shared_folder(self):
        path = Path(self.shared_selector.path())
        if not self.shared_selector.path() or not path.exists():
            show_message("info", self, tr("btn.open"), tr("msg.shared_missing"))
            return
        open_with_system(path)

    # ------------------------------------------------------------------
    # Verificación de estado (solo lectura)
    # ------------------------------------------------------------------
    def _check_status(self):
        self._sync_options_from_ui()
        names = self._get_selected_emulators() or sorted(self.config.get("emulators", {}).keys())
        report = check_status(self.config, names) if names else {}
        rows = [(name, r) for name in names for r in report.get(name, [])]

        self.status_table.setRowCount(len(rows))
        counts = {"ok": 0, "pending": 0, "problems": 0}
        for i, (name, r) in enumerate(rows):
            state = r["state"]
            label = r["folder_name"]
            if r.get("kind") == "file":
                label = tr("status.item_file", name=label)
            color_key = STATE_COLOR_KEYS.get(state, "text")
            self.status_table.setItem(i, 0, QTableWidgetItem(name))
            self.status_table.setItem(i, 1, QTableWidgetItem(
                file_icon(r["folder_name"], is_dir=r.get("kind") != "file"), label))
            state_item = QTableWidgetItem(icon("dot", color_key), tr(f"state.{state}"))
            state_item.setForeground(QColor(THEME[color_key]))
            state_item.setToolTip(tr(f"tip.state.{state}"))
            f = state_item.font()
            f.setBold(True)
            state_item.setFont(f)
            self.status_table.setItem(i, 2, state_item)
            if state in OK_STATES:
                counts["ok"] += 1
            elif state in PROBLEM_STATES:
                counts["problems"] += 1
            elif state in PENDING_STATES:
                counts["pending"] += 1

        self.status_stack.setCurrentIndex(1 if rows else 0)
        self.kpi["emulators"].setText(str(len(self.config.get("emulators", {}))))
        for key, value in counts.items():
            self.kpi[key].setText(str(value))
        stamp = datetime.now().strftime(tr("fmt.time"))
        self.status_hint.setText(tr("status.checked", count=len(rows), time=stamp) if rows else "")
        if not self.worker or not self.worker.isRunning():
            if counts["problems"]:
                set_badge(self.badge_estado, tr("status.problems", count=counts["problems"]), "error")
            elif counts["pending"]:
                set_badge(self.badge_estado, tr("status.pending", count=counts["pending"]), "warn")
            elif rows:
                set_badge(self.badge_estado, tr("status.all_ok"), "ok")
            else:
                set_badge(self.badge_estado, tr("status.ready"), "neutral")

    # ------------------------------------------------------------------
    # Sincronización
    # ------------------------------------------------------------------
    def log(self, text: str, level: str = LOG_INFO) -> None:
        """level: 'ok' | 'error' | 'warn' | 'info'. El color NO se deduce del
        texto (el texto cambia según el idioma)."""
        color = THEME[LOG_COLOR_KEYS.get(level, "text")]
        stamp = datetime.now().strftime(tr("fmt.time"))
        if level in LOG_FILE_LEVELS:
            logging.log(LOG_FILE_LEVELS[level], text)
        self.console.appendHtml(
            f'<span style="color:{THEME["text_muted"]};">{stamp}</span>&nbsp;&nbsp;'
            f'<span style="color:{color};">{html.escape(text)}</span>'
        )

    def _set_syncing_ui(self, active: bool):
        for btn in (self.sync_selected_btn, self.sync_all_btn, self.verify_btn):
            btn.setEnabled(not active)
        self.cancel_btn.setEnabled(active)
        self.progress_bar.setVisible(active)
        if active:
            self.progress_bar.setValue(0)
            set_badge(self.badge_estado, tr("status.syncing"), "info")
            self.status_bar.showMessage(tr("status.syncing"))

    def _run_sync(self, names: List[str]):
        if not names:
            return
        self._sync_options_from_ui()
        save_config(self.config)
        self.console.clear()
        if self.config["options"].get("dry_run"):
            self.log(tr("log.dry_run_active"), LOG_WARN)
        self._set_syncing_ui(True)
        self.progress_bar.setMaximum(len(names))

        self.worker = SyncWorker(names, self.config)
        self.worker.log_message.connect(self.log)
        self.worker.progress_step.connect(lambda cur, tot: self.progress_bar.setValue(cur))
        self.worker.finished_ok.connect(self._on_sync_finished)
        self.worker.start()

    def _on_sync_finished(self, summary: Dict):
        self._set_syncing_ui(False)
        self.status_bar.showMessage(tr("status.sync_done"), 5000)
        if summary.get("failed"):
            names = ", ".join(summary["failed"])
            self.log(tr("log.review_warnings", names=names), LOG_WARN)
            self._banner_action = None
            self.banner.show_message("warning", tr("banner.sync_warnings", names=names))
        else:
            Toast.show_text(self, tr("toast.sync_done"))
        self.worker.wait()
        self._check_status()

    def _sync_selected(self):
        names = self._get_selected_emulators()
        if not names:
            show_message("info", self, tr("btn.sync_selected"), tr("msg.pick_emulators"))
            return
        self._run_sync(names)

    def _sync_all(self):
        self._run_sync(sorted(self.config.get("emulators", {}).keys()))

    def _cancel_sync(self):
        if self.worker:
            self.worker.cancel()

    # ------------------------------------------------------------------
    # Ventana / grip
    # ------------------------------------------------------------------
    def _reposition_grip(self) -> None:
        if hasattr(self, "_grip"):
            self._grip.move(self.width() - self._grip.width(), self.height() - self._grip.height())
            self._grip.raise_()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._reposition_grip()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        # Antes de mostrarse el splitter no conoce su alto real: el reparto
        # se fija acá, una vez. La tabla de estado es lo principal (≈ 3/4).
        if not getattr(self, "_splitter_sized", False):
            self._splitter_sized = True
            if self._splitters_restored:
                return
            total = max(self._right_splitter.height(), 400)
            self._right_splitter.setSizes([total * 3 // 4, total // 4])

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            if not ask_confirm(self, tr("msg.sync_running_title"), tr("msg.sync_running"),
                               confirm_text=tr("btn.stop_and_exit"), danger=True):
                event.ignore()
                return
            self.worker.cancel()
            self.worker.wait()
        self._sync_options_from_ui()
        save_config(self.config)
        save_window_state(self, splitters={"main": self._main_splitter, "right": self._right_splitter})
        event.accept()
