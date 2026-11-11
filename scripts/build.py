"""Build de los ejecutables de EmuLinks con Nuitka. Lo usa el workflow de GitHub
Actions y se puede correr a mano.

    python scripts/build.py                  # Windows: portable (.zip) + instalador (si hay Inno Setup)
    python scripts/build.py --no-installer   # Windows: solo portable
    python scripts/build.py --appimage --appimagetool ./appimagetool.AppImage   # Linux
    python scripts/build.py --standalone-only            # solo compilar (contenedor i386)
    python scripts/build.py --package-appimage build/nuitka/main.dist --arch i686 \
                            --appimagetool ./appimagetool.AppImage            # empaquetar lo compilado

Nuitka traduce el Python a C y lo compila: en el paquete no queda .py ni .pyc
legible. Todo se arma con el Python que corre el script (su arquitectura y su
backend Qt definen la línea):
    PySide6 x64 -> EmuLinks-<ver>-win-x64-{portable.zip,setup.exe}     Windows 10/11
    PySide2     -> EmuLinks-<ver>-win7-{x64,x86}-{portable.zip,setup.exe}  Windows 7 a 11
    Linux       -> EmuLinks-<ver>-linux-{x86_64,i686}.AppImage
(convención <AppName>-<versión>-<os>-<arq>-<variante>)
Todo queda en dist/release/. El build parte de cero cada vez (borra build/ y dist/).
Tiene que correr en Python 3.8 (la línea de Windows 7).
"""

import argparse
import importlib.util
import os
import platform
import shutil
import stat
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build" / "nuitka"
DIST = ROOT / "dist"
RELEASE = DIST / "release"
ENTRY = ROOT / "main.py"
ISCC_CANDIDATES = [
    r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    r"C:\Program Files\Inno Setup 6\ISCC.exe",
]


