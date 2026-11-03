# CLAUDE.md — EmuLinks

Guía para quien trabaje en este repo (personas o Claude Code). Leela antes de
tocar código. Comentarios y textos en español los escribimos en **rioplatense**
("tildá", "revisalo"); la interfaz es **bilingüe ES/EN**.

## Qué es

App de escritorio PySide6/PySide2 que centraliza los datos de los emuladores
(partidas, BIOS/keys, config, logros) en una **carpeta compartida** y deja en
el lugar original un **junction** (Windows, `mklink /J`, sin admin) o symlink
(Linux/macOS). Objetivo #1: **no perder nunca saves, logros ni config.**

La interfaz sigue el **Prompt de Diseño PySide6/PySide2 v5.3** del autor
(temas Grafito/Papel, `tr()`, `set_help()`, tarjetas, badges, KPIs). Si el
prompt se actualiza, el estilo se cambia en `emulinks/ui/theme.py` y
`emulinks/ui/widgets.py`, que son copia de sus secciones: `THEMES` y
`build_stylesheet()` deben quedar **idénticos** al prompt. Lo propio de
EmuLinks va aparte, en la sección "EXTRAS DE EMULINKS" de `theme.py`
(hoy: el estado parcial de las casillas de 3 estados, que el prompt no
estiliza) y se suma al QSS en la misma y única llamada a `app.setStyleSheet()`.

## Cómo correrlo y probarlo

```bash
pip install -r requirements.txt   # PySide6 (Win 10/11 / Linux). PySide2 para Win 7
python main.py                    # o: python -m emulinks
python tests/test_emulinks.py     # o: python -m pytest tests -q
```

- Las pruebas usan carpetas temporales y una config aislada. **Nunca** pruebes
  la sincronización contra carpetas reales de emuladores ni contra la config
  real (`%APPDATA%\EmuLinks\config.json`).
- `detect_installations()` y `check_status()` son de solo lectura: se pueden
  correr sobre la PC real.
- GUI sin pantalla: `QT_QPA_PLATFORM=offscreen` y, para que haya fuentes,
  `QT_QPA_FONTDIR=C:/Windows/Fonts`. El tema/idioma salen de `QSettings`; para
  capturas sin tocar las preferencias del usuario, reemplazá
  `emulinks.ui.qt.QSettings` por un stub **antes** de importar `emulinks.ui.theme`.
- Empaquetado:
  `pyinstaller --noconsole --onefile --name EmuLinks --collect-data PySide6 main.py`
  (`--collect-data` trae las traducciones de los diálogos de Qt).

## Estructura

```
main.py                     lanzador / entrada de PyInstaller
emulinks/
  __init__.py               APP_NAME, APP_VERSION, autor
  app.py                    main(): HighDPI, QApplication, setup_appearance, ventana
  i18n.py                   tr(), tr_opt(), set_language(), check_translations() — SIN Qt
  locales/es.py, en.py      STRINGS por idioma (mismas claves)
  core/                     lógica SIN Qt, testeable
    __init__.py             niveles de log: LOG_OK / LOG_ERROR / LOG_WARN / LOG_INFO
    system.py               IS_WINDOWS…, PLATFORM_KEY
    config.py               rutas, _default_config, load_config (se autorepara), save_config
    fs.py                   enlaces, backups, check_status, sync_emulator, backup_root_files
    emulators_db.py         EMULATOR_DB, categorías
    detection.py            candidate_paths, scan_install, find_portable_installs,
                            detect_installations, apply_detection
  ui/                       PySide6/PySide2
    qt.py                   capa de compatibilidad (único lugar que importa PySide)
    theme.py                SP, THEMES, THEME, idioma, fuentes, íconos, paleta, QSS, setup_appearance
    widgets.py              set_help, make_card/badge/kpi/log_view/empty_state, DotGripWidget
    workers.py              SyncWorker, DetectWorker (QThread + Signal)
    dialogs.py              DetectDialog, EmulatorDialog, RestoreBackupDialog
    main_window.py          EmuLinksWindow
tests/test_emulinks.py
```

Dependencias permitidas: `core` y `i18n` **no importan nada de `ui`** ni de Qt.
`ui` importa de `core`. Orden de import en la UI: `qt → theme → widgets →
workers → dialogs → main_window` (`theme` resuelve `THEME` y el idioma al
importarse, antes de crear cualquier widget).

Formato de un emulador en la config:

```json
"rpcs3": {
  "windows": "E:\\Emus\\RPCS3", "linux": "...", "mac": "...",
  "important_folders": ["dev_hdd0", "config"],
  "important_files": ["config.yml"]
}
```

Carpeta compartida: `<shared_dir>/<id>/<carpeta>`; archivos sueltos en
`<shared_dir>/<id>/_archivos/`; backups en
`<shared_dir>/Backup-EmuLinks/<id>/<id>_<fecha>.zip` — **un zip por emulador y
por sincronización**, con una subcarpeta por cada carpeta respaldada
(`BackupSession` en `core/fs.py`). La rotación cuenta backups por emulador.
`list_backups()` también lee el formato viejo (`<carpeta>_backup_<fecha>.zip`
junto a cada carpeta) para poder restaurarlo.

`config.json` se escribe vía temporal + `os.replace`, y la versión anterior
queda en `config.prev.json`.

## Reglas de seguridad de datos (no negociables)

1. **Antes de cualquier `rmtree`/`unlink` de carpetas** se llama a
   `assert_safe_to_remove(target, shared_dir)`. Nunca se borra la carpeta
   compartida ni algo que la contenga.
