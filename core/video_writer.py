import subprocess
import cv2
from core.ffmpeg_path import executable, hidden_subprocess_options
import numpy as np

class FFmpegVideoWriter:
    """
    Модуль сохранения обработанных кадров с переносом оригинального звука через FFmpeg.
    """
    def __init__(self, output_path: str, width: int, height: int, fps: float, source_audio_path: str = None):
        self.output_path = output_path
        self.width = width
        self.height = height
        self.fps = fps
        self.source_audio_path = source_audio_path

        # Формируем FFmpeg пайплайн через stdin
        cmd = [
            executable("ffmpeg"), "-y", "-loglevel", "error",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{width}x{height}",
            "-pix_fmt", "bgr24",
            "-r", str(fps),
            "-i", "-",  # Чтение кадров из stdin
        ]

        if source_audio_path:
            cmd.extend(["-i", source_audio_path, "-map", "0:v:0", "-map", "1:a:0?", "-c:a", "copy"])

        cmd.extend([
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "fast",
            output_path
        ])

        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **hidden_subprocess_options(),
        )

    def write_frame(self, frame_bgr: np.ndarray):
        if self.process and self.process.stdin:
            try:
                self.process.stdin.write(frame_bgr.tobytes())
            except (BrokenPipeError, OSError) as error:
                details = self._stderr_text()
                message = "FFmpeg прервал экспорт"
                if details:
                    message += f": {details}"
                raise RuntimeError(message) from error

    def _stderr_text(self):
        if not self.process or not self.process.stderr:
            return ""
        data = self.process.stderr.read()
        return data.decode("utf-8", errors="replace").strip()

    def close(self):
        if self.process:
            if self.process.stdin:
                self.process.stdin.close()
            code = self.process.wait()
            details = self._stderr_text()
            if self.process.stderr:
                self.process.stderr.close()
            self.process = None
            if code:
                message = f"FFmpeg завершился с кодом {code}"
                if details:
                    message += f": {details}"
                raise RuntimeError(message)
