#!/usr/bin/env python3
"""Lanzador de EmuLinks y punto de entrada para PyInstaller.

    python main.py
    pyinstaller --noconsole --onefile --name EmuLinks --collect-data PySide6 main.py
"""
from emulinks.app import main

if __name__ == "__main__":
    main()
