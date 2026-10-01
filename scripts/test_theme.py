"""Check contrast, live system changes and stateful controls in both themes."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import customtkinter as ctk
from customtkinter.windows.widgets.appearance_mode.appearance_mode_tracker import AppearanceModeTracker
from ui import theme


def contrast(a,b):
    def luminance(value):
        rgb=[int(value[i:i+2],16)/255 for i in (1,3,5)]
        rgb=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb]
        return sum(v*w for v,w in zip(rgb,(.2126,.7152,.0722)))
    hi,lo=sorted((luminance(a),luminance(b)),reverse=True)
    return (hi+.05)/(lo+.05)


class ThemeTest(unittest.TestCase):
    @unittest.skipUnless(sys.platform == 'win32', 'Windows personalization')
    def test_windows_personalization_and_initial_mode(self):
        import winreg
        for apps, system, expected in ((1, 1, 'Light'), (0, 0, 'Dark'),
                                       (1, 0, 'Dark'), (0, 1, 'Dark')):
            with patch('ui.theme.sys.platform', 'win32'), \
                 patch('winreg.OpenKey'), \
                 patch('winreg.QueryValueEx', side_effect=lambda key, name: (
                     apps if name == 'AppsUseLightTheme' else system, winreg.REG_DWORD)):
                theme.initialize_theme()
                self.assertEqual(ctk.get_appearance_mode(), expected)
                self.assertEqual(AppearanceModeTracker.appearance_mode_set_by, 'system')
        theme.initialize_theme()

    @unittest.skipUnless(sys.platform == 'win32', 'Windows registry fallback')
    def test_detection_fallback(self):
        with patch('winreg.OpenKey', side_effect=OSError), \
             patch('darkdetect.theme', return_value='Dark'):
            self.assertEqual(theme.detect_appearance_mode(), 1)

    def test_text_contrast(self):
        for index in (0,1):
            for ink in (theme.TEXT,theme.SECONDARY,theme.SUCCESS,theme.ERROR,theme.ACCENT):
                for paper in (theme.WINDOW,theme.SIDEBAR,theme.SURFACE):
                    self.assertGreaterEqual(contrast(ink[index],paper[index]),4.5,(ink,paper,index))
            for paper in (theme.ACCENT,theme.ACCENT_HOVER):
                self.assertGreaterEqual(contrast(theme.ON_ACCENT[index],paper[index]),4.5)
            self.assertGreaterEqual(contrast(theme.DISABLED_TEXT[index],theme.DISABLED_SURFACE[index]),4.5)

    def test_main_window_and_gallery_in_both_themes(self):
        from PIL import Image
        from ui.main_window import MainWindow
        app=MainWindow()
        app.state('normal')
        app.geometry('1040x740')
        try:
            app.unique_faces={1:{'enabled':True,'pil_image':Image.new('RGB',(32,32))}}
            app.populate_gallery_ui()
            for mode in ('Light','Dark'):
                ctk.set_appearance_mode(mode)
                app.update()
                self.assertTrue(app.btn_about.winfo_ismapped())
                self.assertTrue(app.unique_faces[1]['widget'].winfo_ismapped())
                self.assertEqual(app.preview_header.cget('text_color'),theme.TEXT)
                app.btn_export.configure(state='normal',text_color=theme.ON_ACCENT)
                self.assertEqual(app.btn_export.cget('fg_color'),theme.ACCENT)
                app.btn_export.configure(state='disabled')
                self.assertEqual(app.btn_export.cget('fg_color'),theme.DISABLED_SURFACE)
        finally:
            for timer in app.tk.call("after", "info"):
                app.tk.call("after", "cancel", timer)
            app.on_closing()
            theme.initialize_theme()

    def test_system_theme_switch_and_button_state(self):
        theme.initialize_theme()
        root=ctk.CTk();root.withdraw()
        button=theme.ThemedButton(root,fg_color=theme.ACCENT,text_color=theme.ON_ACCENT,state='disabled')
        self.assertEqual(button.cget('fg_color'),theme.DISABLED_SURFACE)
        button.configure(state='normal')
        self.assertEqual(button.cget('fg_color'),theme.ACCENT)
        try:
            for mode in ('Light','Dark','Light'):
                with patch.object(AppearanceModeTracker, 'detect_appearance_mode', return_value=int(mode == 'Dark')):
                    AppearanceModeTracker.update()
                    root.update_idletasks()
                    self.assertEqual(ctk.get_appearance_mode(),mode)
                    self.assertEqual(button._apply_appearance_mode(button.cget('text_color')),theme.ON_ACCENT[mode=='Dark'])
                button.configure(state='disabled')
                self.assertEqual(button.cget('fg_color'),theme.DISABLED_SURFACE)
                button.configure(state='normal')
                self.assertEqual(button.cget('fg_color'),theme.ACCENT)
        finally:
            for timer in root.tk.call("after", "info"):
                root.tk.call("after", "cancel", timer)
            root.destroy()
            theme.initialize_theme()

if __name__=='__main__':unittest.main()
