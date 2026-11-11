# Cómo colaborar en EmuLinks

¡Gracias por querer ayudar! EmuLinks centraliza los datos de los emuladores
(partidas, BIOS/keys, config, logros) en una carpeta compartida y deja un
enlace en el lugar original. **Objetivo #1: no perder nunca saves, logros ni
config.** Todo lo demás viene después.

Comentarios y textos en español los escribimos en rioplatense ("tildá",
"revisalo"); la interfaz es bilingüe ES/EN.

## Poner a andar el proyecto

```bash
pip install -r requirements.txt -r requirements-dev.txt   # PySide6 (Windows 10/11 / Linux)
python main.py                    # o: python -m emulinks
python -m pytest tests -q         # o: python tests/test_emulinks.py
```

Para la línea Windows 7/8 y los 32 bits: Python 3.8 + `requirements-legacy.txt` (PySide2).

- Las pruebas corren en carpetas temporales con una config aislada. **Nunca**
  pruebes la sincronización contra carpetas reales de emuladores ni contra tu
  config real (`%APPDATA%\EmuLinks\config.json`).
- `detect_installations()` y `check_status()` son de solo lectura: se pueden
  correr sobre la PC real sin riesgo.

## Antes de mandar un cambio

- **Una rama por tarea** (`feat/…`, `fix/…`) y un Pull Request contra `main`,
  aunque trabajes solo: deja el historial limpio y el CI valida antes de mezclar.
- **Que pasen los tests** (`pytest`) y, si tocás algo visible, agregá o ajustá
  una prueba. El CI corre los tests con Python 3.8 (PySide2) y 3.12 (PySide6),
  compila todo con Nuitka y prueba que cada ejecutable arranque.
- **Compatibilidad con Windows 7/8:** los 32 bits y Windows 7 usan PySide2
  (Qt 5) y **Python 3.8**. No uses API exclusiva de PySide6 ni sintaxis o
  librería de Python posterior a 3.8. Chequeo rápido:
  `pip install vermin && vermin -t=3.8- --violations emulinks`.
- **Subí la versión en `VERSION`** (fuente única, SemVer `MAYOR.MENOR.PARCHE`)
  cuando el cambio sea visible, y sumá una entrada en `CHANGELOG.md`.
- **Mensajes de commit** neutros y técnicos, en presente ("Agrega…",
  "Corrige…").

## Reglas de seguridad de datos (no negociables)

Cualquier cambio que toque enlaces, backups o borrado tiene que respetarlas:

1. Antes de borrar una carpeta se llama a `assert_safe_to_remove(...)`: nunca se
   toca la carpeta compartida ni algo que la contenga.
2. En Windows, `Path.is_symlink()` **no** detecta junctions: usá
   `is_link_like()` y, para quitar un enlace, `remove_link()` (nunca `rmtree`).
3. Backup **antes** de reemplazar una carpeta real por un enlace. Si el backup
   falla, la carpeta no se toca.
4. El modo simulación (`dry_run`) no puede tocar el disco.
5. La detección solo **agrega** a la config, nunca quita.

## Interfaz

La interfaz sigue un sistema de diseño propio: todo texto sale de
`tr("clave")` (agregá la clave en `locales/es.py` **y** `locales/en.py`),
colores desde `THEME`, espaciados desde `SP`, y cada control interactivo lleva
`set_help(...)`. Para agregar un emulador, mirá `core/emulators_db.py`.

## Compilar y publicar

Los ejecutables se arman en GitHub Actions (`.github/workflows/build.yml`) con
**Nuitka**: el Python se compila a binario, sin `.py` ni `.pyc` legibles. Cada
push compila y prueba sin publicar; un tag `vX.Y.Z` (igual a `VERSION`) publica
el Release con `SHA256SUMS.txt` y las notas del `CHANGELOG.md`. Para compilar a
mano en Windows:

```bash
pip install -r requirements.txt -r requirements-build.txt
python scripts/build.py            # dist/release: portable .zip + instalador (con Inno Setup)
```

El ícono maestro es `assets/icon.svg`; si lo cambiás, corré
`python scripts/make_icons.py` y versioná los `.ico`/`.png` que genera.

## Privacidad

- No subas tu `config.json`, rutas de tu PC, nombres de equipos ni capturas con
  datos reales. Para ejemplos usá rutas y datos genéricos.
- Nada de credenciales ni tokens, ni siquiera "de prueba".

## Licencia

EmuLinks es **GPL-3.0** (ver `LICENSE`). Al aportar código aceptás que se
distribuya bajo esa licencia. Para reportar un problema de seguridad, ver
`SECURITY.md`.
