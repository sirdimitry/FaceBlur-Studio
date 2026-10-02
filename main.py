from ui.i18n import tr
from ui.layout_direction import apply_direction
import os
import sys
import time
import threading
import queue
import traceback
import logging
import multiprocessing
import json

from core.platform_paths import matplotlib_cache_dir

# 1. Отключение фона Matplotlib и YOLO до импорта библиотек
os.environ["MPLCONFIGDIR"] = str(matplotlib_cache_dir())
os.environ["YOLO_VERBOSE"] = "False"
os.environ.setdefault("PYTORCH_NVML_BASED_CUDA_CHECK", "1")
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

from app_logging import configure_logging
LOG_FILE = configure_logging()
APP_VERSION = "1.1.28"

logging.getLogger('matplotlib').setLevel(logging.WARNING)

# 6. Фиксация корня проекта в sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import customtkinter as ctk
from ui.theme import (UI_FONT, WINDOW, SIDEBAR, SURFACE, HOVER, TRACK, BORDER, TEXT, SECONDARY, DISABLED_TEXT, ACCENT, ACCENT_HOVER, ON_ACCENT, SUCCESS, ERROR, ERROR_HOVER, ThemedButton, initialize_theme, follow_titlebar, apply_app_icon)
initialize_theme()

from PIL import Image

if sys.platform == "win32":
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("FaceBlurStudio.Desktop")
from core.detector import default_model_filename

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(PROJECT_ROOT, relative_path)

class SmartSplashScreen(ctk.CTk):
    def __init__(self):
        super().__init__()
        apply_app_icon(self)

        self.withdraw()
        self.overrideredirect(True)
        follow_titlebar(self)

        width, height = 520, 320
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.configure(fg_color=WINDOW)

        self.main_frame = ctk.CTkFrame(self, fg_color=WINDOW, border_width=1, border_color=BORDER)
        self.main_frame.pack(fill="both", expand=True)

        icon_path = get_resource_path("AutoBlureFace_icon.png")
        if not os.path.exists(icon_path):
            icon_path = get_resource_path("app_icon.icns")

        if os.path.exists(icon_path):
            try:
                pil_img = Image.open(icon_path)
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(64, 64))
                lbl_img = ctk.CTkLabel(self.main_frame, image=ctk_img, text="")
                lbl_img.pack(pady=(20, 5))
            except Exception:
                pass

        lbl_title = ctk.CTkLabel(self.main_frame, text="FaceBlur Studio", font=(UI_FONT, 20, "bold"), text_color=TEXT)
        lbl_title.pack(pady=(2, 2))

        lbl_sub = ctk.CTkLabel(self.main_frame, text=tr('Версия {0} — Загрузка системы...').format(APP_VERSION), font=(UI_FONT, 13), text_color=SECONDARY)
        lbl_sub.pack(pady=(0, 10))

        self.txt_error = ctk.CTkTextbox(
            self.main_frame,
            height=160,
            fg_color=SURFACE,
            text_color=ERROR,
            font=("Consolas", 13),
            border_width=1,
            border_color=BORDER,
            activate_scrollbars=True
        )

        self.btn_close = ThemedButton(
            self.main_frame,
            text=tr('Закрыть'),
            width=110,
            height=28,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            text_color=ON_ACCENT,
            command=self.destroy
        )

        self.status_bar = ctk.CTkFrame(self.main_frame, height=30, corner_radius=0, fg_color=SURFACE, border_width=1, border_color=BORDER)
        self.status_bar.pack(side="bottom", fill="x")

        self.lbl_status = ctk.CTkLabel(
            self.status_bar,
            text=tr('⏳ Инициализация компонентов...'),
            font=(UI_FONT, 13),
            text_color=SECONDARY,
            anchor="w"
        )
        self.lbl_status.pack(side="left", padx=12, pady=4, fill="x", expand=True)

        self._ui_events = queue.Queue()
        self.after(50, self._drain_ui_events)
        self.is_splash_visible = False
        self.start_time = time.time()

        self.after(400, self.reveal_if_slow)

        apply_direction(self)
        threading.Thread(target=self.load_application, daemon=True).start()

    def _post_ui(self, callback, *args):
        self._ui_events.put((callback, args))

    def _drain_ui_events(self):
        while True:
            try:
                callback, args = self._ui_events.get_nowait()
            except queue.Empty:
                break
            callback(*args)
        self.after(50, self._drain_ui_events)

    def reveal_if_slow(self):
        if not self.is_splash_visible:
            self.is_splash_visible = True
            self.deiconify()
            self.lift()
            self.attributes("-topmost", True)

    def update_status(self, text: str):
        self.lbl_status.configure(text=text, text_color=SECONDARY)

    def show_error(self, err_msg: str):
        self.overrideredirect(False)

        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w, h = 680, 480
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        self.reveal_if_slow()
        last_line = [line for line in err_msg.splitlines() if line.strip()][-1]
        self.lbl_status.configure(text=f"⚠️ {last_line}", text_color=ERROR)

        self.txt_error.pack(padx=20, pady=(0, 8), fill="both", expand=True)
        self.txt_error.insert("1.0", err_msg)
        self.txt_error.configure(state="disabled")

        self.btn_close.pack(pady=(0, 10))

    def load_application(self):
        try:
            self._post_ui(self.update_status, tr('⚙️ Проверка библиотек Python...'))
            import customtkinter as ctk_lib
            import cv2
            import PIL

            self._post_ui(self.update_status, tr('🔍 Проверка весов YOLOv8...'))
            model_name = default_model_filename()
            model_path = get_resource_path(model_name)
            if not os.path.exists(model_path):
                raise FileNotFoundError(tr("Файл модели '{0}' не найден: {1}").format(model_name, model_path))

            self._post_ui(self.update_status, tr('🎨 Инициализация интерфейса...'))
            if sys.platform == "darwin":
                from ui.mac_window import MacMainWindow as MainWindow
            else:
                from ui.main_window import MainWindow

            self._post_ui(self.finish_loading, MainWindow)

        except Exception:
            err = traceback.format_exc()
            logging.exception("Startup failed")
            self._post_ui(self.show_error, err)

    def finish_loading(self, main_window_cls):
        self.main_window_cls = main_window_cls
        self.quit()


