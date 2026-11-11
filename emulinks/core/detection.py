"""Motor del autodetector: rutas estándar, Flatpak e instalaciones portables.

Todo es de solo lectura salvo apply_detection(), que solo modifica el dict de
configuración en memoria (y solo agrega, nunca quita).
"""

import ctypes
import fnmatch
import functools
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from emulinks.core.emulators_db import (
    CATEGORY_ORDER, CONFIG_FILE_EXTS, DEFAULT_UNCHECKED_CATEGORIES, EMULATOR_DB,
    IGNORED_ROOT_FILES, IGNORED_SCAN_DIRS, LARGE_FILE_BYTES,
)
from emulinks.core.fs import get_emulator_path, is_link_like, is_placeholder_link
from emulinks.core.system import IS_WINDOWS, PLATFORM_KEY
from emulinks.i18n import tr


def _known_documents_dir() -> Path:
    """Carpeta Documentos REAL: si Windows la redirigió (OneDrive, otro disco)
    Path.home()/"Documents" apunta al lugar equivocado."""
    if IS_WINDOWS:
        try:
            buf = ctypes.create_unicode_buffer(260)
            CSIDL_PERSONAL = 5
            if ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_PERSONAL, None, 0, buf) == 0 and buf.value:
                return Path(buf.value)
        except Exception:
            pass
    return Path.home() / "Documents"


@functools.lru_cache(maxsize=1)
def _path_tokens() -> Dict[str, str]:
    home = Path.home()
    return {
        "HOME": str(home),
        "APPDATA": os.getenv("APPDATA") or str(home / "AppData" / "Roaming"),
        "LOCALAPPDATA": os.getenv("LOCALAPPDATA") or str(home / "AppData" / "Local"),
        "DOCUMENTS": str(_known_documents_dir()),
        "XDG_CONFIG": os.getenv("XDG_CONFIG_HOME") or str(home / ".config"),
        "XDG_DATA": os.getenv("XDG_DATA_HOME") or str(home / ".local" / "share"),
        "MAC_AS": str(home / "Library" / "Application Support"),
    }


def candidate_paths(emu: Dict[str, Any], platform_key: str = PLATFORM_KEY) -> List[Tuple[Path, str]]:
    """(ruta, origen) de cada ubicación estándar conocida para la plataforma.
    origen: "standard" | "flatpak" (el texto visible es tr("origin.<origen>")).
    En Linux agrega la variante Flatpak (~/.var/app/<id>/…) de cada ruta XDG."""
    tokens = _path_tokens()
    out: List[Tuple[Path, str]] = []
    for tpl in emu["paths"].get(platform_key, []):
        out.append((Path(tpl.format(**tokens)), "standard"))
        flatpak_id = emu.get("flatpak")
        if platform_key == "linux" and flatpak_id:
            for token, sub in (("{XDG_DATA}", "data"), ("{XDG_CONFIG}", "config")):
                if tpl.startswith(token):
                    fp_tpl = "{HOME}/.var/app/" + flatpak_id + "/" + sub + tpl[len(token):]
                    out.append((Path(fp_tpl.format(**tokens)), "flatpak"))
    return out


def _norm(p) -> str:
    return os.path.normcase(os.path.normpath(str(p)))


def _entry_is_reparse(entry: "os.DirEntry") -> bool:
    """Symlink o junction, sin seguirlo. En Windows DirEntry.stat() viene
    cacheado del listado, así que no cuesta una llamada extra por carpeta."""
    try:
        if entry.is_symlink():
            return True
        if IS_WINDOWS:
            return bool(getattr(entry.stat(follow_symlinks=False), "st_file_attributes", 0) & 0x400)
    except OSError:
        return True
    return False


