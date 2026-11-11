"""Componentes del sistema de diseño v6.1 (secciones 6, 7, 10, 14.1, 16, 19 y 21):
ayuda contextual, botones con ícono, tarjetas, badges, KPIs, log, estado vacío,
validación, mensajes, aviso (Banner), notificación (Toast), spinner, selector
de ruta, persistencia de ventana y grip.

Todos se diferencian por objectName; el stylesheet global hace el resto.
"""

import os
import subprocess
from datetime import datetime

from emulinks import APP_NAME
from emulinks import i18n
from emulinks.core.system import IS_MACOS, IS_WINDOWS
from emulinks.i18n import tr, tr_opt
from emulinks.ui.icons import icon, icon_label, icon_pixmap
from emulinks.ui.qt import *  # noqa: F401,F403
from emulinks.ui.theme import ICON_SIZE, SP, THEME


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ▶  HELPERS DE COMPONENTES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _repolish(w) -> None:
    """Reaplica el QSS después de cambiar objectName o una propiedad dinámica."""
    w.style().unpolish(w)
    w.style().polish(w)
    w.update()

_HELP_WIDGET_TYPES = (QPushButton, QToolButton, QCheckBox, QRadioButton, QAction)


def set_help(widget, key: str, shortcut: str = None) -> None:
    """
    Ayuda contextual traducida (tooltip + barra de estado).
      · tip.<key>        → explicación (obligatoria)
      · tip.<key>.title  → título (opcional; en botones/acciones se usa su propio texto)
    """
    body = tr(f"tip.{key}")
    title = tr_opt(f"tip.{key}.title")
    if not title and isinstance(widget, _HELP_WIDGET_TYPES):
        title = widget.text().replace("&", "")
    html = "<qt>"
    if title:
        html += f"<b>{title}</b>"
    if shortcut:
        html += f'&nbsp;&nbsp;&nbsp;<span style="color:{THEME["text_muted"]};">{shortcut}</span>'
    if title or shortcut:
        html += "<br>"
    html += f'<span style="color:{THEME["text_secondary"]};">{body}</span></qt>'
    widget.setToolTip(html)
    widget.setStatusTip(body)


def make_icon_button(name: str, help_key: str, shortcut: str = None, parent=None) -> "QToolButton":
    """Botón solo-ícono. SOLO para acciones universales (cerrar, buscar, actualizar, configuración,
    más opciones, navegación). Siempre con ayuda contextual."""
    btn = QToolButton(parent)
    btn.setObjectName("btnIcon")
    btn.setIcon(icon(name))
    btn.setIconSize(QSize(ICON_SIZE["sm"], ICON_SIZE["sm"]))
    btn.setAutoRaise(True)
    set_help(btn, help_key, shortcut)
    btn.setAccessibleName(tr_opt(f"tip.{help_key}.title") or tr(f"tip.{help_key}"))
    return btn


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ▶  COMPONENTES BASE (sección 10)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def make_card(section_title: str = None, spacing: int = SP["md"], header_widget=None):
    """Tarjeta con padding estándar, etiqueta de sección opcional y widget a la derecha del título
    (ej. un botón secundario). Devuelve (frame, layout)."""
    card = QFrame()
    card.setObjectName("card")
    lay = QVBoxLayout(card)
    lay.setContentsMargins(SP["lg"], SP["md"] + 2, SP["lg"], SP["lg"])
    lay.setSpacing(spacing)
    if section_title or header_widget:
        row = QHBoxLayout()
        row.setSpacing(SP["sm"])
        if section_title:
            lbl = QLabel(section_title.upper())
            lbl.setObjectName("lblSection")
            row.addWidget(lbl)
        row.addStretch(1)
        if header_widget is not None:
            row.addWidget(header_widget)
        lay.addLayout(row)
    return card, lay


def make_divider() -> "QFrame":
    line = QFrame()
    line.setObjectName("divider")
    return line


def make_badge(text: str, kind: str = "neutral") -> "QLabel":
    """kind: ok | error | warn | info | neutral"""
    lbl = QLabel(text)
    lbl.setObjectName(f"badge{kind.capitalize()}")
    lbl.setAlignment(Qt.AlignCenter)
    lbl.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
    return lbl


def set_badge(lbl, text: str, kind: str) -> None:
    lbl.setText(text)
    lbl.setObjectName(f"badge{kind.capitalize()}")
    _repolish(lbl)


