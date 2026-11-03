"""Lógica de filesystem: enlaces/junctions, backups, estado y sincronización.

Reglas de seguridad (ver CLAUDE.md): antes de cualquier borrado de carpeta se
llama a assert_safe_to_remove(); los enlaces se detectan con is_link_like() y
se quitan con remove_link(), nunca con rmtree.
"""

import os
import shutil
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from emulinks.core import LOG_ERROR, LOG_INFO, LOG_OK, LOG_WARN
from emulinks.core.system import IS_WINDOWS, PLATFORM_KEY
from emulinks.i18n import tr

# Las copias de los archivos sueltos viven en <compartida>/<emulador>/_archivos.
ROOT_FILES_DIRNAME = "_archivos"


def get_emulator_path(emu_config: Dict[str, str]) -> Optional[Path]:
    p = emu_config.get(PLATFORM_KEY, "")
    return Path(p) if p else None


def assert_safe_to_remove(target: Path, shared_dir: Path) -> None:
    """Nunca se borra la carpeta compartida ni ninguna carpeta que la contenga.
    Se llama antes de CUALQUIER borrado del programa."""
    # normcase: en Windows "E:\Emu" y "e:\emu" son la misma carpeta, y una
    # comparación sensible a mayúsculas dejaría pasar el borrado.
    target_r = os.path.normcase(str(target.resolve()))
    shared_r = os.path.normcase(str(shared_dir.resolve()))
    if target_r == shared_r or shared_r.startswith(target_r.rstrip(os.sep) + os.sep):
        raise RuntimeError(tr("err.blocked", path=target))


def is_link_like(path: Path) -> bool:
    """Detecta symlinks Y también junctions de Windows.

    CRÍTICO: en Windows, un junction creado con mklink /J NO es detectado
    por Path.is_symlink() — usa una etiqueta de reparse distinta
    (IO_REPARSE_TAG_MOUNT_POINT) a la de un symlink real
    (IO_REPARSE_TAG_SYMLINK). Si no se detecta acá, el código de más abajo
    cree que es una carpeta real e intenta shutil.rmtree() sobre un enlace
    ya existente, lo cual Python rechaza con "Cannot call rmtree on a
    symbolic link" (y con razón: recorrer y borrar a través de un junction
    puede terminar borrando el contenido de la carpeta compartida real)."""
    try:
        if path.is_symlink():
            return True
    except OSError:
        pass
    if IS_WINDOWS:
        try:
            st = os.stat(path, follow_symlinks=False)
            FILE_ATTRIBUTE_REPARSE_POINT = 0x400
            return bool(getattr(st, "st_file_attributes", 0) & FILE_ATTRIBUTE_REPARSE_POINT)
        except OSError:
            return False
    return False


def is_placeholder_link(path: Path) -> bool:
    """Archivo marcador que imita un enlace ("IntxLNK" de Interix/SFU o
    "!<symlink>" de Cygwin/MSYS). Aparece cuando una carpeta con junctions se
    copia con una herramienta que no los entiende: el emulador encuentra un
    ARCHIVO donde esperaba su carpeta y no llega a los datos compartidos.
    Visto en la práctica en RPCS3 y RetroArch portables."""
    try:
        if is_link_like(path) or not path.is_file() or path.stat().st_size > 1024:
            return False
        with open(path, "rb") as f:
            head = f.read(12)
        return head.startswith(b"IntxLNK") or head.startswith(b"!<symlink>")
    except OSError:
        return False


def remove_link(path: Path) -> None:
    """Quita un enlace/junction existente sin tocar el contenido al que
    apunta. Prueba rmdir() primero (correcto para junctions y symlinks de
    carpeta) y cae a unlink() si hace falta (symlinks de archivo)."""
    try:
        path.rmdir()
    except OSError:
        path.unlink()


def _same_path(a: Path, b: Path) -> bool:
    """Compara dos rutas ya resueltas de forma segura entre plataformas
    (Windows no distingue mayúsculas de minúsculas)."""
    return os.path.normcase(str(a)) == os.path.normcase(str(b))


