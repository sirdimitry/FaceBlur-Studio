"""Exercise macOS input, recovery and processing controls with a real video."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cv2
import numpy as np
from core.project_manager import ProjectManager
from ui.mac_window import MacMainWindow


@unittest.skipUnless(sys.platform == 'darwin', 'macOS workspace')
class MacWorkspaceTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.video = Path(self.directory.name) / 'видео.mp4'
        writer = cv2.VideoWriter(str(self.video), cv2.VideoWriter_fourcc(*'mp4v'), 25, (160, 120))
        for _ in range(8):
            writer.write(np.random.default_rng(7).integers(0, 256, (120, 160, 3), dtype=np.uint8))
        writer.release()
        self.app = MacMainWindow()
        self.app.save_settings = lambda: None
        with patch('customtkinter.filedialog.askopenfilename', return_value=str(self.video)):
            self.app.open_video()
        self.pump()

    def pump(self):
        self.app.after(100, self.app.quit)
        self.app.mainloop()

    def tearDown(self):
        for timer in self.app.tk.call('after', 'info'):
            self.app.tk.call('after', 'cancel', timer)
        self.app.on_closing()
        self.directory.cleanup()

    def test_precise_input_and_invalid_value_recovery(self):
        app = self.app
        variable, field = app._value_fields['blur_percent']
        variable.set('101')
        before = app.blurrer.blur_percent
        app._commit_value('blur_percent', app.blur_slider, app.on_blur_slider_change)
        self.assertEqual(app.blurrer.blur_percent, before)
        self.assertTrue(app.lbl_error_log.cget('text'))
        variable.set('42')
        app._commit_value('blur_percent', app.blur_slider, app.on_blur_slider_change)
        self.assertEqual(app.blurrer.blur_percent, 42)
        self.assertEqual(app.blur_slider.get(), 42)
        self.assertFalse(app.lbl_error_log.cget('text'))

    def test_analysis_busy_guard_and_failure_recovery(self):
        app = self.app
        with patch('threading.Thread.start'):
            app.start_analysis_thread()
        self.assertTrue(app.is_analysing)
        self.assertEqual(app.btn_open.cget('state'), 'disabled')
        original_reader = app.reader
        with patch('customtkinter.filedialog.askopenfilename') as dialog:
            app.open_video()
            dialog.assert_not_called()
        self.assertIs(app.reader, original_reader)
        app.stop_analysis()
        self.assertTrue(app.stop_analysis_flag)
        app._on_analysis_failed_ui('Тестовая ошибка')
        self.assertFalse(app.is_analysing)
        self.assertEqual(app.btn_open.cget('state'), 'normal')
        self.assertEqual(app.btn_analyze.cget('state'), 'normal')

    def test_project_preview_selection_and_real_export(self):
        app = self.app
        app.detected_boxes_cache = {i: [{'id': 1, 'bbox': (20, 20, 70, 80)}] for i in range(8)}
        app._on_analysis_finished_ui()
        self.pump()
        self.assertEqual(app.get_active_blur_ids(), {1})
        app.toggle_face_blur(1)
        self.assertEqual(app.get_active_blur_ids(), set())
        project = Path(self.directory.name) / 'проект.fbp'
        with patch('customtkinter.filedialog.asksaveasfilename', return_value=str(project)):
            app.save_project()
        self.assertEqual(ProjectManager.load_project(project)[2], {1: False})
        with patch('customtkinter.filedialog.askopenfilename', return_value=str(project)):
            app.load_project()
        self.assertEqual(app.get_active_blur_ids(), set())
        output = Path(self.directory.name) / 'результат.mp4'
        with patch('customtkinter.filedialog.asksaveasfilename', return_value=str(output)), patch('threading.Thread.start'):
            app.export_video()
        self.assertTrue(app.is_exporting)
        self.assertEqual(app.blur_slider.cget('state'), 'disabled')
        app._run_export(str(output), app.get_active_blur_ids(), False)
        self.pump()
        self.assertFalse(app.is_exporting)
        self.assertEqual(app.btn_open.cget('state'), 'normal')
        self.assertEqual(app.btn_export.cget('text'), 'Видео сохранено')
        cap = cv2.VideoCapture(str(output))
        count = 0
        while cap.read()[0]:
            count += 1
        cap.release()
        self.assertEqual(count, 8)


if __name__ == '__main__':
    unittest.main()
