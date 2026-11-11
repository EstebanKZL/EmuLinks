# Instalación

Los archivos están en la pestaña
[Releases](https://github.com/EstebanKZL/EmuLinks/releases). No hace falta
instalar Python, Qt ni ningún otro programa: todo viene adentro.

## ¿Cuál bajo?

| Mi PC | Archivo |
|-------|---------|
| Windows 10/11 de 64 bits | `EmuLinks-<versión>-win-x64-setup.exe` (o `-portable.zip`) |
| Windows 7 u 8 de 64 bits | `EmuLinks-<versión>-win7-x64-setup.exe` (o `-portable.zip`) |
| Windows de 32 bits (7, 8, 10 u 11) | `EmuLinks-<versión>-win7-x86-setup.exe` (o `-portable.zip`) |
| Linux de 64 bits | `EmuLinks-<versión>-linux-x86_64.AppImage` |
| Linux de 32 bits | `EmuLinks-<versión>-linux-i686.AppImage` |

Las versiones `win7` también funcionan en Windows 10 y 11; las `win` solo en 10 y 11.

Para saber si Windows es de 32 o 64 bits: *Configuración → Sistema → Acerca de →
Tipo de sistema* (en Windows 7: *Panel de control → Sistema*).

## Instalador (Windows)

1. Ejecutar `…-setup.exe` y seguir los pasos. Si Windows muestra "Editor
   desconocido", elegir *Más información → Ejecutar de todas formas* (el
   ejecutable todavía no está firmado).
2. Instala para tu usuario sin pedir permisos de administrador; en el primer
   paso se puede elegir instalar para todos.
3. Para actualizar, instalar la versión nueva encima. Desinstalar **no** borra
   la configuración ni la carpeta compartida con tus partidas.

## Portable (Windows)

Descomprimir `…-portable.zip` en cualquier carpeta (un pendrive sirve) y abrir
`EmuLinks.exe` desde ahí. No se instala nada; la configuración se guarda en el
usuario de Windows, igual que con el instalador.

## Linux (AppImage)

```bash
chmod +x EmuLinks-*-linux-x86_64.AppImage
./EmuLinks-*-linux-x86_64.AppImage
```

Si la distribución no tiene FUSE, agregar `--appimage-extract-and-run` al final.
El de 64 bits necesita una distribución de 2022 en adelante (Ubuntu 22.04,
Debian 12, Fedora 36…); el de 32 bits, Debian 12 o equivalente.

## Requisitos

- Windows 7 SP1 o posterior. Las versiones `win7` ya incluyen la Universal C
  Runtime: no hace falta instalar la actualización KB2999226.
- Pantalla de 1280×720 o más.
- En Windows, los enlaces son *junctions* y no piden permisos de administrador.

## Verificar la descarga

Cada release trae `SHA256SUMS.txt`. En Windows (PowerShell):

```powershell
Get-FileHash .\EmuLinks-<versión>-win-x64-setup.exe -Algorithm SHA256
```

En Linux: `sha256sum -c SHA256SUMS.txt --ignore-missing`. El valor tiene que
coincidir con el de `SHA256SUMS.txt`.