def create_symlink(target: Path, link: Path, shared_dir: Path, dry_run: bool = False) -> Tuple[bool, str]:
    try:
        if dry_run:
            return True, tr("log.dry_link", link=link, target=target)

        # os.path.lexists en vez de link.exists(): esto último sigue el
        # enlace, así que un enlace roto (apunta a algo que ya no existe)
        # pasaría desapercibido y create_symlink fallaría más abajo al
        # intentar crear un enlace donde ya hay uno.
        if os.path.lexists(link):
            if is_link_like(link):
                # Ya es un enlace/junction (funcionando o roto): se quita
                # solo el puntero, nunca se toca lo que hay del otro lado.
                try:
                    remove_link(link)
                except OSError as e:
                    return False, tr("log.link_remove_failed", link=link, error=e)
            elif link.is_dir():
                # Carpeta real con datos (no un enlace): a esta altura del
                # flujo ya se hizo backup si correspondía; se reemplaza.
                assert_safe_to_remove(link, shared_dir)
                shutil.rmtree(link)
            else:
                return False, tr("log.not_dir_or_link", link=link)

        link.parent.mkdir(parents=True, exist_ok=True)

        if IS_WINDOWS:
            # cmd escribe en la página de códigos OEM (cp850 en español:
            # "Vínculo…"), no en UTF-8; decodificar mal tira el hilo lector y
            # se pierde el mensaje de error de mklink.
            result = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(link), str(target)],
                capture_output=True, text=True, encoding="oem", errors="replace"
            )
            if result.returncode != 0:
                return False, tr("log.mklink_error", error=(result.stderr or result.stdout).strip())
        else:
            link.symlink_to(target, target_is_directory=True)

        return True, tr("log.link_created", link=link, target=target)
    except Exception as e:
        return False, tr("log.link_error", link=link, target=target, error=e)


# Todos los backups de un emulador viven en
# <compartida>/Backup-EmuLinks/<emulador>/<emulador>_<fecha>.zip
BACKUP_DIRNAME = "Backup-EmuLinks"


def _unique_backup_path(parent: Path, base_name: str, suffix: str) -> Path:
    """Evita pisar un backup anterior si dos operaciones caen en el mismo
    segundo (timestamp con precisión de segundos): agrega un sufijo _2, _3...
    hasta encontrar un nombre libre."""
    candidate = parent / f"{base_name}{suffix}"
    counter = 1
    while candidate.exists():
        counter += 1
        candidate = parent / f"{base_name}_{counter}{suffix}"
    return candidate


def backup_root(shared_dir: Path, emu_name: str) -> Path:
    return shared_dir / BACKUP_DIRNAME / emu_name


