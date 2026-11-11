"""Información de la aplicación. La versión vive SOLO en el archivo VERSION de
la raíz: la leen este módulo, scripts/build.py, el instalador y el workflow."""

from pathlib import Path


def _read_version() -> str:
    # En desarrollo y en el build de Nuitka, VERSION queda una carpeta arriba
    # del paquete (el build lo copia junto al ejecutable).
    for folder in (Path(__file__).resolve().parent.parent, Path(__file__).resolve().parent):
        try:
            return (folder / "VERSION").read_text(encoding="utf-8").strip()
        except OSError:
            continue
    return "0.0.0"


APP_NAME      = "EmuLinks"
APP_VERSION   = _read_version()
APP_DEVELOPER = "EstebanKZL"
# Correo no-reply de GitHub: no recibe mensajes y no expone un correo personal.
# Lleva el ID de la cuenta porque es la que GitHub asocia al usuario.
APP_EMAIL     = "89585806+EstebanKZL@users.noreply.github.com"
APP_URL       = "https://github.com/EstebanKZL/EmuLinks"
APP_PUBLISHER = APP_DEVELOPER   # metadatos del ejecutable e instalador
# Nombre corto sin espacios ni guiones para los artefactos:
# <AppName>-<versión>-<os>-<arq>-<variante>
APP_SLUG      = "EmuLinks"
