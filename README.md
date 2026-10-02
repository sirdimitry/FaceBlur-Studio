<p align="right"><strong>English</strong> · <a href="README.ru.md">Русский</a></p>

<p align="center"><img src="assets/banner.png" alt="FaceBlur Studio" width="100%"></p>

# FaceBlur Studio

<p align="center"><strong>Local video face blurring</strong><br>Preview, face tracking, and control over which faces are blurred.</p>

> **Download:** [FaceBlur Studio 1.1.23 for Apple Silicon Mac (DMG, 292 MiB)](https://github.com/sirdimitry/FaceBlur-Studio/releases/download/v1.1.23/FaceBlur_Studio_v1.1.23_Apple_Silicon.dmg). This is a preliminary release. **The Windows version is ready — download and try it completely free:** [FaceBlur Studio 1.1.27 for Windows 10/11 x64 (EXE, 126 MiB)](https://github.com/sirdimitry/FaceBlur-Studio/releases/download/v1.1.27/FaceBlur-Studio-1.1.27-Windows-Setup.exe).

## Screenshot

![FaceBlur Studio 1.1.23 showing face analysis and video preview](assets/faceblur-studio-1.1.23.png)

## Features

- Apple Metal (macOS) or DirectML (Windows) inference acceleration with CPU fallback.
- Fast preview, accurate face selection in scaled video, and adjustable mask size, shape, and feathering.
- Automatic face detection and tracking with YOLOv8-face.
- Select which faces to blur, preview the result, and adjust the blur mask.
- Save and reopen `.fbp` projects with analysis results.
- Export MP4 with the original audio track when present.
- Read video frames as needed instead of keeping the whole video decoded in RAM.
- Process video locally without uploading it to a cloud service.

Automatic detection can miss faces. Review the entire exported video before sharing it.

## Installation

**Windows 10/11 x64:** download the [installer](https://github.com/sirdimitry/FaceBlur-Studio/releases/download/v1.1.27/FaceBlur-Studio-1.1.27-Windows-Setup.exe) and run it. Choose English or Russian and follow the setup wizard. Installation defaults to `%LOCALAPPDATA%\Programs\FaceBlur Studio` for the current user and does not require administrator rights. Python, FFmpeg, the face detection model, and inference libraries are bundled. Uninstall through Windows Settings; user projects and settings are preserved.

The Windows installer is unsigned. Installation, reinstallation, packaged startup, and uninstallation were verified on the development Windows 11 machine; a separate clean Windows/VM has not yet been tested. See [installer details](docs/WINDOWS_INSTALLER.md) and [Windows verification results](docs/WINDOWS_VALIDATION.md).

Windows installer SHA-256: `01f751ca1d29a5be5cfb9a4feae240af1d4b2747722c078f27ba1f903039365d`

**Apple Silicon Mac:** download the [DMG](https://github.com/sirdimitry/FaceBlur-Studio/releases/download/v1.1.23/FaceBlur_Studio_v1.1.23_Apple_Silicon.dmg), open it, and drag **FaceBlur Studio** onto **Applications**. Python, FFmpeg, and the face detection model are bundled; they do not need separate installation for the DMG.

This preliminary DMG uses a local ad hoc signature and is **not notarized** by Apple. macOS may block its first launch. If you trust this download and macOS blocks it, follow [Apple's Open Anyway instructions](https://support.apple.com/en-au/102445) in System Settings → Privacy & Security. Installation has not been checked on a separate clean Mac, so trouble-free startup on other systems is not guaranteed. This build targets Apple Silicon; Intel Macs and Windows are not supported by this installer.

SHA-256: `b83947aa54d0b39ebc9bd638eb6c3858e30c63bfd46007604987b319ba712dee`

**Run from source.** Python 3.12 and FFmpeg are required. The `yolov8s-face.pt` model is included in the repository. On macOS, FFmpeg can be installed with `brew install ffmpeg`.

```bash
git clone https://github.com/sirdimitry/FaceBlur-Studio.git
cd FaceBlur-Studio
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

For Windows source setup, use Python 3.12, activate the environment with `.\venv\Scripts\Activate.ps1`, and install `requirements-windows.txt` instead of `requirements.txt`. FFmpeg must be available on PATH. See the [Windows port guide](docs/WINDOWS_HANDOFF.md) and [installer build instructions](docs/WINDOWS_INSTALLER.md). The [DMG build script](scripts/build_macos_dmg.sh) requires `create-dmg`.

## Diagnostics

When run from source, the log is `debug_app.log` in the project folder. For an installed Mac app, it is `~/Library/Logs/FaceBlurStudio/debug_app.log`. For an installed Windows app, it is `%LOCALAPPDATA%\FaceBlurStudio\Logs\debug_app.log`. Logs may contain local file paths; review them before sharing.

## Repository contents

This repository contains the source code, face detection model, [app icon](AutoBlureFace_icon.png), [banner](assets/banner.png), and a current screenshot. The Windows installer is attached to [GitHub Release v1.1.27](https://github.com/sirdimitry/FaceBlur-Studio/releases/tag/v1.1.27) and the DMG to [v1.1.23](https://github.com/sirdimitry/FaceBlur-Studio/releases/tag/v1.1.23), not committed to the source tree.

## License

No separate license file has been published in this repository yet. Reuse terms for the source code and bundled models need to be clarified before redistribution or modification.
