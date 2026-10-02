"""Arabic presentation for Tk, which does not provide a full bidi layout engine.

Only the display boundary is shaped. Project data, filenames and translations
remain logical Unicode. Video pixels, playback order and numeric entry fields
are never mirrored.
"""
import re
import sys
import tkinter as tk
import tkinter.font as tkfont
from functools import lru_cache
import arabic_reshaper
from bidi.algorithm import get_display

ARABIC = re.compile(r'[\u0600-\u06ff]')
_reshaper = arabic_reshaper.ArabicReshaper(configuration={'delete_harakat': False,
                                                        'shift_harakat_position': True})
_installed = False


@lru_cache(maxsize=2048)
def display_text(text, platform=None):
    platform = platform or sys.platform
    # macOS Tk delegates text to CoreText, including shaping and bidi. Sending
    # visual-order glyphs there applies bidi twice and reverses Arabic words.
    if not ARABIC.search(text):
        return text
    # Keep keyboard shortcuts, IDs, extensions and Western numbers in LTR
    # order inside the RTL paragraph. LRM is supported by both text engines.
    text = re.sub(r"(?:[⌘^#][A-Za-z0-9]+|[A-Za-z0-9][A-Za-z0-9_./:%×+\\-]*)",
                  lambda match: "\u200e" + match.group() + "\u200e", text)
    if platform == "darwin":
        return "\n".join("\u200f" + line for line in text.split("\n"))
    return '\n'.join(get_display(_reshaper.reshape(line), base_dir='R')
                     for line in text.split('\n'))


def script_font(text):
    if ARABIC.search(text):
        return 'Geeza Pro' if sys.platform == 'darwin' else 'Segoe UI'
    if any('\u3400' <= char <= '\u9fff' for char in text):
        return 'PingFang SC' if sys.platform == 'darwin' else 'Microsoft YaHei UI'
    return None


def _render_label(label, options):
    """Wrap logical words before bidi reordering, and let Tk keep sizing labels."""
    text = str(label._fb_logical_text)
    font = options.get('font', label._fb_source_font)
    label._fb_source_font = font
    options['font'] = font
    family = script_font(text)
    if family:
        actual = tkfont.Font(root=label, font=font).actual()
        font = (family, actual['size'], actual['weight'], actual['slant'])
        options['font'] = font
    wrap = float(options.get('wraplength', label.cget('wraplength')) or 0)
    if ARABIC.search(text) and wrap > 0:
        metrics = tkfont.Font(root=label, font=font)
        lines = []
        for paragraph in text.split('\n'):
            line = ''
            for word in paragraph.split(' '):
                trial = line + (' ' if line else '') + word
                if line and metrics.measure(display_text(trial)) > wrap:
                    lines.append(line)
                    line = word
                else:
                    line = trial
            lines.append(line)
        text = '\n'.join(lines)
    options['text'] = display_text(text)
    return options


def install_text_rendering():
    """Adapt CTk's Tk label boundary once; keep CTk cget and callbacks logical."""
    global _installed
    if _installed:
        return
    _installed = True
    original_init, original_configure = tk.Label.__init__, tk.Label.configure

    def initialize(label, master=None, cnf=None, **kwargs):
        options = dict(cnf or {}, **kwargs)
        label._fb_logical_text = options.get('text', '')
        label._fb_source_font = options.get('font', 'TkDefaultFont')
        # Avoid changing unrelated native widgets outside this application.
        original_init(label, master, options)
        if isinstance(label._fb_logical_text, str) and label._fb_logical_text:
            original_configure(label, **_render_label(label, {}))

    def configure(label, cnf=None, **kwargs):
        if cnf is not None and not isinstance(cnf, dict):
            return original_configure(label, cnf, **kwargs)
        options = dict(cnf or {}, **kwargs)
        if not options:
            return original_configure(label)
        if 'text' in options:
            label._fb_logical_text = options['text']
        if hasattr(label, '_fb_logical_text') and isinstance(label._fb_logical_text, str):
            options = _render_label(label, options)
        return original_configure(label, **options)

    tk.Label.__init__ = initialize
    tk.Label.configure = tk.Label.config = configure
    # Windows/Linux Tk menus also need presentation order; macOS native menus
    # use the OS text engine and should receive logical text.
    if sys.platform != 'darwin':
        original_add = tk.Menu.add_command
        def add_command(menu, cnf=None, **kwargs):
            options = dict(cnf or {}, **kwargs)
            if 'label' in options:
                options['label'] = display_text(options['label'])
            return original_add(menu, options)
        tk.Menu.add_command = add_command
