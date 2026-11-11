# EmuLinks

Junta las partidas, BIOS, logros y configuraciones de tus emuladores en una
**carpeta compartida** y deja en el lugar original un enlace (junction en
Windows, symlink en Linux). Al reinstalar un emulador o cambiar de PC, apuntás a
esa carpeta y no se pierde nada.

Windows 7 a 11 (32 y 64 bits) y Linux · español e inglés · tema oscuro y claro.

## Descargar

En [Releases](https://github.com/EstebanKZL/EmuLinks/releases): instalador o
portable para Windows y AppImage para Linux. Cuál elegir y cómo instalar:
[Install.md](Install.md).

## Uso

Elegir la carpeta compartida → **Autodetectar** los emuladores → **Verificar
estado** → **Sincronizar**. Detalle de cada pantalla y opción: [Usage.md](Usage.md).

## Desarrollo

```
pip install -r requirements.txt -r requirements-dev.txt
python main.py
python -m pytest -q tests
```

Cómo colaborar: [CONTRIBUTING.md](CONTRIBUTING.md) · cambios por versión:
[CHANGELOG.md](CHANGELOG.md).

## Licencia

[GPL-3.0](LICENSE). Componentes de terceros: [THIRD-PARTY.md](THIRD-PARTY.md).
Problemas o consultas: pestaña **Issues**; seguridad: [SECURITY.md](SECURITY.md).
