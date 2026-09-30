"""Run the FaceBlur processing pipeline without opening the GUI."""

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.blurrer import FaceBlurrer
from core.detector import FaceDetector
from core.project_manager import ProjectManager
from core.video_reader import FFmpegVideoReader
from core.video_writer import FFmpegVideoWriter


class _Checked:
    def get(self):
        return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("video", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("project", type=Path)
    parser.add_argument("--max-frames", type=int)
    args = parser.parse_args()

    reader = FFmpegVideoReader(str(args.video))
    detector = FaceDetector("yolov8s-face.pt")
    blurrer = FaceBlurrer()
    frame_limit = min(len(reader), args.max_frames or len(reader))
    detected_boxes_cache = {}
    unique_faces = {}

    for index, frame in enumerate(reader.read_frames()):
        if index >= frame_limit:
            break
        faces = detector.track_faces(frame)
        detected_boxes_cache[index] = faces
        for face in faces:
            unique_faces.setdefault(int(face["id"]), {"enabled": True})
        if (index + 1) % 100 == 0 or index + 1 == frame_limit:
            print(f"analysis {index + 1}/{frame_limit}", flush=True)

    active_ids = set(unique_faces)
    writer = FFmpegVideoWriter(
        str(args.output), reader.width, reader.height, reader.fps, str(args.video)
    )
    for index, frame in enumerate(reader.read_frames()):
        if index >= frame_limit:
            break
        output_frame = blurrer.apply_blur_only(
            frame, detected_boxes_cache.get(index, []), active_ids
        )
        writer.write_frame(output_frame)
        if (index + 1) % 100 == 0 or index + 1 == frame_limit:
            print(f"export {index + 1}/{frame_limit}", flush=True)
    writer.close()

    settings = {
        "padding_percent": 25,
        "fade_percent": 40,
        "shape_percent": 100,
    }
    ProjectManager.save_project(
        str(args.project),
        str(args.video),
        blurrer,
        settings,
        _Checked(),
        detected_boxes_cache,
        unique_faces,
    )
    _, loaded_cache, loaded_states = ProjectManager.load_project(str(args.project))

    result = {
        "input_frames": len(reader),
        "processed_frames": len(detected_boxes_cache),
        "tracked_faces": len(unique_faces),
        "project_frames": len(loaded_cache),
        "project_states": len(loaded_states),
        "output": str(args.output),
        "project": str(args.project),
    }
    reader.close()
    print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