class BackupSession:
    """Junta en UN solo backup todo lo que se respalda de un emulador en una
    sincronización: un .zip (o una carpeta, si no se comprime) con una
    subcarpeta por cada carpeta respaldada. Se crea recién con la primera
    copia, así una sincronización sin cambios no deja backups vacíos."""

    def __init__(self, shared_dir: Path, emu_name: str, zip_backup: bool):
        self.root = backup_root(shared_dir, emu_name)
        self.emu_name = emu_name
        self.zip_backup = zip_backup
        self.path: Optional[Path] = None
        self._zf: Optional[zipfile.ZipFile] = None

    def _open(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        name = f"{self.emu_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if self.zip_backup:
            self.path = _unique_backup_path(self.root, name, ".zip")
            self._zf = zipfile.ZipFile(self.path, "w", zipfile.ZIP_DEFLATED, allowZip64=True)
        else:
            self.path = _unique_backup_path(self.root, name, "")
            self.path.mkdir()

    def add(self, folder: Path) -> Path:
        """Copia la carpeta al backup. Si falla, lanza la excepción: quien
        llama NO debe reemplazar la carpeta original por el enlace."""
        if self.path is None:
            self._open()
        if self._zf is not None:
            for root, _dirs, files in os.walk(folder):
                root_path = Path(root)
                arc_dir = (Path(folder.name) / root_path.relative_to(folder)).as_posix()
                # Entrada de carpeta: así se restauran también las vacías.
                self._zf.write(root_path, arc_dir + "/")
                for file in files:
                    fp = root_path / file
                    self._zf.write(fp, (Path(folder.name) / fp.relative_to(folder)).as_posix())
        else:
            shutil.copytree(folder, self.path / folder.name)
        return self.path

    def close(self) -> None:
        if self._zf is not None:
            self._zf.close()
            self._zf = None


def rotate_backups(root: Path, max_backups: int, shared_dir: Path) -> None:
    """Conserva los max_backups backups más nuevos de un emulador (0 = todos)."""
    if not max_backups or max_backups <= 0:
        return
    try:
        entries = list(root.iterdir())
    except OSError:
        return
    entries.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    for old in entries[max_backups:]:
        assert_safe_to_remove(old, shared_dir)
        if old.is_dir():
            shutil.rmtree(old)
        else:
            old.unlink()


def _zip_top_folders(path: Path) -> List[str]:
    try:
        with zipfile.ZipFile(path) as zf:
            return sorted({n.split("/", 1)[0] for n in zf.namelist() if "/" in n})
    except (OSError, zipfile.BadZipFile):
        return []


def list_backups(config: Dict[str, Any], emu_name: str) -> List[Dict[str, Any]]:
    """Backups restaurables del emulador, una fila por carpeta respaldada.
    Incluye los de Backup-EmuLinks y los del formato viejo
    (<carpeta>_backup_<fecha>.zip junto a cada carpeta del emulador)."""
    emu = config["emulators"].get(emu_name)
    if not emu:
        return []
    results = []

    def add(folder_name: str, entry: Path, member: Optional[str], legacy: bool):
        st = entry.stat()
        results.append({
            "folder_name": folder_name, "file_name": entry.name, "full_path": entry,
            "is_zip": entry.suffix == ".zip", "member": member, "legacy": legacy,
            "mtime": st.st_mtime,
        })

    root = backup_root(Path(config["shared_dir"]), emu_name)
    try:
        sessions = list(root.iterdir()) if root.is_dir() else []
    except OSError:
        sessions = []
    for entry in sessions:
        if entry.suffix == ".zip":
            for folder_name in _zip_top_folders(entry):
                add(folder_name, entry, folder_name, False)
        elif entry.is_dir():
            for sub in sorted(p for p in entry.iterdir() if p.is_dir()):
                add(sub.name, entry, sub.name, False)

    emu_path = get_emulator_path(emu)
    if emu_path and emu_path.exists():
        try:
            local = list(emu_path.iterdir())
        except OSError:
            local = []
        for folder_name in emu.get("important_folders", []):
            prefix = f"{folder_name}_backup_"
            for e in local:
                if e.name.startswith(prefix):
                    # Los zip viejos guardaban "<carpeta>/..." adentro; las
                    # copias viejas sin comprimir SON la carpeta.
                    add(folder_name, e, folder_name if e.suffix == ".zip" else None, True)
    results.sort(key=lambda r: r["mtime"], reverse=True)
    return results


def restore_backup(backup_path: Path, is_zip: bool, dest_folder: Path,
                   member: Optional[str] = None) -> Tuple[bool, str]:
    """Restaura UNA carpeta de un backup en dest_folder (que no debe existir).
    member: subcarpeta dentro del backup; None = el backup entero es la carpeta."""
    try:
        if dest_folder.exists():
            return False, tr("err.restore_dest_exists")
        dest_folder.parent.mkdir(parents=True, exist_ok=True)
        if not is_zip:
            shutil.copytree(backup_path / member if member else backup_path, dest_folder)
            return True, str(dest_folder)

        tmp = _unique_backup_path(dest_folder.parent, dest_folder.name + "__restore_tmp", "")
        try:
            with zipfile.ZipFile(backup_path, "r") as zf:
                prefix = f"{member}/" if member else ""
                for info in zf.infolist():
                    name = info.filename
                    # Nada fuera de la carpeta pedida, ni rutas que escapen (zip slip).
                    if not name.startswith(prefix) or name.startswith("/") or ".." in Path(name).parts:
                        continue
                    zf.extract(info, tmp)
            source = tmp / member if member else tmp
            if not source.exists():
                return False, tr("err.restore_not_in_backup", folder=member or dest_folder.name)
            shutil.move(str(source), str(dest_folder))
        finally:
            if tmp.exists():
                shutil.rmtree(tmp, ignore_errors=True)
        return True, str(dest_folder)
    except Exception as e:
        return False, str(e)


def check_status(config: Dict[str, Any], emu_names: List[str]) -> Dict[str, List[Dict[str, str]]]:
    """Escaneo de solo lectura: nunca modifica nada en disco."""
    report: Dict[str, List[Dict[str, str]]] = {}
    shared_dir = Path(config["shared_dir"])
    for name in emu_names:
        emu = config["emulators"].get(name)
        if not emu:
            continue
        emu_path = get_emulator_path(emu)
        shared_emu_dir = shared_dir / name
        rows = []
        for folder_name in emu.get("important_folders", []):
            shared = shared_emu_dir / folder_name
            if not emu_path:
                state = "no_path"
            else:
                source = emu_path / folder_name
                if is_placeholder_link(source):
                    state = "placeholder"
                elif is_link_like(source):
                    try:
                        real = source.resolve(strict=False)
                        real_exists = real.exists()
                    except OSError:
                        real = None
                        real_exists = False
                    shared_real = shared.resolve(strict=False) if shared.exists() else None
                    if shared_real and real and _same_path(real, shared_real):
                        state = "linked"
                    elif real_exists:
                        # El enlace funciona pero apunta a otra carpeta —
                        # típicamente porque se cambió la carpeta compartida.
                        state = "stale_shared"
                    else:
                        state = "broken"
                elif source.exists() and shared.exists():
                    state = "pending_link"
                elif source.exists() and not shared.exists():
                    state = "pending_migration"
                elif not source.exists() and shared.exists():
                    state = "missing_local"
                else:
                    state = "missing_both"
            rows.append({"folder_name": folder_name, "kind": "folder", "state": state})
        for file_name in emu.get("important_files", []):
            if not emu_path:
                state = "no_path"
            else:
                src = emu_path / file_name
                dst = shared_emu_dir / ROOT_FILES_DIRNAME / file_name
                try:
                    if not src.is_file():
                        state = "file_missing"
                    elif not dst.is_file():
                        state = "file_pending"
                    else:
                        state = "file_ok" if _file_backup_is_current(src, dst) else "file_outdated"
                except OSError:
                    state = "file_missing"
            rows.append({"folder_name": file_name, "kind": "file", "state": state})
        report[name] = rows
    return report


def _backup_or_skip(backup: BackupSession, source: Path, folder_name: str, log) -> bool:
    """Respalda la carpeta antes de reemplazarla. Si el backup falla, la
    carpeta NO se toca: se informa y se sigue con la siguiente."""
    try:
        path = backup.add(source)
    except Exception as e:
        log(tr("log.backup_failed", folder=folder_name, error=e), LOG_ERROR)
        return False
    log(tr("log.backup_added", folder=folder_name, path=path), LOG_OK)
    return True


def sync_emulator(name: str, emu_config: Dict, shared_dir: Path, options: Dict,
                   log, is_cancelled) -> bool:
    emu_path = get_emulator_path(emu_config)

    if not emu_path:
        log(tr("log.no_path", name=name, platform=PLATFORM_KEY), LOG_ERROR)
        return False

    if not emu_path.exists():
        log(tr("log.emu_dir_created", path=emu_path), LOG_INFO)
        if not options.get("dry_run"):
            emu_path.mkdir(parents=True, exist_ok=True)

    folders = emu_config.get("important_folders", [])
    files = emu_config.get("important_files", [])
    if not folders and not files:
        log(tr("log.nothing_configured", name=name), LOG_WARN)
        return True

    shared_emu_dir = shared_dir / name
    if not shared_emu_dir.exists() and not options.get("dry_run"):
        shared_emu_dir.mkdir(parents=True, exist_ok=True)

    backup = BackupSession(shared_dir, name, options.get("zip_backup", True))
    try:
        ok = _sync_folders(folders, emu_path, shared_dir, shared_emu_dir, options, log,
                           is_cancelled, backup)
    finally:
        backup.close()
    if backup.path is not None:
        rotate_backups(backup.root, options.get("max_backups", 0), shared_dir)
    if ok is None:          # cancelado
        return False

    if files:
        ok = backup_root_files(emu_path, shared_emu_dir, files, options.get("dry_run", False), log) and ok

    return ok


def _sync_folders(folders: List[str], emu_path: Path, shared_dir: Path, shared_emu_dir: Path,
                  options: Dict, log, is_cancelled, backup: BackupSession) -> Optional[bool]:
    """Enlaza cada carpeta. Devuelve True/False según haya errores, o None si
    el usuario canceló."""
    ok = True
    for folder_name in folders:
        if is_cancelled():
            log(tr("log.cancelled"), LOG_WARN)
            return None

        source = emu_path / folder_name
        shared = shared_emu_dir / folder_name

        if is_placeholder_link(source):
            # Son ~34 bytes de texto sin datos reales: se quitan para poder
            # poner el enlace verdadero en su lugar.
            if options.get("dry_run"):
                log(tr("log.dry_placeholder", folder=folder_name), LOG_INFO)
                continue
            try:
                source.unlink()
            except OSError as e:
                log(tr("log.placeholder_remove_failed", folder=folder_name, error=e), LOG_ERROR)
                ok = False
                continue
            log(tr("log.placeholder_removed", folder=folder_name), LOG_WARN)

        if is_link_like(source):
            try:
                current_target = source.resolve(strict=False)
            except OSError:
                current_target = None
            shared_resolved = shared.resolve(strict=False)

            if current_target is not None and _same_path(current_target, shared_resolved):
                log(tr("log.already_linked", folder=folder_name), LOG_INFO)
                continue

            # El enlace existe pero apunta a OTRA carpeta compartida —
            # típicamente porque se cambió la carpeta compartida y quedaron
            # los enlaces viejos apuntando al lugar anterior. Se reubica:
            # se migran los datos reales (si están accesibles) a la nueva
            # carpeta compartida y se recrea el enlace apuntando ahí.
            log(tr("log.relocating", folder=folder_name, current=current_target, shared=shared), LOG_WARN)

            old_target_exists = current_target is not None and current_target.exists()

            if options.get("dry_run"):
                if old_target_exists and not shared.exists():
                    log(tr("log.dry_migrate", src=current_target, dst=shared), LOG_INFO)
                log(tr("log.dry_relink", folder=folder_name, dst=shared), LOG_INFO)
                continue

            if old_target_exists and not shared.exists():
                shared.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(current_target), str(shared))
                log(tr("log.migrated_new_shared", path=shared), LOG_OK)
            elif old_target_exists and shared.exists():
                log(tr("log.both_shared_have_data", folder=folder_name, old=current_target, new=shared), LOG_WARN)
            else:
                shared.mkdir(parents=True, exist_ok=True)
                log(tr("log.old_shared_unreachable", folder=folder_name, new=shared), LOG_WARN)

            try:
                remove_link(source)
            except OSError as e:
                log(tr("log.unlink_old_failed", folder=folder_name, error=e), LOG_ERROR)
                ok = False
                continue

            link_ok, msg = create_symlink(shared, source, shared_dir, False)
            log(msg, LOG_OK if link_ok else LOG_ERROR)
            if not link_ok:
                ok = False
            continue

        source_exists = source.exists()
        shared_exists = shared.exists()

        if not shared_exists:
            if source_exists and options.get("copy_missing"):
                if options.get("backup") and not options.get("dry_run"):
                    if not _backup_or_skip(backup, source, folder_name, log):
                        ok = False
                        continue
                if options.get("dry_run"):
                    log(tr("log.dry_copy", src=source, dst=shared), LOG_INFO)
                else:
                    shutil.copytree(source, shared)
                    log(tr("log.migrated", folder=folder_name), LOG_OK)
            elif not source_exists:
                if not options.get("dry_run"):
                    shared.mkdir(parents=True, exist_ok=True)
                log(tr("log.created_empty_shared", folder=folder_name), LOG_INFO)
            else:
                log(tr("log.local_not_shared", folder=folder_name, option=tr("opt.copy_missing")), LOG_WARN)
                ok = False
                continue
        elif source_exists:
            # Ya existe una versión real y distinta en compartido: se hace backup
            # de la carpeta local ANTES de reemplazarla por el enlace, para no
            # perder datos (esto faltaba en la versión original del script).
            if options.get("backup") and not options.get("dry_run"):
                if not _backup_or_skip(backup, source, folder_name, log):
                    ok = False
                    continue

        link_ok, msg = create_symlink(shared, source, shared_dir, options.get("dry_run", False))
        log(msg, LOG_OK if link_ok else LOG_ERROR)
        if not link_ok:
            ok = False

    return ok


