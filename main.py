import os
import sys
import time
import threading
import queue
import traceback
import logging
import multiprocessing

from core.platform_paths import matplotlib_cache_dir

# 1. Отключение фона Matplotlib и YOLO до импорта библиотек
os.environ["MPLCONFIGDIR"] = str(matplotlib_cache_dir())
os.environ["YOLO_VERBOSE"] = "False"

from app_logging import configure_logging
LOG_FILE = configure_logging()
APP_VERSION = "1.1.23"

logging.getLogger('matplotlib').setLevel(logging.WARNING)

# 6. Фиксация корня проекта в sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import customtkinter as ctk
from PIL import Image

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(PROJECT_ROOT, relative_path)

class SmartSplashScreen(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.withdraw()
        self.overrideredirect(True)
        
        width, height = 520, 320
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.configure(fg_color="#121316")

        self.main_frame = ctk.CTkFrame(self, fg_color="#121316", border_width=1, border_color="#2b2e36")
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

        lbl_title = ctk.CTkLabel(self.main_frame, text="FaceBlur Studio", font=("Helvetica", 20, "bold"), text_color="#ffffff")
        lbl_title.pack(pady=(2, 2))

        lbl_sub = ctk.CTkLabel(self.main_frame, text=f"Версия {APP_VERSION} — Загрузка системы...", font=("Helvetica", 11), text_color="#8a8f9d")
        lbl_sub.pack(pady=(0, 10))

        self.txt_error = ctk.CTkTextbox(
            self.main_frame, 
            height=160, 
            fg_color="#181a1f", 
            text_color="#ff5555", 
            font=("Consolas", 10), 
            border_width=1, 
            border_color="#442222",
            activate_scrollbars=True
        )

        self.btn_close = ctk.CTkButton(
            self.main_frame, 
            text="Закрыть", 
            width=110, 
            height=28, 
            fg_color="#e54e38", 
            hover_color="#c43d28", 
            command=self.destroy
        )

        self.status_bar = ctk.CTkFrame(self.main_frame, height=30, corner_radius=0, fg_color="#16171a", border_width=1, border_color="#262930")
        self.status_bar.pack(side="bottom", fill="x")

        self.lbl_status = ctk.CTkLabel(
            self.status_bar, 
            text="⏳ Инициализация компонентов...", 
            font=("Helvetica", 11), 
            text_color="#8a8f9d", 
            anchor="w"
        )
        self.lbl_status.pack(side="left", padx=12, pady=4, fill="x", expand=True)

        self._ui_events = queue.Queue()
        self.after(50, self._drain_ui_events)
        self.is_splash_visible = False
        self.start_time = time.time()

        self.after(400, self.reveal_if_slow)
        
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
        self.lbl_status.configure(text=text, text_color="#8a8f9d")

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
        self.lbl_status.configure(text=f"⚠️ {last_line}", text_color="#e54e38")
        
        self.txt_error.pack(padx=20, pady=(0, 8), fill="both", expand=True)
        self.txt_error.insert("1.0", err_msg)
        self.txt_error.configure(state="disabled")
        
        self.btn_close.pack(pady=(0, 10))

    def load_application(self):
        try:
            self._post_ui(self.update_status, "⚙️ Проверка библиотек Python...")
            import customtkinter as ctk_lib
            import cv2
            import PIL

            self._post_ui(self.update_status, "🔍 Проверка весов YOLOv8...")
            model_path = get_resource_path("yolov8s-face.pt")
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Файл весов 'yolov8s-face.pt' не найден по пути: {model_path}")

            self._post_ui(self.update_status, "🎨 Инициализация интерфейса...")
            from ui.main_window import MainWindow

            self._post_ui(self.finish_loading, MainWindow)

        except Exception:
            err = traceback.format_exc()
            logging.exception("Startup failed")
            self._post_ui(self.show_error, err)

    def finish_loading(self, main_window_cls):
        self.main_window_cls = main_window_cls
        self.quit()

if __name__ == "__main__":
    multiprocessing.freeze_support()

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