def make_kpi(value: str, caption: str):
    """Tarjeta KPI: número grande + leyenda. Devuelve (frame, label_valor)."""
    card, lay = make_card(spacing=2)
    val = QLabel(value)
    val.setObjectName("lblKpi")
    cap = QLabel(caption)
    cap.setObjectName("lblKpiCaption")
    lay.addWidget(val)
    lay.addWidget(cap)
    return card, val


def make_log_view() -> "QPlainTextEdit":
    log = QPlainTextEdit()
    log.setObjectName("logView")
    log.setReadOnly(True)
    log.setMaximumBlockCount(5000)
    return log


def make_empty_state(text: str, icon_name: str = None, action_button=None) -> "QWidget":
    """Estado vacío: ícono grande apagado + frase útil + botón opcional. Centrado."""
    box = QWidget()
    lay = QVBoxLayout(box)
    lay.setContentsMargins(SP["xl"], SP["xl"], SP["xl"], SP["xl"])
    lay.setSpacing(SP["md"])
    lay.addStretch(1)
    if icon_name:
        ico = icon_label(icon_name, ICON_SIZE["xl"], "text_muted")
        lay.addWidget(ico, 0, Qt.AlignHCenter)
    lbl = QLabel(text)
    lbl.setObjectName("emptyState")
    lbl.setAlignment(Qt.AlignCenter)
    lbl.setWordWrap(True)
    lay.addWidget(lbl)
    if action_button is not None:
        lay.addWidget(action_button, 0, Qt.AlignHCenter)
    lay.addStretch(1)
    return box


def set_field_error(widget, message: str = None, error_label=None) -> None:
    """Marca (o limpia, con message=None) un campo inválido: borde rojo + mensaje."""
    widget.setProperty("invalid", bool(message))
    _repolish(widget)
    if error_label is not None:
        error_label.setText(message or "")
        error_label.setVisible(bool(message))


def make_error_label() -> "QLabel":
    lbl = QLabel()
    lbl.setObjectName("fieldError")
    lbl.setWordWrap(True)
    lbl.setVisible(False)
    return lbl


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ▶  UTILIDADES (sección 19)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def human_size(num_bytes) -> str:
    """1536 → '1,5 KB' (es) / '1.5 KB' (en)."""
    if num_bytes is None:
        return ""
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            break
        size /= 1024.0
    if unit == "B":
        return f"{int(size)} B"
    return f"{QLocale(i18n.LANG).toString(size, 'f', 1)} {unit}"


def format_datetime(ts) -> str:
    """Timestamp (float) o datetime → texto con el formato del idioma activo."""
    if ts is None:
        return ""
    dt = ts if isinstance(ts, datetime) else datetime.fromtimestamp(ts)
    return dt.strftime(tr("fmt.datetime"))


def open_with_system(path) -> bool:
    """Abre un archivo o carpeta con la aplicación predeterminada del sistema."""
    return QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


def reveal_in_folder(path) -> None:
    """Abre el explorador del sistema con el archivo seleccionado."""
    path = os.path.normpath(str(path))
    try:
        if IS_WINDOWS:
            subprocess.Popen(["explorer", "/select,", path])
        elif IS_MACOS:
            subprocess.Popen(["open", "-R", path])
        else:
            open_with_system(path if os.path.isdir(path) else os.path.dirname(path))
    except OSError:
        open_with_system(os.path.dirname(path))


def copy_to_clipboard(text: str) -> None:
    QGuiApplication.clipboard().setText(text)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ▶  PERSISTENCIA (QSettings)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def app_settings() -> "QSettings":
    return QSettings("EstebanKZL", APP_NAME)


def save_window_state(win, splitters: dict = None, headers: dict = None) -> None:
    """Guardar en closeEvent: geometría, estado, splitters y columnas de tablas."""
    st = app_settings()
    st.setValue("window/geometry", win.saveGeometry())
    if isinstance(win, QMainWindow):
        st.setValue("window/state", win.saveState())
    for name, sp in (splitters or {}).items():
        st.setValue(f"splitter/{name}", sp.saveState())
    for name, header in (headers or {}).items():
        st.setValue(f"header/{name}", header.saveState())


