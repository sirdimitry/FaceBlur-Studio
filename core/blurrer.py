import cv2
import numpy as np

class FaceBlurrer:
    def __init__(self, blur_percent=70, padding_percent=25, fade_percent=40, shape_percent=100):
        self.kernel_size = self._calc_kernel_size(blur_percent)
        self.padding_percent = padding_percent / 100.0
        self.fade_percent = fade_percent / 100.0
        self.shape_percent = shape_percent / 100.0

    def set_blur_percent(self, val: int):
        self.kernel_size = self._calc_kernel_size(val)

    def set_padding_percent(self, val: int):
        self.padding_percent = val / 100.0

    def set_fade_percent(self, val: int):
        self.fade_percent = val / 100.0

    def set_shape_percent(self, val: int):
        self.shape_percent = val / 100.0

    def _calc_kernel_size(self, percent: int) -> int:
        val = int(percent)
        if val <= 0:
            return 0
        k_size = int(3 + (val / 100.0) * 196)
        if k_size % 2 == 0:
            k_size += 1
        return k_size

    def _create_alpha_mask(self, width: int, height: int) -> np.ndarray:
        if width <= 0 or height <= 0:
            return np.zeros((1, 1), dtype=np.float32)

        cx, cy = width / 2.0, height / 2.0
        rx, ry = width / 2.0, height / 2.0

        y_grid, x_grid = np.ogrid[:height, :width]

        ellipse_dist = ((x_grid - cx) / rx) ** 2 + ((y_grid - cy) / ry) ** 2
        rect_dist = np.maximum(np.abs(x_grid - cx) / rx, np.abs(y_grid - cy) / ry) ** 2

        dist = self.shape_percent * ellipse_dist + (1.0 - self.shape_percent) * rect_dist

        inner_r = 1.0 - self.fade_percent
        outer_r = 1.0

        alpha = np.zeros((height, width), dtype=np.float32)

        if self.fade_percent <= 0.001:
            alpha[dist <= outer_r] = 1.0
        else:
            mask_inner = dist <= inner_r
            alpha[mask_inner] = 1.0

            mask_fade = (dist > inner_r) & (dist <= outer_r)
            delta = (dist[mask_fade] - inner_r) / (outer_r - inner_r)
            alpha[mask_fade] = 0.5 * (1.0 + np.cos(np.pi * delta))

        return alpha

    def apply_blur_only(
        self, frame: np.ndarray, faces: list, active_blur_ids: set, kernel_scale: float = 1.0
    ) -> np.ndarray:
        if self.kernel_size == 0 or not faces or frame is None:
            return frame

        out_frame = frame.copy()
        img_h, img_w = frame.shape[:2]

        for face in faces:
            if face['id'] not in active_blur_ids:
                continue

            x1, y1, x2, y2 = face['bbox']
            w = x2 - x1
            h = y2 - y1

            if w <= 0 or h <= 0:
                continue

            pad_w = int(w * self.padding_percent)
            pad_h = int(h * self.padding_percent)

            bx1 = max(0, x1 - pad_w)
            by1 = max(0, y1 - pad_h)
            bx2 = min(img_w, x2 + pad_w)
            by2 = min(img_h, y2 + pad_h)

            bw = bx2 - bx1
            bh = by2 - by1

            if bw <= 0 or bh <= 0:
                continue

            roi = out_frame[by1:by2, bx1:bx2]
            kernel_size = max(3, int(self.kernel_size * max(0.05, kernel_scale)))
            if kernel_size % 2 == 0:
                kernel_size += 1
            blurred_roi = cv2.GaussianBlur(roi, (kernel_size, kernel_size), 0)

            alpha_mask = self._create_alpha_mask(bw, bh)[:, :, np.newaxis]
            blended_roi = (blurred_roi * alpha_mask + roi * (1.0 - alpha_mask)).astype(np.uint8)

            out_frame[by1:by2, bx1:bx2] = blended_roi

        return out_frame

    def apply_blur_and_labels(
        self, frame: np.ndarray, faces: list, active_blur_ids: set, kernel_scale: float = 1.0
    ) -> np.ndarray:
        out_frame = self.apply_blur_only(frame, faces, active_blur_ids, kernel_scale=kernel_scale)
        if not faces or out_frame is None:
            return out_frame

        img_h, img_w = out_frame.shape[:2]
        
        scale = max(0.4, img_h / 1080.0)
        font_scale = max(0.35, 0.5 * scale)
        thickness = max(1, int(1.5 * scale))
        padding_px = max(2, int(4 * scale))

        for face in faces:
            track_id = face['id']
            is_active = track_id in active_blur_ids

            # Цвет: Оранжево-красный для включенных, серый для выключенных
            color = (229, 78, 56) if is_active else (85, 85, 85)

            x1, y1, x2, y2 = face['bbox']
            w = x2 - x1
            h = y2 - y1

            pad_w = int(w * self.padding_percent)
            pad_h = int(h * self.padding_percent)

            bx1 = max(0, x1 - pad_w)
            by1 = max(0, y1 - pad_h)
            bx2 = min(img_w, x2 + pad_w)
            by2 = min(img_h, y2 + pad_h)

            cv2.rectangle(out_frame, (bx1, by1), (bx2, by2), color, thickness)

            label = f"#{track_id:02d}"
            (text_w, text_h), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)

            label_bg_y1 = max(0, by1 - text_h - 2 * padding_px)
            label_bg_y2 = by1
            label_bg_x2 = min(img_w, bx1 + text_w + 2 * padding_px)

            cv2.rectangle(out_frame, (bx1, label_bg_y1), (label_bg_x2, label_bg_y2), color, -1)
            cv2.putText(
                out_frame, 
                label, 
                (bx1 + padding_px, label_bg_y2 - padding_px), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                font_scale, 
                (255, 255, 255), 
                thickness, 
                cv2.LINE_AA
            )

        return out_frame
