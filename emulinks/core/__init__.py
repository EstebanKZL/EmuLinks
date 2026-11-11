"""Lógica de EmuLinks sin dependencias de Qt.

Todo lo que está acá se puede probar sin pantalla (ver tests/). Los mensajes
visibles pasan por emulinks.i18n.tr(); los callbacks de log reciben
(texto, nivel) con nivel en LOG_LEVELS.
"""

# Niveles del log de actividad. El color se decide por nivel, nunca buscando
# palabras en el texto (el texto cambia con el idioma).
LOG_OK, LOG_ERROR, LOG_WARN, LOG_INFO = "ok", "error", "warn", "info"
LOG_LEVELS = (LOG_OK, LOG_ERROR, LOG_WARN, LOG_INFO)
