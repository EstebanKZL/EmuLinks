# EmuLinks — análisis y hoja de ruta

Estado al 2026-11-03 (v6.2). Este documento resume qué se encontró al analizar
el proyecto y qué conviene hacer después, ordenado por impacto. Marcá con `[x]`
lo que se vaya haciendo y agregá tu nombre/fecha, así otros colaboradores saben
en qué está cada cosa.

---

## 1. Hecho en la v5.1

- [x] **Autodetector nuevo** (`EMULATOR_DB` + `detect_installations`):
  23 emuladores (Eden, Citron, Sudachi, suyu, yuzu, Ryujinx, DuckStation,
  PCSX2, RPCS3, shadPS4, PPSSPP, Vita3K, Azahar, Citra, Lime3DS, Cemu,
  Dolphin, melonDS, mGBA, xemu, Xenia, Flycast, RetroArch, MAME, ScummVM).
  - Rutas estándar por plataforma + variantes **Flatpak** en Linux.
  - Carpeta **Documentos real** (respeta la redirección a OneDrive/otro disco).
  - **Instalaciones portables** en todos los discos fijos y USB (profundidad 4),
    `SteamLibrary`, `scoop`, `%LOCALAPPDATA%\Programs` y carpetas de búsqueda
    extra que el usuario agrega desde el diálogo (se guardan en
    `options.search_roots`).
  - Clasifica **cada** carpeta (BIOS/keys, partidas, logros, states, config,
    mods, capturas, caché, juegos). Lo desconocido **no se descarta**: aparece
    como "Sin clasificar" para que el usuario decida.
  - Diálogo con árbol y casillas por carpeta/archivo; escaneo en un hilo.
  - Si una carpeta ya está configurada, solo **suma** lo nuevo, nunca quita.
- [x] **Archivos sueltos** (`important_files`): `settings.ini`, `Config.json`,
  `retroarch.cfg`, `config.yml`… no se pueden enlazar con un junction, así que
  se copian a `<compartida>/<emu>/_archivos` en cada sincronización (solo si
  cambiaron). "Verificar estado" los muestra.
- [x] **Enlaces dañados "IntxLNK"**: se detectan y la sincronización los repara.
  Son archivos de 34 bytes que quedan en lugar de un junction cuando la carpeta
  se copia con una herramienta que no entiende reparse points. En esta PC
  aparecieron en RPCS3 y RetroArch de `E:` y `H:`: esos emuladores **no veían**
  sus partidas en la carpeta compartida.
- [x] Bug: la config **no se guardaba** al añadir, editar, borrar o autodetectar
  (solo al sincronizar). Ahora se guarda en cada cambio y al cerrar.
- [x] Bug: `assert_safe_to_remove` comparaba rutas sensible a mayúsculas; en
  Windows `E:\Emu` y `e:\emu` podían esquivar el guardarraíl.
- [x] Bug: la salida de `mklink` se decodificaba como UTF-8 (cmd usa cp850) →
  el hilo lector se caía y el mensaje de error de mklink se perdía.
- [x] Bug: cerrar la ventana durante una sincronización destruía el hilo a mitad
  de un `rmtree`. Ahora pide confirmación, cancela y espera.
- [x] Bug: guardar opciones pisaba claves sin control en la UI (`search_roots`).
- [x] Pruebas automáticas en `tests/` (todo en carpetas temporales).

## 1b. Hecho en la v6.0

- [x] **Separado en módulos**: `emulinks/core` (sin Qt), `emulinks/ui`,
  `emulinks/locales`, lanzador `main.py`. Ver `CLAUDE.md`.
- [x] **Diseño v5.1**: temas Grafito/Papel, encabezado con badge, KPIs,
  tarjetas, estados vacíos, log monoespaciado con colores por nivel, íconos de
  checkbox/flechas generados, cursor de mano, grip en la status bar.
- [x] **Español e inglés** con `tr()` en toda la UI, el log y los errores del
  núcleo; *Ver → Idioma*; diálogos de Qt traducidos.
- [x] **Ayuda contextual** (`set_help`) en todos los controles, encabezados y
  estados de la tabla.
- [x] Verificación de estado automática al abrir; opciones que se guardan solas.
- [x] Copia de seguridad de `config.json` si está corrupto antes de reponerlo.

## 1c. Hecho en la v6.1

- [x] Tema Papel del prompt v5.2 (gris cálido, bordes visibles, texto ≥ 12 px).
- [x] Botones "fantasma" pasan a botones normales (Abrir carpeta, Todos,
  Ninguno, Limpiar log, Agregar carpeta de búsqueda).
- [x] Detector agrupado **por unidad** (con etiqueta de volumen) y casillas de
  3 estados en ciclo: nada → recomendado → todo. Segunda copia en otro disco
  toma la letra en el id (`rpcs3_h`).
- [x] **Backups en un solo zip** por emulador y sincronización, en
  `<compartida>/Backup-EmuLinks/<emulador>/`. Restaurar lee el formato nuevo y el viejo.
- [x] Si un backup falla, la carpeta no se reemplaza por el enlace.
- [x] Un error inesperado en un emulador ya no deja la UI trabada en "Sincronizando…".
- [x] `config.json` con escritura atómica y copia `config.prev.json`.

