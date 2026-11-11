"""Diálogos: autodetectar, añadir/editar emulador, restaurar backups,
configuración y "Acerca de"."""

import platform
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from emulinks import APP_DEVELOPER, APP_EMAIL, APP_NAME, APP_URL, APP_VERSION
from emulinks.core.config import CONFIG_PATH, LOG_DIR
from emulinks.core.detection import _norm
from emulinks.core.emulators_db import DEFAULT_UNCHECKED_CATEGORIES
from emulinks.core.fs import list_backups, restore_backup
from emulinks.i18n import LANGUAGES, tr
from emulinks.ui.filetypes import file_icon
from emulinks.ui.icons import icon, icon_pixmap, set_button_icon
from emulinks.ui.qt import *  # noqa: F401,F403
from emulinks.ui.theme import (
    ICON_SIZE, SP, THEME, get_lang_code, get_theme_name, set_lang_code, set_theme_name,
)
from emulinks.ui.workers import DetectWorker
from emulinks.ui.widgets import (
    BusySpinner, copy_to_clipboard, format_datetime, human_size, make_badge, make_card,
    make_divider, make_empty_state, make_error_label, open_with_system, remember_dir,
    set_badge, set_field_error, set_help, show_message,
)


def _dialog_layout(dialog: QDialog, title: str, hint: str) -> QVBoxLayout:
    """Layout estándar de diálogo: título + ayuda, márgenes de la escala SP."""
    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(SP["xl"], SP["lg"], SP["xl"], SP["lg"])
    layout.setSpacing(SP["md"])
    lbl_title = QLabel(title)
    lbl_title.setObjectName("lblTitle")
    layout.addWidget(lbl_title)
    if hint:
        lbl_hint = QLabel(hint)
        lbl_hint.setObjectName("lblHint")
        lbl_hint.setWordWrap(True)
        layout.addWidget(lbl_hint)
    return layout


def _form_grid() -> "QGridLayout":
    g = QGridLayout()
    g.setHorizontalSpacing(SP["md"])
    g.setVerticalSpacing(SP["sm"])
    g.setColumnMinimumWidth(0, 140)
    g.setColumnStretch(1, 1)
    return g


def _form_label(text: str) -> "QLabel":
    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    return lbl


def _setup_table(table: QTableWidget) -> None:
    """Aspecto común de las tablas chicas (sección 15: QTableWidget con el estilo global)."""
    header = table.horizontalHeader()
    header.setStretchLastSection(True)
    header.setHighlightSections(False)
    header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(32)
    table.setShowGrid(False)
    table.setWordWrap(False)
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)