def version_info():
    spec = importlib.util.spec_from_file_location("v", ROOT / "emulinks" / "version.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def qt_backend() -> str:
    for name in ("PySide6", "PySide2"):
        if importlib.util.find_spec(name):
            return name
    sys.exit("No hay PySide6 ni PySide2 instalado")


def arch() -> str:
    return "x64" if sys.maxsize > 2**32 else "x86"


def linux_arch() -> str:
    return {"x86_64": "x86_64", "amd64": "x86_64"}.get(platform.machine().lower(), "i686")


def label(backend: str) -> str:
    if sys.platform.startswith("linux"):
        return "linux-" + linux_arch()
    return ("win-" if backend == "PySide6" else "win7-") + arch()


def run(cmd, **kw):
    print(">", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run([str(c) for c in cmd], check=True, cwd=str(ROOT), **kw)


def ucrt_dir() -> Path:
    """DLLs de la Universal C Runtime del Windows SDK. Python 3.8 depende de ellas y
    Windows 7 sin la actualización KB2999226 no las tiene ("api-ms-win-crt-runtime-
    l1-1-0.dll is missing"). Microsoft permite copiarlas junto al .exe."""
    kits = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Windows Kits" / "10" / "Redist"
    found = sorted(kits.glob("*/ucrt/DLLs/" + arch())) + [kits / "ucrt" / "DLLs" / arch()]
    for d in reversed(found):
        if (d / "ucrtbase.dll").exists():
            return d
    sys.exit("No se encontró la Universal CRT ({}) del Windows SDK en {}: "
             "sin ella el build no arranca en Windows 7".format(arch(), kits))


def nuitka(v, backend: str) -> Path:
    """Compila y devuelve la carpeta standalone."""
    exe_name = v.APP_SLUG + (".exe" if os.name == "nt" else "")
    numeric = ".".join((v.APP_VERSION.split(".") + ["0", "0", "0"])[:4])
    other = "PySide2" if backend == "PySide6" else "PySide6"
    cmd = [sys.executable, "-m", "nuitka", "--standalone", "--assume-yes-for-downloads",
           "--enable-plugin=" + backend.lower(),
           "--include-module={}.QtSvg".format(backend),          # íconos SVG del tema
           "--include-data-dir={}=emulinks/assets".format(ROOT / "emulinks" / "assets"),
           "--include-data-files={}=VERSION".format(ROOT / "VERSION"),
           "--nofollow-import-to=" + other,
           "--nofollow-import-to=tkinter",
           "--nofollow-import-to=pytest",
           "--output-dir={}".format(BUILD), "--output-filename=" + exe_name,
           "--company-name=" + v.APP_PUBLISHER, "--product-name=" + v.APP_NAME,
           "--file-version=" + numeric, "--product-version=" + numeric,
           "--file-description=" + v.APP_NAME,
           "--copyright=(c) {} - GPL-3.0".format(v.APP_PUBLISHER)]
    if os.name == "nt":
        cmd += ["--windows-console-mode=disable",
                "--windows-icon-from-ico={}".format(ROOT / "assets" / "icon.ico")]
        if os.environ.get("NUITKA_MSVC", "1") == "1":
            cmd.append("--msvc=latest")       # x86 necesita MSVC (el MinGW que baja Nuitka es de 64 bits)
    else:
        cmd.append("--linux-icon={}".format(ROOT / "assets" / "icon.png"))
    run(cmd + [ENTRY])
    return BUILD / "{}.dist".format(ENTRY.stem)


def add_ucrt(folder: Path) -> None:
    ucrt = ucrt_dir()
    print("Universal CRT: {}".format(ucrt))
    for dll in ucrt.glob("*.dll"):
        shutil.copy2(str(dll), str(folder / dll.name))
    for name in ("ucrtbase.dll", "api-ms-win-crt-runtime-l1-1-0.dll"):
        if not (folder / name).exists():
            sys.exit("Falta {} en {}: el build no arrancaría en Windows 7".format(name, folder))


def zip_folder(folder: Path, target: Path, root_name: str) -> None:
    with zipfile.ZipFile(str(target), "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f in sorted(folder.rglob("*")):
            if f.is_file():
                z.write(str(f), str(Path(root_name) / f.relative_to(folder)))


def build_windows(v, backend: str, installer: bool):
    tag = "{}-{}-{}".format(v.APP_SLUG, v.APP_VERSION, label(backend))
    legacy = backend == "PySide2"
    standalone = nuitka(v, backend)
    if legacy:
        add_ucrt(standalone)
    # El portable es la carpeta en .zip, no un --onefile: Windows Defender marca el
    # onefile de Nuitka como "software potencialmente no deseado" (falso positivo),
    # y en Windows 7 las DLL de la UCRT tienen que quedar al lado del .exe desde el arranque.
    zip_folder(standalone, RELEASE / (tag + "-portable.zip"), "{}-{}".format(v.APP_SLUG, v.APP_VERSION))
    if not installer:
        return
    iscc = next((p for p in ISCC_CANDIDATES if os.path.exists(p)), shutil.which("iscc"))
    if not iscc:
        print("Inno Setup no encontrado: se omite el instalador")
        return
    run([iscc, "/Q", "/DAppVersion=" + v.APP_VERSION, "/DArch=" + arch(),
         "/DMinWin=" + ("6.1sp1" if legacy else "10.0"), "/DSourceDir={}".format(standalone),
         "/DOutputDir={}".format(RELEASE), "/DOutputName=" + tag + "-setup",
         "/DPublisher=" + v.APP_PUBLISHER, ROOT / "installer" / "emulinks.iss"])


def package_appimage(v, standalone: Path, appimagetool: str, target_arch: str):
    """Arma el AppImage desde una carpeta standalone ya compilada. appimagetool corre
    en x86_64 y toma el runtime de la arquitectura destino (ARCH): así el de 32 bits
    se empaqueta en el mismo runner de 64."""
    appdir = BUILD / "AppDir"
    shutil.rmtree(str(appdir), ignore_errors=True)
    (appdir / "usr" / "bin").mkdir(parents=True)
    shutil.copytree(str(standalone), str(appdir / "usr" / "bin" / v.APP_SLUG))
    shutil.copy2(str(ROOT / "packaging" / "linux" / "emulinks.desktop"), str(appdir))
    shutil.copy2(str(ROOT / "assets" / "icon.png"), str(appdir / "emulinks.png"))
    (appdir / ".DirIcon").symlink_to("emulinks.png")
    apprun = appdir / "AppRun"
    shutil.copy2(str(ROOT / "packaging" / "linux" / "AppRun"), str(apprun))
    apprun.chmod(apprun.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    RELEASE.mkdir(parents=True, exist_ok=True)
    out = RELEASE / "{}-{}-linux-{}.AppImage".format(v.APP_SLUG, v.APP_VERSION, target_arch)
    env = dict(os.environ, ARCH=target_arch, APPIMAGE_EXTRACT_AND_RUN="1")
    run([appimagetool, "--no-appstream", appdir, out], env=env)


def clean() -> None:
    for d in (BUILD, DIST):
        shutil.rmtree(str(d), ignore_errors=True)
    RELEASE.mkdir(parents=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-installer", action="store_true")
    ap.add_argument("--appimage", action="store_true")
    ap.add_argument("--standalone-only", action="store_true")
    ap.add_argument("--package-appimage", metavar="STANDALONE_DIR")
    ap.add_argument("--arch", default=None, help="arquitectura del AppImage (x86_64 / i686)")
    ap.add_argument("--appimagetool", default="appimagetool")
    args = ap.parse_args()

    v = version_info()
    if args.package_appimage:          # no compila: solo empaqueta (sin Qt en este Python)
        package_appimage(v, Path(args.package_appimage).resolve(), args.appimagetool,
                         args.arch or linux_arch())
    else:
        backend = qt_backend()
        clean()
        print("{} {} · {} · Python {} {}".format(v.APP_NAME, v.APP_VERSION, backend,
                                                 platform.python_version(), arch()))
        if args.standalone_only:
            nuitka(v, backend)
        elif args.appimage:
            package_appimage(v, nuitka(v, backend), args.appimagetool, args.arch or linux_arch())
        else:
            build_windows(v, backend, not args.no_installer)
    if RELEASE.exists():
        for f in sorted(RELEASE.iterdir()):
            print("  {}  ({:.1f} MB)".format(f.name, f.stat().st_size / 1e6))


if __name__ == "__main__":
    main()
