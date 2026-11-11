"""Base de datos de emuladores conocidos para el autodetector.

Las notas y avisos son CLAVES de traducción (emulinks/locales), no texto.
"""

from typing import Any, Dict


# Categorías de carpeta. Las de DEFAULT_UNCHECKED_CATEGORIES se muestran en el
# detector pero vienen destildadas: o se regeneran solas (caché) o pesan mucho
# y es el usuario quien decide (juegos/ROMs).
# El texto visible de cada una es tr("cat.<clave>").
CATEGORY_ORDER = ["system", "saves", "achievements", "states", "config",
                  "mods", "media", "other", "games", "cache"]
DEFAULT_UNCHECKED_CATEGORIES = {"games", "cache"}

IGNORED_SCAN_DIRS = {"logs", "log", "cache", "crashdumps", "crash_dumps", "tmp", "temp", ".git", "dump", "shadercache"}

# Archivos sueltos en la raíz de la carpeta de datos que se consideran
# configuración aunque no estén listados en la base (solo fuera de la carpeta
# del ejecutable: ahí también hay .ini/.json del propio programa).
CONFIG_FILE_EXTS = {".ini", ".cfg", ".json", ".toml", ".yml", ".yaml", ".xml", ".lpl", ".conf"}
IGNORED_ROOT_FILES = {"qt.conf", "portable.txt", "portable.ini", "installed.txt"}
LARGE_FILE_BYTES = 256 * 1024 * 1024


def _emu(name, paths, folders, *, files=(), portable=(), notes=None, flatpak=None, warning=""):
    """Entrada de EMULATOR_DB.

    paths:    plantillas por plataforma ({APPDATA}, {DOCUMENTS}, {XDG_DATA}…)
    folders:  nombre de carpeta en minúsculas -> categoría
    files:    archivos sueltos de la raíz que hay que respaldar
    portable: reglas {exe: [patrones], marker: ruta que debe existir junto al
              exe o None, data: subcarpeta de datos ("" = la del exe),
              unless: ruta que desactiva la regla}
    notes:    nombre en minúsculas -> clave de traducción (note.*)
    flatpak:  id de Flatpak; agrega ~/.var/app/<id>/{data,config}/… en Linux
    warning:  clave de traducción (warn.*) para datos que EmuLinks no puede
              ver (p.ej. saves junto a las ROMs)"""
    return {"name": name, "paths": paths, "folders": folders, "files": list(files),
            "portable": list(portable), "notes": notes or {}, "flatpak": flatpak,
            "warning": warning}


_SWITCH_FOLDERS = {
    "nand": "saves", "sdmc": "saves", "amiibo": "saves", "keys": "system",
    "config": "config", "post_presets": "config", "play_time": "achievements",
    "load": "mods", "post_shaders": "mods", "screenshots": "media", "tas": "other",
    "shader": "cache", "cache": "cache", "dump": "cache", "log": "cache",
    "crash_dumps": "cache", "icons": "cache",
}
_SWITCH_NOTES = {
    "nand": "note.switch_nand", "keys": "note.switch_keys",
    "play_time": "note.play_time", "load": "note.switch_load",
}


def _switch_fork(key, name, exes):
    # yuzu y todos sus forks comparten estructura. En Linux la config (.ini)
    # vive aparte en ~/.config/<key>; acá se toma la carpeta de datos.
    return _emu(name, {
        "windows": [f"{{APPDATA}}/{key}"],
        "linux": [f"{{XDG_DATA}}/{key}"],
        "mac": [f"{{MAC_AS}}/{key}"],
    }, _SWITCH_FOLDERS, notes=_SWITCH_NOTES,
        portable=[{"exe": exes, "marker": "user", "data": "user"}])


_3DS_FOLDERS = {
    "sdmc": "saves", "nand": "saves", "sysdata": "system", "config": "config",
    "states": "states", "load": "mods", "cheats": "mods", "screenshots": "media",
    "shaders": "cache", "dump": "cache", "log": "cache",
}


def _3ds_fork(name, win_dir, linux_dir, exes):
    return _emu(name, {
        "windows": [f"{{APPDATA}}/{win_dir}"],
        "linux": [f"{{XDG_DATA}}/{linux_dir}"],
        "mac": [f"{{MAC_AS}}/{win_dir}"],
    }, _3DS_FOLDERS, notes={"sdmc": "note.3ds_sdmc", "sysdata": "note.3ds_sysdata"},
        portable=[{"exe": exes, "marker": "user", "data": "user"}])


