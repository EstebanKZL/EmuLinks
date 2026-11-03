"""
EmuLinks — centraliza los datos de tus emuladores (saves, config, bios) en una
carpeta compartida, dejando en su lugar un enlace simbólico / junction, para
no perder nada al reinstalar o migrar de PC.

Paquetes:
    emulinks.core     lógica sin Qt (config, filesystem, detección) — testeable
    emulinks.ui       interfaz PySide6/PySide2 (Prompt de Diseño v5.3)
    emulinks.locales  textos en español e inglés
"""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ▶  INFORMACIÓN DE LA APLICACIÓN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
APP_NAME      = "EmuLinks"
APP_VERSION   = "6.4"
APP_DEVELOPER = "EstebanKZL"
APP_URL       = "https://github.com/EstebanKZL/EmuLinks"
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
