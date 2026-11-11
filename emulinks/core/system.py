"""Compatibilidad multiplataforma."""

import platform

IS_WINDOWS = platform.system() == "Windows"
IS_LINUX   = platform.system() == "Linux"
IS_MACOS   = platform.system() == "Darwin"
IS_WIN7    = IS_WINDOWS and platform.release() == "7"

# Clave de plataforma usada en la config ("windows" / "linux" / "mac").
PLATFORM_KEY = "windows" if IS_WINDOWS else ("mac" if IS_MACOS else "linux")
