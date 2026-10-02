import os
import sys
import webbrowser
import customtkinter as ctk
from ui.theme import (WINDOW, SIDEBAR, SURFACE, HOVER, TRACK, BORDER, TEXT, SECONDARY, DISABLED_TEXT, ACCENT, ACCENT_HOVER, ON_ACCENT, SUCCESS, ERROR, ERROR_HOVER, ThemedButton, initialize_theme, follow_titlebar, apply_app_icon)
from PIL import Image
from app_logging import open_log_folder

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), relative_path)

def show_about_dialog(parent_window, cursor_hand):
    dialog = ctk.CTkToplevel(parent_window)
    apply_app_icon(dialog)
    dialog.title("О программе")
    dialog.geometry("380x490")
    dialog.configure(fg_color=WINDOW)
    dialog.resizable(False, False)
    follow_titlebar(dialog)
    dialog.after(250, lambda: dialog.iconbitmap(get_resource_path("app_icon.ico")) if sys.platform == "win32" else None)
    dialog.transient(parent_window)
    dialog.grab_set()

    icon_path = get_resource_path("AutoBlureFace_icon.png")
    if os.path.exists(icon_path):
        pil_img = Image.open(icon_path)
        ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(80, 80))
        lbl_img = ctk.CTkLabel(dialog, image=ctk_img, text="")
        lbl_img.pack(pady=(25, 10))

    lbl_title = ctk.CTkLabel(dialog, text="FaceBlur Studio", font=("Segoe UI", 20, "bold"), text_color=TEXT)
    lbl_title.pack(pady=(5, 2))

    lbl_ver = ctk.CTkLabel(dialog, text="Версия 1.1.27", font=("Segoe UI", 13), text_color=SECONDARY)
    lbl_ver.pack(pady=(0, 10))

    lbl_desc = ctk.CTkLabel(
        dialog,
        text="Полностью автоматический локальный\nинструмент защиты приватности на видео\nс использованием YOLOv8-face.",
        font=("Segoe UI", 13),
        text_color=TEXT,
        justify="center"
    )
    lbl_desc.pack(pady=10)

    lbl_author = ctk.CTkButton(
        dialog,
        text="© @sirdimitry, 2026",
        font=("Segoe UI", 13, "underline"),
        fg_color="transparent",
        hover_color=HOVER,
        text_color=ACCENT,
        cursor=cursor_hand,
        command=lambda: webbrowser.open_new_tab("https://x.com/sirdimitry")
    )
    lbl_author.pack(pady=(15, 20))

    ThemedButton(
        dialog, text="Открыть папку логов", height=32,
        command=open_log_folder, cursor=cursor_hand,
    ).pack(pady=(0, 12))

    btn_close = ThemedButton(
        dialog,
        text="Закрыть",
        width=120,
        height=32,
        font=("Segoe UI", 14),
        fg_color=ACCENT,
        hover_color=ACCENT_HOVER,
        text_color=ON_ACCENT,
        command=dialog.destroy,
        cursor=cursor_hand
    )
    btn_close.pack(pady=(0, 15))
