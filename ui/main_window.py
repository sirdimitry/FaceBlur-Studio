import json
import os
import sys
import threading
import queue
import logging
import datetime
import time
import cv2
import customtkinter as ctk
from ui.theme import (UI_FONT, WINDOW, SIDEBAR, SURFACE, HOVER, TRACK, BORDER, TEXT, SECONDARY, DISABLED_TEXT, ACCENT, ACCENT_HOVER, ON_ACCENT, SUCCESS, ERROR, ERROR_HOVER, ThemedButton, initialize_theme, follow_titlebar, apply_app_icon)
import tkinter as tk
from ui.fluent_slider import FluentSlider
from ui.status_bar import ScrollingStatus, StatusEvents
from PIL import Image, ImageTk, ImageDraw, ImageFont
from core.video_reader import FFmpegVideoReader
from core.detector import FaceDetector, default_model_filename
from core.blurrer import FaceBlurrer
from core.video_writer import FFmpegVideoWriter
from core.project_manager import ProjectManager
from core.platform_paths import app_data_dir
from ui.dialogs import show_about_dialog, get_resource_path

from app_logging import log_path

LOG_FILE = log_path()
if getattr(sys, "frozen", False):
    app_dir = app_data_dir()
    app_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    CONFIG_FILE = str(app_dir / "config.json")
else:
    CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

initialize_theme()

