# Windows GPU startup, 1.1.28

The supplied 1.1.27 log shows `onnxruntime_pybind11_state` failing to initialize
in the analysis worker before provider selection. All four ONNX Runtime native
files are present. The exact failing native dependency is not identified by
that log; the affected RTX 3070 Ti computer is not available for local testing.

The application now registers ONNX Runtime's `capi` DLL directory and imports
ONNX Runtime on the main thread before loading Tk, OpenCV, or the interface.
The directory handle stays alive throughout the process. This removes the
late native-library initialization from the analysis worker. CPU fallback is
still available if the runtime cannot load.

The new `--smoke-test-threaded` check creates a hidden Tk window, loads the UI
module, and runs detection in a worker. It fails unless DirectML is active and
faces are detected. Unlike the earlier command-line smoke test, it exercises
the GUI/worker execution pattern and rejects CPU fallback.

Local verification on Windows 11:

- Source: 12 frames, 115 detections, ONNX Runtime DirectML.
- Packaged EXE with an isolated system-only PATH, outside the source directory:
  32 frames, 315 detections, ONNX Runtime DirectML.
- Packaged result: `build/verification/v1.1.28-gpu-worker/report.json`.
- Final multilingual package: `build/verification/v1.1.28-multilingual-gpu/report.json`
  (32 frames, 315 detections through DirectML with a system-only PATH).

Run the packaged regression with a video containing faces:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_windows_package.ps1 `
  -PackageDirectory 'dist/FaceBlur Studio' -Video 'path/to/faces.mp4' `
  -OutputDirectory 'build/verification/new-gpu-worker' -Mode gpu-worker -MaxFrames 32
```

The startup log should contain `ONNX Runtime startup preload` with
`DmlExecutionProvider`, and the analysis status should show `GPU · DirectML`.
The user subsequently confirmed that this GPU startup fix works on the affected
RTX 3070 Ti computer. The published installer additionally includes the seven
UI languages from the shared 1.1.28 source and a seven-language setup wizard.

Native Windows localization checks passed: seven language regression tests,
four slider tests and two project round-trip tests. Windows Tk pixel-distance
conversion and scrollable-frame border access were corrected while validating
Arabic layout and live language switching.

The final multilingual package also passed the 12-frame pipeline check:
DirectML analysis, selective blur, project save/reopen and exports with/without
audio, followed by decoding both outputs. Report:
`build/verification/v1.1.28-multilingual-pipeline/report.json`.

Inno Setup compiled all seven wizard languages without translation warnings.
The installer round-trip check was not repeated for this build because it
detected an existing installed application and refused to replace it for QA.
Earlier installer round-trip results remain historical; a clean Windows/VM
installation test is still outstanding.