# Rutas verificadas contra documentación oficial / EmuDeck donde fue posible.
# Si una ruta no existe en la PC simplemente no se reporta, y cualquier carpeta
# que no esté en "folders" aparece igual como "Sin clasificar": la base solo
# sirve para clasificar, nunca para esconder datos.
EMULATOR_DB: Dict[str, Dict[str, Any]] = {
    # ── Nintendo Switch ────────────────────────────────────────────────
    "eden": _switch_fork("eden", "Eden (Switch)", ["eden.exe"]),
    "citron": _switch_fork("citron", "Citron (Switch)", ["citron.exe"]),
    "sudachi": _switch_fork("sudachi", "Sudachi (Switch)", ["sudachi.exe"]),
    "suyu": _switch_fork("suyu", "suyu (Switch)", ["suyu.exe"]),
    "yuzu": _switch_fork("yuzu", "yuzu (Switch)", ["yuzu.exe"]),
    "ryujinx": _emu("Ryujinx / Ryubing (Switch)", {
        "windows": ["{APPDATA}/Ryujinx"],
        "linux": ["{XDG_CONFIG}/Ryujinx"],
        "mac": ["{MAC_AS}/Ryujinx"],
    }, {
        "bis": "saves", "sdcard": "saves", "system": "system", "profiles": "config",
        "mods": "mods", "games": "cache", "logs": "cache",
    }, files=["Config.json"],
        portable=[{"exe": ["ryujinx*.exe"], "marker": "portable", "data": "portable"}],
        notes={"bis": "note.ryujinx_bis", "system": "note.ryujinx_system",
               "games": "note.shader_cache_per_game"}),
    # ── PlayStation ────────────────────────────────────────────────────
    "duckstation": _emu("DuckStation (PS1)", {
        "windows": ["{DOCUMENTS}/DuckStation", "{LOCALAPPDATA}/DuckStation"],
        "linux": ["{XDG_DATA}/duckstation"],
        "mac": ["{MAC_AS}/DuckStation"],
    }, {
        "bios": "system", "memcards": "saves", "savestates": "states", "gamesettings": "config",
        "inputprofiles": "config", "cheats": "mods", "patches": "mods", "textures": "mods",
        "shaders": "mods", "subchannels": "mods", "covers": "media", "screenshots": "media",
        "videos": "media", "cache": "cache", "gameicons": "cache", "dump": "cache",
    }, files=["settings.ini"], flatpak="org.duckstation.DuckStation",
        portable=[{"exe": ["duckstation*.exe"], "marker": "portable.txt", "data": ""}],
        notes={"memcards": "note.memcards", "settings.ini": "note.duck_settings"}),
    "pcsx2": _emu("PCSX2 (PS2)", {
        "windows": ["{DOCUMENTS}/PCSX2"],
        "linux": ["{XDG_CONFIG}/PCSX2"],
        "mac": ["{MAC_AS}/PCSX2"],
    }, {
        "bios": "system", "memcards": "saves", "sstates": "states", "inis": "config",
        "gamesettings": "config", "inputprofiles": "config", "cheats": "mods", "patches": "mods",
        "textures": "mods", "covers": "media", "snaps": "media", "videos": "media",
        "cache": "cache", "logs": "cache", "shaders": "cache",
    }, flatpak="net.pcsx2.PCSX2",
        portable=[{"exe": ["pcsx2*.exe"], "marker": "portable.ini", "data": ""},
                  {"exe": ["pcsx2*.exe"], "marker": "portable.txt", "data": ""}],
        notes={"inis": "note.pcsx2_inis", "memcards": "note.memcards"}),
    "rpcs3": _emu("RPCS3 (PS3)", {
        "windows": [],  # en Windows RPCS3 siempre guarda junto al ejecutable
        "linux": ["{XDG_CONFIG}/rpcs3"],
        "mac": ["{MAC_AS}/rpcs3"],
    }, {
        "dev_hdd0": "saves", "dev_usb000": "saves", "dev_flash": "system", "dev_flash2": "system",
        "dev_flash3": "system", "config": "config", "input_configs": "config", "guiconfigs": "config",
        "patches": "mods", "savestates": "states", "captures": "media", "screenshots": "media",
        "dev_bdvd": "games", "games": "games", "dev_hdd1": "cache", "cache": "cache",
        "log": "cache", "shaderlog": "cache", "icons": "cache",
    }, files=["config.yml", "games.yml", "evdev_positive_axis.yml"], flatpak="net.rpcs3.RPCS3",
        portable=[{"exe": ["rpcs3.exe"], "marker": None, "data": ""}],
        notes={"dev_hdd0": "note.rpcs3_hdd0", "dev_flash": "note.ps3_firmware"}),
    "shadps4": _emu("shadPS4 (PS4)", {
        "windows": ["{APPDATA}/shadPS4"],
        "linux": ["{XDG_DATA}/shadPS4"],
        "mac": ["{MAC_AS}/shadPS4"],
    }, {
        "savedata": "saves", "game_data": "saves", "sys_modules": "system", "patches": "mods",
        "mods": "mods", "shader": "cache", "log": "cache",
    }, files=["config.toml"],
        portable=[{"exe": ["shadps4*.exe"], "marker": "user", "data": "user"}],
        notes={"savedata": "note.shadps4_savedata"}),
    "ppsspp": _emu("PPSSPP (PSP)", {
        "windows": ["{DOCUMENTS}/PPSSPP/PSP"],
        "linux": ["{XDG_CONFIG}/ppsspp/PSP"],
        "mac": ["{XDG_CONFIG}/ppsspp/PSP"],
    }, {
        "savedata": "saves", "ppsspp_state": "states", "system": "config", "cheats": "mods",
        "textures": "mods", "plugins": "mods", "screenshot": "media", "game": "games",
        "shaders": "cache", "texdump": "cache",
    }, flatpak="org.ppsspp.PPSSPP",
        # installed.txt junto al exe = versión instalada, usa Documentos.
        portable=[{"exe": ["ppssppwindows*.exe"], "marker": "memstick/PSP",
                   "data": "memstick/PSP", "unless": "installed.txt"}],
        notes={"system": "note.ppsspp_system", "savedata": "note.saves"}),
    "vita3k": _emu("Vita3K (PS Vita)", {
        "windows": ["{APPDATA}/Vita3K/Vita3K"],
        "linux": ["{XDG_DATA}/Vita3K/Vita3K"],
        "mac": ["{MAC_AS}/Vita3K/Vita3K"],
    }, {
        "ux0": "saves", "ur0": "saves", "os0": "system", "vs0": "system", "sa0": "system",
        "pd0": "system", "textures": "mods", "cache": "cache", "shaderlog": "cache", "logs": "cache",
    }, files=["config.yml"],
        portable=[{"exe": ["vita3k.exe"], "marker": "ux0", "data": ""}],
        notes={"ux0": "note.vita_ux0", "os0": "note.firmware"}),
    # ── Nintendo (otras) ───────────────────────────────────────────────
    "azahar": _3ds_fork("Azahar (3DS)", "Azahar", "azahar-emu", ["azahar.exe"]),
    "citra": _3ds_fork("Citra (3DS)", "Citra", "citra-emu", ["citra-qt.exe", "citra.exe"]),
    "lime3ds": _3ds_fork("Lime3DS (3DS)", "Lime3DS", "lime3ds-emu", ["lime3ds*.exe"]),
    "cemu": _emu("Cemu (Wii U)", {
        "windows": ["{APPDATA}/Cemu"],
        # Cemu 2.x en Linux separa datos (~/.local/share) de config (~/.config).
        "linux": ["{XDG_DATA}/Cemu", "{XDG_CONFIG}/Cemu"],
        "mac": ["{MAC_AS}/Cemu"],
    }, {
        "mlc01": "saves", "controllerprofiles": "config", "gameprofiles": "config",
        "graphicpacks": "mods", "shadercache": "cache",
    }, files=["settings.xml", "keys.txt"], flatpak="info.cemu.Cemu",
        portable=[{"exe": ["cemu.exe"], "marker": "portable", "data": "portable"},
                  {"exe": ["cemu.exe"], "marker": "mlc01", "data": ""}],
        notes={"mlc01": "note.cemu_mlc01", "keys.txt": "note.cemu_keys"}),
    "dolphin": _emu("Dolphin (GameCube / Wii)", {
        "windows": ["{DOCUMENTS}/Dolphin Emulator", "{APPDATA}/Dolphin Emulator"],
        "linux": ["{XDG_DATA}/dolphin-emu", "{XDG_CONFIG}/dolphin-emu", "{HOME}/.dolphin-emu"],
        "mac": ["{MAC_AS}/Dolphin"],
    }, {
        "gc": "saves", "wii": "saves", "gba": "saves", "config": "config", "gamesettings": "config",
        "statesaves": "states", "load": "mods", "resourcepacks": "mods", "themes": "mods",
        "styles": "mods", "shaders": "mods", "screenshots": "media", "cache": "cache",
        "logs": "cache", "dump": "cache", "maps": "other", "backup": "other",
    }, flatpak="org.DolphinEmu.dolphin-emu",
        portable=[{"exe": ["dolphin.exe"], "marker": "portable.txt", "data": "User"}],
        notes={"gc": "note.dolphin_gc", "wii": "note.dolphin_wii", "config": "note.dolphin_config"}),
    "melonds": _emu("melonDS (DS)", {
        "windows": ["{APPDATA}/melonDS"],
        "linux": ["{XDG_CONFIG}/melonDS"],
        "mac": ["{MAC_AS}/melonDS"],
    }, {}, files=["melonDS.toml", "melonDS.ini", "bios7.bin", "bios9.bin", "firmware.bin",
                  "dsi_bios7.bin", "dsi_bios9.bin", "dsi_firmware.bin", "dsi_nand.bin"],
        portable=[{"exe": ["melonds*.exe"], "marker": None, "data": ""}],
        warning="warn.saves_next_to_rom"),
    "mgba": _emu("mGBA (GBA)", {
        "windows": ["{APPDATA}/mGBA"],
        "linux": ["{XDG_CONFIG}/mgba"],
        "mac": ["{MAC_AS}/mGBA"],
    }, {"cheats": "mods", "patches": "mods", "screenshots": "media", "shaders": "mods"},
        files=["config.ini", "qt.ini"],
        portable=[{"exe": ["mgba*.exe"], "marker": "portable.ini", "data": ""}],
        warning="warn.saves_next_to_rom"),
    # ── Microsoft ──────────────────────────────────────────────────────
    "xemu": _emu("xemu (Xbox)", {
        "windows": ["{APPDATA}/xemu/xemu"],
        "linux": ["{XDG_DATA}/xemu/xemu"],
        "mac": ["{MAC_AS}/xemu/xemu"],
    }, {}, files=["xemu.toml", "eeprom.bin", "xbox_hdd.qcow2"],
        portable=[{"exe": ["xemu.exe"], "marker": "xemu.toml", "data": ""}],
        notes={"xbox_hdd.qcow2": "note.xemu_hdd"}),
    "xenia": _emu("Xenia / Xenia Canary (Xbox 360)", {
        "windows": ["{DOCUMENTS}/Xenia"],
        "linux": [],
        "mac": [],
    }, {"content": "saves", "patches": "mods", "screenshots": "media",
        "cache": "cache", "cache0": "cache", "cache1": "cache"},
        files=["xenia.config.toml", "xenia-canary.config.toml"],
        portable=[{"exe": ["xenia*.exe"], "marker": "portable.txt", "data": ""}],
        notes={"content": "note.xenia_content"}),
    # ── Sega / arcade / multi ──────────────────────────────────────────
    "flycast": _emu("Flycast (Dreamcast)", {
        "windows": ["{APPDATA}/flycast"],
        "linux": ["{XDG_CONFIG}/flycast", "{XDG_DATA}/flycast"],
        "mac": ["{MAC_AS}/Flycast"],
    }, {"data": "saves", "mappings": "config", "textures": "mods"},
        files=["emu.cfg"],
        portable=[{"exe": ["flycast*.exe"], "marker": "emu.cfg", "data": ""}],
        notes={"data": "note.flycast_data"}),
    "retroarch": _emu("RetroArch", {
        "windows": ["{APPDATA}/RetroArch"],
        "linux": ["{XDG_CONFIG}/retroarch"],
        "mac": ["{MAC_AS}/RetroArch"],
    }, {
        "saves": "saves", "states": "states", "system": "system", "config": "config",
        "autoconfig": "config", "playlists": "config", "cheats": "mods", "shaders": "mods",
        "overlays": "mods", "thumbnails": "media", "screenshots": "media", "recordings": "media",
        "downloads": "other", "cores": "cache", "info": "cache", "assets": "cache",
        "database": "cache", "filters": "cache", "logs": "cache",
    }, files=["retroarch.cfg", "retroarch-core-options.cfg", "content_history.lpl", "content_favorites.lpl"],
        flatpak="org.libretro.RetroArch",
        # En Windows RetroArch siempre guarda junto al ejecutable.
        portable=[{"exe": ["retroarch.exe"], "marker": None, "data": ""}],
        notes={"saves": "note.ra_saves", "system": "note.ra_system",
               "config": "note.ra_config", "thumbnails": "note.ra_thumbnails"}),
    "mame": _emu("MAME (Arcade)", {
        "windows": [],
        "linux": ["{HOME}/.mame"],
        "mac": ["{HOME}/.mame"],
    }, {
        "nvram": "saves", "memcard": "saves", "hi": "saves", "diff": "saves", "cfg": "config",
        "ini": "config", "ctrlr": "config", "sta": "states", "snap": "media", "artwork": "mods",
        "cheat": "mods", "roms": "games", "samples": "games", "plugins": "cache", "hash": "cache",
        "bgfx": "cache", "hlsl": "cache", "language": "cache", "docs": "cache",
    }, files=["mame.ini", "ui.ini", "plugin.ini"],
        portable=[{"exe": ["mame.exe", "mame64.exe"], "marker": None, "data": ""}],
        notes={"nvram": "note.mame_nvram", "cfg": "note.mame_cfg"}),
    "scummvm": _emu("ScummVM", {
        "windows": ["{APPDATA}/ScummVM"],
        "linux": ["{XDG_DATA}/scummvm", "{XDG_CONFIG}/scummvm"],
        "mac": ["{MAC_AS}/ScummVM"],
    }, {"saved games": "saves", "saves": "saves", "icons": "media", "logs": "cache"},
        files=["scummvm.ini"]),
}
