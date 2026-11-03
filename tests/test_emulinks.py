"""Pruebas del núcleo (sin Qt), de las traducciones y una prueba de humo de la GUI.

Todo corre en carpetas temporales: nunca toca los emuladores reales ni la
config real.
    python -m pytest tests -q
(o sin pytest: python tests/test_emulinks.py)
"""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from emulinks import i18n  # noqa: E402
from emulinks.core import LOG_LEVELS  # noqa: E402
from emulinks.core import detection, fs  # noqa: E402
from emulinks.core.emulators_db import EMULATOR_DB  # noqa: E402

OPTIONS = {"backup": True, "zip_backup": True, "copy_missing": True, "dry_run": False, "max_backups": 5}


class _Log:
    """Junta (texto, nivel) y valida que el nivel sea uno de los conocidos."""
    def __init__(self):
        self.entries = []

    def __call__(self, text, level="info"):
        assert level in LOG_LEVELS, level
        self.entries.append((text, level))

    def levels(self):
        return [lvl for _t, lvl in self.entries]


def _make_env(tmp: Path):
    emu = tmp / "emu"
    shared = tmp / "shared"
    (emu / "memcards").mkdir(parents=True)
    (emu / "memcards" / "card1.mcd").write_bytes(b"partida")
    (emu / "settings.ini").write_text("[Main]\nx=1\n", encoding="utf-8")
    # Marcador dañado como los que dejan algunas herramientas de copia.
    (emu / "savestates").write_bytes(b"IntxLNK\x01" + "unsupported".encode("utf-16-le"))
    (shared / "ps1" / "savestates").mkdir(parents=True)
    (shared / "ps1" / "savestates" / "slot1.sav").write_bytes(b"state")
    cfg = {"windows": str(emu), "linux": str(emu), "mac": str(emu),
           "important_folders": ["memcards", "savestates"], "important_files": ["settings.ini"]}
    return emu, shared, cfg


def test_sync_links_repairs_placeholder_and_backs_up_files():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        emu, shared, cfg = _make_env(tmp)
        log = _Log()
        assert fs.is_placeholder_link(emu / "savestates")
        ok = fs.sync_emulator("ps1", cfg, shared, OPTIONS, log, lambda: False)
        assert ok, log.entries
        assert "error" not in log.levels(), log.entries
        # memcards migrada y enlazada, sin perder el contenido
        assert fs.is_link_like(emu / "memcards")
        assert (emu / "memcards" / "card1.mcd").read_bytes() == b"partida"
        # el marcador dañado fue reemplazado por un enlace real a la compartida
        assert fs.is_link_like(emu / "savestates")
        assert (emu / "savestates" / "slot1.sav").read_bytes() == b"state"
        # archivo suelto copiado y el original intacto
        assert (shared / "ps1" / fs.ROOT_FILES_DIRNAME / "settings.ini").is_file()
        assert (emu / "settings.ini").is_file()

        rows = fs.check_status({"shared_dir": str(shared), "emulators": {"ps1": cfg}}, ["ps1"])["ps1"]
        states = {(r["kind"], r["folder_name"]): r["state"] for r in rows}
        assert states[("folder", "memcards")] == "linked"
        assert states[("folder", "savestates")] == "linked"
        assert states[("file", "settings.ini")] == "file_ok"

        # segunda pasada: idempotente, sin errores
        log2 = _Log()
        assert fs.sync_emulator("ps1", cfg, shared, OPTIONS, log2, lambda: False)
        assert i18n.tr("log.file_current", file="settings.ini") in [t for t, _ in log2.entries]


def test_dry_run_changes_nothing():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        emu, shared, cfg = _make_env(tmp)
        before = sorted(p.name for p in emu.iterdir())
        fs.sync_emulator("ps1", cfg, shared, {**OPTIONS, "dry_run": True}, _Log(), lambda: False)
        assert sorted(p.name for p in emu.iterdir()) == before
        assert fs.is_placeholder_link(emu / "savestates")
        assert not (shared / "ps1" / "memcards").exists()


def test_safe_to_remove_is_case_insensitive_on_windows():
    with tempfile.TemporaryDirectory() as t:
        shared = Path(t) / "Shared"
        shared.mkdir()
        targets = [shared, Path(t)]
        if fs.IS_WINDOWS:
            targets.append(Path(str(shared).upper()))
        for target in targets:
            try:
                fs.assert_safe_to_remove(target, shared)
                raise AssertionError(f"debió bloquear {target}")
            except RuntimeError:
                pass
        fs.assert_safe_to_remove(Path(t) / "otra", shared)  # no bloquea