# ══════════════════════════════════════════════════════════════════════════
# AUTODETECTAR
# ══════════════════════════════════════════════════════════════════════════
class DetectDialog(QDialog):
    """Muestra todo lo detectado (estándar, Flatpak y portable) con una casilla
    por carpeta y por archivo. No toca el disco: solo arma la selección."""

    def __init__(self, parent, config: Dict[str, Any]):
        super().__init__(parent)
        self.config = config
        self.worker = None
        self._installs: List[Dict[str, Any]] = []
        self._build_ui()
        self._start_scan()

    def _build_ui(self):
        self.setWindowTitle(tr("dlg.detect.title"))
        self.setModal(True)
        self.setMinimumSize(1000, 640)
        layout = _dialog_layout(self, tr("dlg.detect.title"), tr("dlg.detect.hint"))

        # Estado de la búsqueda + acciones sobre la búsqueda (todas con ícono).
        status_row = QHBoxLayout()
        status_row.setSpacing(SP["sm"])
        self.spinner = BusySpinner()
        status_row.addWidget(self.spinner, 0, Qt.AlignVCenter)
        self.badge = make_badge(tr("status.searching"), "info")
        set_help(self.badge, "badge_detect")
        status_row.addWidget(self.badge, 0, Qt.AlignVCenter)
        self.status_label = QLabel()
        self.status_label.setObjectName("lblHint")
        self.status_label.setWordWrap(True)
        status_row.addWidget(self.status_label, 1)
        self.add_root_btn = QPushButton(tr("btn.add_search_root"))
        set_button_icon(self.add_root_btn, "folder_plus")
        set_help(self.add_root_btn, "add_search_root")
        self.add_root_btn.clicked.connect(self._add_search_root)
        status_row.addWidget(self.add_root_btn)
        self.rescan_btn = QPushButton(tr("btn.rescan"))
        self.rescan_btn.setObjectName("btnSecondary")
        set_button_icon(self.rescan_btn, "refresh")
        set_help(self.rescan_btn, "rescan", shortcut="F5")
        self.rescan_btn.setShortcut("F5")
        self.rescan_btn.clicked.connect(self._start_scan)
        status_row.addWidget(self.rescan_btn)
        layout.addLayout(status_row)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        for col, key in enumerate(("col.detect_item", "col.category", "col.detail")):
            self.tree.headerItem().setText(col, tr(key))
        self.tree.headerItem().setToolTip(1, tr("tip.col_category"))
        self.tree.setColumnWidth(0, 340)
        self.tree.setColumnWidth(1, 220)
        self.tree.setAlternatingRowColors(True)
        self.tree.setIconSize(QSize(ICON_SIZE["sm"], ICON_SIZE["sm"]))
        self._updating = False
        self.tree.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.tree, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(SP["sm"])
        btn_row.addStretch()
        self.cancel_btn = QPushButton(tr("btn.cancel"))
        set_help(self.cancel_btn, "cancel_dialog")
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.cancel_btn)
        self.accept_btn = QPushButton(tr("btn.add_selected"))
        self.accept_btn.setObjectName("btnPrimary")
        set_help(self.accept_btn, "add_selected")
        self.accept_btn.clicked.connect(self.accept)
        btn_row.addWidget(self.accept_btn)
        layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    def _start_scan(self):
        if self.worker and self.worker.isRunning():
            return
        self.tree.clear()
        self._installs = []
        for btn in (self.accept_btn, self.rescan_btn, self.add_root_btn):
            btn.setEnabled(False)
        set_badge(self.badge, tr("status.searching"), "info")
        self.spinner.start()
        self.status_label.setText(tr("detect.standard"))
        self.worker = DetectWorker(self.config)
        self.worker.progress.connect(self.status_label.setText)
        self.worker.done.connect(self._on_done)
        self.worker.start()

    def _on_done(self, result: Dict[str, Any]):
        self.spinner.stop()
        self.rescan_btn.setEnabled(True)
        self.add_root_btn.setEnabled(True)
        if result.get("error"):
            set_badge(self.badge, tr("status.error"), "error")
            self.status_label.setText(tr("detect.error", detail=result["error"]))
            return
        self._installs = result.get("installs", [])
        self._populate(result)
        self.accept_btn.setEnabled(bool(self._installs))

    # ------------------------------------------------------------------
    # Árbol: unidad → emulador → carpetas / archivos sueltos
    # ------------------------------------------------------------------
    # Cada grupo (unidad, emulador, archivos sueltos) tiene 3 estados y un clic
    # los recorre en ciclo: vacío = nada · cuadrado = lo recomendado · tilde =
    # todo. Qt solo ofrece el ciclo con ItemIsUserTristate; el efecto sobre
    # los hijos lo aplicamos acá. Las hojas guardan si vienen recomendadas.
    ROLE_RECOMMENDED = Qt.UserRole + 1

    def _group_item(self, texts: List[str], tag) -> QTreeWidgetItem:
        item = QTreeWidgetItem(texts)
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsUserTristate)
        item.setData(0, Qt.UserRole, tag)
        item.setToolTip(0, tr("tip.tristate"))
        return item

    def _leaf_item(self, parent: QTreeWidgetItem, texts: List[str], tag, recommended: bool) -> QTreeWidgetItem:
        item = QTreeWidgetItem(texts)
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setData(0, Qt.UserRole, tag)
        item.setData(0, self.ROLE_RECOMMENDED, recommended)
        parent.addChild(item)
        item.setCheckState(0, Qt.Checked if recommended else Qt.Unchecked)
        return item

    @staticmethod
    def _is_leaf(item) -> bool:
        tag = item.data(0, Qt.UserRole)
        return bool(tag) and tag[0] in ("folder", "file")

    def _leaves(self, node) -> List[QTreeWidgetItem]:
        out = []
        for i in range(node.childCount()):
            child = node.child(i)
            if self._is_leaf(child):
                out.append(child)
            else:
                out.extend(self._leaves(child))
        return out

    def _refresh_group(self, node) -> None:
        """El estado visible de un grupo sale de sus hojas."""
        if not (node.flags() & Qt.ItemIsUserCheckable):
            return
        leaves = self._leaves(node)
        checked = sum(1 for leaf in leaves if leaf.checkState(0) == Qt.Checked)
        if leaves and checked == len(leaves):
            node.setCheckState(0, Qt.Checked)
        elif checked:
            node.setCheckState(0, Qt.PartiallyChecked)
        else:
            node.setCheckState(0, Qt.Unchecked)

    def _refresh_subtree(self, node) -> None:
        for i in range(node.childCount()):
            child = node.child(i)
            if child.childCount():
                self._refresh_subtree(child)
        if node.childCount():
            self._refresh_group(node)

    def _on_item_changed(self, item, column: int) -> None:
        if self._updating or column != 0 or not (item.flags() & Qt.ItemIsUserCheckable):
            return
        self._updating = True
        try:
            if not self._is_leaf(item):
                state = item.checkState(0)
                for leaf in self._leaves(item):
                    if state == Qt.Checked:
                        target = Qt.Checked
                    elif state == Qt.Unchecked:
                        target = Qt.Unchecked
                    else:
                        target = Qt.Checked if leaf.data(0, self.ROLE_RECOMMENDED) else Qt.Unchecked
                    leaf.setCheckState(0, target)
                self._refresh_subtree(item)
            node = item.parent()
            while node is not None:
                self._refresh_group(node)
                node = node.parent()
        finally:
            self._updating = False

    def _drive_item(self, drive: str, label: str) -> QTreeWidgetItem:
        if drive not in self._drives:
            title = tr("detect.drive_label", drive=drive, label=label) if label else tr("detect.drive", drive=drive)
            item = self._group_item([title, "", ""], ("drive", drive))
            item.setIcon(0, icon("drive"))
            f = item.font(0)
            f.setBold(True)
            item.setFont(0, f)
            self.tree.addTopLevelItem(item)
            self._drives[drive] = item
            self._drive_counts[drive] = 0
        return self._drives[drive]

    def _populate(self, result: Dict[str, Any]):
        muted = QColor(THEME["text_muted"])
        broken_total = 0
        self._drives: Dict[str, QTreeWidgetItem] = {}
        self._drive_counts: Dict[str, int] = {}
        self._updating = True
        try:
            for idx, inst in enumerate(self._installs):
                parent = self._drive_item(inst["drive"], inst["drive_label"])
                self._drive_counts[inst["drive"]] += 1
                origin = tr(f"origin.{inst['origin']}")
                if inst.get("config_id"):
                    origin = tr("detect.origin_existing", origin=origin, id=inst["config_id"])
                else:
                    origin = tr("detect.origin_new", origin=origin, id=inst["id"])
                broken = sum(1 for f in inst["folders"] if f.get("broken"))
                broken_total += broken
                detail = str(inst["data_dir"])
                if inst.get("warning"):
                    detail = tr("detect.with_warning", warning=inst["warning"], path=detail)
                if broken:
                    detail = tr("detect.install_broken", count=broken, detail=detail)
                top = self._group_item([inst["name"], origin, detail], ("install", idx))
                top.setIcon(0, icon("app"))
                top.setToolTip(1, origin)
                top.setToolTip(2, detail)
                f = top.font(0)
                f.setBold(True)
                top.setFont(0, f)
                if broken:
                    top.setForeground(2, QColor(THEME["error"]))
                elif inst.get("warning"):
                    top.setForeground(2, QColor(THEME["counter"]))
                parent.addChild(top)

                for folder in inst["folders"]:
                    label = folder["name"]
                    if folder["linked"]:
                        label = tr("detect.folder_linked", name=label)
                    elif folder.get("broken"):
                        label = tr("detect.folder_broken", name=label)
                    child = self._leaf_item(top, [label, tr(f"cat.{folder['category']}"), folder["note"]],
                                            ("folder", folder["name"]), folder["checked"])
                    child.setIcon(0, file_icon(folder["name"], is_dir=True))
                    child.setToolTip(2, folder["note"])
                    if folder.get("broken"):
                        for col in (0, 2):
                            child.setForeground(col, QColor(THEME["error"]))
                    elif folder["linked"]:
                        child.setForeground(0, QColor(THEME["ok"]))
                    elif folder["category"] in DEFAULT_UNCHECKED_CATEGORIES:
                        child.setForeground(1, muted)
                    elif folder["category"] == "other":
                        child.setForeground(1, QColor(THEME["counter"]))

                if inst["files"]:
                    group = self._group_item([tr("detect.loose_files"), tr("detect.loose_files_cat"),
                                              tr("detect.loose_files_detail")], ("files", idx))
                    group.setIcon(0, icon("file"))
                    top.addChild(group)
                    for fi in inst["files"]:
                        size = human_size(fi["size"])
                        detail = tr("detect.file_detail", size=size, note=fi["note"]) if fi["note"] else size
                        leaf = self._leaf_item(group, [fi["name"], tr("cat.file"), detail],
                                               ("file", fi["name"]), fi["checked"])
                        leaf.setIcon(0, file_icon(fi["name"], is_dir=False))
                    group.setExpanded(True)

            for w in result.get("without_data", []):
                parent = self._drive_item(w["drive"], w["drive_label"])
                item = QTreeWidgetItem([w["name"], tr("detect.without_data"), str(w["exe_dir"])])
                item.setIcon(0, icon("app", "text_muted"))
                item.setToolTip(0, tr("tip.without_data"))
                item.setToolTip(1, tr("tip.without_data"))
                for col in range(3):
                    item.setForeground(col, muted)
                parent.addChild(item)

            for drive, item in self._drives.items():
                item.setText(1, tr("detect.drive_count", count=self._drive_counts[drive]))
                if not self._leaves(item):
                    # Solo instalaciones sin datos: no hay nada para tildar.
                    item.setFlags(item.flags() & ~Qt.ItemIsUserCheckable & ~Qt.ItemIsUserTristate)
                    item.setData(0, Qt.CheckStateRole, None)
                self._refresh_subtree(item)
                item.setExpanded(True)
        finally:
            self._updating = False

        n_folders = sum(len(i["folders"]) for i in self._installs)
        n_files = sum(len(i["files"]) for i in self._installs)
        if not self._installs:
            set_badge(self.badge, tr("status.nothing_found"), "neutral")
            self.status_label.setText(tr("detect.nothing"))
            return
        msg = tr("detect.summary", installs=len(self._installs), drives=len(self._drives),
                 folders=n_folders, files=n_files)
        if broken_total:
            msg = tr("detect.summary_broken", summary=msg, broken=broken_total)
        if result.get("cancelled"):
            msg = tr("detect.summary_cancelled", summary=msg)
        set_badge(self.badge, tr("status.found", count=len(self._installs)),
                  "warn" if broken_total else "ok")
        self.status_label.setText(msg)

    def _add_search_root(self):
        directory = QFileDialog.getExistingDirectory(self, tr("dlg.pick_search_root"),
                                                     remember_dir("search_root"))
        if not directory:
            return
        remember_dir("search_root", directory)
        roots = self.config.setdefault("options", {}).setdefault("search_roots", [])
        if _norm(directory) not in {_norm(r) for r in roots}:
            roots.append(directory)
        self._start_scan()

    # ------------------------------------------------------------------
    def selected(self) -> List[Tuple[Dict[str, Any], List[str], List[str]]]:
        """[(instalación, carpetas tildadas, archivos tildados)] — solo las
        instalaciones con algo tildado."""
        out = []

        def walk(node):
            for i in range(node.childCount()):
                child = node.child(i)
                tag = child.data(0, Qt.UserRole)
                if tag and tag[0] == "install":
                    folders, files = [], []
                    for leaf in self._leaves(child):
                        if leaf.checkState(0) == Qt.Checked:
                            kind, name = leaf.data(0, Qt.UserRole)
                            (folders if kind == "folder" else files).append(name)
                    if folders or files:
                        out.append((self._installs[tag[1]], folders, files))
                else:
                    walk(child)

        walk(self.tree.invisibleRootItem())
        return out

    def done(self, r):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()
        super().done(r)


