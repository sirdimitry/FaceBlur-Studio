"""Language preferences, logical UI text and live translation for all platforms."""
import ctypes
import json
import locale
import os
import plistlib
import re
import string
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from core.platform_paths import app_data_dir
from ui.translation_catalog import TRANSLATIONS, LOCALIZED

LANGUAGES = {'en': 'English', 'ru': 'Русский', 'zh': '简体中文', 'ar': 'العربية',
             'sr': 'Српски', 'el': 'Ελληνικά', 'es': 'Español'}
CONFIG_FILE = (app_data_dir() / 'config.json' if getattr(sys, 'frozen', False)
               else Path(__file__).resolve().parents[1] / 'config.json')


def normalize_language(identifier):
    return str(identifier or '').replace('_', '-').split('-')[0].lower()


def system_language_candidates():
    """Read user UI preferences, not just the regional number/date locale."""
    if sys.platform == 'win32':
        try:
            count, length = ctypes.c_ulong(), ctypes.c_ulong()
            api = ctypes.windll.kernel32.GetUserPreferredUILanguages
            api.argtypes = [ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong),
                            ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_ulong)]
            api.restype = ctypes.c_int
            if api(8, ctypes.byref(count), None, ctypes.byref(length)):
                buffer = ctypes.create_unicode_buffer(length.value)
                if api(8, ctypes.byref(count), buffer, ctypes.byref(length)):
                    return [item for item in ctypes.wstring_at(buffer, length.value).split('\0') if item]
        except (OSError, AttributeError, ValueError):
            pass
    elif sys.platform == 'darwin':
        try:
            result = subprocess.run(['/usr/bin/defaults', 'export', '-g', '-'],
                                    capture_output=True, timeout=2, check=True)
            languages = plistlib.loads(result.stdout).get('AppleLanguages', [])
            if languages:
                return languages
        except (OSError, ValueError, plistlib.InvalidFileException, subprocess.SubprocessError):
            pass
    candidates = os.environ.get('LANGUAGE', '').split(':')
    candidates += [os.environ.get(name, '') for name in ('LC_ALL', 'LC_MESSAGES', 'LANG')]
    try:
        candidates.append(locale.getlocale()[0])
    except ValueError:
        pass
    return candidates


def detect_system_language():
    for identifier in system_language_candidates():
        code = normalize_language(identifier)
        if code in LANGUAGES:
            return code
    return 'en'


def saved_language():
    """Return preference; auto remains auto so future OS changes are respected."""
    try:
        value = json.loads(CONFIG_FILE.read_text(encoding='utf-8')).get('language', 'auto')
        return value if value in (*LANGUAGES, 'auto') else 'auto'
    except (OSError, ValueError, AttributeError, TypeError):
        return 'auto'


_preference = saved_language()
_language = detect_system_language() if _preference == 'auto' else _preference


def set_language(preference):
    global _language, _preference
    if preference not in (*LANGUAGES, 'auto'):
        raise ValueError('Unsupported language')
    _preference = preference
    _language = detect_system_language() if preference == 'auto' else preference


def get_language():
    return _language


def get_preference():
    return _preference


def is_rtl():
    return _language == 'ar'


def template(source, language=None):
    language = language or _language
    english = TRANSLATIONS.get(source, source)
    if language == 'ru':
        return source
    if language == 'en':
        return english
    return LOCALIZED[language].get(english, english)


class LocalizedText(str):
    """Keep message identity and values through formatting and live language changes."""
    def __new__(cls, source, args=(), kwargs=None):
        kwargs = kwargs or {}
        values = tuple(tr_value(value) for value in args)
        named = {key: tr_value(value) for key, value in kwargs.items()}
        value = template(source)
        if args or kwargs:
            value = value.format(*values, **named)
        result = super().__new__(cls, value)
        result.source, result.args, result.kwargs = source, args, kwargs
        return result

    def format(self, *args, **kwargs):
        return LocalizedText(self.source, args, kwargs)


def tr_value(value):
    if isinstance(value, LocalizedText):
        return LocalizedText(value.source, value.args, value.kwargs)
    return value


def tr(source):
    return LocalizedText(source)


def translate_display(text, previous):
    """Translate logical text; formatted values retain their original order and content."""
    if isinstance(text, LocalizedText):
        return tr_value(text)
    for key in TRANSLATIONS:
        source, target = template(key, previous), template(key)
        fields = list(string.Formatter().parse(source))
        names = [field for literal, field, spec, conversion in fields if field is not None]
        pattern = ''.join(re.escape(literal) + ('(.*?)' if field is not None else '')
                          for literal, field, spec, conversion in fields)
        match = re.fullmatch(pattern, text, re.DOTALL)
        if match:
            values = {name: translate_display(value, previous)
                      for name, value in zip(names, match.groups())}
            return ''.join(literal + (values[field] if field is not None else '')
                           for literal, field, spec, conversion in string.Formatter().parse(target))
    return text


def refresh_widgets(widget, previous):
    # CTk retains logical text; native child labels hold presentation glyphs.
    if not isinstance(widget, tk.Label):
        try:
            text = widget.cget('text')
            if isinstance(text, str):
                widget.configure(text=translate_display(text, previous))
        except (ValueError, AttributeError, TypeError, tk.TclError):
            pass
    if isinstance(widget, tk.Toplevel):
        widget.title(translate_display(widget.title(), previous))
    for child in widget.winfo_children():
        refresh_widgets(child, previous)
