"""Shared logging for source runs and installed bundles."""
import logging
import os
import sys
import platform
import subprocess
from pathlib import Path

from core.platform_paths import log_dir

MAX_LOG_BYTES = 10 * 1024 * 1024


class BoundedFileHandler(logging.FileHandler):
    """Clear the log at the size limit, retaining the newest record."""

    def _open(self):
        return open(self.baseFilename, self.mode, encoding=self.encoding,
                    errors=self.errors, newline='')

    def emit(self, record):
        try:
            message = self.format(record) + self.terminator
            encoded = message.encode('utf-8', errors='backslashreplace')
            if len(encoded) >= MAX_LOG_BYTES:
                message = '[Oversized log record truncated]\n' + encoded[-(MAX_LOG_BYTES - 128):].decode('utf-8', errors='ignore')
                encoded = message.encode('utf-8')
            if self.stream is None:
                self.stream = self._open()
            self.stream.seek(0, os.SEEK_END)
            if self.stream.tell() + len(encoded) >= MAX_LOG_BYTES:
                self.stream.seek(0)
                self.stream.truncate()
            self.stream.write(message)
            self.flush()
        except Exception:
            self.handleError(record)


def open_log_folder():
    folder = log_path().parent
    folder.mkdir(parents=True, exist_ok=True)
    if sys.platform == 'win32':
        os.startfile(str(folder))
    else:
        subprocess.Popen(['open' if sys.platform == 'darwin' else 'xdg-open', str(folder)])


def log_path():
    if getattr(sys, 'frozen', False):
        return log_dir() / 'debug_app.log'
    return Path(__file__).resolve().parent / 'debug_app.log'


def configure_logging():
    path = log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = BoundedFileHandler(path, encoding='utf-8', errors='backslashreplace')
    if path.stat().st_size >= MAX_LOG_BYTES:
        handler.stream.seek(0)
        handler.stream.truncate()
    for index in range(1, 4):
        path.with_name(f'{path.name}.{index}').unlink(missing_ok=True)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    handler.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)s] [%(process)d:%(threadName)s] [%(filename)s:%(lineno)d] %(message)s'))
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
    logging.info('Process start: version=%s frozen=%s pid=%s', '1.1.25', getattr(sys, 'frozen', False), os.getpid())
    logging.info('System: %s; machine=%s; Python=%s; executable=%s; log=%s',
                 platform.platform(), platform.machine(), sys.version, sys.executable, path)
    return path