def restore_window_state(win, splitters: dict = None, headers: dict = None) -> bool:
    """Llamar al final de _build_ui(). Si no hay nada guardado, no hace nada.
    EmuLinks: devuelve True si restauró algún splitter (si no, la ventana fija el reparto)."""
    st = app_settings()
    geo = st.value("window/geometry")
    if geo is not None:
        win.restoreGeometry(geo)
    state = st.value("window/state")
    if state is not None and isinstance(win, QMainWindow):
        win.restoreState(state)
    restored = False
    for name, sp in (splitters or {}).items():
        val = st.value(f"splitter/{name}")
        if val is not None:
            restored = sp.restoreState(val) or restored
    for name, header in (headers or {}).items():
        val = st.value(f"header/{name}")
        if val is not None:
            header.restoreState(val)
    return restored


def remember_dir(key: str, path: str = None) -> str:
    """Última carpeta usada en un diálogo (por clave). Sin path: la lee."""
    st = app_settings()
    if path:
        st.setValue(f"last_dir/{key}", path if os.path.isdir(path) else os.path.dirname(path))
    return st.value(f"last_dir/{key}", os.path.expanduser("~"))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ▶  SELECTOR DE RUTA (campo + Examinar…)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class PathSelector(QWidget):
    """
    Campo de ruta con botón 'Examinar…' (diálogo nativo del sistema), validación y
    recuerdo de la última carpeta.
      mode: "folder" | "open" (un archivo) | "open_many" | "save"
      file_filter: ej. tr("filter.pdf") → "Documentos PDF (*.pdf)"
    EmuLinks: help_key/browse_help_key para la ayuda del campo y del botón.
    """
    pathChanged = Signal(str)

    def __init__(self, mode: str = "folder", file_filter: str = "", key: str = "default",
                 must_exist: bool = True, parent=None, help_key: str = None,
                 browse_help_key: str = "browse"):
        super().__init__(parent)
        self._mode, self._filter, self._key, self._must_exist = mode, file_filter, key, must_exist
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(SP["xs"])
        row = QHBoxLayout()
        row.setSpacing(SP["sm"])
        self.edit = QLineEdit()
        self.edit.setPlaceholderText(tr("ph.folder") if mode == "folder" else tr("ph.file"))
        self.edit.addAction(icon("folder" if mode == "folder" else "file", "text_muted"),
                            QLineEdit.LeadingPosition)
        if help_key:
            set_help(self.edit, help_key)
        self.edit.editingFinished.connect(self._on_edited)
        self.btn = QPushButton(tr("btn.browse"))
        set_help(self.btn, browse_help_key)
        self.btn.clicked.connect(self._browse)
        row.addWidget(self.edit, 1)
        row.addWidget(self.btn)
        lay.addLayout(row)
        self.error = make_error_label()
        lay.addWidget(self.error)

    def path(self) -> str:
        return self.edit.text().strip()

    def set_path(self, path: str) -> None:
        self.edit.setText(os.path.normpath(path) if path else "")
        self._on_edited()

    def is_valid(self) -> bool:
        return self._validate(self.path())

    def _validate(self, path: str) -> bool:
        if not path:
            set_field_error(self.edit, None, self.error)
            return False
        if self._must_exist and self._mode != "save":
            if self._mode == "folder":
                exists = os.path.isdir(path)
            else:
                exists = all(os.path.isfile(p) for p in path.split(";") if p)
            if not exists:
                set_field_error(self.edit, tr("err.path_not_found"), self.error)
                return False
        set_field_error(self.edit, None, self.error)
        return True

    def _on_edited(self) -> None:
        if self._validate(self.path()):
            self.pathChanged.emit(self.path())

    def _browse(self) -> None:
        start = self.path() or remember_dir(self._key)
        title = tr("dlg.choose_folder") if self._mode == "folder" else tr("dlg.choose_file")
        if self._mode == "folder":
            path = QFileDialog.getExistingDirectory(self, title, start)
        elif self._mode == "save":
            path = QFileDialog.getSaveFileName(self, tr("dlg.save_as"), start, self._filter)[0]
        elif self._mode == "open_many":
            paths = QFileDialog.getOpenFileNames(self, title, start, self._filter)[0]
            path = ";".join(paths)
        else:
            path = QFileDialog.getOpenFileName(self, title, start, self._filter)[0]
        if path:
            remember_dir(self._key, path.split(";")[0])
            self.set_path(path) if self._mode != "open_many" else self.edit.setText(path)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ▶  MENSAJES Y CONFIRMACIONES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_KIND_ICON = {"info": ("info", "ip"), "success": ("success", "ok"),
              "warning": ("warning", "counter"), "error": ("error", "error"),
              "question": ("help", "ip")}


