from ui.i18n import tr
import math
import subprocess
import json
import logging
import cv2
from core.ffmpeg_path import executable, hidden_subprocess_options

class FFmpegVideoReader:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.cap = cv2.VideoCapture(file_path)
        
        if not self.cap.isOpened():
            raise ValueError(tr("Не удалось открыть видеофайл: {0}").format(file_path))

        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 25.0
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self._current_frame = -1
        self._cached_frame = None

        # Вычисляем соотношение сторон (Aspect Ratio)
        gcd = math.gcd(self.width, self.height)
        if gcd > 0:
            self.aspect_ratio = f"{self.width // gcd}:{self.height // gcd}"
        else:
            self.aspect_ratio = "16:9"

        # Получаем данные о кодеке и битрейте через ffprobe
        fourcc = int(self.cap.get(cv2.CAP_PROP_FOURCC))
        fourcc_name = "".join(chr((fourcc >> (8 * i)) & 0xff) for i in range(4)).strip("\x00 ")
        self.codec = {"avc1": "H264", "hvc1": "HEVC", "hev1": "HEVC"}.get(fourcc_name.lower(), fourcc_name.upper() or "Unknown")
        self.bitrate_str = "N/A"
        self._extract_extended_info()

    def _extract_extended_info(self):
        try:
            probe = executable("ffprobe")
        except FileNotFoundError:
            return
        cmd = [
            probe, "-v", "quiet", "-print_format", "json",
            "-show_streams", "-show_format", self.file_path
        ]
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                **hidden_subprocess_options(),
            )
            data = json.loads(result.stdout)
            
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "video":
                    self.codec = stream.get("codec_name", "h264").upper()
                    break

            bitrate = data.get("format", {}).get("bit_rate")
            if bitrate:
                mbps = float(bitrate) / 1_000_000
                self.bitrate_str = f"{mbps:.1f} Mbps"
        except Exception:
            pass

    def read_frames(self):
        # Анализ и экспорт читают файл своим декодером, не меняя позицию превью.
        cap = cv2.VideoCapture(self.file_path)
        if not cap.isOpened():
            raise ValueError(tr("Не удалось открыть видеофайл: {0}").format(self.file_path))
        decoded_count = 0
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    if decoded_count != self.total_frames:
                        logging.warning("Video frame count corrected after EOF: %s -> %s",
                                        self.total_frames, decoded_count)
                        self.total_frames = decoded_count
                    break
                decoded_count += 1
                yield frame
        finally:
            cap.release()

    def __len__(self):
        return self.total_frames

    def __getitem__(self, index):
        if not 0 <= index < self.total_frames:
            raise IndexError(index)
        if index == self._current_frame and self._cached_frame is not None:
            return self._cached_frame
        if index != self._current_frame + 1:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, index)
        ret, frame = self.cap.read()
        if not ret:
            raise ValueError(tr("Не удалось прочитать кадр {0} из видео").format(index + 1))
        self._current_frame = index
        self._cached_frame = frame
        return frame

    def __iter__(self):
        return self.read_frames()

    def close(self):
        if self.cap:
            self.cap.release()
            self.cap = None
        self._cached_frame = None
