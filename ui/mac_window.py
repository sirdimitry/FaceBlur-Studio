"""macOS workspace; the Windows MainWindow layout remains independent."""
import os
import tkinter as tk
import customtkinter as ctk
from ui.main_window import MainWindow
from ui.theme import (UI_FONT, WINDOW, SURFACE, HOVER, BORDER, TEXT, SECONDARY,
                      ACCENT, ACCENT_HOVER, ON_ACCENT, ERROR, ThemedButton)
from ui.dialogs import show_about_dialog

CONTROL_HEIGHT = 36
RADIUS = 8


class MacMainWindow(MainWindow):
    def __init__(self):
        self._value_fields = {}
        self._busy_states = None
        super().__init__()
        self.sidebar.configure(width=340, border_width=0)
        self.sidebar.pack_propagate(False)
        self.right_frame.pack_configure(padx=24, pady=20)
        self.preview_header.configure(text="Ваше видео", font=(UI_FONT, 23, "bold"))
        self.preview_hint.configure(text="Откройте видео, найдите лица и проверьте размытие перед экспортом")
        self.lbl_inspector_header.configure(font=(UI_FONT, 20, "bold"), height=32)
        self.lbl_inspector_header.pack_configure(pady=(18, 12))
        self.btn_open.configure(text="Открыть видео", fg_color=SURFACE,
                                hover_color=ACCENT_HOVER, text_color=TEXT,
                                border_width=1, border_color=BORDER)
        for button in (self.btn_open, self.btn_save_proj, self.btn_load_proj,
                       self.btn_analyze, self.btn_stop, self.btn_export,
                       self.btn_about, self.btn_play):
            button.configure(corner_radius=RADIUS, height=CONTROL_HEIGHT)
            button.bind('<FocusIn>', lambda event, b=button: b.configure(border_color=ACCENT, border_width=2))
            button.bind('<FocusOut>', lambda event, b=button: b.configure(border_color=BORDER, border_width=1))
            # CTk's canvas buttons need an explicit keyboard focus target.
            button._canvas.configure(takefocus=1)
            button._canvas.bind('<FocusIn>', lambda event, b=button: b.configure(border_color=ACCENT, border_width=2))
            button._canvas.bind('<FocusOut>', lambda event, b=button: b.configure(border_color=BORDER, border_width=1))
            for key in ('<Return>', '<space>'):
                button._canvas.bind(key, lambda event, b=button: self._invoke(b))
        self.btn_export.configure(height=42, fg_color=ACCENT,
                                  hover_color=ACCENT_HOVER, text_color=ON_ACCENT)
        self.lbl_error_log.configure(text_color=ERROR, wraplength=308)
        self.player_controls.configure(corner_radius=RADIUS)
        self.gallery_frame.configure(corner_radius=RADIUS)
        self.canvas_container.configure(corner_radius=12)
        # Project commands share a quiet toolbar, leaving room for the faces list.
        self.project_btn_frame.pack_forget()
        self.btn_about.pack_forget()
        toolbar = ctk.CTkFrame(self.right_frame, fg_color='transparent')
        toolbar.pack(fill='x', before=self.canvas_container, pady=(0, 12))
        self.btn_save_proj = ThemedButton(toolbar, text='Сохранить проект · ⌘S',
                                         width=180, height=32, corner_radius=RADIUS,
                                         font=(UI_FONT, 13), text_color=TEXT, fg_color=SURFACE, command=self.save_project, state='disabled')
        self.btn_load_proj = ThemedButton(toolbar, text='Открыть проект', width=140,
                                         height=32, corner_radius=RADIUS,
                                         font=(UI_FONT, 13), text_color=TEXT, fg_color=SURFACE, command=self.load_project)
        self.btn_about = ThemedButton(toolbar, text='О программе', width=120,
                                     height=32, corner_radius=RADIUS,
                                     font=(UI_FONT, 13), text_color=TEXT, fg_color=SURFACE,
                                     command=lambda: show_about_dialog(self, 'pointinghand'))
        for button in (self.btn_save_proj, self.btn_load_proj, self.btn_about):
            button.pack(side='left', padx=(0, 8))
            button._canvas.configure(takefocus=1)
            button._canvas.bind('<FocusIn>', lambda event, b=button: b.configure(border_color=ACCENT, border_width=2))
            button._canvas.bind('<FocusOut>', lambda event, b=button: b.configure(border_color=BORDER, border_width=1))
            for key in ('<Return>', '<space>'):
                button._canvas.bind(key, lambda event, b=button: self._invoke(b))
        self._add_value_fields()
        self.lbl_gallery.configure(text="ЛИЦА ДЛЯ РАЗМЫТИЯ")
        self.populate_gallery_ui()
        self._bind_shortcuts()
        self._refresh_workspace()

    def _invoke(self, button):
        if button.cget('state') == 'normal':
            button.invoke()
        return 'break'

    def _bind_shortcuts(self):
        for key, button in (('<Command-o>', self.btn_open),
                            ('<Command-s>', self.btn_save_proj),
                            ('<Command-Shift-O>', self.btn_load_proj),
                            ('<Command-e>', self.btn_export)):
            self.bind(key, lambda event, b=button: self._invoke(b))
        self.bind('<Escape>', lambda event: self.stop_analysis() if self.is_analysing else self.reset_zoom())
        self.bind('<Command-0>', lambda event: self.reset_zoom())
        self.bind('<space>', self._play_shortcut)

    def _play_shortcut(self, event):
        # Preserve text editing and focused controls' own Space behavior.
        if isinstance(event.widget, (tk.Entry, tk.Text)) or event.widget != self:
            return
        return self._invoke(self.btn_play)

    def _add_value_fields(self):
        for key, label, slider, callback in (
            ('blur_percent', self.lbl_blur_title, self.blur_slider, self.on_blur_slider_change),
            ('padding_percent', self.lbl_pad_title, self.pad_slider, self.on_pad_slider_change),
            ('fade_percent', self.lbl_fade_title, self.fade_slider, self.on_fade_slider_change),
            ('shape_percent', self.lbl_shape_title, self.shape_slider, self.on_shape_slider_change),
        ):
            label.pack_configure(fill='x')
            label.configure(anchor='w', height=26)
            value = tk.StringVar(value=str(int(slider.get())))
            field = ctk.CTkEntry(self.sidebar, width=50, height=26, corner_radius=6,
                                 font=(UI_FONT, 13), textvariable=value,
                                 justify='right', fg_color=SURFACE,
                                 border_color=BORDER, text_color=TEXT)
            field.place(in_=label, relx=1, rely=.5, anchor='e')
            self._value_fields[key] = (value, field)
            field.bind('<Return>', lambda event, k=key, s=slider, c=callback: self._commit_value(k, s, c))
            field.bind('<FocusOut>', lambda event, k=key, s=slider, c=callback: self._commit_value(k, s, c))
            slider._value_format = lambda number: f'{number:.0f} / 100'
        self.lbl_shape_title.configure(text="Форма маски · овал")

    def _commit_value(self, key, slider, callback):
        value, field = self._value_fields[key]
        if self.is_exporting:
            value.set(str(int(slider.get())))
            return 'break'
        try:
            number = int(value.get())
            if not 0 <= number <= 100:
                raise ValueError
        except ValueError:
            field.configure(border_color=ERROR)
            self.log_error('Введите целое число от 0 до 100; затем нажмите Enter.')
            field.focus_set()
            return 'break'
        field.configure(border_color=BORDER)
        slider.set(number)
        callback(number)
        self.clear_error_log()
        return 'break'

    def _sync_value(self, key, value):
        if key in self._value_fields:
            self._value_fields[key][0].set(str(int(value)))

    def on_blur_slider_change(self, value):
        super().on_blur_slider_change(value)
        self._sync_value('blur_percent', value)

    def on_pad_slider_change(self, value):
        super().on_pad_slider_change(value)
        self._sync_value('padding_percent', value)

    def on_fade_slider_change(self, value):
        super().on_fade_slider_change(value)
        self._sync_value('fade_percent', value)

    def on_shape_slider_change(self, value):
        super().on_shape_slider_change(value)
        self.lbl_shape_title.configure(text=f'Форма маски · {self.get_shape_text(int(value)).lower()}')
        self._sync_value('shape_percent', value)

    def _lock_workspace(self):
        controls = [self.btn_open, self.btn_load_proj, self.btn_save_proj,
                    self.btn_analyze, self.btn_play, self.slider,
                    self.blur_slider, self.pad_slider, self.fade_slider,
                    self.shape_slider, self.chk_export_labels]
        controls.extend(field for _, field in self._value_fields.values())
        for row in self.gallery_frame.winfo_children():
            controls.extend(widget for widget in row.winfo_children() if isinstance(widget, ctk.CTkCheckBox))
        if self._busy_states is None:
            self._busy_states = [(control, control.cget('state')) for control in controls]
        for control in controls:
            control.configure(state='disabled')
        self.is_playing = False
        self.btn_play.configure(text='▶  Смотреть')

    def _unlock_workspace(self):
        for control, state in self._busy_states or []:
            if control.winfo_exists():
                control.configure(state=state)
        self._busy_states = None

    def open_video(self):
        if self.is_exporting or self.is_analysing:
            return
        super().open_video()
        self.analysis_status.configure(text='Нажмите «Найти лица»' if self.raw_frames else 'Добавьте видео, чтобы найти лица', text_color=SECONDARY)
        self.export_status.configure(text='MP4 · исходное разрешение · со звуком', text_color=SECONDARY)
        self.populate_gallery_ui()

    def load_project(self):
        if self.is_exporting or self.is_analysing:
            return
        self.is_playing = False
        self.btn_play.configure(text='▶  Смотреть')
        super().load_project()
        if self.raw_frames and self.detected_boxes_cache:
            self.analysis_status.configure(
                text=f'Проект · кадры: {len(self.detected_boxes_cache)}/{len(self.raw_frames)} · лиц: {len(self.unique_faces)}',
                text_color=SECONDARY)

    def start_analysis_thread(self):
        if not self.raw_frames or self.is_analysing or self.is_exporting:
            return
        self._lock_workspace()
        super().start_analysis_thread()

    def export_video(self):
        if self.is_analysing or self.is_exporting:
            return
        super().export_video()
        if self.is_exporting:
            self._lock_workspace()

    def _on_analysis_finished_ui(self):
        self._unlock_workspace()
        super()._on_analysis_finished_ui()
        if self.stop_analysis_flag:
            self.analysis_status.configure(text=f'Остановлено · обработано {len(self.detected_boxes_cache)} кадров')
        elif not self.unique_faces:
            self.analysis_status.configure(text='Лица не найдены · проверьте видео', text_color=SECONDARY)

    def _on_analysis_failed_ui(self, message):
        self._unlock_workspace()
        super()._on_analysis_failed_ui(message)
        self.btn_play.configure(state='normal' if self.raw_frames else 'disabled')

    def _on_export_finished_ui(self):
        self._unlock_workspace()
        super()._on_export_finished_ui()
        self.btn_export.configure(text='Видео сохранено')

    def _on_export_failed_ui(self, message):
        self._unlock_workspace()
        super()._on_export_failed_ui(message)

    def toggle_face_blur(self, track_id):
        if not self.is_exporting and not self.is_analysing:
            super().toggle_face_blur(track_id)

    def populate_gallery_ui(self):
        super().populate_gallery_ui()
        self.lbl_gallery.configure(text=f'ЛИЦА ДЛЯ РАЗМЫТИЯ · {len(self.unique_faces)}')
        if not self.unique_faces:
            ctk.CTkLabel(self.gallery_frame,
                         text='Найденные лица появятся здесь.\nОтметьте лица для размытия.',
                         font=(UI_FONT, 13), text_color=SECONDARY,
                         justify='left', anchor='w', wraplength=250).pack(fill='x', padx=12, pady=16)

    def _refresh_workspace(self):
        if self._closing:
            return
        path = self.reader.file_path if self.reader and self.raw_frames else None
        name = os.path.basename(path) if path else 'Ваше видео'
        # Keep long filenames out of the controls' layout.
        available = max(24, self.right_frame.winfo_width() // 13)
        title = name if len(name) <= available else name[:available - 1] + '…'
        if self.preview_header.cget('text') != title:
            self.preview_header.configure(text=title)
        hint = ('Двойной клик — выбор лица · колесо — масштаб · ⌘0 — вписать видео' if path else
                'Откройте видео, найдите лица и проверьте размытие перед экспортом')
        if self.preview_hint.cget('text') != hint:
            self.preview_hint.configure(text=hint)
        phase = (bool(path), bool(self.detected_boxes_cache), self.is_analysing)
        if getattr(self, '_action_phase', None) != phase:
            self._action_phase = phase
            self.btn_open.configure(fg_color=SURFACE if path else ACCENT,
                                    hover_color=HOVER if path else ACCENT_HOVER,
                                    text_color=TEXT if path else ON_ACCENT)
            analyze_primary = bool(path) and not self.detected_boxes_cache and not self.is_analysing
            self.btn_analyze.configure(fg_color=ACCENT if analyze_primary else SURFACE,
                                       hover_color=ACCENT_HOVER if analyze_primary else HOVER,
                                       text_color=ON_ACCENT if analyze_primary else TEXT)
        # The plain Tk status canvas must follow CTk appearance changes too.
        mode = ctk.get_appearance_mode()
        if getattr(self, '_last_status_theme', None) != mode:
            self._last_status_theme = mode
            self.lbl_status_left.configure(background=self._apply_appearance_mode(WINDOW))
            self.lbl_status_left.itemconfigure(self.lbl_status_left.item, fill=self._apply_appearance_mode(SECONDARY), font=(UI_FONT, 12))
        self.after(250, self._refresh_workspace)
