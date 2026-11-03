"""Configuración de EmuLinks: dónde vive y cómo se carga/repara."""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from emulinks import APP_NAME
from emulinks.core.system import IS_WINDOWS


if IS_WINDOWS:
    _appdata = os.getenv("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    BASE_DATA_DIR = Path(_appdata) / APP_NAME
else:
    BASE_DATA_DIR = Path.home() / ".config" / APP_NAME

BASE_DATA_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_PATH = BASE_DATA_DIR / "config.json"
LOG_DIR = BASE_DATA_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)


def _default_config() -> Dict[str, Any]:
    home = Path.home()
    return {
        "shared_dir": str(home / "Emulation" / "Shared"),
        "emulators": {
            "eden": {
                "windows": str(home / "AppData" / "Roaming" / "eden"),
                "linux": str(home / ".local" / "share" / "eden"),
                "mac": str(home / "Library" / "Application Support" / "eden"),
                # Verificado en la documentación oficial de yuzu (eden es un fork):
                # las carpetas reales son config/nand/sdmc/keys — NO existen
                # "saves"/"configs"/"controls"/"shaders"/"states" en esta ruta.
                "important_folders": ["keys", "config", "nand", "sdmc"],
            },
            "pcsx2": {
                "windows": str(home / "Documents" / "PCSX2"),
                "linux": str(home / ".config" / "PCSX2"),
                "mac": str(home / "Library" / "Application Support" / "PCSX2"),
                # PCSX2 usa "sstates" (no "savestates"), y "inis" guarda la
                # configuración (PCSX2.ini) — antes faltaba.
                "important_folders": ["bios", "memcards", "sstates", "inis", "cheats", "patches"],
            },
            "rpcs3": {
                "windows": str(home / "AppData" / "Roaming" / "rpcs3"),
                "linux": str(home / ".config" / "rpcs3"),
                "mac": str(home / "Library" / "Application Support" / "rpcs3"),
                "important_folders": ["dev_hdd0", "dev_flash", "dev_flash2", "dev_flash3", "dev_usb000", "config"],
            },
            "duckstation": {
                "windows": str(home / "Documents" / "DuckStation"),
                "linux": str(home / ".local" / "share" / "duckstation"),
                "mac": str(home / "Library" / "Application Support" / "duckstation"),
                # DuckStation usa "savestates" (no "saves").
                "important_folders": ["bios", "memcards", "savestates", "cheats", "screenshots", "covers"],
            },
            "retroarch": {
                "windows": str(home / "AppData" / "Roaming" / "RetroArch"),
                "linux": str(home / ".config" / "retroarch"),
                "mac": str(home / "Library" / "Application Support" / "RetroArch"),
                "important_folders": ["config", "shaders", "saves", "screenshots", "states", "cheats"],
            },
        },
        "options": {
            "backup": True,
            "zip_backup": True,
            "dry_run": False,
            "copy_missing": True,
            "max_backups": 5,
            # Carpetas extra donde el autodetector busca instalaciones portables.
            "search_roots": [],
        },
    }


def load_config() -> Dict[str, Any]:
    defaults = _default_config()
    if not CONFIG_PATH.exists():
        save_config(defaults)
        return defaults
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        repaired = False
        raw_emulators = data.get("emulators")
        if not isinstance(raw_emulators, dict):
            # El campo no existe o está corrompido estructuralmente (no es
            # ni siquiera un dict): esto sí amerita reponer los valores de
            # referencia, es una config nueva o rota de verdad.
            emulators = defaults["emulators"]
            repaired = True
        else:
            emulators = raw_emulators
            for key in list(emulators.keys()):
                emu = emulators[key]
                if not isinstance(emu, dict):
                    del emulators[key]
                    repaired = True
                    continue
                if not isinstance(emu.get("important_folders"), list):
                    emu["important_folders"] = []
                    repaired = True
                if not isinstance(emu.get("important_files", []), list):
                    emu["important_files"] = []
                    repaired = True
                for plat in ("windows", "linux", "mac"):
                    if not isinstance(emu.get(plat), str):
                        emu[plat] = str(emu.get(plat) or "")
                        repaired = True
            # OJO: si "emulators" queda en {} porque el usuario borró todos
            # los emuladores a propósito desde la lista, eso es legítimo y
            # NO se repone acá. Antes esto hacía que los emuladores borrados
            # "resucitaran" solos al cerrar y reabrir el programa.
        data["emulators"] = emulators

        if not isinstance(data.get("shared_dir"), str) or not data["shared_dir"].strip():
            data["shared_dir"] = defaults["shared_dir"]
            repaired = True

        options = data.get("options")
        if not isinstance(options, dict):
            options = {}
        data["options"] = {**defaults["options"], **options}

        if repaired:
            save_config(data)
        return data
    except Exception as e:
        try:
            with open(LOG_DIR / "config-errors.log", "a", encoding="utf-8") as f:
                f.write(f"{datetime.now().isoformat()} - Error leyendo config.json: {e}\n")
        except Exception:
            pass
        # Antes de reponer los valores por defecto se guarda una copia del
        # archivo roto: ahí están las rutas y carpetas que el usuario cargó.
        try:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            shutil.copy2(CONFIG_PATH, CONFIG_PATH.with_name(f"config.corrupt_{stamp}.json"))
        except Exception:
            pass
        save_config(defaults)
        return defaults


def save_config(config: Dict[str, Any]) -> bool:
    """Escribe a un temporal y lo reemplaza de una vez (un corte de luz no deja
    el archivo a medias). La versión anterior queda en config.prev.json, para
    poder volver atrás si se borra algo sin querer."""
    try:
        new_text = json.dumps(config, indent=2, ensure_ascii=False)
        if CONFIG_PATH.exists():
            try:
                old_text = CONFIG_PATH.read_text(encoding="utf-8")
            except Exception:
                old_text = None
            if old_text is not None and old_text != new_text:
                shutil.copy2(CONFIG_PATH, CONFIG_PATH.with_name("config.prev.json"))
        tmp = CONFIG_PATH.with_name("config.json.tmp")
        tmp.write_text(new_text, encoding="utf-8")
        os.replace(tmp, CONFIG_PATH)
        return True
    except Exception:
        return False
