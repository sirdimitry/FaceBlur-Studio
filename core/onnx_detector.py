"""Windows face detection using ONNX Runtime DirectML with CPU fallback."""

import logging
import os

import cv2
import lap
import numpy as np


class _IouTracker:
    def __init__(self, max_missing=30, match_threshold=0.75):
        self.max_missing = max_missing
        self.match_threshold = match_threshold
        self.next_id = 1
        self.tracks = {}

    @staticmethod
    def _iou_matrix(track_boxes, detection_boxes):
        if len(track_boxes) == 0 or len(detection_boxes) == 0:
            return np.empty((len(track_boxes), len(detection_boxes)), dtype=np.float32)
        a = np.asarray(track_boxes, dtype=np.float32)[:, None, :]
        b = np.asarray(detection_boxes, dtype=np.float32)[None, :, :]
        top_left = np.maximum(a[..., :2], b[..., :2])
        bottom_right = np.minimum(a[..., 2:], b[..., 2:])
        intersection = np.prod(np.maximum(0.0, bottom_right - top_left), axis=2)
        area_a = np.prod(np.maximum(0.0, a[..., 2:] - a[..., :2]), axis=2)
        area_b = np.prod(np.maximum(0.0, b[..., 2:] - b[..., :2]), axis=2)
        return intersection / np.maximum(area_a + area_b - intersection, 1e-6)

    def update(self, boxes):
        track_ids = list(self.tracks)
        track_boxes = [self.tracks[track_id]["bbox"] for track_id in track_ids]
        matches = {}

        if track_boxes and boxes:
            costs = 1.0 - self._iou_matrix(track_boxes, boxes)
            _, assignments, _ = lap.lapjv(
                costs,
                extend_cost=True,
                cost_limit=self.match_threshold,
            )
            for track_index, detection_index in enumerate(assignments):
                if detection_index >= 0:
                    matches[int(detection_index)] = track_ids[track_index]

        matched_track_ids = set(matches.values())
        for track_id in track_ids:
            if track_id not in matched_track_ids:
                self.tracks[track_id]["missing"] += 1

        output = []
        for detection_index, box in enumerate(boxes):
            track_id = matches.get(detection_index)
            if track_id is None:
                track_id = self.next_id
                self.next_id += 1
            clean_box = tuple(int(value) for value in box)
            self.tracks[track_id] = {"bbox": clean_box, "missing": 0}
            output.append({"id": track_id, "bbox": clean_box})

        self.tracks = {
            track_id: track
            for track_id, track in self.tracks.items()
            if track["missing"] <= self.max_missing
        }
        return output


class OnnxFaceDetector:
    INPUT_SIZE = 640

    def __init__(self, model_path):
        import onnxruntime as ort

        self.model_path = str(model_path)
        options = ort.SessionOptions()
        options.enable_mem_pattern = False
        options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL

        available = ort.get_available_providers()
        self.backend = "cpu"
        providers = ["CPUExecutionProvider"]
        requested_device = os.environ.get("FACEBLUR_DEVICE", "auto").strip().lower()
        if requested_device != "cpu" and "DmlExecutionProvider" in available:
            device_id = int(os.environ.get("FACEBLUR_DML_DEVICE", "0"))
            providers = [
                ("DmlExecutionProvider", {"device_id": device_id}),
                "CPUExecutionProvider",
            ]
            self.backend = "directml"

        try:
            self.session = ort.InferenceSession(
                self.model_path,
                sess_options=options,
                providers=providers,
            )
        except Exception:
            if self.backend == "cpu":
                raise
            logging.exception("DirectML initialization failed; using ONNX Runtime CPU")
            self.backend = "cpu"
            self.session = ort.InferenceSession(
                self.model_path,
                sess_options=options,
                providers=["CPUExecutionProvider"],
            )

        active_provider = self.session.get_providers()[0]
        self.device_description = (
            "ONNX Runtime DirectML" if active_provider == "DmlExecutionProvider" else "ONNX Runtime CPU"
        )
        self.input_name = self.session.get_inputs()[0].name
        self.tracker = _IouTracker()
        logging.info("Устройство распознавания: %s", self.device_description)

    def _prepare(self, frame):
        height, width = frame.shape[:2]
        scale = min(self.INPUT_SIZE / width, self.INPUT_SIZE / height)
        resized_w = round(width * scale)
        resized_h = round(height * scale)
        resized = cv2.resize(frame, (resized_w, resized_h), interpolation=cv2.INTER_LINEAR)
        pad_x = (self.INPUT_SIZE - resized_w) / 2
        pad_y = (self.INPUT_SIZE - resized_h) / 2
        left = round(pad_x - 0.1)
        right = round(pad_x + 0.1)
        top = round(pad_y - 0.1)
        bottom = round(pad_y + 0.1)
        padded = cv2.copyMakeBorder(
            resized,
            top,
            bottom,
            left,
            right,
            cv2.BORDER_CONSTANT,
            value=(114, 114, 114),
        )
        tensor = padded[:, :, ::-1].transpose(2, 0, 1)
        tensor = np.ascontiguousarray(tensor, dtype=np.float32) / 255.0
        return tensor[None], scale, left, top

    def _detect(self, frame):
        tensor, scale, pad_x, pad_y = self._prepare(frame)
        prediction = self.session.run(None, {self.input_name: tensor})[0][0].T
        scores = prediction[:, 4]
        prediction = prediction[scores >= 0.3]
        scores = scores[scores >= 0.3]
        if not len(prediction):
            return []

        xywh = prediction[:, :4]
        boxes = np.empty_like(xywh)
        boxes[:, 0] = xywh[:, 0] - xywh[:, 2] / 2
        boxes[:, 1] = xywh[:, 1] - xywh[:, 3] / 2
        boxes[:, 2] = xywh[:, 2]
        boxes[:, 3] = xywh[:, 3]
        indices = cv2.dnn.NMSBoxes(boxes.tolist(), scores.tolist(), 0.3, 0.5)
        if len(indices) == 0:
            return []

        height, width = frame.shape[:2]
        output = []
        for index in np.asarray(indices).reshape(-1):
            x, y, w, h = boxes[index]
            x1 = int(np.clip((x - pad_x) / scale, 0, width - 1))
            y1 = int(np.clip((y - pad_y) / scale, 0, height - 1))
            x2 = int(np.clip((x + w - pad_x) / scale, x1 + 1, width))
            y2 = int(np.clip((y + h - pad_y) / scale, y1 + 1, height))
            output.append((x1, y1, x2, y2))
        return output

    def track_faces(self, frame):
        try:
            boxes = self._detect(frame)
        except Exception:
            if self.backend == "cpu":
                raise
            logging.exception("DirectML inference failed; rebuilding session on CPU")
            import onnxruntime as ort

            options = ort.SessionOptions()
            options.enable_mem_pattern = False
            options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
            self.session = ort.InferenceSession(
                self.model_path,
                sess_options=options,
                providers=["CPUExecutionProvider"],
            )
            self.backend = "cpu"
            self.device_description = "ONNX Runtime CPU (DirectML fallback)"
            boxes = self._detect(frame)
        return self.tracker.update(boxes)