def run_packaged_smoke_test(video_path, report_path, frame_count=30):
    """Exercise the packaged detector without opening the interface."""
    from core.detector import FaceDetector
    from core.video_reader import FFmpegVideoReader

    detector = FaceDetector(get_resource_path(default_model_filename()))
    reader = FFmpegVideoReader(video_path)
    detections = 0
    processed = min(int(frame_count), len(reader))
    for index in range(processed):
        detections += len(detector.track_faces(reader[index]))
    reader.close()
    with open(report_path, "w", encoding="utf-8") as report:
        json.dump(
            {
                "backend": detector.backend,
                "device": detector.device_description,
                "frames": processed,
                "detections": detections,
            },
            report,
            ensure_ascii=False,
            indent=2,
        )

def run_verification(callback, *args):
    """Report diagnostic failures without PyInstaller's interactive error dialog."""
    try:
        callback(*args)
    except Exception:
        logging.exception("Packaged verification failed")
        raise SystemExit(1)


if __name__ == "__main__":
    multiprocessing.freeze_support()

    if len(sys.argv) >= 4 and sys.argv[1] == "--verify-reader":
        from core.pipeline_verification import verify_reader

        run_verification(verify_reader, sys.argv[2], sys.argv[3])
        raise SystemExit(0)

    if len(sys.argv) >= 4 and sys.argv[1] == "--verify-pipeline":
        from core.pipeline_verification import verify_pipeline

        frame_count = int(sys.argv[4]) if len(sys.argv) >= 5 else None
        run_verification(verify_pipeline, sys.argv[2], sys.argv[3],
                         get_resource_path(default_model_filename()), frame_count)
        raise SystemExit(0)

    if len(sys.argv) >= 4 and sys.argv[1] == "--smoke-test":
        frame_count = int(sys.argv[4]) if len(sys.argv) >= 5 else 30
        run_verification(run_packaged_smoke_test, sys.argv[2], sys.argv[3], frame_count)
        raise SystemExit(0)

    app_splash = SmartSplashScreen()
    app_splash.mainloop()
    main_window_cls = getattr(app_splash, 'main_window_cls', None)
    app_splash.destroy()
    if main_window_cls:
        try:
            app = main_window_cls()
            app.mainloop()
        except Exception:
            logging.exception("Application failed")
            raise
