"""Locate FFmpeg bundled with the app, with a system fallback for source runs."""
import os
import shutil
import sys
from pathlib import Path

BUNDLED_FFMPEG = "ffmpeg-macos-aarch64-v7.1"


def executable(name):
    if getattr(sys, "frozen", False):
        bundled = Path(sys._MEIPASS) / BUNDLED_FFMPEG
        if name == "ffmpeg" and bundled.is_file() and os.access(bundled, os.X_OK):
            return str(bundled)
        if name == "ffmpeg":
            raise FileNotFoundError("В приложении отсутствует встроенный FFmpeg. Переустановите FaceBlur Studio.")
        raise FileNotFoundError(f"{name} не входит в приложение")
    found = shutil.which(name)
    if found:
        return found
    for directory in ("/opt/homebrew/bin", "/usr/local/bin"):
        candidate = os.path.join(directory, name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    raise FileNotFoundError(f"{name} не найден")
