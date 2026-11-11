# Registro de cambios

Todas las versiones notables de EmuLinks. El formato sigue
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el versionado es
[SemVer](https://semver.org/lang/es/). La versión vive en el archivo `VERSION`,
fuente única que leen el programa, el instalador y los nombres de los artefactos.

## [6.6.0] — 2026-11-11

### Cambiado
- Los ejecutables se compilan con **Nuitka**: el código va como binario nativo,
  sin `.py` ni `.pyc` legibles, y arranca más rápido.
- Nuevos nombres de descarga: `EmuLinks-<versión>-<sistema>-<arq>-<variante>`.
  Windows 10/11 (`win-x64`), Windows 7 a 11 (`win7-x64` y `win7-x86`) y Linux
  (`linux-x86_64` y `linux-i686`, en AppImage).
- Un instalador por arquitectura. El portable de Windows pasa a ser un `.zip`
  con la carpeta del programa (el ejecutable único daba falsos positivos de
  antivirus).
- La versión vive en un solo archivo, `VERSION`.
- Contacto en la barra de estado y en "Acerca de": el correo no-reply de GitHub.

### Agregado
- Cada build se prueba arrancando el ejecutable compilado antes de publicarse.
- `Install.md` y `Usage.md` con la instalación y el uso detallados.

## [6.5.1] — 2026-11-11

### Cambiado
- Cambió el identificador de la configuración guardada (`QSettings`) a
  `EstebanKZL`. **Al actualizar, el tema, el idioma y el tamaño de ventana
  guardados se reinician una vez**: la app arranca con tema oscuro y el idioma
  del sistema, y se vuelven a elegir en *Ver → Configuración*.

## [6.5] — 2026-11-11

### Agregado
- Diseño v6.1: íconos SVG propios coloreados por tema en botones, menús, tabla
  de estado (punto de color por estado) y árbol del autodetector (unidad,
  emulador, carpetas y archivos por tipo, con categoría propia para partidas).
- **Configuración** (*Ver → Configuración*): tema, idioma, carpeta de registros
  y carpetas de búsqueda del autodetector, que ahora también se pueden quitar.
- **Acerca de** con botón para copiar versión y datos del sistema.
- Avisos con ícono, confirmación con botón rojo para lo que borra, aviso dentro
  de la ventana si falta la carpeta compartida y notificaciones breves.
- Registro rotativo en la carpeta de logs y captura de errores inesperados.

### Cambiado
- Las acciones de apoyo se ven como botones (azul suave); se dejó de usar `btnGhost`.
- Ventana y tamaños de panel recordados entre sesiones.

## [6.4] — 2026-11-03

### Agregado
- Ícono propio (carpeta con mando y eslabón) en el ejecutable, la ventana, los
  instaladores y el AppImage.
- Builds para Windows 7 SP1 / 8 / 8.1 (x64 y x86) con Python 3.8 + PySide2.
- Instaladores de Inno Setup por generación (Windows 10/11 y Windows 7/8), con
  las dos arquitecturas en el mismo setup.

## [6.3] — 2026-11-03

### Cambiado
- Builds hasta cuatro veces más chicos: se quitó `--collect-data PySide6`, que
  incluía todos los binarios de Qt.

### Agregado
- AppImage para Linux x86_64 e i686.

## [6.2] — 2026-11-03

Primera versión pública.

### Agregado
- Paquete modular (`core` sin Qt, `ui`, `locales` ES/EN) con tests.
- Autodetección de emuladores por unidad de disco; backups en un solo zip por
  emulador y sincronización.
- Interfaz bilingüe con temas Grafito/Papel.
- Integración y empaquetado por GitHub Actions; Release por tag.

[6.6.0]: https://github.com/EstebanKZL/EmuLinks/releases/tag/v6.6.0
[6.5.1]: https://github.com/EstebanKZL/EmuLinks/releases/tag/v6.5.1
[6.5]: https://github.com/EstebanKZL/EmuLinks/releases/tag/v6.5
[6.4]: https://github.com/EstebanKZL/EmuLinks/releases/tag/v6.4
[6.3]: https://github.com/EstebanKZL/EmuLinks/releases/tag/v6.3
[6.2]: https://github.com/EstebanKZL/EmuLinks/releases/tag/v6.2