# ══════════════════════════════════════════════════════════════════════════
# AÑADIR / EDITAR EMULADOR
# ══════════════════════════════════════════════════════════════════════════
class EmulatorDialog(QDialog):
    def __init__(self, parent=None, emu_name: Optional[str] = None, emu_config: Optional[Dict] = None):
        super().__init__(parent)
        self.emu_name = emu_name
        self.emu_config = emu_config or {}
        self._build_ui()

    def _build_ui(self):
        title = tr("dlg.emu.edit_title") if self.emu_name else tr("dlg.emu.add_title")
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(640)
        layout = _dialog_layout(self, title, tr("dlg.emu.hint"))

        form = _form_grid()
        self.name_edit = QLineEdit(self.emu_name or "")
        self.name_edit.setPlaceholderText(tr("ph.emu_id"))
        set_help(self.name_edit, "emu_id")
        self.name_error = make_error_label()
        self.name_edit.editingFinished.connect(self._validate_name)
        self.windows_edit = QLineEdit(self.emu_config.get("windows", ""))
        self.linux_edit = QLineEdit(self.emu_config.get("linux", ""))
        self.mac_edit = QLineEdit(self.emu_config.get("mac", ""))
        for edit, key in ((self.windows_edit, "path_windows"), (self.linux_edit, "path_linux"),
                          (self.mac_edit, "path_mac")):
            edit.setPlaceholderText(tr(f"ph.{key}"))
            edit.addAction(icon("folder", "text_muted"), QLineEdit.LeadingPosition)
            set_help(edit, key)
        form.addWidget(_form_label(tr("lbl.emu_id")), 0, 0)
        form.addWidget(self.name_edit, 0, 1)
        form.addWidget(self.name_error, 1, 1)
        for row, (key, widget) in enumerate((("lbl.path_windows", self.windows_edit),
                                             ("lbl.path_linux", self.linux_edit),
                                             ("lbl.path_mac", self.mac_edit)), start=2):
            form.addWidget(_form_label(tr(key)), row, 0)
            form.addWidget(widget, row, 1)
        layout.addLayout(form)

        lists = QHBoxLayout()
        lists.setSpacing(SP["lg"])
        self.folders_edit = self._list_editor(lists, "lbl.folders", "folders_list",
                                              self.emu_config.get("important_folders", []))
        self.files_edit = self._list_editor(lists, "lbl.files", "files_list",
                                            self.emu_config.get("important_files", []))
        layout.addLayout(lists, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(SP["sm"])
        btn_row.addStretch()
        self.cancel_btn = QPushButton(tr("btn.cancel"))
        set_help(self.cancel_btn, "cancel_dialog")
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.cancel_btn)
        self.save_btn = QPushButton(tr("btn.save"))
        self.save_btn.setObjectName("btnPrimary")
        set_help(self.save_btn, "save_emulator", shortcut="Ctrl+S")
        self.save_btn.setShortcut("Ctrl+S")
        self.save_btn.setDefault(True)
        self.save_btn.clicked.connect(self._validate_and_accept)
        btn_row.addWidget(self.save_btn)
        layout.addLayout(btn_row)

    @staticmethod
    def _list_editor(parent_layout, label_key: str, help_key: str, values: List[str]) -> QPlainTextEdit:
        col = QVBoxLayout()
        col.setSpacing(SP["sm"])
        lbl = QLabel(tr(label_key))
        lbl.setObjectName("lblSubtitle")
        lbl.setWordWrap(True)
        col.addWidget(lbl)
        edit = QPlainTextEdit()
        edit.setPlainText("\n".join(values))
        edit.setMinimumHeight(140)
        set_help(edit, help_key)
        col.addWidget(edit, 1)
        parent_layout.addLayout(col, 1)
        return edit

    def _validate_name(self) -> bool:
        """Se valida al salir del campo o al guardar, nunca en cada tecla."""
        ok = bool(self.name_edit.text().strip())
        set_field_error(self.name_edit, None if ok else tr("msg.emu_id_empty"), self.name_error)
        return ok

    def _validate_and_accept(self):
        if not self._validate_name():
            self.name_edit.setFocus()
            return
        self.accept()

    def get_data(self) -> Tuple[str, Dict[str, Any]]:
        def lines(edit):
            return [f.strip() for f in edit.toPlainText().split("\n") if f.strip()]
        return self.name_edit.text().strip(), {
            "windows": self.windows_edit.text().strip(),
            "linux": self.linux_edit.text().strip(),
            "mac": self.mac_edit.text().strip(),
            "important_folders": lines(self.folders_edit),
            "important_files": lines(self.files_edit),
        }


