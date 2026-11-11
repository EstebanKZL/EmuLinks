"""
EmuLinks — centraliza los datos de tus emuladores (saves, config, bios) en una
carpeta compartida, dejando en su lugar un enlace simbólico / junction, para
no perder nada al reinstalar o migrar de PC.

Paquetes:
    emulinks.core     lógica sin Qt (config, filesystem, detección) — testeable
    emulinks.ui       interfaz PySide6/PySide2 (sistema de diseño propio)
    emulinks.locales  textos en español e inglés
"""

# Información de la aplicación: vive en emulinks/version.py (la versión, en VERSION).
from emulinks.version import (  # noqa: F401
    APP_DEVELOPER, APP_EMAIL, APP_NAME, APP_PUBLISHER, APP_SLUG, APP_URL, APP_VERSION,
)
