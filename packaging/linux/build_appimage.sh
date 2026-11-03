#!/usr/bin/env bash
# Arma un AppImage a partir de la carpeta que deja `pyinstaller --onedir`.
#   uso: build_appimage.sh <dist/EmuLinks> <x86_64|i686> <salida.AppImage>
# appimagetool corre en x86_64 y toma el runtime de la arquitectura destino,
# así el AppImage de 32 bits se empaqueta en el mismo runner de 64.
set -euo pipefail

ONEDIR="$1"; ARCH="$2"; OUT="$3"
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="$(mktemp -d)"
APPDIR="$WORK/EmuLinks.AppDir"

mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/share/applications" "$APPDIR/usr/share/icons/hicolor/scalable/apps"
cp -a "$ONEDIR" "$APPDIR/usr/bin/EmuLinks"
cp "$HERE/emulinks.desktop" "$APPDIR/emulinks.desktop"
cp "$HERE/emulinks.desktop" "$APPDIR/usr/share/applications/"
cp "$HERE/emulinks.svg" "$APPDIR/emulinks.svg"
cp "$HERE/emulinks.svg" "$APPDIR/usr/share/icons/hicolor/scalable/apps/"
ln -s emulinks.svg "$APPDIR/.DirIcon"

cat > "$APPDIR/AppRun" <<'EOF'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/EmuLinks/EmuLinks" "$@"
EOF
chmod +x "$APPDIR/AppRun"

BASE="https://github.com/AppImage"
curl -fsSL -o "$WORK/appimagetool" "$BASE/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
curl -fsSL -o "$WORK/runtime" "$BASE/type2-runtime/releases/download/continuous/runtime-$ARCH"
chmod +x "$WORK/appimagetool"

# Sin FUSE en el runner: la herramienta se extrae y corre sola.
APPIMAGE_EXTRACT_AND_RUN=1 ARCH="$ARCH" "$WORK/appimagetool" --no-appstream \
    --runtime-file "$WORK/runtime" "$APPDIR" "$OUT"
rm -rf "$WORK"