def scan_install(data_dir: Path, emu: Dict[str, Any], in_place: bool) -> Tuple[List[Dict], List[Dict]]:
    """Lista TODO lo que hay en la carpeta de datos, clasificado.

    Nada se descarta en silencio: lo desconocido aparece como "Sin clasificar"
    para que el usuario decida. in_place=True significa que los datos viven en
    la misma carpeta que el ejecutable (RPCS3, RetroArch, MAME…): ahí lo
    desconocido viene destildado porque suele ser parte del programa."""
    folders: List[Dict] = []
    files: List[Dict] = []
    notes = {k: tr(v) for k, v in emu.get("notes", {}).items()}
    db_files = {f.lower() for f in emu.get("files", [])}
    try:
        entries = list(os.scandir(data_dir))
    except OSError:
        return folders, files

    for entry in entries:
        name = entry.name
        low = name.lower()
        # Backups y temporales del propio EmuLinks.
        if "_backup_" in low or low.endswith("__restore_tmp"):
            continue
        linked = is_link_like(Path(entry.path))
        broken = not linked and is_placeholder_link(Path(entry.path))
        try:
            is_dir = entry.is_dir()  # sigue el enlace: un junction ya hecho cuenta como carpeta
        except OSError:
            is_dir = False
        if is_dir or linked or broken:
            category = emu["folders"].get(low)
            if category is None:
                category = "cache" if low in IGNORED_SCAN_DIRS else "other"
            checked = linked or broken or (category not in DEFAULT_UNCHECKED_CATEGORIES
                                           and not (in_place and category == "other"))
            note = notes.get(low, "")
            if broken:
                note = tr("note.broken_link")
            folders.append({"name": name, "category": category, "checked": checked,
                            "linked": linked, "broken": broken, "note": note})
            continue

        if low in IGNORED_ROOT_FILES:
            continue
        known = low in db_files
        if not known and (in_place or Path(low).suffix not in CONFIG_FILE_EXTS):
            continue
        try:
            size = entry.stat().st_size
        except OSError:
            size = 0
        files.append({"name": name, "size": size, "checked": known or size <= LARGE_FILE_BYTES,
                      "note": notes.get(low, "")})

    folders.sort(key=lambda f: (CATEGORY_ORDER.index(f["category"]), f["name"].lower()))
    files.sort(key=lambda f: f["name"].lower())
    return folders, files


# Carpetas que nunca se recorren buscando ejecutables portables.
WALK_SKIP_DIRS = {
    "windows", "programdata", "recovery", "perflogs", "system volume information",
    "appdata", "node_modules", "winsxs", "__pycache__", "site-packages", "msocache",
    "config.msi", "windowsapps", "proc", "sys", "dev", "usr", "lib", "lib64", "snap",
}
WALK_MAX_DIRS = 300_000


def default_search_roots() -> List[Tuple[Path, int]]:
    """(raíz, profundidad) donde buscar instalaciones portables."""
    home = Path.home()
    roots: List[Tuple[Path, int]] = []
    if IS_WINDOWS:
        drives: List[Path] = []
        try:
            mask = ctypes.windll.kernel32.GetLogicalDrives()
            for i in range(26):
                if mask & (1 << i):
                    drive = f"{chr(65 + i)}:\\"
                    # 2 = removible (pendrive/disco USB), 3 = disco fijo. Se
                    # saltean unidades de red y lectoras: lentas o sin sentido.
                    if ctypes.windll.kernel32.GetDriveTypeW(drive) in (2, 3):
                        drives.append(Path(drive))
        except Exception:
            drives.append(Path("C:\\"))
        for d in drives:
            roots.append((d, 4))
            roots.append((d / "SteamLibrary" / "steamapps" / "common", 2))
        local = os.getenv("LOCALAPPDATA")
        if local:
            roots.append((Path(local) / "Programs", 2))
        roots.append((home / "scoop" / "apps", 3))
        for pf in (os.getenv("ProgramFiles(x86)"), os.getenv("ProgramFiles")):
            if pf:
                roots.append((Path(pf) / "Steam" / "steamapps" / "common", 2))
    else:
        roots += [(Path("/opt"), 2), (Path("/mnt"), 4), (Path("/media"), 4), (Path("/run/media"), 4)]
    roots.append((home, 5))
    return roots


