"""Locate FFmpeg bundled with the app, with a system fallback for source runs."""

import shutil
import subprocess
import sys
from pathlib import Path


def _bundled_ffmpeg_names():
    """Return supported PyInstaller resource names for the current platform."""
    if sys.platform == "win32":
        return ("ffmpeg.exe", "ffmpeg-win-x86_64-v7.1.exe")
    if sys.platform == "darwin":
        return ("ffmpeg-macos-aarch64-v7.1",)
    return ("ffmpeg",)


def _bundled_ffmpeg_path():
    resource_dir = Path(sys._MEIPASS)
    for filename in _bundled_ffmpeg_names():
        candidate = resource_dir / filename
        if candidate.is_file():
            return candidate
    return None


def executable(name):
    if getattr(sys, "frozen", False):
        if name == "ffmpeg":
            bundled = _bundled_ffmpeg_path()
            if bundled is not None:
                return str(bundled)
            expected = ", ".join(_bundled_ffmpeg_names())
            raise FileNotFoundError(
                f"В приложении отсутствует встроенный FFmpeg ({expected}). "
                "Переустановите FaceBlur Studio."
            )
        raise FileNotFoundError(f"{name} не входит в сборку приложения")

    found = shutil.which(name)
    if found:
        return found
    for directory in ("/opt/homebrew/bin", "/usr/local/bin"):
        candidate = Path(directory) / name
        if candidate.is_file():
            return str(candidate)
    raise FileNotFoundError(f"{name} не найден")


def hidden_subprocess_options():
    """Prevent FFmpeg and FFprobe from opening console windows on Windows."""
    if sys.platform != "win32":
        return {}
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
    return {
        "creationflags": subprocess.CREATE_NO_WINDOW,
        "startupinfo": startupinfo,
    }
