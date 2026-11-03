# EmuLinks (Python / PySide6-PySide2)

Centraliza los datos de tus emuladores (saves, config, bios) en una carpeta
compartida, dejando en su lugar un enlace simbólico / junction. Portado del
script original en PyQt5 y de la versión Electron. La interfaz sigue el
`Prompt_Diseno_PySide6-PySide2_v5_2.md`: temas Grafito/Papel, español e
inglés, ayuda contextual en cada control.

## Descarga (portable)

En [Releases](https://github.com/EstebanKZL/EmuLinks/releases) hay un único
ejecutable por sistema; no hace falta instalar Python:

| Archivo | Sistema |
|---|---|
| `EmuLinks-windows-x64.exe` | Windows 10/11 64 bits |
| `EmuLinks-windows-x86.exe` | Windows 7/8/10 32 bits (Qt 5) |
| `EmuLinks-linux-x86_64.AppImage` / `EmuLinks-linux-x64.tar.gz` | Linux 64 bits (glibc 2.35+, p. ej. Ubuntu 22.04+) |
| `EmuLinks-linux-i686.AppImage` / `EmuLinks-linux-x86.tar.gz` | Linux 32 bits (Qt 5, glibc 2.36+, p. ej. Debian 12) |

En Linux, el AppImage: `chmod +x EmuLinks-linux-*.AppImage && ./EmuLinks-linux-*.AppImage`
(si tu distro no tiene FUSE: agregá `--appimage-extract-and-run`).
El tar.gz: `tar xzf EmuLinks-linux-*.tar.gz && ./EmuLinks`.

## Cómo correrlo

```bash
pip install -r requirements.txt   # PySide6 (Windows 10/11 / Linux, Python 3.10+)
# pip install PySide2             # Windows 7, Python 3.8

python main.py                    # o: python -m emulinks
```

No tiene más dependencias externas: los enlaces se hacen con `os`/`pathlib`,
los backups con `zipfile`/`shutil` (todo librería estándar).

## Empaquetado a .exe

```bash
pip install pyinstaller
pyinstaller --noconsole --onefile --name EmuLinks main.py
```

Los 4 ejecutables de Releases los arma GitHub Actions
(`.github/workflows/build.yml`): cada push a `main` corre los tests y deja los
binarios como artefactos; un tag `vX.Y` además publica la Release.

## Qué tiene

Paquete `emulinks/` en módulos (detalle en `CLAUDE.md`): `core/` es la lógica
sin Qt (config, enlaces, detección) y se prueba sin pantalla; `ui/` es la
interfaz; `locales/` tiene los textos en español e inglés.

Interfaz según el prompt de diseño v5.3:

- Capa de compatibilidad automática PySide6/PySide2 (usa lo que esté instalado).
- Temas **Grafito** (oscuro) y **Papel** (claro), y **español / inglés**
  (primer inicio según el idioma del sistema), persistentes vía
  `QSettings("EstebanCasales", "EmuLinks")`; se aplican al reiniciar — menú **Ver**.
- Encabezado con badge de estado, fila de KPIs (enlazado / pendiente /
  problemas), tarjetas, tabla de estado con estado vacío y log con colores por nivel.
- Tooltips con título y explicación en cada control, también en la barra de estado.
- Ventana 1280×720 mínimo.

Funcionalmente es la misma app que la versión Electron que armamos antes:

- **Enlaces simbólicos / junctions**: en Windows usa `mklink /J` (no requiere
  admin), en Linux/macOS `symlink_to`.
- **Backup de seguridad antes de enlazar**, siempre que la opción esté activa
  — no solo cuando se migra una carpeta nueva (ese era el bug real del script
  original en PyQt5: borraba sin backup si la carpeta compartida ya tenía datos).
- **Los backups nunca se pisan entre sí**: si dos corren en el mismo segundo,
  se agrega un sufijo `_2`, `_3`... en vez de sobreescribir el anterior (bug
  que encontré y corregí durante las pruebas de esta versión, y que también
  arreglé en la versión Electron).
- **Backups ordenados**: todo lo que se respalda de un emulador en una
  sincronización va a **un solo zip** en `Backup-EmuLinks/<emulador>/` dentro
  de la carpeta compartida. Si un backup falla, esa carpeta no se toca.
- **Rotación de backups** (`Backups a conservar por emulador`).
- **Verificar estado**: escaneo de solo lectura, no modifica nada.
- **Restaurar backups**: doble clic en un emulador de la lista.
- La verificación de estado corre sola al abrir (es de solo lectura).
- **Autodetectar**: 23 emuladores, rutas estándar + Flatpak +
  **instalaciones portables en todos los discos**, agrupadas **por unidad**.
  Cada grupo se tilda en 3 estados: nada / lo recomendado / todo. Lista *todas* las carpetas
  y archivos de datos clasificados (partidas, BIOS/keys, logros, config,
  caché…) en un árbol con casillas; lo desconocido aparece como "Sin
  clasificar", nunca se esconde. Ver `EMULATOR_DB` en el código.
- **Archivos sueltos** (`settings.ini`, `Config.json`…): se copian a
  `<compartida>/<emu>/_archivos` en cada sincronización.
- **Repara enlaces dañados** ("IntxLNK": archivos de 34 bytes que quedan en
  lugar de un junction al copiar con ciertas herramientas).
- **Nunca borra la carpeta compartida**: `assert_safe_to_remove()` se llama
  antes de cualquier borrado (al reemplazar una carpeta local por el enlace,
  al rotar backups viejos) y frena la operación si el destino es la carpeta
  compartida o la contiene.
- Config en JSON en `%APPDATA%\EmuLinks\config.json` (Windows) /
  `~/.config/EmuLinks/config.json` (Linux/macOS) — se autorepara si queda
  vacía o corrupta, sin diálogos bloqueantes que puedan colgar el arranque.

## Pruebas automáticas

```bash
python tests/test_emulinks.py
```

Corren en carpetas temporales con una config aislada, incluida una prueba de
humo que arma la ventana completa sin pantalla. Para colaborar, leé `CLAUDE.md`; lo pendiente
está en `ROADMAP.md`.

## Probado

Corrí la app en modo offscreen (sin pantalla) para confirmar que arranca sin
errores, y probé de punta a punta: sincronización con migración, backup antes
de reemplazar un enlace, verificación de estado, restauración de un backup, y
el guardarraíl que bloquea cualquier intento de borrar la carpeta compartida.
