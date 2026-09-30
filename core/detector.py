import cv2
import logging
import torch
from ultralytics import YOLO

from core.compute_device import ComputeDevice, select_compute_device

class FaceDetector:
    def __init__(self, model_path="yolov8s-face.pt"):
        # Инициализация скачанной модели YOLOv8s-face
        self.model = YOLO(model_path)
        self.compute = select_compute_device()
        logging.info("Устройство распознавания: %s", self.compute.description)

    @property
    def device_description(self):
        return self.compute.description

    def _track(self, frame):
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
        self.compute = ComputeDevice(torch.device("cpu"), "cpu", "CPU (GPU fallback)")
        self.model.predictor = None
        self.model.to("cpu")

    def track_faces(self, frame):
        try:
            results = self._track(frame)
        except (RuntimeError, ValueError, NotImplementedError):
            if self.compute.backend == "cpu":
                raise
            self._fallback_to_cpu()
            results = self._track(frame)
        
        current_faces = []

        if results and results[0].boxes and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            track_ids = results[0].boxes.id.int().cpu().tolist()

            for box, t_id in zip(boxes, track_ids):
                x1, y1, x2, y2 = map(int, box)
                current_faces.append({'id': t_id, 'bbox': (x1, y1, x2, y2)})

        return current_faces