CURSOR_HAND = "pointinghand" if sys.platform == "darwin" else "hand2"


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        apply_app_icon(self)
        
        # Разделитель нового запуска с датой, временем и секундами
        start_time_str = datetime.datetime.now().strftime("%H:%M:%S %d.%m.%Y")
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as log_file:
                log_file.write(f"\n******************** {start_time_str} ********************\n")
        except Exception:
            pass

        logging.info("Инициализация MainWindow FaceBlur Studio v1.1.27")
        self.title("FaceBlur Studio — v1.1.27")
        
        self.geometry("1280x820")
        self.minsize(1040, 740)
        if sys.platform == "win32":
            self.state("zoomed")
        self.deiconify()
        self.focus_force()

        # Безопасный шрифт для галереи
        self.gallery_font = ctk.CTkFont(family=UI_FONT, size=13, weight="normal")
        self.gallery_photo_refs = []  # Защита миниатюр от сборщика мусора

        self.after(250, self._apply_window_identity)
        follow_titlebar(self)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.configure(fg_color=WINDOW)

        self.settings = self.load_settings()

        self.reader = None
        self.video_status_error = None
        self.selected_video_path = None
        self.detector = None
        self.blurrer = FaceBlurrer(
            blur_percent=self.settings.get("blur_percent", 70), 
            padding_percent=self.settings.get("padding_percent", 25), 
            fade_percent=self.settings.get("fade_percent", 40),
            shape_percent=self.settings.get("shape_percent", 100)
        )
        self.is_playing = False
        self._playback_anchor_frame = 0
        self._playback_anchor_time = 0.0
        self.current_frame_idx = 0
        
        self.raw_frames = []
        self.detected_boxes_cache = {}
        self.unique_faces = {}

        self.is_analysing = False
        self.is_exporting = False
        self._ui_events = queue.Queue()
        self._closing = False
        self.after(50, self._drain_ui_events)
        self.stop_analysis_flag = False

        self.zoom_factor = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.current_pil_img = None
        self.tk_image_ref = None

        # Нижняя строка состояния
        self.status_bar = ctk.CTkFrame(self, height=28, corner_radius=0, fg_color=WINDOW, border_width=1, border_color=BORDER)
        self.status_bar.pack(side="bottom", fill="x")
        self.status_bar.bind("<Configure>", self.on_status_bar_resize)

        self.lbl_status_right = ctk.CTkLabel(
            self.status_bar, 
            text="", 
            font=(UI_FONT, 13),
            text_color=SECONDARY,
            anchor="e"
        )
        self.lbl_status_right.pack(side="right", padx=(5, 15), pady=2)

        self.lbl_status_left = ScrollingStatus(self.status_bar, WINDOW, SECONDARY)
        self.lbl_status_left.pack(side="left", fill="x", expand=True, padx=(1, 0))
        self.set_status("Готов к работе")
        self._status_events = StatusEvents(self)
        logging.getLogger().addHandler(self._status_events)

        self.sidebar = ctk.CTkFrame(self, width=340, corner_radius=0, fg_color=SIDEBAR, border_width=1, border_color=SURFACE)
        self.sidebar.pack(side="left", fill="y", padx=(0, 0), pady=0)

        self.lbl_inspector_header = ctk.CTkLabel(
            self.sidebar,
            text="FaceBlur Studio",
            font=(UI_FONT, 22, "bold"),
            text_color=TEXT,
            anchor="w"
        )
        logo = Image.open(get_resource_path("AutoBlureFace_icon.png"))
        self.brand_image = ctk.CTkImage(light_image=logo, dark_image=logo, size=(28, 28))
        self.lbl_inspector_header.configure(image=self.brand_image, compound="left", padx=8)
        self.lbl_inspector_header.pack(padx=15, pady=(12, 8), fill="x")
        self.lbl_inspector_header.configure(height=26)

        self.btn_open = ThemedButton(
            self.sidebar, 
            text="+  Добавить видео",
            height=42,
            corner_radius=4,
            font=(UI_FONT, 14),
            fg_color=SURFACE,
            hover_color=HOVER,
            text_color=TEXT,
            cursor=CURSOR_HAND,
            border_width=1,
            border_color=BORDER,
            command=self.open_video
        )
        self.btn_open.pack(padx=15, pady=(0, 8), fill="x")
        self.btn_open.configure(fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color=ON_ACCENT, border_width=0)

        self.project_btn_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.project_btn_frame.pack(padx=15, pady=(0, 10), fill="x")

        self.btn_save_proj = ThemedButton(
            self.project_btn_frame,
            text="Сохранить проект",
            height=32,
            font=(UI_FONT, 13),
            fg_color=SURFACE,
            hover_color=HOVER,
            text_color=TEXT,
            cursor=CURSOR_HAND,
            border_width=1,
            border_color=BORDER,
            command=self.save_project,
            state="disabled"
        )
        self.btn_save_proj.pack(side="left", expand=True, fill="x", padx=(0, 2))

        self.btn_load_proj = ThemedButton(
            self.project_btn_frame,
            text="Открыть проект",
            height=32,
            font=(UI_FONT, 13),
            fg_color=SURFACE,
            hover_color=HOVER,
            text_color=TEXT,
            cursor=CURSOR_HAND,
            border_width=1,
            border_color=BORDER,
            command=self.load_project
        )
        self.btn_load_proj.pack(side="right", expand=True, fill="x", padx=(2, 0))

        self.div1 = ctk.CTkFrame(self.sidebar, height=1, fg_color=SURFACE)
        self.div1.pack(fill="x", padx=15, pady=5)

        blur_val = self.settings.get("blur_percent", 70)
        self.lbl_blur_title = ctk.CTkLabel(self.sidebar, text="Сила размытия", font=(UI_FONT, 13), text_color=TEXT)
        self.lbl_blur_title.pack(padx=15, pady=(4, 0), anchor="w")
        self.lbl_blur_title.configure(height=18)

        self.blur_slider = FluentSlider(self.sidebar, from_=0, to=100, number_of_steps=100, button_color=TEXT, button_hover_color=SURFACE, progress_color=ACCENT, fg_color=TRACK, command=self.on_blur_slider_change)
        self.blur_slider.set(blur_val)
        self.blur_slider.pack(padx=15, pady=(2, 6), fill="x")

        pad_val = self.settings.get("padding_percent", 25)
        self.lbl_pad_title = ctk.CTkLabel(self.sidebar, text="Размер маски", font=(UI_FONT, 13), text_color=TEXT)
        self.lbl_pad_title.pack(padx=15, pady=(4, 0), anchor="w")
        self.lbl_pad_title.configure(height=18)

        self.pad_slider = FluentSlider(self.sidebar, from_=0, to=100, number_of_steps=100, button_color=TEXT, button_hover_color=SURFACE, progress_color=ACCENT, fg_color=TRACK, command=self.on_pad_slider_change)
        self.pad_slider.set(pad_val)
        self.pad_slider.pack(padx=15, pady=(2, 6), fill="x")

        fade_val = self.settings.get("fade_percent", 40)
        self.lbl_fade_title = ctk.CTkLabel(self.sidebar, text="Мягкость краёв", font=(UI_FONT, 13), text_color=TEXT)
        self.lbl_fade_title.pack(padx=15, pady=(4, 0), anchor="w")
        self.lbl_fade_title.configure(height=18)

        self.fade_slider = FluentSlider(self.sidebar, from_=0, to=100, number_of_steps=100, button_color=TEXT, button_hover_color=SURFACE, progress_color=ACCENT, fg_color=TRACK, command=self.on_fade_slider_change)
        self.fade_slider.set(fade_val)
        self.fade_slider.pack(padx=15, pady=(2, 6), fill="x")

        shape_val = self.settings.get("shape_percent", 100)
        self.lbl_shape_title = ctk.CTkLabel(self.sidebar, text=f"Форма маски: {self.get_shape_text(shape_val)}", font=(UI_FONT, 13), text_color=TEXT)
        self.lbl_shape_title.pack(padx=15, pady=(4, 0), anchor="w")
        self.lbl_shape_title.configure(height=18)

        self.shape_slider = FluentSlider(self.sidebar, from_=0, to=100, number_of_steps=100, button_color=TEXT, button_hover_color=SURFACE, progress_color=ACCENT, fg_color=TRACK, command=self.on_shape_slider_change)
        self.shape_slider.set(shape_val)
        self.shape_slider.pack(padx=15, pady=(2, 8), fill="x")

        self.div2 = ctk.CTkFrame(self.sidebar, height=1, fg_color=SURFACE)
        self.div2.pack(fill="x", padx=15, pady=5)

        self.analysis_btn_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.analysis_btn_frame.pack(padx=15, pady=4, fill="x")

        self.btn_analyze = ThemedButton(
            self.analysis_btn_frame,
            text="Найти лица",
            height=36,
            font=(UI_FONT, 14),
            fg_color=SURFACE,
            hover_color=HOVER,
            text_color=TEXT,
            border_width=1,
            border_color=BORDER,
            cursor=CURSOR_HAND,
            command=self.start_analysis_thread,
            state="disabled"
        )
        self.btn_analyze.pack(side="left", expand=True, fill="x", padx=(0, 4))

        self.btn_stop = ThemedButton(
            self.analysis_btn_frame,
            text="Стоп",
            width=60,
            height=36,
            font=(UI_FONT, 14),
            fg_color=SURFACE,
            hover_color=HOVER,
            text_color=ACCENT,
            border_width=1,
            border_color=BORDER,
            cursor=CURSOR_HAND,
            command=self.stop_analysis,
            state="disabled"
        )
        self.btn_stop.pack(side="right")
        self.btn_stop.configure(text_color=ERROR, hover_color=ERROR_HOVER)
        self.analysis_status = ctk.CTkLabel(self.sidebar, text="Добавьте видео, чтобы найти лица", font=(UI_FONT, 13), text_color=SECONDARY, anchor="w")
        self.analysis_status.pack(fill="x", padx=15, pady=(0, 2))
        self.analysis_status.configure(height=18)

        self.chk_export_labels = ctk.CTkCheckBox(
            self.sidebar,
            text="Показывать ID в экспорте",
            font=(UI_FONT, 13),
            text_color=TEXT,
            border_color=SECONDARY,
            checkmark_color=ON_ACCENT,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            cursor=CURSOR_HAND,
            command=self.on_export_labels_toggle
        )
        if self.settings.get("export_labels", False):
            self.chk_export_labels.select()
        else:
            self.chk_export_labels.deselect()
        self.chk_export_labels.pack(padx=15, pady=(6, 4), anchor="w")

        self.btn_export = ThemedButton(
            self.sidebar,
            text="Экспортировать видео",
            height=36,
            font=(UI_FONT, 14),
            fg_color=SURFACE,
            hover_color=HOVER,
            text_color=DISABLED_TEXT,
            border_width=1,
            border_color=BORDER,
            cursor=CURSOR_HAND,
            command=self.export_video,
            state="disabled"
        )
        self.btn_export.pack(padx=15, pady=(4, 5), fill="x")
        self.btn_export.configure(fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color=ON_ACCENT, text_color_disabled="#ffffff", border_width=0, corner_radius=4)
        self.export_status = ctk.CTkLabel(self.sidebar, text="MP4 · исходное разрешение · со звуком", font=(UI_FONT, 12), text_color=SECONDARY, anchor="w")
        self.export_status.pack(fill="x", padx=15, pady=0)
        self.export_status.configure(height=18)

        self.export_progress = ctk.CTkProgressBar(self.sidebar, height=4, progress_color=ACCENT, fg_color=TRACK)
        self.export_progress.set(0)
        self.export_progress.pack(padx=15, pady=(0, 6), fill="x")

        self.lbl_gallery = ctk.CTkLabel(self.sidebar, text="ЛИЦА В ВИДЕО", font=(UI_FONT, 12, "bold"), text_color=SECONDARY)
        self.lbl_gallery.pack(padx=15, pady=(4, 2), anchor="w")
        self.lbl_gallery.configure(height=20)

        self.gallery_frame = ctk.CTkScrollableFrame(self.sidebar, fg_color=WINDOW, scrollbar_button_color=("#858585", "#999999"), scrollbar_button_hover_color=("#606060", "#c5c5c5"), border_width=1, border_color=BORDER)
        self.gallery_frame.pack(padx=15, pady=5, fill="both", expand=True)


        self.lbl_error_log = ctk.CTkLabel(
            self.sidebar,
            text="",
            font=(UI_FONT, 13),
            text_color=ACCENT,
            wraplength=270,
            justify="left",
            anchor="w"
        )
        self.lbl_error_log.pack(padx=15, pady=(2, 2), fill="x", side="bottom")
        self.lbl_error_log.configure(height=0)

        self.btn_about = ThemedButton(
            self.sidebar,
            text="О программе",
            height=32,
            font=(UI_FONT, 13),
            fg_color=SURFACE,
            hover_color=HOVER,
            text_color=TEXT,
            cursor=CURSOR_HAND,
            command=lambda: show_about_dialog(self, CURSOR_HAND)
        )
        self.btn_about.pack(padx=15, pady=(5, 8), fill="x", side="bottom")

        # Правая часть (Canvas)
        self.right_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.right_frame.pack(side="right", expand=True, fill="both", padx=16, pady=16)
        self.preview_header = ctk.CTkLabel(self.right_frame, text="Предпросмотр", font=(UI_FONT, 24, "bold"), text_color=TEXT, anchor="w")
        self.preview_header.pack(fill="x", pady=(0, 4))
        self.preview_hint = ctk.CTkLabel(self.right_frame, text="Колесо — масштаб · двойной клик — выбор лица", font=(UI_FONT, 12), text_color=SECONDARY, anchor="w")
        self.preview_hint.pack(fill="x", pady=(0, 12))

        self.canvas_container = ctk.CTkFrame(self.right_frame, fg_color="#0b1016", border_width=1, border_color="#23262e")
        self.canvas_container.pack(expand=True, fill="both", padx=0, pady=(0, 10))

        self.canvas = tk.Canvas(self.canvas_container, bg="#0b1016", highlightthickness=0)
        self.canvas.pack(expand=True, fill="both", padx=8, pady=8)

        self.canvas.bind("<Configure>", self.on_canvas_resize)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<Button-4>", lambda e: self.on_mouse_zoom_step(1.05))
        self.canvas.bind("<Button-5>", lambda e: self.on_mouse_zoom_step(0.95))
        self.canvas.bind("<ButtonPress-1>", self.on_drag_start)
        self.canvas.bind("<B1-Motion>", self.on_drag_motion)
        self.canvas.bind("<Double-Button-1>", self.on_canvas_double_click)

        # Плеер
        self.player_controls = ctk.CTkFrame(self.right_frame, height=50, fg_color=SURFACE, border_width=1, border_color=BORDER)
        self.player_controls.pack(fill="x", side="bottom", padx=0, pady=0)

        self.btn_play = ThemedButton(
            self.player_controls, 
            text="▶  Смотреть",
            width=112,
            height=30,
            font=(UI_FONT, 14),
            fg_color=SURFACE,
            hover_color=HOVER,
            text_color=TEXT,
            cursor=CURSOR_HAND,
            border_width=1,
            border_color=BORDER,
            command=self.toggle_play,
            state="disabled"
        )
        self.btn_play.pack(side="left", padx=10, pady=10)

        self.time_label = ctk.CTkLabel(self.player_controls, text="00:00 / 00:00", font=(UI_FONT, 13), text_color=SECONDARY)
        self.time_label.pack(side="right", padx=10, pady=10)

        self.slider = FluentSlider(
            self.player_controls, 
            from_=0, 
            to=100, 
            button_color=TEXT,
            button_hover_color=SURFACE,
            progress_color=ACCENT,
            fg_color=BORDER,
            command=self.on_slider_seek,
            state="disabled"
        )
        self.slider._value_format = lambda value: f"{int(value / max(1, self.reader.fps if self.reader else 30)) // 60:02d}:{int(value / max(1, self.reader.fps if self.reader else 30)) % 60:02d}"
        self.slider.pack(side="left", expand=True, fill="x", padx=10, pady=10)
        for button in (self.btn_open, self.btn_save_proj, self.btn_load_proj,
                       self.btn_analyze, self.btn_stop, self.btn_export, self.btn_about, self.btn_play):
            button.configure(corner_radius=4, text_color_disabled="#767676")
        self.btn_export.configure(text_color_disabled="#ffffff", height=40)
        self.gallery_frame.pack_forget()
        self.gallery_frame.pack(padx=15, pady=5, fill="both", expand=True)
        self._command_icons = []
        if sys.platform == "win32":
            # Windows Fluent command glyphs, rendered separately from button text.
            glyphs = ((self.btn_open, "\ue8e5", ON_ACCENT),
                      (self.btn_save_proj, "\ue74e", TEXT),
                      (self.btn_load_proj, "\ue8da", TEXT),
                      (self.btn_export, "\ue898", ON_ACCENT),
                      (self.btn_about, "\ue946", TEXT))
            try:
                icon_font = ImageFont.truetype(os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts", "segmdl2.ttf"), 40)
                for button, glyph, color in glyphs:
                    images = []
                    for ink in color:
                        bitmap = Image.new("RGBA", (48, 48))
                        ImageDraw.Draw(bitmap).text((24, 24), glyph, font=icon_font, anchor="mm", fill=ink)
                        images.append(bitmap)
                    icon = ctk.CTkImage(light_image=images[0], dark_image=images[1], size=(16, 16))
                    self._command_icons.append(icon)
                    button.configure(image=icon, compound="left")
                self.btn_open.configure(text="Добавить видео")
            except OSError:
                logging.debug("Windows command icon font unavailable")
        for slider in (self.blur_slider, self.pad_slider, self.fade_slider, self.shape_slider, self.slider):
            slider.configure(button_color=ACCENT, button_hover_color=ACCENT_HOVER, height=16, button_length=14)


    def _apply_window_identity(self):
        try:
            self.iconbitmap(get_resource_path("app_icon.ico"))
            if sys.platform == "win32":
                import ctypes
                hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
                # Keep the system title bar, snap layouts and Windows 11 corners.
                value = ctypes.c_int(2)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(value), 4)
        except Exception:
            logging.debug("Window identity unavailable", exc_info=True)

    def _post_ui(self, callback, *args, **kwargs):
        self._ui_events.put((callback, args, kwargs))

    def _drain_ui_events(self):
        if self._closing:
            return
        while True:
            try:
                callback, args, kwargs = self._ui_events.get_nowait()
            except queue.Empty:
                break
            try:
                callback(*args, **kwargs)
            except Exception:
                logging.exception("UI event failed")
        self.after(50, self._drain_ui_events)

    def on_closing(self):
        logging.getLogger().removeHandler(self._status_events)
        logging.info("Вызван метод on_closing. Уничтожение приложения.")
        self._closing = True
        self.is_playing = False
        self.stop_analysis_flag = True

        if self.reader:
            try:
                self.reader.close()
            except Exception:
                pass

        try:
            self.clear_gallery_ui()
            self.unique_faces.clear()
            self.raw_frames = []
        except Exception:
            pass

        try:
            self.quit()
            self.destroy()
        except Exception:
            pass


    def save_project(self):
        logging.info("Событие: Нажата кнопка 'Сохранить проект'.")
        if not self.reader or not self.detected_boxes_cache:
            logging.warning("Сохранение отклонено: нет активного ридера или кэша.")
            return

        initial_dir = self.settings.get("last_directory", os.path.expanduser("~"))
        default_name = os.path.splitext(os.path.basename(self.reader.file_path))[0] + ".fbp"

        file_path = ctk.filedialog.asksaveasfilename(
            initialdir=initial_dir,
            initialfile=default_name,
            defaultextension=".fbp",
            filetypes=[("FaceBlur Project", "*.fbp")]
        )
        if not file_path:
            logging.info("Сохранение отменено пользователем.")
            return

        try:
            ProjectManager.save_project(
                file_path=file_path,
                video_path=self.reader.file_path,
                blurrer=self.blurrer,
                settings=self.settings,
                chk_export_labels=self.chk_export_labels,
                detected_boxes_cache=self.detected_boxes_cache,
                unique_faces=self.unique_faces
            )
            logging.info(f"Проект успешно сохранен в {file_path}")
            self.btn_save_proj.configure(text="Проект сохранён")
            self.after(3000, lambda: self.btn_save_proj.configure(text="Сохранить проект"))
        except Exception as e:
            logging.error(f"Ошибка сохранения проекта: {e}", exc_info=True)
            self.log_error(f"Ошибка сохранения: {e}")

    def load_project(self):
        logging.info("Событие: Нажата кнопка 'Открыть проект'.")
        initial_dir = self.settings.get("last_directory", os.path.expanduser("~"))

        file_path = ctk.filedialog.askopenfilename(
            initialdir=initial_dir,
            filetypes=[("FaceBlur Project", "*.fbp")]
        )
        if not file_path:
            logging.info("Открытие проекта отменено пользователем.")
            return

        try:
            project_data, detected_boxes_cache, active_states = ProjectManager.load_project(file_path)
            logging.info(f"Проект загружен из {file_path}. Найдено кадров в кэше: {len(detected_boxes_cache)}")

            video_path = project_data.get("video_path")
            if not os.path.exists(video_path):
                logging.error(f"Видеофайл из проекта не найден: {video_path}")
                self.log_error("Видео из проекта не найдено по пути!")
                return

            if self.reader:
                self.reader.close()

            self.reader = FFmpegVideoReader(video_path)
            self.update_status_bar_text()
            if self.reader.total_frames <= 0:
                raise ValueError("Не удалось определить количество кадров видео.")
            self.reader[0]
            self.raw_frames = self.reader

            total = len(self.raw_frames)
            if total == 0:
                logging.warning("Загруженное видео содержит 0 кадров.")
                return

            self.detected_boxes_cache = detected_boxes_cache

            self.blur_slider.set(project_data.get("blur_percent", 70))
            self.on_blur_slider_change(project_data.get("blur_percent", 70))

            self.pad_slider.set(project_data.get("padding_percent", 25))
            self.on_pad_slider_change(project_data.get("padding_percent", 25))

            self.fade_slider.set(project_data.get("fade_percent", 40))
            self.on_fade_slider_change(project_data.get("fade_percent", 40))

            self.shape_slider.set(project_data.get("shape_percent", 100))
            self.on_shape_slider_change(project_data.get("shape_percent", 100))

            if project_data.get("export_labels", False):
                self.chk_export_labels.select()
            else:
                self.chk_export_labels.deselect()
            self.on_export_labels_toggle()

            self.clear_gallery_ui()
            self.build_unique_faces_from_cache(active_states)

            self.slider.configure(state="normal", from_=0, to=total - 1, number_of_steps=total)
            self.slider.set(0)
            self.btn_play.configure(state="normal")
            
            self.btn_analyze.configure(
                text="Повторить анализ",
                text_color=SUCCESS,
                state="normal"
            )
            self.btn_save_proj.configure(state="normal")
            self.btn_export.configure(
                text="Экспортировать видео",
                state="normal", 
                text_color=ON_ACCENT
            )
            
            self.populate_gallery_ui()
            self.show_frame(0)

        except Exception as e:
            logging.error(f"Ошибка загрузки проекта: {e}", exc_info=True)
            self.log_error(f"Ошибка загрузки: {e}")

    def on_canvas_double_click(self, event):
        logging.info(f"Событие: Двойной клик на холсте [x={event.x}, y={event.y}]. Текущий кадр: {self.current_frame_idx}")
        if not self.current_pil_img or not self.raw_frames:
            logging.warning("Двойной клик проигнорирован: нет изображения на холсте.")
            self.reset_zoom()
            return

        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        img_w, img_h = self.current_pil_img.size

        scale = min(canvas_w / img_w, canvas_h / img_h) * self.zoom_factor
        new_w = max(10, int(img_w * scale))
        new_h = max(10, int(img_h * scale))

        center_x = (canvas_w // 2) + self.pan_x
        center_y = (canvas_h // 2) + self.pan_y

        img_x1 = center_x - (new_w // 2)
        img_y1 = center_y - (new_h // 2)

        # Hit-test the exact downscaled boxes drawn in the preview, without
        # extending them by the blur mask padding. Use each rendered axis scale
        # to account for integer rounding when the image is resized.
        click_video_x = (event.x - img_x1) * img_w / new_w
        click_video_y = (event.y - img_y1) * img_h / new_h
        clicked_id = None
        faces = getattr(self, "_preview_faces", [])
        if 0 <= click_video_x < img_w and 0 <= click_video_y < img_h:
            # The last drawn rectangle is on top when detections overlap.
            for face in reversed(faces):
                bbox = face.get('bbox', face.get('box', [0, 0, 0, 0])) if isinstance(face, dict) else face[:4]
                x1, y1, x2, y2 = bbox
                if x1 <= click_video_x <= x2 and y1 <= click_video_y <= y2:
                    raw_id = face.get('id', face.get('track_id', 0)) if isinstance(face, dict) else (face[4] if len(face) > 4 else 0)
                    candidate = int(raw_id)
                    if candidate in self.unique_faces:
                        clicked_id = candidate
                        break

        if clicked_id is not None and clicked_id in self.unique_faces:
            logging.info(f"Двойной клик попал на объект ID #{clicked_id}. Переключение состояния блюра.")
            self.toggle_face_blur(clicked_id)
            self.populate_gallery_ui()
        else:
            logging.info(f"Двойной клик не попал в рамку лица в видео-точке [x={click_video_x}, y={click_video_y}]. Сброс зума.")
            self.reset_zoom()

    def log_error(self, message: str):
        self.set_status(f"Ошибка: {message}")
        logging.error(f"UI Error Log displayed: {message}")
        self.lbl_error_log.configure(text=f"⚠️ {message}")

    def clear_error_log(self):
        self.lbl_error_log.configure(text="")

    def get_shape_text(self, val: int) -> str:
        if val >= 90:
            return "Овал"
        elif val <= 10:
            return "Квадрат"
        return "Скругление"

    def load_settings(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "blur_percent": 70, 
            "padding_percent": 25, 
            "fade_percent": 40,
            "shape_percent": 100,
            "export_labels": False,
            "last_directory": os.path.expanduser("~")
        }

    def save_settings(self):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.settings, f)
            os.chmod(CONFIG_FILE, 0o600)
        except Exception:
            logging.exception("Не удалось сохранить настройки")

    def on_export_labels_toggle(self):
        val = bool(self.chk_export_labels.get())
        logging.info(f"Событие: Чекбокс 'Показывать ID в экспорте' переключен в состояние: {val}")
        self.settings["export_labels"] = val
        self.save_settings()

    def stop_analysis(self):
        logging.info("Событие: Нажата кнопка остановки анализа (⏹).")
        if self.is_analysing:
            self.stop_analysis_flag = True
            self.btn_stop.configure(state="disabled")

    def reset_zoom(self, event=None):
        logging.info("Событие: Сброс зума холста.")
        self.zoom_factor = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.render_canvas_image()

    def on_mouse_wheel(self, event):
        if event.delta > 0:
            factor = 1.05
        else:
            factor = 0.95
        self.zoom_factor = max(1.0, min(4.0, self.zoom_factor * factor))
        if self.zoom_factor == 1.0:
            self.pan_x = 0
            self.pan_y = 0
        self.render_canvas_image()

    def on_mouse_zoom_step(self, factor):
        self.zoom_factor = max(1.0, min(4.0, self.zoom_factor * factor))
        if self.zoom_factor == 1.0:
            self.pan_x = 0
            self.pan_y = 0
        self.render_canvas_image()

    def on_drag_start(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def on_drag_motion(self, event):
        if self.zoom_factor > 1.0:
            dx = event.x - self.drag_start_x
            dy = event.y - self.drag_start_y
            self.pan_x += dx
            self.pan_y += dy
            self.drag_start_x = event.x
            self.drag_start_y = event.y
            self.render_canvas_image()

    def on_canvas_resize(self, event):
        self.render_canvas_image()

    def set_status(self, message):
        self.lbl_status_left.set_message(message)
        self._update_compute_status()

    def _update_compute_status(self):
        if not self.detector:
            text = "Распознавание: ещё не запущено"
        elif self.detector.backend == "directml":
            text = "GPU · DirectML"
        elif self.detector.backend == "cpu":
            text = "CPU · OpenCV" if "OpenCV" in self.detector.device_description else "CPU"
        else:
            text = self.detector.device_description
        self.lbl_status_right.configure(text=text, text_color=ACCENT if self.detector and self.detector.backend != "cpu" else SECONDARY)

    def on_status_bar_resize(self, event):
        self._update_compute_status()

    def update_status_bar_text(self):
        if self.video_status_error:
            self.set_status(self.video_status_error)
        elif self.reader:
            self.set_status(
                f"Файл: {os.path.basename(self.reader.file_path)} · "
                f"{self.reader.width}×{self.reader.height} · {self.reader.codec} · "
                f"{self.reader.fps:.2f} FPS · кадров: {self.reader.total_frames}"
            )
        else:
            self.set_status("Готов к работе")

    def render_canvas_image(self):
        if not self.current_pil_img:
            self.canvas.delete("all")
            cx = self.canvas.winfo_width() // 2
            cy = self.canvas.winfo_height() // 2
            self.canvas.create_text(cx, cy - 24, text="Лица под вашим контролем", fill="#ffffff", font=(UI_FONT, 22, "bold"))
            self.canvas.create_text(cx, cy + 16, text="Добавьте видео → найдите лица → сохраните результат", fill="#b8c4d0", font=(UI_FONT, 13))
            return

        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()

        if canvas_w < 50 or canvas_h < 50:
            self.canvas.update_idletasks()
            canvas_w = self.canvas.winfo_width()
            canvas_h = self.canvas.winfo_height()

        if canvas_w < 50 or canvas_h < 50:
            self.after(50, self.render_canvas_image)
            return

        img_w, img_h = self.current_pil_img.size
        scale = min(canvas_w / img_w, canvas_h / img_h) * self.zoom_factor

        new_w = max(10, int(img_w * scale))
        new_h = max(10, int(img_h * scale))

        resized_img = self.current_pil_img.resize((new_w, new_h), Image.Resampling.BILINEAR)
        self.tk_image_ref = ImageTk.PhotoImage(resized_img, master=self.canvas)

        self.canvas.delete("all")
        center_x = (canvas_w // 2) + self.pan_x
        center_y = (canvas_h // 2) + self.pan_y
        self.canvas.create_image(center_x, center_y, image=self.tk_image_ref, anchor="center")

    def on_blur_slider_change(self, value):
        val = int(value)
        logging.info(f"Слайдер: Изменена сила размытия -> {val}%")
        self.blurrer.set_blur_percent(val)
        self.settings["blur_percent"] = val
        self.save_settings()
        self.show_frame(self.current_frame_idx)

    def on_pad_slider_change(self, value):
        val = int(value)
        logging.info(f"Слайдер: Изменен размер маски -> {val}%")
        self.blurrer.set_padding_percent(val)
        self.settings["padding_percent"] = val
        self.save_settings()
        self.show_frame(self.current_frame_idx)

    def on_fade_slider_change(self, value):
        val = int(value)
        logging.info(f"Слайдер: Изменена мягкость краев (Fade) -> {val}%")
        self.blurrer.set_fade_percent(val)
        self.settings["fade_percent"] = val
        self.save_settings()
        self.show_frame(self.current_frame_idx)

    def on_shape_slider_change(self, value):
        val = int(value)
        logging.info(f"Слайдер: Изменена форма маски -> {val}%")
        self.blurrer.set_shape_percent(val)
        self.lbl_shape_title.configure(text=f"Форма маски: {self.get_shape_text(val)}")
        self.settings["shape_percent"] = val
        self.save_settings()
        self.show_frame(self.current_frame_idx)

    def open_video(self):
        logging.info("Событие: Нажата кнопка '+ Выбрать видео'.")
        self.clear_error_log()
        try:
            if self.is_analysing:
                self.stop_analysis_flag = True

            initial_dir = self.settings.get("last_directory", os.path.expanduser("~"))

            file_path = ctk.filedialog.askopenfilename(
                initialdir=initial_dir,
                filetypes=[("Video files", "*.mp4 *.mov *.mkv *.avi")]
            )
            if not file_path:
                logging.info("Диалог выбора видео отменен.")
                return

            logging.info(f"Пользователь выбрал файл: {file_path}")
            self.settings["last_directory"] = os.path.dirname(file_path)
            self.save_settings()

            self.selected_video_path = file_path
            self.video_status_error = None
            if self.reader:
                self.reader.close()
            self.reader = None

            self.is_playing = False
            self.btn_play.configure(text="▶  Смотреть")
            self.btn_play.configure(state="disabled")
            self.btn_analyze.configure(text="Найти лица", state="disabled")
            self.btn_save_proj.configure(state="disabled")
            self.btn_export.configure(state="disabled")
            self.btn_stop.configure(state="disabled")
            self.slider.configure(state="disabled")
            self.time_label.configure(text="00:00 / 00:00")
            self.current_frame_idx = 0
            self.raw_frames = []
            self.current_pil_img = None
            self.tk_image_ref = None
            self.canvas.delete("all")
            self.detected_boxes_cache.clear()
            self.unique_faces.clear()
            self.reset_zoom()
            self.export_progress.set(0)
            self.clear_gallery_ui()

            self.reader = FFmpegVideoReader(file_path)
            self.update_status_bar_text()

            if self.reader.total_frames <= 0:
                raise ValueError("Не удалось определить количество кадров видео.")
            self.reader[0]  # Проверяем декодирование до включения управления.
            self.raw_frames = self.reader
            total = len(self.raw_frames)
            logging.info(f"Видео открыто. Кадров по данным файла: {total}; кадры читаются по мере надобности.")

            if total > 0:
                self.slider.configure(state="normal", from_=0, to=total - 1, number_of_steps=total)
                self.slider.set(0)
                self.btn_play.configure(state="normal")
                self.btn_analyze.configure(
                    text="Найти лица",
                    text_color=ACCENT,
                    state="normal"
                )
                self.btn_save_proj.configure(state="disabled")
                self.btn_stop.configure(state="disabled")
                
                self.btn_export.configure(
                    text="Экспортировать видео",
                    state="disabled", 
                    text_color=DISABLED_TEXT
                )
                self.show_frame(0)
            else:
                raise ValueError("Не удалось декодировать кадры видео. Проверьте файл или кодек.")
        except Exception as e:
            logging.error(f"Критическая ошибка при открытии видео: {e}", exc_info=True)
            if self.reader:
                self.reader.close()
            self.video_status_error = f"Ошибка: {e}"
            self.update_status_bar_text()
            self.log_error(str(e))

    def export_video(self):
        logging.info("Событие: Нажата кнопка 'Экспорт'.")
        if not self.raw_frames or self.is_exporting:
            logging.warning("Экспорт заблокирован: нет кадров или экспорт уже активен.")
            return

        initial_dir = self.settings.get("last_directory", os.path.expanduser("~"))
        default_name = "blurred_" + os.path.basename(self.reader.file_path)

        output_path = ctk.filedialog.asksaveasfilename(
            initialdir=initial_dir,
            initialfile=default_name,
            defaultextension=".mp4",
            filetypes=[("MP4 Video", "*.mp4")]
        )
        if not output_path:
            logging.info("Экспорт отменен пользователем.")
            return

        logging.info(f"Выбран путь для экспорта видео: {output_path}")
        self.settings["last_directory"] = os.path.dirname(output_path)
        self.save_settings()

        self.is_exporting = True
        self.export_status.configure(text="Подготовка экспорта…", text_color=SECONDARY)
        self.export_progress.set(0)
        
        self.btn_export.configure(
            state="disabled", 
            text="Экспортируется…",
            text_color=ON_ACCENT
        )
        active_ids = self.get_active_blur_ids()
        save_labels = bool(self.chk_export_labels.get())
        threading.Thread(target=self._run_export, args=(output_path, active_ids, save_labels), daemon=True).start()

    def _run_export(self, output_path, active_blur_ids, save_labels):
        writer = None
        try:
            logging.info("Фоновый поток экспорта запущен.")
            writer = FFmpegVideoWriter(
                output_path=output_path,
                width=self.reader.width,
                height=self.reader.height,
                fps=self.reader.fps,
                source_audio_path=self.reader.file_path
            )

            total_frames = len(self.raw_frames)

            for i, frame in enumerate(self.raw_frames):
                faces_data = self.detected_boxes_cache.get(i, [])
                
                if save_labels:
                    out_frame = self.blurrer.apply_blur_and_labels(frame, faces_data, active_blur_ids)
                else:
                    out_frame = self.blurrer.apply_blur_only(frame, faces_data, active_blur_ids)

                writer.write_frame(out_frame)
                
                progress_ratio = (i + 1) / total_frames
                if i % max(1, total_frames // 100) == 0 or i + 1 == total_frames:
                    self._post_ui(self._update_export_progress, progress_ratio, i + 1, total_frames)

            writer.close()
            logging.info("Экспорт видео успешно завершен.")
            self._post_ui(self._on_export_finished_ui)
        except Exception as e:
            logging.error(f"Ошибка в потоке экспорта: {e}", exc_info=True)
            self._post_ui(self._on_export_failed_ui, str(e))

    def _on_export_failed_ui(self, message):
        self.is_exporting = False
        self.export_status.configure(text="Не удалось сохранить видео", text_color=ERROR)
        self.btn_export.configure(text="Экспортировать видео", state="normal")
        self.log_error(message)

    def _update_export_progress(self, ratio, current, total):
        self.set_status(f"Экспорт · {int(ratio * 100)}% · кадр {current} из {total}")
        self.export_progress.set(ratio)
        self.export_status.configure(text=f"Экспорт · {int(ratio * 100)}% · кадр {current} из {total}", text_color=SECONDARY)

    def _on_export_finished_ui(self):
        self.is_exporting = False
        self._sync_video_frame_count_ui()
        self.set_status("Экспорт завершён · видео сохранено")
        self.export_status.configure(text="Видео сохранено", text_color=SUCCESS)
        self.export_progress.set(1.0)
        self.btn_export.configure(
            text="Проект сохранёно",
            text_color=ON_ACCENT,
            state="normal"
        )
        self.after(5000, self._reset_export_button_ui)

    def _reset_export_button_ui(self):
        if not self.is_exporting:
            self.export_progress.set(0)
            self.btn_export.configure(
                text="Экспортировать видео",
                text_color=ON_ACCENT,
                state="normal"
            )

    def clear_gallery_ui(self):
        logging.info("Очистка UI галереи объектов...")
        self.gallery_photo_refs.clear()
        for widget in self.gallery_frame.winfo_children():
            widget.destroy()

    def start_analysis_thread(self):
        logging.info("Событие: Нажата кнопка 'Анализировать' (⚡).")
        self.is_analysing = True
        self.analysis_status.configure(text="Поиск лиц…", text_color=ACCENT)
        self.stop_analysis_flag = False
        self.btn_analyze.configure(state="disabled", text="Анализ…", text_color=TEXT)
        self.btn_stop.configure(state="normal")
        self.btn_play.configure(state="disabled")
        
        self.btn_export.configure(state="disabled", text_color=DISABLED_TEXT)
        self.export_progress.set(0)
        self.clear_gallery_ui()
        self.unique_faces.clear()
        threading.Thread(target=self._run_full_analysis, daemon=True).start()

    def _run_full_analysis(self):
        try:
            logging.info("Фоновый поток анализа: старт детекции лиц.")
            if not self.detector:
                model_path = get_resource_path(default_model_filename())
                logging.info(f"Загрузка весов YOLOv8 из: {model_path}")
                self.detector = FaceDetector(model_path=model_path)

            self.detected_boxes_cache.clear()
            total_frames = len(self.raw_frames)

            for i, frame in enumerate(self.raw_frames):
                if self.stop_analysis_flag:
                    logging.info("Анализ прерван пользователем по флагу stop.")
                    break

                tracked_faces = self.detector.track_faces(frame)
                self.detected_boxes_cache[i] = tracked_faces

                progress = int(((i + 1) / total_frames) * 100)
                if i % max(1, total_frames // 100) == 0 or i + 1 == total_frames:
                    self._post_ui(self.set_status, f"Поиск лиц · {progress}% · кадр {i + 1} из {total_frames}")
                    self._post_ui(self.analysis_status.configure, text=f"Поиск лиц · {progress}%")

            logging.info(f"Детекция завершена. Всего обработано кадров: {len(self.detected_boxes_cache)}")
            self._post_ui(self._on_analysis_finished_ui)
        except Exception as e:
            logging.error(f"Ошибка в фоновом потоке анализа: {e}", exc_info=True)
            self._post_ui(self._on_analysis_failed_ui, str(e))

    def _on_analysis_failed_ui(self, message):
        self.is_analysing = False
        self.analysis_status.configure(text="Ошибка анализа · можно повторить", text_color=ERROR)
        self.btn_analyze.configure(text="Найти лица", state="normal")
        self.btn_stop.configure(state="disabled")
        self.log_error(message)

    def build_unique_faces_from_cache(self, active_states=None):
        self.unique_faces.clear()
        if active_states is None:
            active_states = {}

        logging.info("Начало построения словаря unique_faces из кэша детекции...")
        face_count_raw = 0

        for frame_idx, faces in self.detected_boxes_cache.items():
            if frame_idx >= len(self.raw_frames):
                continue
            if not faces:
                continue

            ids = [int(face.get('id', face.get('track_id', 0))) if isinstance(face, dict)
                   else int(face[4]) if len(face) > 4 and face[4] is not None else 0
                   for face in faces if isinstance(face, (dict, list, tuple))]
            if all(t_id in self.unique_faces for t_id in ids):
                continue
            frame = self.raw_frames[frame_idx]

            h, w = frame.shape[:2]

            for face in faces:
                face_count_raw += 1
                if isinstance(face, dict):
                    raw_id = face.get('id', face.get('track_id', 0))
                    t_id = int(raw_id)
                    bbox = face.get('bbox', face.get('box', [0, 0, 0, 0]))
                elif isinstance(face, (list, tuple)) and len(face) >= 4:
                    bbox = face[:4]
                    t_id = int(face[4]) if len(face) > 4 and face[4] is not None else 0
                else:
                    logging.warning(f"Неизвестный формат объекта лица в кадре {frame_idx}: {face}")
                    continue

                if t_id not in self.unique_faces:
                    try:
                        x1, y1, x2, y2 = [int(v) for v in bbox]
                        x1 = max(0, min(w - 2, x1))
                        y1 = max(0, min(h - 2, y1))
                        x2 = max(x1 + 1, min(w, x2))
                        y2 = max(y1 + 1, min(h, y2))

                        if x2 > x1 and y2 > y1:
                            crop = frame[y1:y2, x1:x2]
                            if crop.size > 0:
                                crop_rgb = crop[:, :, ::-1]
                                pil_img = Image.fromarray(crop_rgb)
                                
                                is_enabled = active_states.get(str(t_id), active_states.get(t_id, True))
                                self.unique_faces[t_id] = {
                                    'pil_image': pil_img,
                                    'enabled': is_enabled,
                                    'widget': None
                                }
                                logging.info(f"Добавлено уникальное лицо ID #{t_id} (crop shape: {crop.shape})")
                            else:
                                logging.warning(f"Кроп для лица ID #{t_id} имеет нулевой размер.")
                    except Exception as ex:
                        logging.error(f"Ошибка при вырезании лица ID #{t_id}: {ex}", exc_info=True)

        logging.info(f"Всего сырых детектирований: {face_count_raw}. Уникальных валидных лиц собрано: {len(self.unique_faces)}")

    def _sync_video_frame_count_ui(self):
        if self.reader and len(self.reader) > 0:
            total = len(self.reader)
            self.slider.configure(to=total - 1, number_of_steps=total)
            self.update_status_bar_text()

    def _on_analysis_finished_ui(self):
        logging.info("UI: Анализ завершен, обновление элементов интерфейса...")
        self.is_analysing = False
        self.btn_stop.configure(state="disabled")
        self._sync_video_frame_count_ui()
        
        self.build_unique_faces_from_cache()
        self.set_status("Анализ остановлен" if self.stop_analysis_flag else f"Анализ завершён · найдено лиц: {len(self.unique_faces)}")
        self.analysis_status.configure(text=("Анализ остановлен" if self.stop_analysis_flag else f"Готово · найдено лиц: {len(self.unique_faces)}"), text_color=SUCCESS)

        if self.stop_analysis_flag:
            self.btn_analyze.configure(
                text="Продолжить анализ",
                text_color=ACCENT,
                state="normal"
            )
        else:
            self.btn_analyze.configure(
                text="Повторить анализ",
                text_color=SUCCESS,
                state="normal"
            )

        self.btn_save_proj.configure(state="normal")
        self.btn_play.configure(state="normal")
        
        self.btn_export.configure(
            text="Экспортировать видео",
            state="normal", 
            text_color=ON_ACCENT
        )
        
        logging.info("Вызов populate_gallery_ui() и show_frame(0)")
        self.populate_gallery_ui()
        self.after(50, lambda: self.show_frame(0))

    def populate_gallery_ui(self):
        self.clear_gallery_ui()
        self.lbl_gallery.configure(text=f"ЛИЦА В ВИДЕО  ·  {len(self.unique_faces)}")
        if not self.unique_faces:
            logging.warning("populate_gallery_ui прерван: словарь unique_faces пуст!")
            return

        logging.info(f"Начало пакетной отрисовки галереи. Всего объектов: {len(self.unique_faces)}")
        
        sorted_ids = sorted(self.unique_faces.keys(), key=lambda x: int(x))
        self._render_gallery_batch(sorted_ids, 0)

    def _render_gallery_batch(self, ids_list, index):
        batch_size = 5
        end_idx = min(index + batch_size, len(ids_list))
        
        try:
            for i in range(index, end_idx):
                t_id = ids_list[i]
                data = self.unique_faces[t_id]
                
                row = ctk.CTkFrame(self.gallery_frame, fg_color=SURFACE, corner_radius=6, border_width=1, border_color=BORDER)
                row.pack(fill="x", pady=4, padx=4)
                data['widget'] = row

                # Прямое создание standard PhotoImage с мастером `self` для предотвращения RuntimeError
                pil_img = data['pil_image'].resize((32, 32), Image.Resampling.BILINEAR)
                tk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(32, 32))
                self.gallery_photo_refs.append(tk_img)

                lbl_img = ctk.CTkLabel(row, image=tk_img, text="", width=32, height=32, font=self.gallery_font)
                lbl_img.image = tk_img
                lbl_img.pack(side="left", padx=(8, 6), pady=6)

                chk = ctk.CTkCheckBox(
                    row, 
                    text=f"Лицо #{int(t_id):02d}",
                    font=self.gallery_font,
                    text_color=TEXT,
                    border_color=SECONDARY,
                    checkmark_color=ON_ACCENT,
                    fg_color=ACCENT,
                    hover_color=ACCENT_HOVER,
                    cursor=CURSOR_HAND,
                    command=lambda id_=t_id: self.toggle_face_blur(id_)
                )
                if data['enabled']:
                    chk.select()
                else:
                    chk.deselect()
                chk.pack(side="left", padx=4, pady=6, fill="y", expand=True)

                logging.info(f"Батч-рендеринг: успешно создан элемент галереи для ID #{t_id}")

            if end_idx < len(ids_list):
                self.after(10, lambda: self._render_gallery_batch(ids_list, end_idx))
            else:
                self.gallery_frame.update_idletasks()
                logging.info("Пакетная отрисовка галереи полностью завершена.")
        except Exception as e:
            logging.error(f"Ошибка в процессе пакетного рендеринга галереи: {e}", exc_info=True)

    def toggle_face_blur(self, track_id):
        tid = int(track_id)
        if tid in self.unique_faces:
            curr = self.unique_faces[tid]['enabled']
            self.unique_faces[tid]['enabled'] = not curr
            logging.info(f"Переключение состояния блюра для ID #{tid}: {'ВКЛ' if not curr else 'ВЫКЛ'}")
            self.show_frame(self.current_frame_idx)

    def get_active_blur_ids(self):
        return {t_id for t_id, data in self.unique_faces.items() if data['enabled']}

    def update_gallery_highlighting(self, active_frame_ids):
        for t_id, data in self.unique_faces.items():
            widget = data.get('widget')
            if widget:
                if t_id in active_frame_ids:
                    widget.configure(border_color=ACCENT, border_width=1.5)
                else:
                    widget.configure(border_color=BORDER, border_width=1)

    def show_frame(self, frame_idx: int):
        if not self.raw_frames or frame_idx >= len(self.raw_frames):
            return

        self.current_frame_idx = frame_idx
        faces_in_current_frame = self.detected_boxes_cache.get(frame_idx, [])
        frame_active_ids = {int(f.get('id', f.get('track_id', 0)) if isinstance(f, dict) else (f[4] if len(f) > 4 else 0)) for f in faces_in_current_frame}

        self.update_gallery_highlighting(frame_active_ids)
        active_blur_ids = self.get_active_blur_ids()

        source_frame = self.raw_frames[frame_idx]
        source_h, source_w = source_frame.shape[:2]
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        if canvas_w < 50 or canvas_h < 50:
            canvas_w, canvas_h = 960, 540

        preview_scale = min(1.0, canvas_w / source_w, canvas_h / source_h)
        if preview_scale < 1.0:
            preview_w = max(2, int(source_w * preview_scale))
            preview_h = max(2, int(source_h * preview_scale))
            preview_frame = cv2.resize(source_frame, (preview_w, preview_h), interpolation=cv2.INTER_AREA)
            preview_faces = []
            for face in faces_in_current_frame:
                if isinstance(face, dict):
                    scaled_face = dict(face)
                    bbox = face.get('bbox', face.get('box', [0, 0, 0, 0]))
                    scaled_face['bbox'] = tuple(int(value * preview_scale) for value in bbox)
                    preview_faces.append(scaled_face)
                else:
                    scaled_face = list(face)
                    scaled_face[:4] = [int(value * preview_scale) for value in face[:4]]
                    preview_faces.append(scaled_face)
        else:
            preview_frame = source_frame
            preview_faces = faces_in_current_frame

        self._preview_faces = preview_faces
        frame_bgr = self.blurrer.apply_blur_and_labels(
            preview_frame,
            preview_faces,
            active_blur_ids,
            kernel_scale=preview_scale,
        )

        frame_rgb = frame_bgr[:, :, ::-1]
        self.current_pil_img = Image.fromarray(frame_rgb)
        self.render_canvas_image()

        curr_sec = int(frame_idx / self.reader.fps)
        total_sec = int(len(self.raw_frames) / self.reader.fps)
        self.time_label.configure(
            text=f"{curr_sec // 60:02d}:{curr_sec % 60:02d} / {total_sec // 60:02d}:{total_sec % 60:02d}"
        )

    def on_slider_seek(self, value):
        self.is_playing = False
        self.btn_play.configure(text="▶  Смотреть")
        idx = int(value)
        logging.info(f"Событие: Перемотка слайдером на кадр #{idx}")
        self.show_frame(idx)

    def toggle_play(self):
        if not self.raw_frames:
            return
        self.is_playing = not self.is_playing
        logging.info(f"Событие: Кнопка Play/Pause нажата. Статус: {'PLAY' if self.is_playing else 'PAUSE'}")
        if self.is_playing:
            self.btn_play.configure(text="Ⅱ  Пауза")
            self._playback_anchor_frame = self.current_frame_idx
            self._playback_anchor_time = time.perf_counter()
            self.play_loop()
        else:
            self.btn_play.configure(text="▶  Смотреть")

    def play_loop(self):
        if not self.is_playing:
            return
        
        if self.current_frame_idx < len(self.raw_frames) - 1:
            elapsed = time.perf_counter() - self._playback_anchor_time
            expected_frame = self._playback_anchor_frame + max(1, int(elapsed * self.reader.fps))
            self.current_frame_idx = min(expected_frame, len(self.raw_frames) - 1)
            self.slider.set(self.current_frame_idx)
            render_started = time.perf_counter()
            self.show_frame(self.current_frame_idx)
            render_ms = int((time.perf_counter() - render_started) * 1000)
            delay = max(1, int(1000 / self.reader.fps) - render_ms)
            self.after(delay, self.play_loop)
        else:
            self.is_playing = False
            self.btn_play.configure(text="▶  Смотреть")
