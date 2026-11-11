# Componentes de terceros

EmuLinks incluye o se apoya en los siguientes proyectos, cuyos autores se
reconocen y cuyas licencias se respetan:

| Proyecto | Autor / Origen | Licencia |
|----------|----------------|----------|
| Qt for Python (PySide6 / PySide2, shiboken) | The Qt Company | LGPL-3.0 |
| Qt | The Qt Company | LGPL-3.0 |
| Python (intérprete y biblioteca estándar) | Python Software Foundation | PSF-2.0 |
| Universal C Runtime (solo builds para Windows 7) | Microsoft | Redistribuible del Windows SDK |

El texto completo de cada licencia está en la carpeta [`licenses/`](licenses/)
(la LGPL-3.0 se apoya en la GPL-3.0, que también se incluye).

Qt y PySide se distribuyen como bibliotecas separadas dentro de la carpeta del
programa, sin modificar; se pueden reemplazar por otra versión compatible.
El código fuente de Qt y de Qt for Python está disponible en
<https://download.qt.io/official_releases/>.

Las herramientas de construcción (Nuitka, Inno Setup, appimagetool) se usan solo
para armar los ejecutables y no se distribuyen como parte del programa.
