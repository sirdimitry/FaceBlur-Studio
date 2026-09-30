"""Platform-specific writable locations used by FaceBlur Studio."""

import os
import sys
from pathlib import Path


APP_DIR_NAME = "FaceBlurStudio"


def _windows_local_app_data() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data)
    return Path.home() / "AppData" / "Local"


def app_data_dir() -> Path:
    """Return the writable per-user directory for persistent app data."""
    if sys.platform == "win32":
        return _windows_local_app_data() / APP_DIR_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_DIR_NAME
    data_home = os.environ.get("XDG_DATA_HOME")
    return Path(data_home) / APP_DIR_NAME if data_home else Path.home() / ".local" / "share" / APP_DIR_NAME


def log_dir() -> Path:
    """Return the writable per-user directory for application logs."""
    if sys.platform == "win32":
        return app_data_dir() / "Logs"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Logs" / APP_DIR_NAME
    state_home = os.environ.get("XDG_STATE_HOME")
    return Path(state_home) / APP_DIR_NAME if state_home else Path.home() / ".local" / "state" / APP_DIR_NAME


def matplotlib_cache_dir() -> Path:
    """Return a writable Matplotlib cache without changing the existing macOS path."""
    if sys.platform == "win32":
        return app_data_dir() / "Cache" / "Matplotlib"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "FaceBlurStudio_Matplotlib"
    cache_home = os.environ.get("XDG_CACHE_HOME")
    base = Path(cache_home) if cache_home else Path.home() / ".cache"
    return base / APP_DIR_NAME / "Matplotlib"