def find_portable_installs(roots: List[Tuple[Path, int]], is_cancelled=lambda: False,
                           progress=lambda m: None) -> List[Tuple[str, Path]]:
    """Recorre las raíces buscando ejecutables de emuladores conocidos.
    Devuelve [(clave_emulador, carpeta_del_exe)] sin repetidos."""
    patterns = [(key, pat) for key, emu in EMULATOR_DB.items()
                for rule in emu.get("portable", []) for pat in rule["exe"]]
    best_depth: Dict[str, int] = {}
    found: List[Tuple[str, Path]] = []
    found_keys = set()
    stack = list(roots)
    visited = 0
    while stack and not is_cancelled():
        current, depth = stack.pop()
        norm = _norm(current)
        # Se puede llegar a la misma carpeta desde dos raíces (C:\ y el home):
        # solo se vuelve a entrar si esta vez queda más profundidad.
        if best_depth.get(norm, -1) >= depth:
            continue
        best_depth[norm] = depth
        try:
            entries = list(os.scandir(current))
        except OSError:
            continue
        visited += 1
        if visited > WALK_MAX_DIRS:
            progress(tr("detect.limit"))
            break
        if visited % 2000 == 0:
            progress(tr("detect.walking", count=visited))

        file_names: List[str] = []
        subdirs: List[str] = []
        for e in entries:
            try:
                if e.is_file():
                    file_names.append(e.name.lower())
                elif e.is_dir(follow_symlinks=False) and not _entry_is_reparse(e):
                    subdirs.append(e.path)
            except OSError:
                continue

        matched = sorted({key for key, pat in patterns for f in file_names if fnmatch.fnmatchcase(f, pat)})
        for key in matched:
            if (key, norm) not in found_keys:
                found_keys.add((key, norm))
                found.append((key, current))
        # Dentro de la carpeta de un emulador no se sigue bajando: sus
        # subcarpetas (dev_hdd0, roms…) pueden tener miles de entradas.
        if matched or depth <= 0:
            continue
        for sub in subdirs:
            low = os.path.basename(sub).lower()
            if low in WALK_SKIP_DIRS or low.startswith("$") or low.startswith("."):
                continue
            stack.append((Path(sub), depth - 1))
    return found


def _resolve_portable(key: str, exe_dir: Path) -> Optional[Tuple[Path, bool]]:
    """Aplica las reglas portables del emulador: (carpeta_de_datos, in_place)."""
    for rule in EMULATOR_DB[key].get("portable", []):
        if rule.get("unless") and (exe_dir / rule["unless"]).exists():
            continue
        if rule.get("marker") and not (exe_dir / rule["marker"]).exists():
            continue
        data_dir = exe_dir / rule["data"] if rule["data"] else exe_dir
        if data_dir.is_dir():
            return data_dir, rule["data"] == ""
    return None


def volume_of(path: Path) -> Tuple[str, str]:
    """(unidad, etiqueta) donde vive path, para agrupar resultados por disco.
    Windows: ("E:", "Datos"); Linux/macOS: (punto de montaje, "")."""
    if IS_WINDOWS:
        drive = os.path.splitdrive(str(path))[0].upper() or "?"
        label = ""
        try:
            buf = ctypes.create_unicode_buffer(261)
            root = drive + "\\"   # "E:\\" o "\\\\servidor\\recurso\\"
            if ctypes.windll.kernel32.GetVolumeInformationW(root, buf, 261, None, None, None, None, 0):
                label = buf.value
        except Exception:
            pass
        return drive, label
    p = os.path.abspath(str(path))
    while not os.path.ismount(p):
        parent = os.path.dirname(p)
        if parent == p:
            break
        p = parent
    return p, ""


def _match_config_entry(config: Dict[str, Any], data_dir: Path) -> Optional[str]:
    """Id del emulador ya configurado que apunta a esta misma carpeta, si hay."""
    target = _norm(data_dir)
    for name, emu in config.get("emulators", {}).items():
        p = get_emulator_path(emu)
        if p and _norm(p) == target:
            return name
    return None


