import json

class ProjectManager:
    @staticmethod
    def save_project(file_path, video_path, blurrer, settings, chk_export_labels, detected_boxes_cache, unique_faces):
        serializable_cache = {}
        for frame_idx, faces in detected_boxes_cache.items():
            serializable_cache[str(frame_idx)] = faces

        active_states = {str(t_id): data['enabled'] for t_id, data in unique_faces.items()}

        project_data = {
            "format_version": 2,
            "video_path": video_path,
            "blur_percent": blurrer.blur_percent,
            "padding_percent": settings.get("padding_percent", 25),
            "fade_percent": settings.get("fade_percent", 40),
            "shape_percent": settings.get("shape_percent", 100),
            "export_labels": bool(chk_export_labels.get()),
            "detected_boxes_cache": serializable_cache,
            "unique_faces_states": active_states
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(project_data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def load_project(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            project_data = json.load(f)

        # Original projects stored the Gaussian kernel under "blur_percent".
        if project_data.get("format_version", 1) < 2 and "blur_percent" in project_data:
            kernel = int(project_data["blur_percent"])
            project_data["blur_percent"] = (
                0 if kernel <= 0 else max(1, min(100, round((kernel - 3) * 100 / 196)))
            )

        raw_cache = project_data.get("detected_boxes_cache", {})
        detected_boxes_cache = {int(k): v for k, v in raw_cache.items()}
        active_states = {int(k): v for k, v in project_data.get("unique_faces_states", {}).items()}

        return project_data, detected_boxes_cache, active_states