def test_scan_install_keeps_unknown_folders_and_classifies():
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        for name in ("memcards", "bios", "cache", "mis_cosas"):
            (d / name).mkdir()
        (d / "settings.ini").write_text("x", encoding="utf-8")
        (d / "memcards_backup_20260101_000000.zip").write_bytes(b"")
        folders, files = detection.scan_install(d, EMULATOR_DB["duckstation"], in_place=False)
        by_name = {f["name"]: f for f in folders}
        assert by_name["memcards"]["category"] == "saves" and by_name["memcards"]["checked"]
        assert by_name["memcards"]["note"] == i18n.tr("note.memcards")   # nota traducida
        assert by_name["bios"]["category"] == "system"
        assert by_name["cache"]["category"] == "cache" and not by_name["cache"]["checked"]
        assert by_name["mis_cosas"]["category"] == "other" and by_name["mis_cosas"]["checked"]
        assert [f["name"] for f in files] == ["settings.ini"]
        assert not any("_backup_" in f["name"] for f in folders + files)


def test_portable_rules_and_apply_detection_only_adds():
    with tempfile.TemporaryDirectory() as t:
        root = Path(t)
        ryu = root / "Emus" / "Ryujinx"
        (ryu / "portable" / "bis").mkdir(parents=True)
        (ryu / "Ryujinx.exe").write_bytes(b"")
        found = detection.find_portable_installs([(root, 3)])
        assert ("ryujinx", ryu) in found
        data_dir, in_place = detection._resolve_portable("ryujinx", ryu)
        assert data_dir == ryu / "portable" and not in_place

        config = {"emulators": {"ryujinx": {"windows": str(data_dir), "linux": str(data_dir),
                                            "mac": str(data_dir), "important_folders": ["bis"]}}}
        inst = {"id": "ryujinx", "data_dir": data_dir, "platform_paths": {}}
        assert detection.apply_detection(config, inst, ["BIS", "system"], ["Config.json"]) == "updated"
        assert config["emulators"]["ryujinx"]["important_folders"] == ["bis", "system"]
        assert detection.apply_detection(config, inst, ["bis"], []) == "unchanged"


def test_translations_complete_and_db_keys_exist():
    assert i18n.missing_translations() == {}
    keys = set(i18n.STRINGS["es"])
    for emu in EMULATOR_DB.values():
        for note_key in emu["notes"].values():
            assert note_key in keys, note_key
        if emu["warning"]:
            assert emu["warning"] in keys, emu["warning"]
    for code in i18n.LANGUAGES:
        i18n.set_language(code)
        assert i18n.tr("log.processing", name="x", current=1, total=2)
    i18n.set_language("es")


class _IsolatedConfig:
    """Apunta config.json y la carpeta de logs a un temporal (nunca a los reales)."""
    def __enter__(self):
        from emulinks.core import config as cfgmod
        self.mod = cfgmod
        self.tmp = tempfile.TemporaryDirectory()
        self.saved = (cfgmod.CONFIG_PATH, cfgmod.LOG_DIR)
        cfgmod.CONFIG_PATH = Path(self.tmp.name) / "config.json"
        cfgmod.LOG_DIR = Path(self.tmp.name)
        return Path(self.tmp.name)

    def __exit__(self, *exc):
        self.mod.CONFIG_PATH, self.mod.LOG_DIR = self.saved
        self.tmp.cleanup()


def test_corrupt_config_is_preserved():
    with _IsolatedConfig() as d:
        from emulinks.core import config as cfgmod
        cfgmod.CONFIG_PATH.write_text("{ esto no es json", encoding="utf-8")
        data = cfgmod.load_config()
        assert "emulators" in data
        copies = list(d.glob("config.corrupt_*.json"))
        assert copies and copies[0].read_text(encoding="utf-8") == "{ esto no es json"


def test_save_config_keeps_previous_version():
    with _IsolatedConfig() as d:
        from emulinks.core import config as cfgmod
        assert cfgmod.save_config({"emulators": {"eden": {}}})
        assert cfgmod.save_config({"emulators": {}})
        import json
        assert json.loads((d / "config.prev.json").read_text(encoding="utf-8")) == {"emulators": {"eden": {}}}
        assert not (d / "config.json.tmp").exists()


def test_backups_go_to_one_zip_and_restore():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        emu, shared = tmp / "emu", tmp / "shared"
        for folder in ("memcards", "bios"):
            (emu / folder).mkdir(parents=True)
            (emu / folder / "x.bin").write_bytes(folder.encode())
            (shared / "ps1" / folder).mkdir(parents=True)        # existe en los dos lados
        (emu / "bios" / "vacia").mkdir()
        cfg = {"windows": str(emu), "linux": str(emu), "mac": str(emu),
               "important_folders": ["memcards", "bios"]}
        assert fs.sync_emulator("ps1", cfg, shared, OPTIONS, _Log(), lambda: False)

        zips = list((shared / fs.BACKUP_DIRNAME / "ps1").glob("*.zip"))
        assert len(zips) == 1, zips                                  # UN zip para todo
        assert not list(emu.glob("*_backup_*"))                      # nada suelto en el emulador
        config = {"shared_dir": str(shared), "emulators": {"ps1": cfg}}
        entries = {e["folder_name"]: e for e in fs.list_backups(config, "ps1")}
        assert set(entries) == {"memcards", "bios"}

        dest = tmp / "restaurado" / "bios"
        e = entries["bios"]
        ok, msg = fs.restore_backup(e["full_path"], e["is_zip"], dest, e["member"])
        assert ok, msg
        assert (dest / "x.bin").read_bytes() == b"bios" and (dest / "vacia").is_dir()
        assert not (dest / "memcards").exists()


