"""Componentes estándar del sistema de diseño v5.3 (secciones 6, 9, 10 y 15):
ayuda contextual, tarjetas, badges, KPIs, log, estado vacío y grip.

Todos se diferencian por objectName; el stylesheet global hace el resto.
"""

from emulinks import i18n
from emulinks.i18n import tr, tr_opt
from emulinks.ui.qt import *  # noqa: F401,F403
from emulinks.ui.theme import SP, THEME


def _repolish(w):
    """Necesario tras cambiar el objectName en caliente (p. ej. un badge)."""
    w.style().unpolish(w); w.style().polish(w); w.update()


# ══════════════════════════════════════════════════════════════════════════
# 6 — AYUDA CONTEXTUAL
# ══════════════════════════════════════════════════════════════════════════
_HELP_WIDGET_TYPES = (QPushButton, QToolButton, QCheckBox, QRadioButton)


def set_help(widget, key: str, shortcut: str = None) -> None:
    """
    Asigna ayuda contextual traducida a un widget o QAction.
      · tip.<key>        → explicación (obligatoria)
      · tip.<key>.title  → título (opcional; en botones/checkbox se usa su propio texto)
    También la copia a la barra de estado (statusTip).
    """
    body  = tr(f"tip.{key}")
    title = tr_opt(f"tip.{key}.title")
    if not title and isinstance(widget, _HELP_WIDGET_TYPES + (QAction,)):
        title = widget.text().replace("&", "")
    html = "<qt>"
    if title:
        html += f'<b>{title}</b>'
    if shortcut:
        html += f'&nbsp;&nbsp;&nbsp;<span style="color:{THEME["text_muted"]};">{shortcut}</span>'
    if title or shortcut:
        html += "<br>"
    html += f'<span style="color:{THEME["text_secondary"]};">{body}</span></qt>'
    widget.setToolTip(html)
    widget.setStatusTip(body)


# ══════════════════════════════════════════════════════════════════════════
# 10 — CATÁLOGO DE COMPONENTES
# ══════════════════════════════════════════════════════════════════════════

def make_card(section_title: str = None, spacing: int = SP["md"]):
    """Tarjeta con padding estándar y etiqueta de sección opcional. Devuelve (frame, layout)."""
    card = QFrame()
    card.setObjectName("card")
    lay = QVBoxLayout(card)
    lay.setContentsMargins(SP["lg"], SP["md"] + 2, SP["lg"], SP["lg"])
    lay.setSpacing(spacing)
    if section_title:
        lbl = QLabel(section_title.upper())
        lbl.setObjectName("lblSection")
        lay.addWidget(lbl)
    return card, lay


def make_divider() -> QFrame:
    line = QFrame()
    line.setObjectName("divider")
    return line


def make_badge(text: str, kind: str = "neutral") -> QLabel:
    """kind: ok | error | warn | info | neutral"""
    lbl = QLabel(text)
    lbl.setObjectName(f"badge{kind.capitalize()}")
    lbl.setAlignment(Qt.AlignCenter)
    lbl.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
    return lbl


def set_badge(lbl: QLabel, text: str, kind: str) -> None:
    lbl.setText(text)
    lbl.setObjectName(f"badge{kind.capitalize()}")
    _repolish(lbl)


def make_kpi(value: str, caption: str):
    """Tarjeta KPI: número grande + leyenda. Devuelve (frame, label_valor)."""
    card, lay = make_card(spacing=2)
    val = QLabel(value);   val.setObjectName("lblKpi")
    cap = QLabel(caption); cap.setObjectName("lblKpiCaption")
    lay.addWidget(val); lay.addWidget(cap)
    return card, val


def make_log_view() -> QPlainTextEdit:
    log = QPlainTextEdit()
    log.setObjectName("logView")
    log.setReadOnly(True)
    log.setMaximumBlockCount(5000)      # evita que crezca sin límite
    return log


def make_empty_state(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("emptyState")
    lbl.setAlignment(Qt.AlignCenter)
    lbl.setWordWrap(True)
    return lbl


def format_size(n: int) -> str:
    """Tamaño legible con el separador decimal del idioma activo."""
    value = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            break
        value /= 1024
    if unit == "B":
        return f"{int(value)} B"
    return f"{QLocale(i18n.LANG).toString(value, 'f', 1)} {unit}"


# ══════════════════════════════════════════════════════════════════════════
# 15 — DOTGRIPWIDGET — GRIP DE REDIMENSIÓN
# ══════════════════════════════════════════════════════════════════════════

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
        self.setStyleSheet(f"background: {bg_color};" if bg_color else "background: transparent;")
        self._hovered = self._dragging = False
        self._drag_pos = self._drag_size = None
        self.setMouseTracking(True)

    def enterEvent(self, e):  self._hovered = True;  self.update()
    def leaveEvent(self, e):  self._hovered = False; self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._dragging  = True
            self._drag_pos  = _global_pos(e)
            self._drag_size = self.window().size()

    def mouseMoveEvent(self, e):
        if self._dragging:
            d = _global_pos(e) - self._drag_pos
            win = self.window()
            win.resize(
                max(win.minimumWidth(),  self._drag_size.width()  + d.x()),
                max(win.minimumHeight(), self._drag_size.height() + d.y()),
            )

    def mouseReleaseEvent(self, e):
        self._dragging = False

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self._bg_color:
            p.fillRect(self.rect(), QColor(self._bg_color))
        dot_r, spacing, cols, rows = 2, 5, 3, 3
        ox = self.width()  - cols * spacing + 1
        oy = self.height() - rows * spacing + 1
        color = QColor(self._dot_color)
        color.setAlpha(220 if self._hovered else 130)
        if self._hovered:
            halo = QColor(self._dot_color); halo.setAlpha(30)
            p.setPen(QPen(halo, 0)); p.setBrush(halo)
            p.drawEllipse(0, 0, self.width(), self.height())
        p.setPen(QPen(color, 0)); p.setBrush(color)
        for row in range(rows):
            for col in range(cols):
                if row + col < 2:
                    continue
                p.drawEllipse(ox + col * spacing - dot_r, oy + row * spacing - dot_r,
                              dot_r * 2, dot_r * 2)
