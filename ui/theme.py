"""Shared Fluent color resources and system theme integration."""
import ctypes
import sys
import customtkinter as ctk
import darkdetect
from customtkinter.windows.widgets.appearance_mode.appearance_mode_tracker import AppearanceModeTracker

WINDOW = ('#f3f3f3', '#202020')
SIDEBAR = ('#eef2f6', '#202020')
SURFACE = ('#ffffff', '#2b2b2b')
HOVER = ('#eeeeee', '#383838')
TRACK = ('#dedede', '#505050')
BORDER = ('#d6d6d6', '#494949')
TEXT = ('#242424', '#f5f5f5')
SECONDARY = ('#5c5c5c', '#c5c5c5')
DISABLED_TEXT = ('#646464', '#b5b5b5')
DISABLED_SURFACE = ('#e5e5e5', '#383838')
ACCENT = ('#0067c0', '#60cdff')
ACCENT_HOVER = ('#005a9e', '#8bdcff')
ON_ACCENT = ('#ffffff', '#10202b')
SUCCESS = ('#0f7b0f', '#8de18d')
ERROR = ('#b42318', '#ffb4ab')
ERROR_HOVER = ('#fbe9e7', '#502c2a')
PREVIEW = '#0b1016'
UI_FONT = 'SF Pro Text' if sys.platform == 'darwin' else 'Segoe UI'

# macOS evolves independently; Windows keeps its Fluent resources.
if sys.platform == 'darwin':
    WINDOW = ('#f5f6f8', '#191b20')
    SIDEBAR = ('#eceef2', '#22252c')
    SURFACE = ('#ffffff', '#2c3038')
    HOVER = ('#e4e8ee', '#3a404b')
    TRACK = ('#b8c1ce', '#697586')
    BORDER = ('#b8c1ce', '#697586')
    TEXT = ('#202733', '#f2f5fa')
    SECONDARY = ('#515d6e', '#b8c3d3')
    DISABLED_TEXT = ('#586271', '#b8c3d3')
    DISABLED_SURFACE = ('#e1e5eb', '#343a44')
    ACCENT = ('#005fc4', '#82baff')
    ACCENT_HOVER = ('#004fa5', '#a6ceff')
    ON_ACCENT = ('#ffffff', '#13253b')
    SUCCESS = ('#216b39', '#97d8ac')
    ERROR = ('#ae2925', '#ffb4ab')
    ERROR_HOVER = ('#fbe9e7', '#502c2a')


def detect_appearance_mode():
    """Honor dark Windows personalization even when app/system settings differ."""
    if sys.platform == 'win32':
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize') as key:
                values = []
                for name in ('AppsUseLightTheme', 'SystemUsesLightTheme'):
                    try:
                        values.append(winreg.QueryValueEx(key, name)[0])
                    except OSError:
                        pass
                if values:
                    return int(0 in values)
        except OSError:
            pass
    return int(darkdetect.theme() == 'Dark')


def initialize_theme():
    from ui.text_direction import install_text_rendering
    install_text_rendering()
    if sys.platform == 'win32':
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('FaceBlurStudio.Desktop')
    ctk.set_default_color_theme('blue')
    # Use the same detector for startup and CTk's live theme polling.
    AppearanceModeTracker.detect_appearance_mode = staticmethod(detect_appearance_mode)
    ctk.set_appearance_mode('System')
    AppearanceModeTracker.init_appearance_mode()


def apply_app_icon(window):
    from pathlib import Path
    from PIL import Image, ImageTk
    root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))
    if sys.platform == 'win32':
        # Call immediately to prevent CTk's delayed default icon assignment.
        window.iconbitmap(str(root / 'app_icon.ico'))
    window._brand_icon_photos = [ImageTk.PhotoImage(Image.open(root / 'AutoBlureFace_icon.png').resize((size,size), Image.Resampling.LANCZOS), master=window) for size in (16,32,48,64,256)]
    window.iconphoto(True, *window._brand_icon_photos)


def apply_titlebar(window):
    if sys.platform != 'win32':
        return
    try:
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        dark = ctypes.c_int(ctk.get_appearance_mode() == 'Dark')
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark), 4)
    except (OSError, AttributeError):
        pass


def follow_titlebar(window):
    last = None
    def update():
        nonlocal last
        if not window.winfo_exists():
            return
        mode = ctk.get_appearance_mode()
        if mode != last:
            apply_titlebar(window)
            last = mode
        window.after(250, update)
    window.after(250, update)


class ThemedButton(ctk.CTkButton):
    """Use a neutral disabled surface and restore the enabled theme resources."""
    def __init__(self, *args, **kwargs):
        if sys.platform == 'darwin':
            kwargs.setdefault('fg_color', SURFACE)
            kwargs.setdefault('hover_color', HOVER)
            kwargs.setdefault('text_color', TEXT)
            kwargs.setdefault('border_width', 1)
            kwargs.setdefault('border_color', BORDER)
            kwargs.setdefault('corner_radius', 8)
        self._enabled_fill = kwargs.get('fg_color', SURFACE)
        self._enabled_image = kwargs.get('image')
        kwargs.setdefault('text_color_disabled', DISABLED_TEXT)
        kwargs.setdefault('corner_radius', 4)
        if kwargs.get('state') == 'disabled':
            kwargs['fg_color'] = DISABLED_SURFACE
            kwargs['image'] = None
        super().__init__(*args, **kwargs)

    def configure(self, require_redraw=False, **kwargs):
        if 'fg_color' in kwargs:
            self._enabled_fill = kwargs['fg_color']
        if 'image' in kwargs:
            self._enabled_image = kwargs['image']
        state = kwargs.get('state', self.cget('state'))
        kwargs['fg_color'] = DISABLED_SURFACE if state == 'disabled' else self._enabled_fill
        kwargs['image'] = None if state == 'disabled' else self._enabled_image
        kwargs['text_color_disabled'] = DISABLED_TEXT
        super().configure(require_redraw=require_redraw, **kwargs)


def keyboard_button(button):
    """Give a canvas button keyboard activation and a visible focus border."""
    width, color = button.cget('border_width'), button.cget('border_color')
    button._canvas.configure(takefocus=1)
    button._canvas.bind('<FocusIn>', lambda event: button.configure(border_width=2, border_color=ACCENT))
    button._canvas.bind('<FocusOut>', lambda event: button.configure(border_width=width, border_color=color))
    def activate(event):
        button.invoke()
        return 'break'
    button._canvas.bind('<Return>', activate)
    button._canvas.bind('<space>', activate)
