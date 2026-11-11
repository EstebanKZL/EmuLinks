"""Tipos de archivo: ícono, color y nombre legible.

Con las extensiones propias de EmuLinks agregadas a
FILE_CATEGORIES (partidas de emuladores en "save").
"""

import os

from emulinks.i18n import tr
from emulinks.ui.icons import icon
from emulinks.ui.qt import *  # noqa: F401,F403


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ▶  TIPOS DE ARCHIVO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# categoría: (ícono, color, extensiones). Agregar las extensiones propias del proyecto acá.
FILE_CATEGORIES = {
    "folder":   ("folder",        "ft_folder", ()),
    "pdf":      ("file_pdf",      "ft_red",    (".pdf",)),
    "doc":      ("file_doc",      "ft_blue",   (".doc", ".docx", ".docm", ".odt", ".rtf")),
    "sheet":    ("file_sheet",    "ft_green",  (".xls", ".xlsx", ".xlsm", ".ods", ".csv", ".tsv")),
    "slides":   ("file_slides",   "ft_orange", (".ppt", ".pptx", ".odp")),
    "text":     ("file_text",     "ft_gray",   (".txt", ".md", ".log", ".nfo")),
    "code":     ("file_code",     "ft_teal",   (".py", ".pyw", ".js", ".ts", ".html", ".htm", ".css", ".c", ".h",
                                                ".cpp", ".hpp", ".cs", ".java", ".sh", ".bat", ".cmd", ".ps1",
                                                ".lua", ".go", ".rs", ".php", ".sql", ".ino")),
    "config":   ("file_config",   "ft_gray",   (".ini", ".cfg", ".conf", ".json", ".xml", ".yaml", ".yml",
                                                ".toml", ".reg", ".env", ".properties")),
    "archive":  ("file_archive",  "ft_brown",  (".zip", ".rar", ".7z", ".tar", ".gz", ".tgz", ".bz2", ".xz",
                                                ".zst", ".cab", ".lz", ".lzh")),
    "image":    ("file_image",    "ft_purple", (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".ico",
                                                ".svg", ".tif", ".tiff", ".heic", ".psd")),
    "audio":    ("file_audio",    "ft_pink",   (".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".wma", ".opus")),
    "video":    ("file_video",    "ft_pink",   (".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm", ".flv", ".m4v")),
    "exec":     ("file_exec",     "ft_blue",   (".exe", ".msi", ".appimage", ".deb", ".rpm", ".apk", ".jar", ".lnk")),
    "disk":     ("file_disk",     "ft_gray",   (".iso", ".img", ".dmg", ".vhd", ".vhdx", ".vmdk", ".wim")),
    "database": ("file_db",       "ft_orange", (".db", ".sqlite", ".sqlite3", ".mdb", ".accdb")),
    "firmware": ("file_firmware", "ft_teal",   (".hex", ".bin", ".rom", ".elf", ".fw", ".uf2")),
    "key":      ("file_key",      "ft_orange", (".pem", ".crt", ".cer", ".der", ".key", ".pub", ".ppk", ".p12",
                                                ".pfx", ".csr", ".gpg", ".asc")),
    "capture":  ("file_capture",  "ft_teal",   (".pcap", ".pcapng", ".cap", ".har")),
    "mail":     ("file_mail",     "ft_blue",   (".eml", ".msg", ".mbox")),
    # EmuLinks: partidas y memorias de emuladores
    "save":     ("save",          "ft_green",  (".sav", ".srm", ".mcr", ".mcd", ".ps2", ".dsv", ".sv",
                                                ".eep", ".fla", ".mpk", ".gci", ".state")),
    "file":     ("file",          "ft_gray",   ()),        # cualquier otro
}

_EXT_TO_CATEGORY = {ext: cat for cat, (_i, _c, exts) in FILE_CATEGORIES.items() for ext in exts}

# Respaldo por tipo MIME para archivos sin extensión o con extensión desconocida
_MIME_TO_CATEGORY = (
    ("application/pdf", "pdf"), ("image/", "image"), ("audio/", "audio"), ("video/", "video"),
    ("application/zip", "archive"), ("application/x-7z", "archive"), ("application/x-rar", "archive"),
    ("application/gzip", "archive"), ("application/x-tar", "archive"),
    ("application/x-executable", "exec"), ("application/x-msdownload", "exec"),
    ("application/x-sqlite3", "database"), ("application/json", "config"), ("text/", "text"),
)

_mime_db = None


def file_category(path: str, is_dir: bool = None, deep: bool = False) -> str:
    """
    Categoría de un archivo ('pdf', 'archive', 'folder'…).
    deep=True: si la extensión no alcanza, mira el CONTENIDO (firma/magic bytes) con QMimeDatabase.
    Para listas grandes usar deep=False (rápido, solo extensión).
    """
    if is_dir is None:
        is_dir = os.path.isdir(path)
    if is_dir:
        return "folder"
    cat = _EXT_TO_CATEGORY.get(os.path.splitext(path)[1].lower())
    if cat:
        return cat
    global _mime_db
    if _mime_db is None:
        _mime_db = QMimeDatabase()
    mode = QMimeDatabase.MatchDefault if deep else QMimeDatabase.MatchExtension
    mime = _mime_db.mimeTypeForFile(path, mode).name()
    for prefix, category in _MIME_TO_CATEGORY:
        if mime.startswith(prefix):
            return category
    return "file"


def file_icon(path: str, is_dir: bool = None) -> "QIcon":
    ico_name, color, _exts = FILE_CATEGORIES[file_category(path, is_dir)]
    return icon(ico_name, color)


def file_type_name(path: str, is_dir: bool = None) -> str:
    """Nombre legible y traducido: 'Documento PDF', 'Archivo comprimido (ZIP)', 'Archivo XYZ'."""
    cat = file_category(path, is_dir)
    ext = os.path.splitext(path)[1].lstrip(".").upper()
    if cat == "file":
        return tr("ftype.generic", ext=ext) if ext else tr("ftype.file")
    name = tr(f"ftype.{cat}")
    if cat in ("archive", "image", "audio", "video", "disk", "firmware") and ext:
        name += f" ({ext})"
    return name


def warm_file_icons() -> None:
    """Crea de antemano todos los íconos de archivo (hilo principal).
    Obligatorio antes de usar FileIconProvider: QFileSystemModel pide íconos desde otro hilo."""
    for ico_name, color, _exts in FILE_CATEGORIES.values():
        icon(ico_name, color)
