"""Diálogos: autodetectar, añadir/editar emulador y restaurar backups."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from emulinks.core.detection import _norm
from emulinks.core.emulators_db import DEFAULT_UNCHECKED_CATEGORIES
from emulinks.core.fs import list_backups, restore_backup
from emulinks.i18n import tr
from emulinks.ui.qt import *  # noqa: F401,F403
from emulinks.ui.theme import SP, THEME
from emulinks.ui.workers import DetectWorker
from emulinks.ui.widgets import (
    format_size, make_badge, make_empty_state, set_badge, set_help,
)


def _dialog_layout(dialog: QDialog, title: str, hint: str) -> QVBoxLayout:
    """Layout estándar de diálogo: título + ayuda, márgenes de la escala SP."""
    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(SP["lg"], SP["lg"], SP["lg"], SP["lg"])
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

        status_row = QHBoxLayout()
        status_row.setSpacing(SP["sm"])
        self.badge = make_badge(tr("status.searching"), "info")
        set_help(self.badge, "badge_detect")
        status_row.addWidget(self.badge, 0, Qt.AlignVCenter)
        self.status_label = QLabel()
        self.status_label.setObjectName("lblHint")
        self.status_label.setWordWrap(True)
        status_row.addWidget(self.status_label, 1)
        layout.addLayout(status_row)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        for col, key in enumerate(("col.detect_item", "col.category", "col.detail")):
            self.tree.headerItem().setText(col, tr(key))
        self.tree.headerItem().setToolTip(1, tr("tip.col_category"))
        self.tree.setColumnWidth(0, 340)
        self.tree.setColumnWidth(1, 220)
        self.tree.setAlternatingRowColors(True)
        self._updating = False
        self.tree.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.tree, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(SP["sm"])
        self.add_root_btn = QPushButton(tr("btn.add_search_root"))
        set_help(self.add_root_btn, "add_search_root")
        self.add_root_btn.clicked.connect(self._add_search_root)
        btn_row.addWidget(self.add_root_btn)
        self.rescan_btn = QPushButton(tr("btn.rescan"))
        set_help(self.rescan_btn, "rescan")
        self.rescan_btn.clicked.connect(self._start_scan)
        btn_row.addWidget(self.rescan_btn)
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
        self.status_label.setText(tr("detect.standard"))
        self.worker = DetectWorker(self.config)
        self.worker.progress.connect(self.status_label.setText)
        self.worker.done.connect(self._on_done)
        self.worker.start()

    def _on_done(self, result: Dict[str, Any]):
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
                    top.addChild(group)
                    for fi in inst["files"]:
                        size = format_size(fi["size"])
                        detail = tr("detect.file_detail", size=size, note=fi["note"]) if fi["note"] else size
                        self._leaf_item(group, [fi["name"], tr("cat.file"), detail],
                                        ("file", fi["name"]), fi["checked"])
                    group.setExpanded(True)

            for w in result.get("without_data", []):
                parent = self._drive_item(w["drive"], w["drive_label"])
                item = QTreeWidgetItem([w["name"], tr("detect.without_data"), str(w["exe_dir"])])
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
        directory = QFileDialog.getExistingDirectory(self, tr("dlg.pick_search_root"), str(Path.home()))
        if not directory:
            return
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
        self.setMinimumWidth(620)
        layout = _dialog_layout(self, title, tr("dlg.emu.hint"))

        form = QGridLayout()
        form.setHorizontalSpacing(SP["md"])
        form.setVerticalSpacing(SP["sm"])
        self.name_edit = QLineEdit(self.emu_name or "")
        self.name_edit.setPlaceholderText(tr("ph.emu_id"))
        set_help(self.name_edit, "emu_id")
        self.windows_edit = QLineEdit(self.emu_config.get("windows", ""))
        self.linux_edit = QLineEdit(self.emu_config.get("linux", ""))
        self.mac_edit = QLineEdit(self.emu_config.get("mac", ""))
        for edit, key in ((self.windows_edit, "path_windows"), (self.linux_edit, "path_linux"),
                          (self.mac_edit, "path_mac")):
            edit.setPlaceholderText(tr(f"ph.{key}"))
            set_help(edit, key)
        rows = (("lbl.emu_id", self.name_edit), ("lbl.path_windows", self.windows_edit),
                ("lbl.path_linux", self.linux_edit), ("lbl.path_mac", self.mac_edit))
        for row, (key, widget) in enumerate(rows):
            lbl = QLabel(tr(key))
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            form.addWidget(lbl, row, 0)
            form.addWidget(widget, row, 1)
        form.setColumnStretch(1, 1)
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
        set_help(self.save_btn, "save_emulator")
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

    def _validate_and_accept(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, tr("msg.error_title"), tr("msg.emu_id_empty"))
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
        self.setMinimumSize(640, 420)
        layout = _dialog_layout(self, title, tr("dlg.restore.hint"))

        self.table = QTableWidget(0, 3)
        for col, key in enumerate(("col.folder", "col.backup", "col.date")):
            self.table.setHorizontalHeaderItem(col, QTableWidgetItem(tr(key)))
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setHighlightSections(False)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.doubleClicked.connect(self._restore_selected)

        self.stack = QStackedWidget()
        self.stack.addWidget(make_empty_state(tr("empty.backups")))
        self.stack.addWidget(self.table)
        layout.addWidget(self.stack, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(SP["sm"])
        btn_row.addStretch()
        self.close_btn = QPushButton(tr("btn.close"))
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
            date_str = datetime.fromtimestamp(b["mtime"]).strftime(tr("fmt.datetime"))
            self.table.setItem(row, 0, QTableWidgetItem(b["folder_name"]))
            name_item = QTableWidgetItem(tr("dlg.restore.legacy", name=b["file_name"]) if b.get("legacy")
                                         else b["file_name"])
            name_item.setToolTip(str(b["full_path"]))
            self.table.setItem(row, 1, name_item)
            self.table.setItem(row, 2, QTableWidgetItem(date_str))
        self.table.resizeColumnsToContents()
        self.stack.setCurrentIndex(1 if self._backups else 0)
        self.restore_btn.setEnabled(bool(self._backups))

    def _restore_selected(self, *_):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._backups):
            QMessageBox.information(self, tr("btn.restore"), tr("msg.pick_backup"))
            return
        b = self._backups[row]
        dest_folder = Path(self.config["shared_dir"]) / self.emu_name / b["folder_name"]
        ok, msg = restore_backup(b["full_path"], b["is_zip"], dest_folder, b.get("member"))
        if ok:
            QMessageBox.information(self, tr("msg.restored_title"), tr("msg.restored", path=msg))
            self.accept()
        else:
            QMessageBox.critical(self, tr("msg.restore_error_title"), msg)