def _message_box(kind: str, parent, title: str, text: str, details: str = None):
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    box.setTextFormat(Qt.PlainText)
    ico_name, color = _KIND_ICON[kind]
    box.setIconPixmap(icon_pixmap(ico_name, ICON_SIZE["xl"], color))
    if details:
        box.setDetailedText(details)
    return box


def show_message(kind: str, parent, title: str, text: str, details: str = None) -> None:
    """kind: info | success | warning | error. 'details' agrega un desplegable 'Mostrar detalles'."""
    box = _message_box(kind, parent, title, text, details)
    ok = box.addButton(tr("common.ok"), QMessageBox.AcceptRole)
    ok.setObjectName("btnPrimary")
    box.setDefaultButton(ok)
    _exec(box)


def ask_confirm(parent, title: str, text: str, confirm_text: str = None, danger: bool = False) -> bool:
    """
    Pregunta Sí/No con verbos claros ('Eliminar' / 'Cancelar', nunca 'Sí' / 'No').
    danger=True → botón rojo y 'Cancelar' como opción por defecto (Enter no borra nada).
    """
    box = _message_box("warning" if danger else "question", parent, title, text)
    yes = box.addButton(confirm_text or tr("common.accept"), QMessageBox.AcceptRole)
    no = box.addButton(tr("common.cancel"), QMessageBox.RejectRole)
    yes.setObjectName("btnDanger" if danger else "btnPrimary")
    box.setDefaultButton(no if danger else yes)
    box.setEscapeButton(no)
    _exec(box)
    return box.clickedButton() is yes


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ▶  AVISO DENTRO DE LA VENTANA (banner)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class Banner(QFrame):
    """
    Aviso persistente arriba de una tarjeta o pantalla: requiere atención pero no bloquea.
    kind: info | success | warning | error. Acción opcional (botón secundario) y botón cerrar.
    """
    actionClicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("banner")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(SP["md"], SP["sm"], SP["sm"], SP["sm"])
        lay.setSpacing(SP["sm"])
        self._icon = QLabel()
        self._icon.setFixedSize(ICON_SIZE["md"], ICON_SIZE["md"])
        self._text = QLabel()
        self._text.setWordWrap(True)
        self._text.setTextFormat(Qt.PlainText)
        self._action = QPushButton()
        self._action.setObjectName("btnSecondary")
        self._action.clicked.connect(self.actionClicked)
        self._close = make_icon_button("close", "close_notice")
        self._close.clicked.connect(self.hide)
        lay.addWidget(self._icon, 0, Qt.AlignTop)
        lay.addWidget(self._text, 1)
        lay.addWidget(self._action, 0, Qt.AlignVCenter)
        lay.addWidget(self._close, 0, Qt.AlignTop)
        self.hide()

    def show_message(self, kind: str, text: str, action_text: str = None, closable: bool = True) -> None:
        ico_name, color = _KIND_ICON[kind]
        self.setProperty("kind", kind)
        _repolish(self)
        self._icon.setPixmap(icon_pixmap(ico_name, ICON_SIZE["md"], color))
        self._text.setText(text)
        self._action.setVisible(bool(action_text))
        self._action.setText(action_text or "")
        self._close.setVisible(closable)
        self.show()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ▶  NOTIFICACIÓN TEMPORAL (toast)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class Toast(QFrame):
    """
    Confirmación breve que desaparece sola ('Archivo guardado', 'Copiado').
    Aparece abajo a la derecha de la ventana, encima de la barra de estado. No usar para errores.
    Uso: Toast.show_text(self, tr("toast.saved"), "success")
    """
    _active = None

    def __init__(self, window, text: str, kind: str = "success", msec: int = 3000):
        super().__init__(window)
        self.setObjectName("toast")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(SP["md"], SP["sm"] + 2, SP["lg"], SP["sm"] + 2)
        lay.setSpacing(SP["sm"])
        ico_name, color = _KIND_ICON[kind]
        lay.addWidget(icon_label(ico_name, ICON_SIZE["sm"], color))
        lbl = QLabel(text)
        lay.addWidget(lbl)
        self.adjustSize()
        self._effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effect)
        self._anim = QPropertyAnimation(self._effect, b"opacity", self)
        self._anim.setDuration(180)
        QTimer.singleShot(msec, self._fade_out)

    @classmethod
    def show_text(cls, window, text: str, kind: str = "success", msec: int = 3000) -> None:
        if cls._active is not None:
            cls._active.deleteLater()
        toast = cls(window, text, kind, msec)
        cls._active = toast
        sb = window.statusBar().height() if isinstance(window, QMainWindow) and window.statusBar() else 0
        toast.move(window.width() - toast.width() - SP["lg"], window.height() - toast.height() - sb - SP["lg"])
        toast.show()
        toast.raise_()
        toast._anim.setStartValue(0.0)
        toast._anim.setEndValue(1.0)
        toast._anim.start()

    def _fade_out(self) -> None:
        self._anim.stop()
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.finished.connect(self._remove)
        self._anim.start()

    def _remove(self) -> None:
        if Toast._active is self:
            Toast._active = None
        self.deleteLater()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ▶  INDICADOR DE ACTIVIDAD (spinner)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class BusySpinner(QWidget):
    """Para esperas de duración desconocida (conectando, leyendo). Si se conoce el total,
    usar QProgressBar."""
    def __init__(self, size: int = 18, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self.hide()

    def start(self) -> None:
        self.show()
        self._timer.start(16)

    def stop(self) -> None:
        self._timer.stop()
        self.hide()

    def _tick(self) -> None:
        self._angle = (self._angle + 6) % 360
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = 2.0
        r = QRectF(w, w, self.width() - 2 * w, self.height() - 2 * w)
        pen = QPen(QColor(THEME["border_strong"]), w)
        p.setPen(pen)
        p.drawEllipse(r)
        pen.setColor(QColor(THEME["accent"]))
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.drawArc(r, int(-self._angle * 16), int(100 * 16))
        p.end()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ▶  GRIP DE REDIMENSIÓN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class DotGripWidget(QWidget):
    """
    Grip de redimensión con puntos en la esquina inferior derecha.
    bg_color : None = transparente | THEME["status_bg"] = sobre la status bar.
    dot_color: None → THEME["status_text"] si hay bg_color, THEME["text_muted"] si es transparente.
    """
    def __init__(self, parent=None, bg_color=None, dot_color=None):
        super().__init__(parent)
        self.setFixedSize(20, 20)
        self.setCursor(Qt.SizeFDiagCursor)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._bg_color = bg_color
        if dot_color is None:
            dot_color = THEME["status_text"] if bg_color else THEME["text_muted"]
        self._dot_color = QColor(dot_color)
        self._hovered = self._dragging = False
        self._drag_pos = self._drag_size = None
        self.setMouseTracking(True)

    def enterEvent(self, e):
        self._hovered = True
        self.update()

    def leaveEvent(self, e):
        self._hovered = False
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_pos = _global_pos(e)
            self._drag_size = self.window().size()

    def mouseMoveEvent(self, e):
        if self._dragging:
            d = _global_pos(e) - self._drag_pos
            win = self.window()
            win.resize(max(win.minimumWidth(), self._drag_size.width() + d.x()),
                       max(win.minimumHeight(), self._drag_size.height() + d.y()))

    def mouseReleaseEvent(self, e):
        self._dragging = False

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self._bg_color:
            p.fillRect(self.rect(), QColor(self._bg_color))
        dot_r, spacing, cols, rows = 2, 5, 3, 3
        ox = self.width() - cols * spacing + 1
        oy = self.height() - rows * spacing + 1
        color = QColor(self._dot_color)
        color.setAlpha(220 if self._hovered else 130)
        if self._hovered:
            halo = QColor(self._dot_color)
            halo.setAlpha(30)
            p.setPen(QPen(halo, 0))
            p.setBrush(halo)
            p.drawEllipse(0, 0, self.width(), self.height())
        p.setPen(QPen(color, 0))
        p.setBrush(color)
        for row in range(rows):
            for col in range(cols):
                if row + col < 2:
                    continue
                p.drawEllipse(ox + col * spacing - dot_r, oy + row * spacing - dot_r, dot_r * 2, dot_r * 2)
        p.end()
