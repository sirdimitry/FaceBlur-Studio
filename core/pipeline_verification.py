"""Opt-in release verification using the same modules as the application."""

import json
from pathlib import Path
import subprocess
import time
import ctypes
import sys

import cv2
import numpy as np

from core.blurrer import FaceBlurrer
from core.detector import FaceDetector
from core.ffmpeg_path import executable, hidden_subprocess_options
from core.project_manager import ProjectManager
from core.video_reader import FFmpegVideoReader
from core.video_writer import FFmpegVideoWriter


class _Unchecked:
    def get(self):
        return False


def verify_pipeline(video_path, output_dir, model_path, max_frames=None):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "report.json"
    report = {"input": str(video_path), "checks": {}, "status": "running"}

    def record(name, details):
        report["checks"][name] = details
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    reader = None
    try:
        reader = FFmpegVideoReader(str(video_path))
        count = min(len(reader), int(max_frames)) if max_frames else len(reader)
        if count <= 0:
            raise ValueError("Input has no frames")
        record("metadata", {"frames": len(reader), "tested_frames": count,
                            "width": reader.width, "height": reader.height, "fps": reader.fps})
        detector = FaceDetector(model_path)
        blurrer = FaceBlurrer()
        cache, states = {}, {}
        started = time.monotonic()
        for index, frame in enumerate(reader.read_frames()):
            if index >= count:
                break
            faces = detector.track_faces(frame)
            cache[index] = faces
            for face in faces:
                states[int(face["id"])] = {"enabled": True}
        assert len(cache) == count, "Input ended early"
        assert states, "No faces detected; use a fixture containing faces"
        record("analysis", {"backend": detector.backend, "device": detector.device_description,
                            "frames": len(cache), "face_ids": len(states),
                            "seconds": round(time.monotonic() - started, 2)})

        index = next(i for i, faces in cache.items() if faces)
        original = reader[index]
        assert np.array_equal(original, blurrer.apply_blur_only(original, cache[index], set()))
        assert not np.array_equal(original, blurrer.apply_blur_only(original, cache[index], set(states)))
        chosen = int(cache[index][0]["id"])
        states[chosen]["enabled"] = False
        active = {face_id for face_id, state in states.items() if state["enabled"]}
        assert np.array_equal(
            blurrer.apply_blur_only(original, cache[index], active),
            blurrer.apply_blur_only(original, [f for f in cache[index] if int(f["id"]) != chosen], active))
        record("blur_toggle", {"disabled_face_id": chosen, "disabled_unchanged": True,
                               "enabled_changes_pixels": True})

        project = output_dir / "проект проверки.fbp"
        ProjectManager.save_project(str(project), str(video_path), blurrer,
                                    {"padding_percent": 25, "fade_percent": 40, "shape_percent": 100},
                                    _Unchecked(), cache, states)
        data, restored, restored_states = ProjectManager.load_project(str(project))
        normalized = json.loads(json.dumps(cache))
        assert {str(k): v for k, v in restored.items()} == normalized
        assert restored_states == {k: v["enabled"] for k, v in states.items()}
        assert data["video_path"] == str(video_path)
        assert data["blur_percent"] == blurrer.blur_percent
        restored_blurrer = FaceBlurrer(data["blur_percent"], data["padding_percent"],
                                       data["fade_percent"], data["shape_percent"])
        restored_active = {k for k, enabled in restored_states.items() if enabled}
        assert np.array_equal(blurrer.apply_blur_only(original, cache[index], active),
                              restored_blurrer.apply_blur_only(original, restored[index], restored_active))
        record("project_roundtrip", {"frames": len(restored), "states": len(restored_states),
                                     "disabled_state_preserved": True, "render_equal": True})

        for position in (count - 1, 0, count // 2, index):
            assert reader[position].shape == original.shape
        record("seek", {"positions": [count - 1, 0, count // 2, index]})

        for label, audio_source in (("with_audio", str(video_path)), ("without_audio", None)):
            destination = output_dir / f"экспорт {label}.mp4"
            writer = FFmpegVideoWriter(str(destination), reader.width, reader.height,
                                       reader.fps, audio_source)
            try:
                for i, frame in enumerate(reader.read_frames()):
                    if i >= count:
                        break
                    writer.write_frame(blurrer.apply_blur_only(frame, restored[i], restored_active))
            finally:
                writer.close()
            decoded = cv2.VideoCapture(str(destination))
            decoded_count = 0
            try:
                while True:
                    ok, frame = decoded.read()
                    if not ok:
                        break
                    assert frame.shape == original.shape
                    decoded_count += 1
            finally:
                decoded.release()
            assert decoded_count == count, f"Export frame mismatch: {decoded_count}/{count}"
            subprocess.run([executable("ffmpeg"), "-v", "error", "-xerror", "-i", str(destination),
                            "-f", "null", "-"], check=True, capture_output=True,
                           **hidden_subprocess_options())
            record(label, {"path": str(destination), "decoded_frames": decoded_count,
                           "ffmpeg_decode": "passed", "bytes": destination.stat().st_size})
        report["status"] = "passed"
    except Exception as error:
        report["status"] = "failed"
        report["error"] = repr(error)
        raise
    finally:
        if reader is not None:
            reader.close()
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def _working_set_bytes():
    if sys.platform != "win32":
        return None

    class Counters(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong)] + [
            (name, ctypes.c_size_t) for name in
            ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
             "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage",
             "PagefileUsage", "PeakPagefileUsage")]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(Counters), ctypes.c_ulong]
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return counters.WorkingSetSize


def verify_reader(video_path, report_path):
    """Read a long video sequentially while recording bounded-memory evidence."""
    reader = FFmpegVideoReader(str(video_path))
    report = {"input": str(video_path), "status": "running", "frames": len(reader),
              "samples": [], "read_frames": 0}
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    try:
        for index, frame in enumerate(reader.read_frames()):
            assert frame.shape[:2] == (reader.height, reader.width)
            report["read_frames"] = index + 1
            if index % 5000 == 0 or index + 1 == len(reader):
                report["samples"].append({"frame": index + 1, "working_set_bytes": _working_set_bytes()})
                report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        assert report["read_frames"] == len(reader)
        report["corrected_frames"] = len(reader)
        report["metadata_count_matches"] = report["frames"] == report["read_frames"]
        for index in (len(reader) - 1, 0, len(reader) // 2):
            assert reader[index] is not None
        reader.close()
        second = FFmpegVideoReader(str(video_path))
        try:
            assert second[0] is not None
        finally:
            second.close()
        try:
            FFmpegVideoReader(str(report_path.parent / "missing video.mp4"))
        except ValueError:
            report["invalid_input_rejected"] = True
        else:
            raise AssertionError("Missing video was accepted")
        report["seek_and_reopen"] = "passed"
        report["seconds"] = round(time.monotonic() - started, 2)
        report["status"] = "passed"
    except Exception as error:
        report["status"] = "failed"
        report["error"] = repr(error)
        raise
    finally:
        reader.close()
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
