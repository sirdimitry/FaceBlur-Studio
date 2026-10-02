"""Face detector with DirectML on Windows and PyTorch on other platforms."""

import logging
import sys
from pathlib import Path


def default_model_filename():
    return "yolov8s-face.onnx" if sys.platform == "win32" else "yolov8s-face.pt"


class FaceDetector:
    def __init__(self, model_path=None):
        model_path = model_path or default_model_filename()
        self._onnx = None
        self.model = None
        self.compute = None

        onnx_path = Path(model_path)
        if sys.platform == "win32" and onnx_path.suffix.lower() == ".onnx" and onnx_path.is_file():
            from core.onnx_detector import OnnxFaceDetector

            self._onnx = OnnxFaceDetector(onnx_path)
            return

        import torch
        from ultralytics import YOLO

        from core.compute_device import ComputeDevice, select_compute_device

        self._torch = torch
        self._compute_device_type = ComputeDevice
        self.model = YOLO(model_path)
        self.compute = select_compute_device()
        logging.info("Устройство распознавания: %s", self.compute.description)

    @property
    def backend(self):
        return self._onnx.backend if self._onnx else self.compute.backend

    @property
    def device_description(self):
        return self._onnx.device_description if self._onnx else self.compute.description

    def _track_torch(self, frame):
        return self.model.track(
            frame,
            persist=True,
            tracker="botsort.yaml",
            verbose=False,
            conf=0.3,
            device=self.compute.device,
        )

    def _fallback_to_cpu(self):
        logging.warning(
            "GPU backend %s failed; retrying face detection on CPU",
            self.compute.description,
            exc_info=True,
        )
        self.compute = self._compute_device_type(
            self._torch.device("cpu"), "cpu", "CPU (GPU fallback)"
        )
        self.model.predictor = None
        self.model.to("cpu")

    def track_faces(self, frame):
        if self._onnx:
            return self._onnx.track_faces(frame)

        try:
            results = self._track_torch(frame)
        except (RuntimeError, ValueError, NotImplementedError):
            if self.compute.backend == "cpu":
                raise
            self._fallback_to_cpu()
            results = self._track_torch(frame)

        current_faces = []
        if results and results[0].boxes and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            track_ids = results[0].boxes.id.int().cpu().tolist()
            for box, track_id in zip(boxes, track_ids):
                current_faces.append(
                    {"id": track_id, "bbox": tuple(map(int, box))}
                )
        return current_faces