def test_failed_backup_leaves_folder_untouched():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        emu, shared = tmp / "emu", tmp / "shared"
        (emu / "memcards").mkdir(parents=True)
        (emu / "memcards" / "card.mcd").write_bytes(b"partida")
        cfg = {"windows": str(emu), "linux": str(emu), "mac": str(emu), "important_folders": ["memcards"]}
        original = fs.BackupSession.add
        fs.BackupSession.add = lambda self, folder: (_ for _ in ()).throw(OSError("disco lleno"))
        try:
            log = _Log()
            assert not fs.sync_emulator("ps1", cfg, shared, OPTIONS, log, lambda: False)
        finally:
            fs.BackupSession.add = original
        assert "error" in log.levels()
        assert not fs.is_link_like(emu / "memcards")
        assert (emu / "memcards" / "card.mcd").read_bytes() == b"partida"


def test_volume_of():
    drive, _label = detection.volume_of(Path(tempfile.gettempdir()))
    assert drive
    if fs.IS_WINDOWS:
        assert drive.endswith(":")


def _qt_app():
    from emulinks.ui.qt import QApplication
    from emulinks.ui.theme import setup_appearance
    app = QApplication.instance() or QApplication([])
    if not getattr(app, "_emulinks_setup", False):
        setup_appearance(app)
        app._emulinks_setup = True
    return app


def test_detect_tree_drive_groups_and_tristate_cycle():
    _qt_app()
    from emulinks.ui import dialogs
    from emulinks.ui.qt import Qt

    def folder(name, checked):
        return {"name": name, "category": "saves" if checked else "cache", "checked": checked,
                "linked": False, "broken": False, "note": ""}
    inst = lambda key, drive, path: {  # noqa: E731
        "emu_key": key, "name": key, "id": key, "config_id": None, "origin": "portable",
        "data_dir": Path(path), "drive": drive, "drive_label": "", "warning": "",
        "folders": [folder("saves", True), folder("cache", False)], "files": []}
    result = {"installs": [inst("rpcs3", "E:", "E:/a"), inst("mame", "E:", "E:/b"), inst("rpcs3_h", "H:", "H:/c")],
              "without_data": [], "cancelled": False}

    original = dialogs.DetectDialog._start_scan
    dialogs.DetectDialog._start_scan = lambda self: None
    try:
        d = dialogs.DetectDialog(None, {"emulators": {}})
    finally:
        dialogs.DetectDialog._start_scan = original
    d._installs = result["installs"]
    d._populate(result)

    assert d.tree.topLevelItemCount() == 2                      # E: y H:
    drive_e = d.tree.topLevelItem(0)
    assert drive_e.childCount() == 2
    rpcs3 = drive_e.child(0)
    # Arranca en lo recomendado → cuadrado
    assert rpcs3.checkState(0) == Qt.PartiallyChecked
    # Ciclo del clic: cuadrado → tilde (todo) → vacío (nada) → cuadrado (recomendado)
    rpcs3.setCheckState(0, Qt.Checked)
    assert all(rpcs3.child(i).checkState(0) == Qt.Checked for i in range(2))
    rpcs3.setCheckState(0, Qt.Unchecked)
    assert all(rpcs3.child(i).checkState(0) == Qt.Unchecked for i in range(2))
    rpcs3.setCheckState(0, Qt.PartiallyChecked)
    assert [rpcs3.child(i).checkState(0) for i in range(2)] == [Qt.Checked, Qt.Unchecked]
    # La unidad aplica lo mismo a todo lo que tiene adentro
    drive_e.setCheckState(0, Qt.Unchecked)
    assert [i["id"] for i, _f, _fi in d.selected()] == ["rpcs3_h"]
    d.done(0)


def test_gui_smoke_offscreen():
    """Arma la ventana completa en modo offscreen con una config aislada."""
    with _IsolatedConfig():
        _qt_app()
        from emulinks.ui import main_window
        win = main_window.EmuLinksWindow()
        win._check_status()
        assert win.kpi["emulators"].text() == str(len(win.config["emulators"]))
        win.log("prueba <con> & símbolos", "warn")
        assert "prueba <con> & símbolos" in win.console.toPlainText()
        win.close()


if __name__ == "__main__":
    failed = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"OK    {name}")
            except Exception as ex:  # noqa: BLE001
                failed += 1
                print(f"FALLA {name}: {ex!r}")
    sys.exit(1 if failed else 0)