def _file_backup_is_current(src: Path, dst: Path) -> bool:
    s, d = src.stat(), dst.stat()
    return s.st_size == d.st_size and s.st_mtime <= d.st_mtime


def backup_root_files(emu_path: Path, shared_emu_dir: Path, files: List[str],
                      dry_run: bool, log) -> bool:
    """Los archivos sueltos de la raíz (settings.ini, Config.json…) no se
    pueden enlazar: un junction solo sirve para carpetas y un symlink de
    archivo pide admin en Windows. Se copian a <compartida>/<emu>/_archivos
    cada vez que se sincroniza, solo si cambiaron. El original no se toca."""
    ok = True
    dest_dir = shared_emu_dir / ROOT_FILES_DIRNAME
    for file_name in files:
        src = emu_path / file_name
        dst = dest_dir / file_name
        if not src.is_file():
            log(tr("log.file_missing", file=file_name, path=emu_path), LOG_WARN)
            continue
        try:
            if dst.is_file() and _file_backup_is_current(src, dst):
                log(tr("log.file_current", file=file_name), LOG_INFO)
                continue
            if dry_run:
                log(tr("log.dry_copy", src=src, dst=dst), LOG_INFO)
                continue
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            log(tr("log.file_backed", file=file_name, dst=dst), LOG_OK)
        except OSError as e:
            log(tr("log.file_copy_error", file=file_name, error=e), LOG_ERROR)
            ok = False
    return ok
