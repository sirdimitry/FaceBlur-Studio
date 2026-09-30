import json
import os
import sys
import threading
import queue
import logging
import datetime
import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageTk
from core.video_reader import FFmpegVideoReader
from core.detector import FaceDetector
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

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

CURSOR_HAND = "pointinghand" if sys.platform == "darwin" else "hand2"


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Разделитель нового запуска с датой, временем и секундами
        start_time_str = datetime.datetime.now().strftime("%H:%M:%S %d.%m.%Y")
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as log_file:
                log_file.write(f"\n******************** {start_time_str} ********************\n")
        except Exception:
            pass

        logging.info("Инициализация MainWindow FaceBlur Studio v1.1.23")
        self.title("FaceBlur Studio — v1.1.23")
        
        self.geometry("1100x750")
        if sys.platform == "win32":
            self.state("zoomed")
        self.deiconify()
        self.focus_force()

        # Безопасный шрифт для галереи
        self.gallery_font = ctk.CTkFont(family="Helvetica", size=11, weight="bold")
        self.gallery_photo_refs = []  # Защита миниатюр от сборщика мусора

        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.configure(fg_color="#121316")

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
        self.status_bar = ctk.CTkFrame(self, height=28, corner_radius=0, fg_color="#16171a", border_width=1, border_color="#262930")
        self.status_bar.pack(side="bottom", fill="x")
        self.status_bar.bind("<Configure>", self.on_status_bar_resize)

        self.lbl_status_right = ctk.CTkLabel(
            self.status_bar, 
            text="", 
            font=("Helvetica", 11),
            text_color="#8a8f9d",
            anchor="e"
        )
        self.lbl_status_right.pack(side="right", padx=(5, 15), pady=2)

        self.lbl_status_left = ctk.CTkLabel(
            self.status_bar, 
            text="Готов к работе", 
            font=("Helvetica", 11),
            text_color="#8a8f9d",
            anchor="w"
        )
        self.lbl_status_left.pack(side="left", padx=(15, 5), pady=2, fill="x", expand=True)

        # Левая панель Инспектора
        self.sidebar = ctk.CTkFrame(self, width=310, corner_radius=0, fg_color="#1e2025", border_width=1, border_color="#2b2e36")
        self.sidebar.pack(side="left", fill="y", padx=0, pady=0)

        self.lbl_inspector_header = ctk.CTkLabel(
            self.sidebar,
            text="INSPECTOR / НАСТРОЙКИ",
            font=("Helvetica", 11, "bold"),
            text_color="#e54e38",
            anchor="w"
        )
        self.lbl_inspector_header.pack(padx=15, pady=(12, 8), fill="x")

        self.btn_open = ctk.CTkButton(
            self.sidebar, 
            text="+ Выбрать видео", 
            height=38, 
            font=("Helvetica", 13, "bold"),
            fg_color="#2b2e36",
            hover_color="#383c47",
            text_color="#d1d5db",
            cursor=CURSOR_HAND,
            border_width=1,
            border_color="#3a3e4a",
            command=self.open_video
        )
        self.btn_open.pack(padx=15, pady=(0, 6), fill="x")

        self.project_btn_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.project_btn_frame.pack(padx=15, pady=(0, 10), fill="x")

        self.btn_save_proj = ctk.CTkButton(
            self.project_btn_frame,
            text="📁 Сохранить",
            height=28,
            font=("Helvetica", 11),
            fg_color="#252830",
            hover_color="#323642",
            text_color="#b0b5c0",
            cursor=CURSOR_HAND,
            border_width=1,
            border_color="#323642",
            command=self.save_project,
            state="disabled"
        )
        self.btn_save_proj.pack(side="left", expand=True, fill="x", padx=(0, 2))

        self.btn_load_proj = ctk.CTkButton(
            self.project_btn_frame,
            text="📂 Открыть",
            height=28,
            font=("Helvetica", 11),
            fg_color="#252830",
            hover_color="#323642",
            text_color="#b0b5c0",
            cursor=CURSOR_HAND,
            border_width=1,
            border_color="#323642",
            command=self.load_project
        )
        self.btn_load_proj.pack(side="right", expand=True, fill="x", padx=(2, 0))

        self.div1 = ctk.CTkFrame(self.sidebar, height=1, fg_color="#2b2e36")
        self.div1.pack(fill="x", padx=15, pady=5)

        blur_val = self.settings.get("blur_percent", 70)
        self.lbl_blur_title = ctk.CTkLabel(self.sidebar, text=f"Сила размытия: {blur_val}%", font=("Helvetica", 11), text_color="#c2c7d0")
        self.lbl_blur_title.pack(padx=15, pady=(4, 0), anchor="w")

        self.blur_slider = ctk.CTkSlider(self.sidebar, from_=0, to=100, number_of_steps=100, button_color="#d1d5db", button_hover_color="#ffffff", progress_color="#e54e38", fg_color="#16171a", command=self.on_blur_slider_change)
        self.blur_slider.set(blur_val)
        self.blur_slider.pack(padx=15, pady=(2, 6), fill="x")

        pad_val = self.settings.get("padding_percent", 25)
        self.lbl_pad_title = ctk.CTkLabel(self.sidebar, text=f"Размер маски: {pad_val}%", font=("Helvetica", 11), text_color="#c2c7d0")
        self.lbl_pad_title.pack(padx=15, pady=(4, 0), anchor="w")

        self.pad_slider = ctk.CTkSlider(self.sidebar, from_=0, to=100, number_of_steps=100, button_color="#d1d5db", button_hover_color="#ffffff", progress_color="#e54e38", fg_color="#16171a", command=self.on_pad_slider_change)
        self.pad_slider.set(pad_val)
        self.pad_slider.pack(padx=15, pady=(2, 6), fill="x")

        fade_val = self.settings.get("fade_percent", 40)
        self.lbl_fade_title = ctk.CTkLabel(self.sidebar, text=f"Мягкость краев (Fade): {fade_val}%", font=("Helvetica", 11), text_color="#c2c7d0")
        self.lbl_fade_title.pack(padx=15, pady=(4, 0), anchor="w")

        self.fade_slider = ctk.CTkSlider(self.sidebar, from_=0, to=100, number_of_steps=100, button_color="#d1d5db", button_hover_color="#ffffff", progress_color="#e54e38", fg_color="#16171a", command=self.on_fade_slider_change)
        self.fade_slider.set(fade_val)
        self.fade_slider.pack(padx=15, pady=(2, 6), fill="x")

        shape_val = self.settings.get("shape_percent", 100)
        self.lbl_shape_title = ctk.CTkLabel(self.sidebar, text=f"Форма маски: {self.get_shape_text(shape_val)}", font=("Helvetica", 11), text_color="#c2c7d0")
        self.lbl_shape_title.pack(padx=15, pady=(4, 0), anchor="w")

        self.shape_slider = ctk.CTkSlider(self.sidebar, from_=0, to=100, number_of_steps=100, button_color="#d1d5db", button_hover_color="#ffffff", progress_color="#e54e38", fg_color="#16171a", command=self.on_shape_slider_change)
        self.shape_slider.set(shape_val)
        self.shape_slider.pack(padx=15, pady=(2, 8), fill="x")

        self.div2 = ctk.CTkFrame(self.sidebar, height=1, fg_color="#2b2e36")
        self.div2.pack(fill="x", padx=15, pady=5)

        self.analysis_btn_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.analysis_btn_frame.pack(padx=15, pady=4, fill="x")

        self.btn_analyze = ctk.CTkButton(
            self.analysis_btn_frame,
            text="⚡ Анализировать",
            height=36,
            font=("Helvetica", 12, "bold"),
            fg_color="#2b2e36",
            hover_color="#383c47",
            text_color="#d1d5db",
            border_width=1,
            border_color="#3a3e4a",
            cursor=CURSOR_HAND,
            command=self.start_analysis_thread,
            state="disabled"
        )
        self.btn_analyze.pack(side="left", expand=True, fill="x", padx=(0, 4))

        self.btn_stop = ctk.CTkButton(
            self.analysis_btn_frame,
            text="⏹",
            width=36,
            height=36,
            font=("Helvetica", 12, "bold"),
            fg_color="#2b2e36",
            hover_color="#383c47",
            text_color="#e54e38",
            border_width=1,
            border_color="#3a3e4a",
            cursor=CURSOR_HAND,
            command=self.stop_analysis,
            state="disabled"
        )
        self.btn_stop.pack(side="right")

        self.chk_export_labels = ctk.CTkCheckBox(
            self.sidebar,
            text="Сохранять номера ID в видео",
            font=("Helvetica", 11),
            text_color="#b0b5c0",
            checkmark_color="#ffffff",
            fg_color="#e54e38",
            hover_color="#d9532f",
            cursor=CURSOR_HAND,
            command=self.on_export_labels_toggle
        )
        if self.settings.get("export_labels", False):
            self.chk_export_labels.select()
        else:
            self.chk_export_labels.deselect()
        self.chk_export_labels.pack(padx=15, pady=(6, 4), anchor="w")

        self.btn_export = ctk.CTkButton(
            self.sidebar,
            text="💾 Экспорт",
            height=36,
            font=("Helvetica", 12, "bold"),
            fg_color="#2b2e36",
            hover_color="#383c47",
            text_color="#717684",
            border_width=1,
            border_color="#3a3e4a",
            cursor=CURSOR_HAND,
            command=self.export_video,
            state="disabled"
        )
        self.btn_export.pack(padx=15, pady=(4, 2), fill="x")

        self.export_progress = ctk.CTkProgressBar(self.sidebar, height=4, progress_color="#e54e38", fg_color="#16171a")
        self.export_progress.set(0)
        self.export_progress.pack(padx=15, pady=(0, 6), fill="x")

        self.lbl_gallery = ctk.CTkLabel(self.sidebar, text="НАЙДЕННЫЕ ОБЪЕКТЫ:", font=("Helvetica", 10, "bold"), text_color="#8a8f9d")
        self.lbl_gallery.pack(padx=15, pady=(4, 2), anchor="w")

        self.gallery_frame = ctk.CTkScrollableFrame(self.sidebar, fg_color="#16171a", border_width=1, border_color="#282b33")
        self.gallery_frame.pack(padx=15, pady=5, fill="both", expand=True)

        self.bind_scroll_events(self.gallery_frame)

        self.lbl_error_log = ctk.CTkLabel(
            self.sidebar,
            text="",
            font=("Helvetica", 11),
            text_color="#e54e38",
            wraplength=270,
            justify="left",
            anchor="w"
        )
        self.lbl_error_log.pack(padx=15, pady=(2, 2), fill="x", side="bottom")

        self.btn_about = ctk.CTkButton(
            self.sidebar,
            text="ℹ️ О программе",
            height=28,
            font=("Helvetica", 11),
            fg_color="#252830",
            hover_color="#323642",
            text_color="#9ca3af",
            cursor=CURSOR_HAND,
            command=lambda: show_about_dialog(self, CURSOR_HAND)
        )
        self.btn_about.pack(padx=15, pady=(5, 8), fill="x", side="bottom")

        # Правая часть (Canvas)
        self.right_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.right_frame.pack(side="right", expand=True, fill="both", padx=10, pady=10)

        self.canvas_container = ctk.CTkFrame(self.right_frame, fg_color="#0c0d0f", border_width=1, border_color="#23262e")
        self.canvas_container.pack(expand=True, fill="both", padx=0, pady=(0, 10))

        self.canvas = tk.Canvas(self.canvas_container, bg="#0c0d0f", highlightthickness=0)
        self.canvas.pack(expand=True, fill="both")

        self.canvas.bind("<Configure>", self.on_canvas_resize)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<Button-4>", lambda e: self.on_mouse_zoom_step(1.05))
        self.canvas.bind("<Button-5>", lambda e: self.on_mouse_zoom_step(0.95))
        self.canvas.bind("<ButtonPress-1>", self.on_drag_start)
        self.canvas.bind("<B1-Motion>", self.on_drag_motion)
        self.canvas.bind("<Double-Button-1>", self.on_canvas_double_click)

        # Плеер
        self.player_controls = ctk.CTkFrame(self.right_frame, height=50, fg_color="#181a1f", border_width=1, border_color="#262930")
        self.player_controls.pack(fill="x", side="bottom", padx=0, pady=0)

        self.btn_play = ctk.CTkButton(
            self.player_controls, 
            text="▶ Play", 
            width=70, 
            height=30,
            font=("Helvetica", 12, "bold"),
            fg_color="#2b2e36",
            hover_color="#383c47",
            text_color="#d1d5db",
            cursor=CURSOR_HAND,
            border_width=1,
            border_color="#3a3e4a",
            command=self.toggle_play,
            state="disabled"
        )
        self.btn_play.pack(side="left", padx=10, pady=10)

        self.time_label = ctk.CTkLabel(self.player_controls, text="00:00 / 00:00", font=("Helvetica", 11), text_color="#8a8f9d")
        self.time_label.pack(side="right", padx=10, pady=10)

        self.slider = ctk.CTkSlider(
            self.player_controls, 
            from_=0, 
            to=100, 
            button_color="#d1d5db",
            button_hover_color="#ffffff",
            progress_color="#e54e38",
            fg_color="#111215",
            command=self.on_slider_seek,
            state="disabled"
        )
        self.slider.pack(side="left", expand=True, fill="x", padx=10, pady=10)

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
            self.btn_save_proj.configure(text="✅ Сохранен")
            self.after(3000, lambda: self.btn_save_proj.configure(text="📁 Сохранить"))
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

            self.clear_gallery_ui()
            self.build_unique_faces_from_cache(active_states)

            self.slider.configure(state="normal", from_=0, to=total - 1, number_of_steps=total)
            self.slider.set(0)
            self.btn_play.configure(state="normal")
            
            self.btn_analyze.configure(
                text="✅ Проект загружен", 
                text_color="#38ef7d",
                state="normal"
            )
            self.btn_save_proj.configure(state="normal")
            self.btn_export.configure(
                text="💾 Экспорт", 
                state="normal", 
                text_color="#d1d5db"
            )
            
            self.populate_gallery_ui()
            self.show_frame(0)

        except Exception as e:
            logging.error(f"Ошибка загрузки проекта: {e}", exc_info=True)
            self.log_error(f"Ошибка загрузки: {e}")

    def bind_scroll_events(self, widget):
        widget.bind_all("<MouseWheel>", self._on_generic_scroll)
        widget.bind_all("<Button-4>", lambda e: self.gallery_frame._parent_canvas.yview_scroll(-1, "units"))
        widget.bind_all("<Button-5>", lambda e: self.gallery_frame._parent_canvas.yview_scroll(1, "units"))

    def _on_generic_scroll(self, event):
        if hasattr(self, 'gallery_frame') and self.gallery_frame.winfo_exists():
            if sys.platform == "darwin":
                self.gallery_frame._parent_canvas.yview_scroll(int(-1 * event.delta), "units")
            else:
                self.gallery_frame._parent_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

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

        click_video_x = int((event.x - img_x1) / scale)
        click_video_y = int((event.y - img_y1) / scale)

        faces = self.detected_boxes_cache.get(self.current_frame_idx, [])
        clicked_id = None

        for face in faces:
            if isinstance(face, dict):
                bbox = face.get('bbox', [0, 0, 0, 0])
            else:
                bbox = face[:4]
            x1, y1, x2, y2 = [int(v) for v in bbox]
            pad_w = int((x2 - x1) * self.blurrer.padding_percent)
            pad_h = int((y2 - y1) * self.blurrer.padding_percent)

            bx1 = x1 - pad_w
            by1 = y1 - pad_h
            bx2 = x2 + pad_w
            by2 = y2 + pad_h

            if bx1 <= click_video_x <= bx2 and by1 <= click_video_y <= by2:
                raw_id = face.get('id', face.get('track_id', 0)) if isinstance(face, dict) else (face[4] if len(face) > 4 else 0)
                clicked_id = int(raw_id)
                break

        if clicked_id is not None and clicked_id in self.unique_faces:
            logging.info(f"Двойной клик попал на объект ID #{clicked_id}. Переключение состояния блюра.")
            self.toggle_face_blur(clicked_id)
            self.populate_gallery_ui()
        else:
            logging.info(f"Двойной клик не попал в рамку лица в видео-точке [x={click_video_x}, y={click_video_y}]. Сброс зума.")
            self.reset_zoom()

    def log_error(self, message: str):
        logging.error(f"UI Error Log displayed: {message}")
        self.lbl_error_log.configure(text=f"⚠️ {message}")

    def clear_error_log(self):
        self.lbl_error_log.configure(text="")

    def get_shape_text(self, val: int) -> str:
        if val >= 90:
            return f"Овал ({val}%)"
        elif val <= 10:
            return f"Квадрат ({val}%)"
        return f"Скругление ({val}%)"

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
        logging.info(f"Событие: Чекбокс 'Сохранять номера ID в видео' переключен в состояние: {val}")
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
        if self.current_pil_img:
            self.render_canvas_image()

    def on_status_bar_resize(self, event):
        if self.reader:
            self.update_status_bar_text()

    def update_status_bar_text(self):
        if self.video_status_error:
            name = os.path.basename(self.selected_video_path) if self.selected_video_path else ""
            self.lbl_status_left.configure(text=f"Файл: {name}" if name else "Видео не открыто")
            codec = self.reader.codec if self.reader and self.reader.codec != "Unknown" else "не определён"
            self.lbl_status_right.configure(
                text=f"Кодек: {codec}  |  {self.video_status_error}",
                text_color="#e54e38"
            )
            return

        self.lbl_status_right.configure(text_color="#8a8f9d")
        if not self.reader:
            self.lbl_status_left.configure(text="Готов к работе")
            self.lbl_status_right.configure(text="")
            return

        right_text = (
            f"Разрешение: {self.reader.width}x{self.reader.height} ({self.reader.aspect_ratio})  |  "
            f"Кодек: {self.reader.codec} ({self.reader.bitrate_str})  |  "
            f"FPS: {self.reader.fps:.2f}  |  "
            f"Кадров: {self.reader.total_frames}"
        )
        self.lbl_status_right.configure(text=right_text)

        total_width = self.status_bar.winfo_width()
        right_width = self.lbl_status_right.winfo_reqwidth()
        available_left_px = max(100, total_width - right_width - 40)

        orig_filename = os.path.basename(self.reader.file_path)
        max_chars = max(10, int(available_left_px / 8))
        if len(orig_filename) > max_chars:
            ext = orig_filename.split('.')[-1]
            name_no_ext = orig_filename[:-len(ext)-1]
            short_name = name_no_ext[:max_chars - 3] + "..." + "." + ext
        else:
            short_name = orig_filename

        self.lbl_status_left.configure(text=f"Файл: {short_name}")

    def render_canvas_image(self):
        if not self.current_pil_img:
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
        self.lbl_blur_title.configure(text=f"Сила размытия: {val}%")
        self.settings["blur_percent"] = val
        self.save_settings()
        self.show_frame(self.current_frame_idx)

    def on_pad_slider_change(self, value):
        val = int(value)
        logging.info(f"Слайдер: Изменен размер маски -> {val}%")
        self.blurrer.set_padding_percent(val)
        self.lbl_pad_title.configure(text=f"Размер маски: {val}%")
        self.settings["padding_percent"] = val
        self.save_settings()
        self.show_frame(self.current_frame_idx)

    def on_fade_slider_change(self, value):
        val = int(value)
        logging.info(f"Слайдер: Изменена мягкость краев (Fade) -> {val}%")
        self.blurrer.set_fade_percent(val)
        self.lbl_fade_title.configure(text=f"Мягкость краев (Fade): {val}%")
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
            self.btn_play.configure(text="▶ Play")
            self.btn_play.configure(state="disabled")
            self.btn_analyze.configure(text="⚡ Анализировать", state="disabled")
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
                    text="⚠️ Требуется анализ", 
                    text_color="#e54e38",
                    state="normal"
                )
                self.btn_save_proj.configure(state="disabled")
                self.btn_stop.configure(state="disabled")
                
                self.btn_export.configure(
                    text="💾 Экспорт", 
                    state="disabled", 
                    text_color="#717684"
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
        self.export_progress.set(0)
        
        self.btn_export.configure(
            state="disabled", 
            text="⏳ Экспорт: 0%", 
            text_color="#ffffff"
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
        self.btn_export.configure(text="💾 Экспорт", state="normal")
        self.log_error(message)

    def _update_export_progress(self, ratio, current, total):
        self.export_progress.set(ratio)
        self.btn_export.configure(text=f"⏳ Экспорт: {int(ratio * 100)}% ({current}/{total})")

    def _on_export_finished_ui(self):
        self.is_exporting = False
        self.export_progress.set(1.0)
        self.btn_export.configure(
            text="✅ Сохранено", 
            text_color="#38ef7d",
            state="normal"
        )
        self.after(5000, self._reset_export_button_ui)

    def _reset_export_button_ui(self):
        if not self.is_exporting:
            self.export_progress.set(0)
            self.btn_export.configure(
                text="💾 Экспорт",
                text_color="#d1d5db",
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
        self.stop_analysis_flag = False
        self.btn_analyze.configure(state="disabled", text="⏳ Детекция...", text_color="#d1d5db")
        self.btn_stop.configure(state="normal")
        self.btn_play.configure(state="disabled")
        
        self.btn_export.configure(state="disabled", text_color="#717684")
        self.export_progress.set(0)
        self.clear_gallery_ui()
        self.unique_faces.clear()
        threading.Thread(target=self._run_full_analysis, daemon=True).start()

    def _run_full_analysis(self):
        try:
            logging.info("Фоновый поток анализа: старт детекции лиц.")
            if not self.detector:
                model_path = get_resource_path("yolov8s-face.pt")
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
                    backend = self.detector.compute.backend.upper()
                    self._post_ui(self.btn_analyze.configure, text=f"⏳ Анализ [{backend}]: {progress}%")

            logging.info(f"Детекция завершена. Всего обработано кадров: {len(self.detected_boxes_cache)}")
            self._post_ui(self._on_analysis_finished_ui)
        except Exception as e:
            logging.error(f"Ошибка в фоновом потоке анализа: {e}", exc_info=True)
            self._post_ui(self._on_analysis_failed_ui, str(e))

    def _on_analysis_failed_ui(self, message):
        self.is_analysing = False
        self.btn_analyze.configure(text="⚡ Анализировать", state="normal")
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

    def _on_analysis_finished_ui(self):
        logging.info("UI: Анализ завершен, обновление элементов интерфейса...")
        self.is_analysing = False
        self.btn_stop.configure(state="disabled")
        
        self.build_unique_faces_from_cache()

        if self.stop_analysis_flag:
            self.btn_analyze.configure(
                text="⚠️ Остановлен", 
                text_color="#e54e38", 
                state="normal"
            )
        else:
            self.btn_analyze.configure(
                text="✅ Анализ актуален", 
                text_color="#38ef7d", 
                state="normal"
            )

        self.btn_save_proj.configure(state="normal")
        self.btn_play.configure(state="normal")
        
        self.btn_export.configure(
            text="💾 Экспорт",
            state="normal", 
            text_color="#d1d5db"
        )
        
        logging.info("Вызов populate_gallery_ui() и show_frame(0)")
        self.populate_gallery_ui()
        self.after(50, lambda: self.show_frame(0))

    def populate_gallery_ui(self):
        self.clear_gallery_ui()
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
                
                row = ctk.CTkFrame(self.gallery_frame, fg_color="#21242c", corner_radius=6, border_width=1, border_color="#2f333e")
                row.pack(fill="x", pady=4, padx=4)
                data['widget'] = row

                # Прямое создание standard PhotoImage с мастером `self` для предотвращения RuntimeError
                pil_img = data['pil_image'].resize((32, 32), Image.Resampling.BILINEAR)
                tk_img = ImageTk.PhotoImage(pil_img, master=self)
                self.gallery_photo_refs.append(tk_img)

                lbl_img = ctk.CTkLabel(row, image=tk_img, text="", width=32, height=32, font=self.gallery_font)
                lbl_img.image = tk_img
                lbl_img.pack(side="left", padx=(8, 6), pady=6)

                chk = ctk.CTkCheckBox(
                    row, 
                    text=f"Объект #{int(t_id):02d}", 
                    font=self.gallery_font,
                    text_color="#d1d5db",
                    checkmark_color="#ffffff",
                    fg_color="#e54e38",
                    hover_color="#d9532f",
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
                    widget.configure(border_color="#e54e38", border_width=1.5)
                else:
                    widget.configure(border_color="#2f333e", border_width=1)

    def show_frame(self, frame_idx: int):
        if not self.raw_frames or frame_idx >= len(self.raw_frames):
            return

        self.current_frame_idx = frame_idx
        faces_in_current_frame = self.detected_boxes_cache.get(frame_idx, [])
        frame_active_ids = {int(f.get('id', f.get('track_id', 0)) if isinstance(f, dict) else (f[4] if len(f) > 4 else 0)) for f in faces_in_current_frame}

        self.update_gallery_highlighting(frame_active_ids)
        active_blur_ids = self.get_active_blur_ids()

        frame_bgr = self.blurrer.apply_blur_and_labels(self.raw_frames[frame_idx], faces_in_current_frame, active_blur_ids)

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
        self.btn_play.configure(text="▶ Play")
        idx = int(value)
        logging.info(f"Событие: Перемотка слайдером на кадр #{idx}")
        self.show_frame(idx)

    def toggle_play(self):
        if not self.raw_frames:
            return
        self.is_playing = not self.is_playing
        logging.info(f"Событие: Кнопка Play/Pause нажата. Статус: {'PLAY' if self.is_playing else 'PAUSE'}")
        if self.is_playing:
            self.btn_play.configure(text="⏸ Pause")
            self.play_loop()
        else:
            self.btn_play.configure(text="▶ Play")

    def play_loop(self):
        if not self.is_playing:
            return
        
        if self.current_frame_idx < len(self.raw_frames) - 1:
            self.current_frame_idx += 1
            self.slider.set(self.current_frame_idx)
            self.show_frame(self.current_frame_idx)
            delay = int(1000 / self.reader.fps)
            self.after(delay, self.play_loop)
        else:
            self.is_playing = False
            self.btn_play.configure(text="▶ Play")
