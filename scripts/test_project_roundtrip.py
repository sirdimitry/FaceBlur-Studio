"""Regression checks for project settings and the original project format."""

import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.blurrer import FaceBlurrer
from core.project_manager import ProjectManager


class _Checked:
    def get(self):
        return True


class ProjectRoundtripTest(unittest.TestCase):
    def test_settings_and_face_selection_survive_reopen(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "проект с пробелами.fbp"
            for percent in (0, 1, 25, 70, 100):
                with self.subTest(percent=percent):
                    blurrer = FaceBlurrer(percent, 17, 33, 65)
                    ProjectManager.save_project(str(path), "видео с пробелами.mp4", blurrer,
                                                {"padding_percent": 17, "fade_percent": 33,
                                                 "shape_percent": 65}, _Checked(),
                                                {0: [{"id": 7, "bbox": (2, 3, 40, 50)}]},
                                                {7: {"enabled": False}})
                    data, cache, states = ProjectManager.load_project(str(path))
                    reopened = FaceBlurrer(data["blur_percent"], data["padding_percent"],
                                           data["fade_percent"], data["shape_percent"])
                    self.assertEqual(reopened.kernel_size, blurrer.kernel_size)
                    self.assertEqual(reopened.padding_percent, blurrer.padding_percent)
                    self.assertEqual(reopened.fade_percent, blurrer.fade_percent)
                    self.assertEqual(reopened.shape_percent, blurrer.shape_percent)
                    self.assertEqual(data["blur_percent"], percent)
                    self.assertTrue(data["export_labels"])
                    self.assertEqual(states, {7: False})
                    self.assertEqual(cache, {0: [{"id": 7, "bbox": [2, 3, 40, 50]}]})

    def test_legacy_kernel_values_preserve_blur(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "legacy.fbp"
            for percent in range(101):
                with self.subTest(percent=percent):
                    kernel = FaceBlurrer(percent).kernel_size
                    path.write_text(json.dumps({"blur_percent": kernel}), encoding="utf-8")
                    data, _, _ = ProjectManager.load_project(str(path))
                    self.assertEqual(FaceBlurrer(data["blur_percent"]).kernel_size, kernel)


if __name__ == "__main__":
    unittest.main()
