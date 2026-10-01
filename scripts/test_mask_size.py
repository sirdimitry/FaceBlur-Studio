"""Check actual affected pixels, endpoints and mask/label geometry."""
import sys
import unittest
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.blurrer import FaceBlurrer


class MaskSizeTest(unittest.TestCase):
    def test_minimum_and_maximum_coverage(self):
        frame = np.random.default_rng(4).integers(0, 256, (400, 400, 3), dtype=np.uint8)
        faces = [{'id': 1, 'bbox': (150, 150, 240, 240)}]
        for percent, expected in [(0, 30), (25, 134), (100, 270)]:
            with self.subTest(percent=percent):
                blurrer = FaceBlurrer(100, percent, 0, 0)
                result = blurrer.apply_blur_only(frame, faces, {1})
                y, x = np.where(np.any(result != frame, axis=2))
                self.assertEqual(int(x.max() - x.min() + 1), expected)
                self.assertEqual(int(y.max() - y.min() + 1), expected)
                self.assertTrue(np.array_equal(frame, blurrer.apply_blur_only(frame, faces, set())))

    def test_detection_overlay_is_independent_of_mask_settings(self):
        frame = np.zeros((400, 400, 3), dtype=np.uint8)
        faces = [{'id': 1, 'bbox': (150, 150, 240, 240)}]
        for active in ({1}, set()):
            reference = FaceBlurrer(0, 0).apply_blur_and_labels(frame, faces, active)
            for percent in (6, 25, 50, 100):
                blurrer = FaceBlurrer(0, percent, percent, percent)
                result = blurrer.apply_blur_and_labels(frame, faces, active)
                self.assertTrue(np.array_equal(reference, result))
            self.assertTrue(np.any(reference[150, 150]))
            self.assertTrue(np.any(reference[240, 240]))

    def test_range_is_continuous_and_monotonic(self):
        values = [FaceBlurrer(padding_percent=p).padding_percent for p in range(101)]
        self.assertTrue(all(a < b for a, b in zip(values, values[1:])))
        self.assertAlmostEqual(values[0], -1 / 3)
        self.assertEqual(values[25], .25)
        self.assertEqual(values[100], 1)


if __name__ == '__main__':
    unittest.main()
