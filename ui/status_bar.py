"""A clipped status message with time-based, gently reversing scrolling."""
import logging
import math
import time
import tkinter as tk


class ScrollingStatus(tk.Canvas):
    def __init__(self, parent, background, foreground):
        background = parent._apply_appearance_mode(background)
        foreground = parent._apply_appearance_mode(foreground)
        super().__init__(parent, height=28, background=background,
                         highlightthickness=0, borderwidth=0)
        self.message = ''
        self.started = time.monotonic()
        self.item = self.create_text(12, 14, anchor='w', fill=foreground,
                                     font=('Segoe UI', 10), text='')
        self.bind('<Configure>', lambda event: self._restart())
        self.timer = self.after(16, self._animate)

    def set_message(self, message):
        message = ' '.join(str(message).split())
        if message == self.message:
            return
        self.message = message
        self.itemconfigure(self.item, text=message)
        self._restart()

    def _restart(self):
        self.started = time.monotonic()
        self.coords(self.item, 12, self.winfo_height() / 2)

    def _animate(self):
        box = self.bbox(self.item)
        overflow = max(0, box[2] - box[0] - self.winfo_width() + 24) if box else 0
        offset = 0
        if overflow:
            # Two seconds at either end, with cosine easing and no wrap jump.
            travel = max(2.0, overflow * math.pi / (2 * 24))
            phase = (time.monotonic() - self.started) % (2 * travel + 4)
            if 2 < phase < 2 + travel:
                offset = overflow * (1 - math.cos(math.pi * (phase - 2) / travel)) / 2
            elif 2 + travel <= phase <= 4 + travel:
                offset = overflow
            elif phase > 4 + travel:
                offset = overflow * (1 + math.cos(math.pi * (phase - 4 - travel) / travel)) / 2
        self.coords(self.item, 12 - offset, self.winfo_height() / 2)
        self.timer = self.after(16, self._animate)

    def destroy(self):
        self.after_cancel(self.timer)
        super().destroy()


class StatusEvents(logging.Handler):
    """Forward user actions and outcomes through the main window's UI queue."""
    def __init__(self, window):
        super().__init__(logging.INFO)
        self.window = window

    def emit(self, record):
        message = record.getMessage()
        if record.filename != 'main_window.py':
            return
        if message.startswith('Событие:'):
            message = message.removeprefix('Событие:').strip()
        elif message.startswith('UI Error Log displayed:'):
            message = 'Ошибка: ' + message.removeprefix('UI Error Log displayed:').strip()
        elif not (record.levelno >= logging.ERROR or any(word in message for word in
                  ('успешно', 'отменен', 'отменён', 'Видео открыто', 'Проект загружен',
                   'Переключение состояния', 'Слайдер:', 'Чекбокс'))):
            return
        self.window._post_ui(self.window.set_status, message)