2. **Nunca uses `Path.is_symlink()` solo**: en Windows no detecta junctions.
   Usá `is_link_like()`. Para quitar un enlace usá `remove_link()`, jamás
   `rmtree` (recorrería el enlace y borraría los datos reales).
3. Backup **antes** de reemplazar una carpeta real por un enlace, si la opción
   está activa. Los backups nunca se pisan (`_unique_backup_path`).
4. `dry_run` (modo simulación) no puede tocar el disco: toda rama nueva de
   `sync_emulator` tiene que respetarlo y tener su prueba.
5. La detección **solo agrega** a la config (`_union_ci`), nunca quita.
6. Lo desconocido se muestra, no se esconde: una carpeta que no está en
   `EMULATOR_DB` aparece como "Sin clasificar".
7. Para leer la salida de `cmd` en Windows usá `encoding="oem"` en
   `subprocess.run` (cmd no escribe en UTF-8).
8. Si `config.json` está corrupto se guarda una copia `config.corrupt_*.json`
   antes de reponer los valores por defecto.
9. **Si el backup de una carpeta falla, esa carpeta no se reemplaza por el
   enlace** (`_backup_or_skip`). Nunca borrar sin backup cuando la opción está activa.
10. Los tests aíslan `CONFIG_PATH` **y** `LOG_DIR` (`_IsolatedConfig`).
11. Los botones de acción se ven como botones: no usar `btnGhost` para
    acciones (decisión del autor, v6.1), solo botón neutro o semántico.

## Reglas de interfaz (resumen del Prompt v5.3)

- **Todo texto visible sale de `tr("clave")`**, también el log y los errores
  del núcleo. Clave nueva = agregarla en `locales/es.py` **y** `locales/en.py`
  a la vez (el test `test_translations_complete_and_db_keys_exist` falla si no).
  Parámetros con nombre (`tr("log.migrated", folder=x)`), nunca concatenar.
- El color del log va por **nivel** (`log(text, LOG_WARN)`), nunca buscando
  palabras en el texto. Los callbacks de log del núcleo reciben `(texto, nivel)`.
- Colores siempre `THEME["clave"]`; espaciados de `SP`; estilos por
  `objectName` (`btnPrimary`, `btnStart`, `btnStop`, `btnGhost`, `card`,
  `badge*`, `lblHint`…). Nada de `setStyleSheet` inline salvo el padding del
  label de la status bar, ni hex sueltos, ni emojis/símbolos decorativos.
- Una sola acción `btnPrimary` por tarjeta/zona.
- Todo control interactivo lleva `set_help(widget, "clave")` → `tip.clave`
  (y `tip.clave.title` si no es un botón/checkbox). Máx. ~140 caracteres,
  verbo al inicio, aclarar si es lento o irreversible.
- Tablas/listas vacías muestran `make_empty_state()` vía `QStackedWidget`.
- Árbol del detector: unidad → emulador → carpetas/archivos. Los grupos usan
  `Qt.ItemIsUserTristate` con significado propio: vacío = nada, cuadrado =
  lo recomendado (`ROLE_RECOMMENDED` de cada hoja), tilde = todo. El estado
  visible de un grupo siempre se recalcula desde sus hojas (`_refresh_group`).
- Tema e idioma se cambian desde *Ver* y se aplican al reiniciar; nunca en caliente.
- Ventana 1280×720 mínima. `_exec()` y `_global_pos()` en vez de `exec()`/`globalPos()`.

## Cómo agregar un emulador

1. Agregá una entrada a `core/emulators_db.py` con `_emu(...)` (o
   `_switch_fork` / `_3ds_fork`). Claves de `folders` en **minúsculas**.
2. Rutas con plantillas: `{APPDATA}`, `{LOCALAPPDATA}`, `{DOCUMENTS}`,
   `{XDG_CONFIG}`, `{XDG_DATA}`, `{MAC_AS}`, `{HOME}`. Con Flatpak, poné
   `flatpak="org.x.Y"` y las variantes se generan solas.
3. Regla portable: `{"exe": ["nombre*.exe"], "marker": "portable.txt" | None,
   "data": "subcarpeta" | "", "unless": "installed.txt"}`. Patrones en minúsculas.
4. `notes` y `warning` son **claves** (`note.*`, `warn.*`): agregá el texto en
   los dos idiomas.
5. Comentá de dónde sacaste las rutas (doc oficial, EmuDeck, probado) y agregá
   una prueba si tiene una regla nueva.

## Trabajo en equipo

- Repo público en GitHub: `EstebanKZL/EmuLinks`, rama principal `main`.
  Para sumar colaboradores: *Settings → Collaborators* en GitHub.
- Commits firmados como `EstebanKZL <89585806+EstebanKZL@users.noreply.github.com>`
  (sin mail personal). Cada colaborador usa su propio noreply de GitHub.
- CI y builds: `.github/workflows/build.yml` corre `tests/` y compila
  Windows x64/x86 y Linux x64/x86 en cada push. Release: subí `APP_VERSION`,
  `git tag vX.Y && git push origin vX.Y`. Los 32 bits usan PySide2 (Qt 5): no
  uses API exclusiva de PySide6 ni sintaxis de Python > 3.10 (f-strings 3.12).
  `.gitignore` excluye `config.json`, backups y builds; `.gitattributes`
  fuerza LF para todos.
- Una rama por tarea (`feat/…`, `fix/…`), PR con descripción y resultado de
  `python tests/test_emulinks.py`. No mezclar refactors grandes con features.
- Antes de empezar algo de `ROADMAP.md`, marcalo en curso con tu nombre.
- Subí `APP_VERSION` (en `emulinks/__init__.py`) en cambios visibles.
- No subas configs personales (`config.json`) ni rutas de tu PC a la base de
  emuladores: usá las plantillas.
