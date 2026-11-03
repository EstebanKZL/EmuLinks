"""Genera los íconos de EmuLinks desde packaging/icon/emulinks.svg.

    python packaging/make_icons.py      (necesita PySide6 y Pillow)

Salidas (se versionan, así el CI no necesita QtSvg ni Pillow):
    emulinks/assets/emulinks.png        ícono de ventana (256 px)
    packaging/icon/emulinks.ico         exe e instalador de Windows (16–256 px)
    packaging/linux/emulinks.svg        copia para el AppImage
"""
import io
import shutil
import sys
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

ROOT = Path(__file__).resolve().parent.parent
SVG = ROOT / "packaging" / "icon" / "emulinks.svg"
ICO_SIZES = [16, 20, 24, 32, 40, 48, 64, 128, 256]


def render(renderer: QSvgRenderer, size: int) -> Image.Image:
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    painter = QPainter(img)
    painter.setRenderHint(QPainter.Antialiasing)
    renderer.render(painter)
    painter.end()
    data = QByteArray()
    buf = QBuffer(data)
    buf.open(QIODevice.WriteOnly)
    img.save(buf, "PNG")
    return Image.open(io.BytesIO(bytes(data))).convert("RGBA")


def main() -> None:
    app = QGuiApplication(sys.argv)  # noqa: F841 — QPainter necesita la app
    renderer = QSvgRenderer(str(SVG))
    images = [render(renderer, s) for s in ICO_SIZES]

    assets = ROOT / "emulinks" / "assets"
    assets.mkdir(exist_ok=True)
    images[-1].save(assets / "emulinks.png")
    # Cada tamaño se dibuja desde el SVG (no se achica el de 256): más nítido en 16 px.
    images[-1].save(ROOT / "packaging" / "icon" / "emulinks.ico", format="ICO",
                    sizes=[(s, s) for s in ICO_SIZES], append_images=images[:-1])
    shutil.copyfile(SVG, ROOT / "packaging" / "linux" / "emulinks.svg")
    print("íconos generados")


if __name__ == "__main__":
    main()