# ══════════════════════════════════════════════════════════════════════════
# RESTAURAR BACKUPS
# ══════════════════════════════════════════════════════════════════════════
class RestoreBackupDialog(QDialog):
    def __init__(self, parent, config: Dict[str, Any], emu_name: str):
        super().__init__(parent)
        self.config = config
        self.emu_name = emu_name
        self._backups: List[Dict[str, Any]] = []
        self._build_ui()
        self._populate()

    def _build_ui(self):
        title = tr("dlg.restore.title", name=self.emu_name)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumSize(680, 440)
        layout = _dialog_layout(self, title, tr("dlg.restore.hint"))

        self.table = QTableWidget(0, 3)
        for col, key in enumerate(("col.folder", "col.backup", "col.date")):
            self.table.setHorizontalHeaderItem(col, QTableWidgetItem(tr(key)))
        _setup_table(self.table)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setIconSize(QSize(ICON_SIZE["sm"], ICON_SIZE["sm"]))
        self.table.doubleClicked.connect(self._restore_selected)

        self.stack = QStackedWidget()
        self.stack.addWidget(make_empty_state(tr("empty.backups"), "file_archive"))
        self.stack.addWidget(self.table)
        layout.addWidget(self.stack, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(SP["sm"])
        btn_row.addStretch()
        self.close_btn = QPushButton(tr("btn.close"))
        set_help(self.close_btn, "cancel_dialog")
        self.close_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.close_btn)
        self.restore_btn = QPushButton(tr("btn.restore"))
        self.restore_btn.setObjectName("btnPrimary")
        set_help(self.restore_btn, "restore")
        self.restore_btn.clicked.connect(self._restore_selected)
        btn_row.addWidget(self.restore_btn)
        layout.addLayout(btn_row)

    def _populate(self):
        self._backups = list_backups(self.config, self.emu_name)
        self.table.setRowCount(len(self._backups))
        for row, b in enumerate(self._backups):
            folder_item = QTableWidgetItem(icon("folder", "ft_folder"), b["folder_name"])
            self.table.setItem(row, 0, folder_item)
            name = tr("dlg.restore.legacy", name=b["file_name"]) if b.get("legacy") else b["file_name"]
            name_item = QTableWidgetItem(file_icon(str(b["full_path"]), is_dir=not b["is_zip"]), name)
            name_item.setToolTip(str(b["full_path"]))
            self.table.setItem(row, 1, name_item)
            self.table.setItem(row, 2, QTableWidgetItem(format_datetime(b["mtime"])))
        self.table.resizeColumnsToContents()
        self.stack.setCurrentIndex(1 if self._backups else 0)
        self.restore_btn.setEnabled(bool(self._backups))
        if self._backups:
            self.table.selectRow(0)

    def _restore_selected(self, *_):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._backups):
            show_message("info", self, tr("btn.restore"), tr("msg.pick_backup"))
            return
        b = self._backups[row]
        dest_folder = Path(self.config["shared_dir"]) / self.emu_name / b["folder_name"]
        ok, msg = restore_backup(b["full_path"], b["is_zip"], dest_folder, b.get("member"))
        if ok:
            show_message("success", self, tr("msg.restored_title"), tr("msg.restored", path=msg))
            self.accept()
        else:
            show_message("error", self, tr("msg.restore_error_title"), msg)


