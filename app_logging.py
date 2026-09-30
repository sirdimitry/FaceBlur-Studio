"""Shared logging for source runs and installed bundles."""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def log_path():
    if getattr(sys, 'frozen', False):
        return Path.home() / 'Library' / 'Logs' / 'FaceBlurStudio' / 'debug_app.log'
    return Path(__file__).resolve().parent / 'debug_app.log'


def configure_logging():
    path = log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding='utf-8')
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    handler.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)s] [%(process)d:%(threadName)s] [%(filename)s:%(lineno)d] %(message)s'))
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
    logging.info('Process start: version=%s frozen=%s pid=%s', '1.1.23', getattr(sys, 'frozen', False), os.getpid())
    return path