def detect_installations(config: Dict[str, Any], progress=lambda m: None,
                         is_cancelled=lambda: False) -> Dict[str, Any]:
    """Escaneo de solo lectura: ubicaciones estándar + Flatpak + instalaciones
    portables en todos los discos. Nunca modifica nada en disco."""
    installs: List[Dict[str, Any]] = []
    seen = set()

    def add(key: str, data_dir: Path, origin: str, in_place: bool, exe_dir: Optional[Path] = None):
        norm = _norm(data_dir)
        if norm in seen:
            return
        seen.add(norm)
        emu = EMULATOR_DB[key]
        folders, files = scan_install(data_dir, emu, in_place)
        if not folders and not files:
            return  # carpeta vacía: el emulador nunca se abrió desde ahí
        platform_paths = {}
        if origin != "portable":
            for plat in ("windows", "linux", "mac"):
                cands = candidate_paths(emu, plat)
                platform_paths[plat] = str(cands[0][0]) if cands else ""
        drive, drive_label = volume_of(data_dir)
        installs.append({
            "emu_key": key, "name": emu["name"], "data_dir": data_dir, "origin": origin,
            "in_place": in_place, "exe_dir": exe_dir, "folders": folders, "files": files,
            "warning": tr(emu["warning"]) if emu.get("warning") else "", "platform_paths": platform_paths,
            "drive": drive, "drive_label": drive_label,
        })

    progress(tr("detect.standard"))
    for key, emu in EMULATOR_DB.items():
        for path, origin in candidate_paths(emu):
            if path.is_dir():
                add(key, path, origin, False)

    extra_roots = [(Path(p), 6) for p in config.get("options", {}).get("search_roots", []) if p]
    without_data = []
    for key, exe_dir in find_portable_installs(extra_roots + default_search_roots(), is_cancelled, progress):
        hit = _resolve_portable(key, exe_dir)
        if hit:
            add(key, hit[0], "portable", hit[1], exe_dir)
        else:
            drive, drive_label = volume_of(exe_dir)
            without_data.append({"emu_key": key, "name": EMULATOR_DB[key]["name"], "exe_dir": exe_dir,
                                 "drive": drive, "drive_label": drive_label})

    # Un exe "sin datos" es normal si ese emulador guarda en la ruta estándar.
    keys_with_data = {i["emu_key"] for i in installs}
    without_data = [w for w in without_data if w["emu_key"] not in keys_with_data]

    # Orden estable antes de asignar ids: el recorrido de discos no tiene un
    # orden fijo y así la misma PC siempre produce los mismos ids.
    installs.sort(key=lambda i: (i["name"].lower(), i["origin"], _norm(i["data_dir"])))
    without_data.sort(key=lambda w: (w["drive"], w["name"].lower()))

    # Ids: si ya hay un emulador configurado con esa carpeta se reutiliza su
    # id (se le suman carpetas nuevas); si no, uno libre sin pisar a nadie.
    # Una segunda copia en otro disco toma la letra de la unidad: "rpcs3_h".
    taken = set(config.get("emulators", {}).keys())
    for inst in installs:
        existing = _match_config_entry(config, inst["data_dir"])
        if existing:
            inst["id"], inst["config_id"] = existing, existing
            continue
        base = inst["emu_key"]
        drive_tag = "".join(c for c in inst["drive"].lower() if c.isalnum())
        candidates = [base] + ([f"{base}_{drive_tag}"] if drive_tag else []) + \
                     [f"{base}_{inst['origin']}"] + [f"{base}_{n}" for n in range(2, 100)]
        inst["id"] = next(c for c in candidates if c not in taken)
        inst["config_id"] = None
        taken.add(inst["id"])

    return {"installs": installs, "without_data": without_data, "cancelled": is_cancelled()}


def _union_ci(current: List[str], new: List[str]) -> List[str]:
    """Une dos listas de nombres sin duplicados (sin distinguir mayúsculas)
    y sin quitar nunca lo que ya estaba."""
    out = list(current)
    seen = {n.lower() for n in out}
    for n in new:
        if n.lower() not in seen:
            out.append(n)
            seen.add(n.lower())
    return out


def apply_detection(config: Dict[str, Any], inst: Dict[str, Any],
                    folders: List[str], files: List[str]) -> str:
    """Vuelca una detección en la config. Solo agrega, nunca quita.
    Devuelve "added", "updated" o "unchanged"."""
    emulators = config.setdefault("emulators", {})
    eid = inst["id"]
    if eid in emulators:
        emu = emulators[eid]
        before = (list(emu.get("important_folders", [])), list(emu.get("important_files", [])))
        emu["important_folders"] = _union_ci(emu.get("important_folders", []), folders)
        emu["important_files"] = _union_ci(emu.get("important_files", []), files)
        if not emu.get(PLATFORM_KEY):
            emu[PLATFORM_KEY] = str(inst["data_dir"])
        after = (emu["important_folders"], emu["important_files"])
        return "updated" if before != after else "unchanged"

    entry = {"windows": "", "linux": "", "mac": ""}
    entry.update(inst.get("platform_paths", {}))
    entry[PLATFORM_KEY] = str(inst["data_dir"])
    entry["important_folders"] = list(folders)
    entry["important_files"] = list(files)
    emulators[eid] = entry
    return "added"