## 1d. Hecho en la v6.2

- [x] Tema Papel del prompt v5.3: blanco grisáceo neutro (sin tinte marrón).
- [x] Borde `control_border` en todas las casillas, también dentro de listas
  y del árbol del detector.
- [x] Estado parcial ("lo recomendado") visible: cuadradito color acento.

## 2. Riesgos de datos todavía abiertos (prioridad alta)

- [ ] **Juegos con partidas junto a la ROM** (melonDS, mGBA, Snes9x, Mesen…):
  el detector avisa, pero EmuLinks no las protege. Idea: opción "carpeta de
  ROMs" por emulador y copiar solo `*.sav/*.srm` a `_archivos/saves`.
- [ ] **Instalaciones duplicadas** (en esta PC `H:` "Disco_Backup" es una copia
  de `E:`): ya se ven separadas por unidad; falta destildar sola la copia
  ("misma estructura que X") para no crear dos carpetas compartidas.
- [ ] **Ordenar backups viejos**: mover los `<carpeta>_backup_*.zip` sueltos
  dentro de las carpetas de los emuladores a `Backup-EmuLinks`.
- [ ] **Versionado de `_archivos`**: hoy la copia se pisa con la versión más
  nueva; si el emulador corrompe `settings.ini`, la copia buena se pierde.
  Guardar las últimas N versiones con fecha.
- [ ] **Restaurar `_archivos`** desde la UI (hoy hay que copiar a mano).
- [ ] **Comprobar espacio libre** antes de migrar/zipear (`shutil.disk_usage`);
  `dev_hdd0` o `ux0` pueden pesar decenas de GB.
- [ ] **Emulador abierto durante la sincronización**: detectar el proceso
  (`tasklist`/`psutil`) y frenar, para no mover carpetas en uso.
- [ ] **Verificación post-migración**: comparar cantidad y tamaño de archivos
  (o hash) entre origen y compartida antes de borrar el original.
- [ ] Linux: los forks de yuzu guardan la config aparte en `~/.config/<emu>`;
  hoy solo se detecta la carpeta de datos.

## 3. Funcionalidades nuevas (valor alto)

- [ ] **Modo "solo respaldo"** (sin enlaces): snapshot programado de todas las
  carpetas a un ZIP con fecha, para quien no quiere junctions.
- [ ] **Programador**: sincronizar/respaldar al iniciar sesión o cada X horas
  (Programador de tareas de Windows / systemd timer), con CLI `--sync --quiet`.
- [ ] **CLI** (`python emulinks.py detect|status|sync --json`): habilita
  automatización y pruebas sin GUI.
- [ ] **Exportar / importar perfil**: un `.emulinks.json` con rutas relativas a
  la carpeta compartida para replicar todo en otra PC en un clic.
- [ ] **Nube/NAS**: validar que la compartida esté en OneDrive/Dropbox/Syncthing
  y advertir de conflictos (`* (1).sav`, `.sync-conflict`).
- [ ] **Explorador de partidas por juego**: leer `nand/user/save`, `memcards`,
  `dev_hdd0/home/*/savedata` y mostrar título, fecha y tamaño.
- [ ] **Logros**: mostrar trofeos de RPCS3/Vita3K, tiempo de juego de los forks
  de yuzu, y usuario de RetroAchievements configurado en cada emulador.
- [ ] **Base de emuladores en JSON externo** (`emulators.json`) actualizable sin
  recompilar el .exe, con la versión de la base visible en "Acerca de".

## 4. Interfaz

- [ ] Badges por estado dentro de la tabla (hoy: texto en color semántico).
- [ ] Panel de detalle al seleccionar un emulador: rutas, tamaño por carpeta,
  último backup, botón "Abrir carpeta".
- [ ] Filtro/búsqueda en la tabla de estado y botón "Reparar todo lo dañado".
- [ ] Barra de progreso por carpeta (no solo por emulador) con MB copiados.
- [ ] Bajar el mínimo de 1280×720 o hacer el panel izquierdo colapsable para
  notebooks con escalado al 150 %.
- [x] Traducción ES/EN (v6.0). Para sumar un idioma: `locales/<código>.py` +
  `LANGUAGES` en `i18n.py`.

## 5. Código y mantenimiento

- [x] **Partir `emulinks.py`** en paquete `core/` + `ui/` + `locales/` (v6.0).
- [ ] `ui/main_window.py` (~800 líneas) se puede seguir partiendo: una clase
  por tarjeta (carpeta compartida, emuladores, estado).
- [x] **Git + GitHub**: repo público `EstebanKZL/EmuLinks` (v6.2).
- [x] CI (GitHub Actions): tests + builds portables Windows/Linux x64/x86 y Release por tag (v6.2).
- [x] AppImage x86_64/i686 y builds sin `--collect-data PySide6` (~4 veces más chicos) (v6.3).
- [ ] Logging a archivo (`logs/sync-YYYYMMDD.log`) además de la consola.
- [ ] Build reproducible del .exe: `EmuLinks.spec` de PyInstaller con icono,
  versión del archivo, `--noconsole` y `--collect-data PySide6` (hoy se arma a
  mano con el comando del README).
