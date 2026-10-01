"""Regression checks for inaccurate container frame-count metadata."""

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.video_reader import FFmpegVideoReader


class ReaderFrameCountTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = str(Path(self.folder.name) / "fixture.avi")
        writer = cv2.VideoWriter(self.path, cv2.VideoWriter_fourcc(*"MJPG"), 10, (64, 48))
        self.assertTrue(writer.isOpened())
        for index in range(8):
            writer.write(np.full((48, 64, 3), index * 25, dtype=np.uint8))
        writer.release()

    def tearDown(self):
        self.folder.cleanup()

    def capture_factory(self, offset):
        original = cv2.VideoCapture

        class Capture:
            def __init__(self, path):
                self.cap = original(path)

            def get(self, prop):
                value = self.cap.get(prop)
                return value + offset if prop == cv2.CAP_PROP_FRAME_COUNT else value

            def __getattr__(self, name):
                return getattr(self.cap, name)

        return Capture

    def test_complete_read_corrects_metadata_and_last_seek(self):
        for offset in (-1, 1):
            with self.subTest(offset=offset), \
                    patch("core.video_reader.cv2.VideoCapture", self.capture_factory(offset)), \
                    patch.object(FFmpegVideoReader, "_extract_extended_info"):
                reader = FFmpegVideoReader(self.path)
                try:
                    self.assertEqual(len(reader), 8 + offset)
                    decoded = list(reader.read_frames())
                    self.assertEqual(len(decoded), 8)
                    self.assertEqual(len(reader), 8)
                    np.testing.assert_array_equal(reader[7], decoded[7])
                    with self.assertRaises(IndexError):
                        reader[8]
                finally:
                    reader.close()

    def test_partial_read_does_not_shorten_video(self):
        with patch("core.video_reader.cv2.VideoCapture", self.capture_factory(1)), \
                patch.object(FFmpegVideoReader, "_extract_extended_info"):
            reader = FFmpegVideoReader(self.path)
            frames = reader.read_frames()
            try:
                next(frames)
                frames.close()
                self.assertEqual(len(reader), 9)
            finally:
                reader.close()


if __name__ == "__main__":
    unittest.main()