# ══════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN (sección 18)
# ══════════════════════════════════════════════════════════════════════════
def _page(title: str, subtitle: str = None):
    """Página de configuración: título + subtítulo + contenido con scroll. Devuelve (scroll, layout)."""
    inner = QWidget()
    lay = QVBoxLayout(inner)
    lay.setContentsMargins(SP["xl"], SP["lg"], SP["xl"], SP["lg"])
    lay.setSpacing(SP["md"])
    t = QLabel(title)
    t.setObjectName("lblTitle")
    lay.addWidget(t)
    if subtitle:
        s = QLabel(subtitle)
        s.setObjectName("lblSubtitle")
        s.setWordWrap(True)
        lay.addWidget(s)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setWidget(inner)
    return scroll, lay


class SettingsDialog(QDialog):
    """
    Configuración con navegación lateral. Trae la página 'General' (tema, idioma, registros).
    Cada programa agrega las suyas con new_page() + add_page(..., on_save=fn); fn devuelve
    True si el cambio requiere reiniciar.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("settings.title"))
        self.resize(800, 540)
        self.setMinimumSize(720, 480)
        self._savers: List[Callable[[], bool]] = []

        side = QFrame()
        side.setObjectName("sidebar")
        side.setFixedWidth(200)
        side_lay = QVBoxLayout(side)
        side_lay.setContentsMargins(SP["sm"], SP["md"], SP["sm"], SP["md"])
        self.nav = QListWidget()
        self.nav.setObjectName("sideNav")
        self.nav.setIconSize(QSize(ICON_SIZE["sm"], ICON_SIZE["sm"]))
        side_lay.addWidget(self.nav)
        self.pages = QStackedWidget()
        self.nav.currentRowChanged.connect(self.pages.setCurrentIndex)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(side)
        body.addWidget(self.pages, 1)

        hint = QLabel(tr("settings.restart_hint"))
        hint.setObjectName("lblHint")
        btn_cancel = QPushButton(tr("common.cancel"))
        set_help(btn_cancel, "cancel_dialog")
        btn_save = QPushButton(tr("common.save"))
        btn_save.setObjectName("btnPrimary")
        set_help(btn_save, "settings_save")
        btn_save.setDefault(True)
        btn_cancel.clicked.connect(self.reject)
        btn_save.clicked.connect(self.accept)
        foot = QHBoxLayout()
        foot.setContentsMargins(SP["lg"], SP["md"], SP["lg"], SP["md"])
        foot.setSpacing(SP["sm"])
        foot.addWidget(hint, 1)
        foot.addWidget(btn_cancel)
        foot.addWidget(btn_save)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addLayout(body, 1)
        root.addWidget(make_divider())
        root.addLayout(foot)

        self._build_general()
        self.nav.setCurrentRow(0)

    def new_page(self, icon_name: str, title: str, subtitle: str = None):
        return _page(title, subtitle)

    def add_page(self, icon_name: str, title: str, page, on_save=None) -> None:
        self.nav.addItem(QListWidgetItem(icon(icon_name), title))
        self.pages.addWidget(page)
        if on_save:
            self._savers.append(on_save)

    def _build_general(self) -> None:
        page, lay = _page(tr("settings.general"), tr("settings.general_sub"))
        card, card_lay = make_card(tr("settings.appearance"))
        grid = _form_grid()
        self.cmb_theme = QComboBox()
        self.cmb_theme.addItem(icon("moon"), tr("theme.dark"), "dark")
        self.cmb_theme.addItem(icon("monitor"), tr("theme.light"), "light")
        self.cmb_theme.setCurrentIndex(self.cmb_theme.findData(get_theme_name()))
        set_help(self.cmb_theme, "theme")
        self.cmb_lang = QComboBox()
        for code, name in LANGUAGES.items():
            self.cmb_lang.addItem(name, code)
        self.cmb_lang.setCurrentIndex(self.cmb_lang.findData(get_lang_code()))
        set_help(self.cmb_lang, "language")
        grid.addWidget(_form_label(tr("settings.theme")), 0, 0)
        grid.addWidget(self.cmb_theme, 0, 1)
        grid.addWidget(_form_label(tr("settings.language")), 1, 0)
        grid.addWidget(self.cmb_lang, 1, 1)
        card_lay.addLayout(grid)
        lay.addWidget(card)

        card2, card2_lay = make_card(tr("settings.data"))
        row = QHBoxLayout()
        lbl = QLabel(tr("settings.logs_hint"))
        lbl.setObjectName("lblHint")
        lbl.setWordWrap(True)
        btn_logs = QPushButton(tr("settings.open_logs"))
        set_button_icon(btn_logs, "open")
        set_help(btn_logs, "open_logs")
        btn_logs.clicked.connect(lambda: open_with_system(LOG_DIR))
        row.addWidget(lbl, 1)
        row.addWidget(btn_logs)
        card2_lay.addLayout(row)
        lay.addWidget(card2)
        lay.addStretch(1)
        self.add_page("settings", tr("settings.general"), page, on_save=self._save_general)

    def _save_general(self) -> bool:
        """Devuelve True si algo requiere reiniciar."""
        changed = False
        if self.cmb_theme.currentData() != get_theme_name():
            set_theme_name(self.cmb_theme.currentData())
            changed = True
        if self.cmb_lang.currentData() != get_lang_code():
            set_lang_code(self.cmb_lang.currentData())
            changed = True
        return changed

    def accept(self) -> None:
        needs_restart = any([saver() for saver in self._savers])
        super().accept()
        if needs_restart:
            show_message("info", self.parent(), tr("msg.restart_title"), tr("msg.restart_text", app=APP_NAME))


class SearchRootsPage:
    """Página propia de EmuLinks en Configuración: carpetas extra donde el
    autodetector busca emuladores portables. Antes solo se podían agregar
    (desde el autodetector); acá también se quitan."""

    def __init__(self, dlg: SettingsDialog, config: Dict[str, Any]):
        self.config = config
        page, lay = dlg.new_page("search", tr("settings.detect"), tr("settings.detect_sub"))
        btn_add = QPushButton(tr("btn.add_search_root"))
        btn_add.setObjectName("btnSecondary")
        set_button_icon(btn_add, "folder_plus")
        set_help(btn_add, "add_search_root_settings")
        btn_add.clicked.connect(self._add)
        card, card_lay = make_card(tr("settings.search_roots"), header_widget=btn_add)
        self.list = QListWidget()
        self.list.setMinimumHeight(180)
        self.list.setIconSize(QSize(ICON_SIZE["sm"], ICON_SIZE["sm"]))
        set_help(self.list, "search_roots_list")
        for root in config.get("options", {}).get("search_roots", []):
            self._add_item(root)
        self.stack = QStackedWidget()
        self.stack.addWidget(make_empty_state(tr("empty.search_roots"), "folder"))
        self.stack.addWidget(self.list)
        card_lay.addWidget(self.stack, 1)
        row = QHBoxLayout()
        row.addStretch(1)
        self.btn_remove = QPushButton(tr("btn.remove"))
        set_button_icon(self.btn_remove, "trash")
        set_help(self.btn_remove, "remove_search_root")
        self.btn_remove.clicked.connect(self._remove)
        row.addWidget(self.btn_remove)
        card_lay.addLayout(row)
        lay.addWidget(card, 1)
        self._sync()
        self.list.currentRowChanged.connect(lambda _r: self._sync())
        dlg.add_page("search", tr("settings.detect"), page, on_save=self._save)

    def _add_item(self, path: str) -> None:
        self.list.addItem(QListWidgetItem(icon("folder", "ft_folder"), path))

    def _roots(self) -> List[str]:
        return [self.list.item(i).text() for i in range(self.list.count())]

    def _sync(self) -> None:
        self.stack.setCurrentIndex(1 if self.list.count() else 0)
        self.btn_remove.setEnabled(self.list.currentRow() >= 0)

    def _add(self) -> None:
        directory = QFileDialog.getExistingDirectory(self.list, tr("dlg.pick_search_root"),
                                                     remember_dir("search_root"))
        if directory and _norm(directory) not in {_norm(r) for r in self._roots()}:
            remember_dir("search_root", directory)
            self._add_item(directory)
            self.list.setCurrentRow(self.list.count() - 1)
        self._sync()

    def _remove(self) -> None:
        row = self.list.currentRow()
        if row >= 0:
            self.list.takeItem(row)
        self._sync()

    def _save(self) -> bool:
        self.config.setdefault("options", {})["search_roots"] = self._roots()
        return False        # se usa en la próxima búsqueda, sin reiniciar


# ══════════════════════════════════════════════════════════════════════════
# ACERCA DE (sección 18)
# ══════════════════════════════════════════════════════════════════════════
class AboutDialog(QDialog):
    def __init__(self, parent=None, description: str = None):
        super().__init__(parent)
        self.setWindowTitle(tr("about.title", app=APP_NAME))
        self.setMinimumWidth(500)
        app_icon = QApplication.windowIcon()
        logo = QLabel()
        logo.setPixmap(app_icon.pixmap(48, 48) if not app_icon.isNull()
                       else icon_pixmap("app", 48, "accent"))
        name = QLabel(APP_NAME)
        name.setObjectName("lblTitle")
        ver = QLabel(tr("about.version", v=APP_VERSION))
        ver.setObjectName("lblSubtitle")
        head = QHBoxLayout()
        head.setSpacing(SP["md"])
        head.addWidget(logo, 0, Qt.AlignTop)
        titles = QVBoxLayout()
        titles.setSpacing(2)
        titles.addWidget(name)
        titles.addWidget(ver)
        head.addLayout(titles, 1)

        # Contacto: el no-reply de GitHub, nunca un correo personal.
        info = [
            (tr("about.developer"), APP_DEVELOPER),
            (tr("about.contact"), APP_EMAIL),
            (tr("about.project"), APP_URL),
            ("Qt", f"{_QT_BACKEND}"),
            ("Python", platform.python_version()),
            (tr("about.system"), f"{platform.system()} {platform.release()} ({platform.machine()})"),
            (tr("about.config"), str(CONFIG_PATH)),
        ]
        self._info_text = "\n".join([f"{APP_NAME} v{APP_VERSION}"] + [f"{k}: {v}" for k, v in info])
        grid = _form_grid()
        grid.setColumnMinimumWidth(0, 100)
        for r, (k, v) in enumerate(info):
            grid.addWidget(_form_label(k), r, 0)
            val = QLabel(v)
            val.setTextInteractionFlags(Qt.TextSelectableByMouse)
            grid.addWidget(val, r, 1)

        btn_copy = QPushButton(tr("about.copy"))
        btn_copy.setObjectName("btnSecondary")
        set_button_icon(btn_copy, "copy")
        set_help(btn_copy, "about_copy")
        btn_copy.clicked.connect(lambda: (copy_to_clipboard(self._info_text),
                                          btn_copy.setText(tr("about.copied"))))
        btn_close = QPushButton(tr("common.close"))
        btn_close.setObjectName("btnPrimary")
        btn_close.setDefault(True)
        btn_close.clicked.connect(self.accept)
        foot = QHBoxLayout()
        foot.addWidget(btn_copy)
        foot.addStretch(1)
        foot.addWidget(btn_close)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(SP["xl"], SP["xl"], SP["xl"], SP["lg"])
        lay.setSpacing(SP["lg"])
        lay.addLayout(head)
        if description:
            d = QLabel(description)
            d.setWordWrap(True)
            lay.addWidget(d)
        lay.addLayout(grid)
        lay.addLayout(foot)
