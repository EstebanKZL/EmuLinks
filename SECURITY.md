# Política de seguridad

## Versiones con soporte

Se da soporte a la última versión publicada en
[Releases](https://github.com/EstebanKZL/EmuLinks/releases). Antes de reportar,
probá con la última.

| Versión | Soporte |
|---------|---------|
| 6.6.x   | ✅      |
| < 6.6   | ❌      |

## Cómo reportar una vulnerabilidad

Reportá en privado, **sin abrir un issue público**, desde la pestaña
**Security → Report a vulnerability** del repositorio
(<https://github.com/EstebanKZL/EmuLinks/security/advisories/new>), que abre un
aviso privado de GitHub. Contacto del autor: `89585806+EstebanKZL@users.noreply.github.com`
(correo no-reply de GitHub: para reportes, usá el aviso privado).

Incluí, si podés: qué versión y sistema usabas, los pasos para reproducirlo y
qué esperabas que pasara. Se responde apenas se pueda y se avisa cuando haya
una versión con la corrección.

## Alcance

EmuLinks trabaja con archivos locales (enlaces y backups de carpetas de
emuladores) y no abre puertos ni expone servicios de red. Interesan sobre todo:
pérdida o corrupción de datos al sincronizar o restaurar, y rutas que escapen
de la carpeta compartida.
