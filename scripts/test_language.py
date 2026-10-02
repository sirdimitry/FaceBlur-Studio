"""Behavioral language, RTL and documentation checks using real Tk windows."""
import ast
import ctypes
import json
import plistlib
import re
import string
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ui import i18n
from ui.main_window import MainWindow
from ui.mac_window import MacMainWindow
from ui.dialogs import show_about_dialog
from ui.translation_catalog import TRANSLATIONS, LOCALIZED
from ui.text_direction import display_text
from scripts.render_readmes import load_content, render, filename


def fields(text):
    return sorted((name, spec, conversion) for literal, name, spec, conversion
                  in string.Formatter().parse(text) if name is not None)


def close(app):
    for timer in app.tk.call('after', 'info'):
        app.tk.call('after', 'cancel', timer)
    app.on_closing()


class LanguageTest(unittest.TestCase):
    def tearDown(self):
        i18n.set_language('en')

    def test_defaults_corrupt_settings_and_explicit_preference(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'config.json'
            with patch.object(i18n, 'CONFIG_FILE', config):
                self.assertEqual(i18n.saved_language(), 'auto')
                for value in ('{invalid', '[]', '{"language":"invalid"}'):
                    config.write_text(value)
                    self.assertEqual(i18n.saved_language(), 'auto')
                for code in (*i18n.LANGUAGES, 'auto'):
                    config.write_text(json.dumps({'language': code}))
                    self.assertEqual(i18n.saved_language(), code)
            with patch.object(i18n, 'system_language_candidates', return_value=['fr-FR', 'ar-SA']):
                i18n.set_language('auto')
                self.assertEqual(i18n.get_language(), 'ar')
                self.assertEqual(i18n.get_preference(), 'auto')
                i18n.set_language('en')
                self.assertEqual(i18n.get_language(), 'en')
            for identifier, expected in [('zh-Hans-CN', 'zh'), ('sr_Cyrl_RS', 'sr'),
                                         ('el-GR', 'el'), ('es-MX', 'es'), ('de-DE', 'en')]:
                with patch.object(i18n, 'system_language_candidates', return_value=[identifier]):
                    self.assertEqual(i18n.detect_system_language(), expected)

    def test_native_macos_preferences(self):
        result = SimpleNamespace(stdout=plistlib.dumps({'AppleLanguages': ['es-MX', 'en']}))
        with patch.object(i18n.sys, 'platform', 'darwin'), patch.object(i18n.subprocess, 'run', return_value=result):
            self.assertEqual(i18n.detect_system_language(), 'es')

    def test_native_windows_preferences(self):
        def api(flags, count, buffer, length):
            value = 'ar-SA\0en-US\0\0'
            count._obj.value = 2
            if buffer is None:
                length._obj.value = len(value)
            else:
                for index, char in enumerate(value):
                    buffer[index] = char
            return 1
        native = SimpleNamespace(kernel32=SimpleNamespace(GetUserPreferredUILanguages=api))
        with patch.object(i18n.sys, 'platform', 'win32'), patch.object(ctypes, 'windll', native, create=True):
            self.assertEqual(i18n.detect_system_language(), 'ar')

    def test_all_catalogs_and_ui_keys_are_complete(self):
        english = set(TRANSLATIONS.values())
        for code, translations in LOCALIZED.items():
            self.assertEqual(english, translations.keys(), code)
            for source, target in translations.items():
                self.assertEqual(fields(source), fields(target), (code, source))
        for path in [ROOT / 'main.py', *list((ROOT / 'ui').glob('*.py')), *list((ROOT / 'core').glob('*.py'))]:
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'tr':
                    if node.args and isinstance(node.args[0], ast.Constant):
                        self.assertIn(node.args[0].value, TRANSLATIONS, (path.name, node.lineno))

    def test_message_values_and_arabic_presentation(self):
        path = '/tmp/فيديو-01.mp4'
        i18n.set_language('en')
        message = i18n.tr('Ошибка: {0}').format(path)
        nested = i18n.tr('Форма маски: {0}').format(i18n.tr('Овал'))
        for code in i18n.LANGUAGES:
            i18n.set_language(code)
            self.assertIn(path, i18n.translate_display(message, 'en'))
            self.assertIn(i18n.tr('Овал'), i18n.translate_display(nested, 'en'))
        i18n.set_language('ar')
        message = i18n.tr('Экспорт · {0}% · кадр {1} из {2}').format(50, 12, 100)
        native = display_text(message, platform='darwin')
        self.assertEqual(native.replace('\u200e', '').replace('\u200f', ''), message)
        rendered = display_text(message, platform='win32')
        for number in ('50', '12', '100'):
            self.assertIn(number, rendered)
        self.assertTrue(any('\ufb50' <= char <= '\ufeff' for char in rendered))
        self.assertEqual(display_text('FaceBlur.mp4 01:23'), 'FaceBlur.mp4 01:23')

    def test_live_switch_layout_settings_and_state_preservation(self):
        for cls in (MainWindow, MacMainWindow):
            with self.subTest(window=cls.__name__), tempfile.TemporaryDirectory() as directory:
                config = Path(directory) / 'config.json'
                with patch('ui.main_window.CONFIG_FILE', str(config)), \
                     patch.object(i18n, 'system_language_candidates', return_value=['en-US']):
                    app = cls()
                    try:
                        app.update()
                        self.assertEqual(i18n.get_preference(), 'auto')
                        app.btn_settings._canvas.focus_force()
                        app.update()
                        app.btn_settings._canvas.event_generate("<Return>")
                        app.update()
                        settings = app._settings_window
                        app.show_settings()
                        self.assertIs(settings, app._settings_window)
                        self.assertIsNone(app.grab_current())
                        slider = app.blur_slider.get()
                        cache = app.detected_boxes_cache
                        for code in ('ru', 'zh', 'ar', 'sr', 'el', 'es', 'en', 'ar', 'en'):
                            app.change_language(code)
                            app.update()
                            self.assertEqual(app.btn_analyze.cget('text'), i18n.tr('Найти лица'))
                            self.assertEqual(app.btn_settings.cget('text'), i18n.tr('Настройки'))
                            self.assertEqual(settings.title(), i18n.tr('Настройки'))
                            self.assertEqual(app.sidebar.pack_info()['side'], 'right' if code == 'ar' else 'left')
                            self.assertEqual(app.btn_play.pack_info()['side'], 'left')
                            self.assertEqual(app.preview_header.cget('anchor'), 'e' if code == 'ar' else 'w')
                            self.assertEqual(app.gallery_frame._scrollbar.grid_info()['column'], 0 if code == 'ar' else 1)
                            self.assertEqual(app.blur_slider.get(), slider)
                            self.assertIs(app.detected_boxes_cache, cache)
                            self.assertEqual(json.loads(config.read_text())['language'], code)
                            if cls is MacMainWindow:
                                field = app._value_fields['blur_percent'][1]
                                self.assertEqual(float(field.place_info()['relx']), 0 if code == 'ar' else 1)
                                self.assertEqual(field.cget('justify'), 'right')
                        import customtkinter as ctk
                        for mode in ('Dark', 'Light'):
                            ctk.set_appearance_mode(mode)
                            app.after(50, app.quit)
                            app.mainloop()
                            self.assertEqual(app.lbl_status_left.cget('background'),
                                             app.status_bar._apply_appearance_mode(app.lbl_status_left._background_colors))
                        app.change_language('auto')
                        self.assertEqual(json.loads(config.read_text())['language'], 'auto')
                        app.change_language('ar')
                        show_about_dialog(app, 'pointinghand' if sys.platform == 'darwin' else 'hand2')
                        app.update()
                        app.change_language('en')
                        self.assertTrue(any(child.title() == 'About' for child in app.winfo_children()
                                            if hasattr(child, 'title')))
                    finally:
                        close(app)
                    reopened = cls()
                    try:
                        self.assertEqual(i18n.get_preference(), 'en')
                    finally:
                        close(reopened)

    def test_readme_navigation_structure_links_and_generation(self):
        content = load_content()
        english = render('en', content['en'])
        links = lambda text: sorted(re.findall(r'\]\(([^)]+)\)', text))
        headings = len(re.findall(r'^## ', english, re.M))
        for code, source in content.items():
            generated = render(code, source)
            self.assertEqual((ROOT / filename(code)).read_text(), generated)
            self.assertEqual(headings, len(re.findall(r'^## ', generated, re.M)))
            self.assertEqual(links(english), links(generated))
            for other in i18n.LANGUAGES:
                if other != code:
                    self.assertIn(f'href="{filename(other)}"', generated.splitlines()[0])
            if code == 'ar':
                self.assertIn('<div dir="rtl" lang="ar">', generated)
                self.assertIn('<div dir="ltr">\n\n```bash', generated)


if __name__ == '__main__':
    unittest.main()
