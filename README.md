<p align="right"><strong>English</strong> · <a href="README.ru.md">Русский</a></p>

<p align="center"><img src="assets/banner.png" alt="FaceBlur Studio" width="100%"></p>

# FaceBlur Studio

<p align="center"><strong>Local video face blurring</strong><br>Preview, face tracking, and control over which faces are blurred.</p>

> **Download:** [FaceBlur Studio 1.1.23 for Apple Silicon Mac (DMG, 292 MiB)](https://github.com/sirdimitry/FaceBlur-Studio/releases/download/v1.1.23/FaceBlur_Studio_v1.1.23_Apple_Silicon.dmg). This is a preliminary release. A Windows installer is planned but not available yet.

## Screenshot

![FaceBlur Studio 1.1.23 showing face analysis and video preview](assets/faceblur-studio-1.1.23.png)

## Features

- Automatic face detection and tracking with YOLOv8-face.
- Select which faces to blur, preview the result, and adjust the blur mask.
- Save and reopen `.fbp` projects with analysis results.
- Export MP4 with the original audio track when present.
- Read video frames as needed instead of keeping the whole video decoded in RAM.
- Process video locally without uploading it to a cloud service.

Automatic detection can miss faces. Review the entire exported video before sharing it.

## Installation

**Apple Silicon Mac:** download the [DMG](https://github.com/sirdimitry/FaceBlur-Studio/releases/download/v1.1.23/FaceBlur_Studio_v1.1.23_Apple_Silicon.dmg), open it, and drag **FaceBlur Studio** onto **Applications**. Python, FFmpeg, and the face detection model are bundled; they do not need separate installation for the DMG.

This preliminary DMG uses a local ad hoc signature and is **not notarized** by Apple. macOS may block its first launch. If you trust this download and macOS blocks it, follow [Apple's Open Anyway instructions](https://support.apple.com/en-au/102445) in System Settings → Privacy & Security. Installation has not been checked on a separate clean Mac, so trouble-free startup on other systems is not guaranteed. This build targets Apple Silicon; Intel Macs and Windows are not supported by this installer.

SHA-256: `ced92a61d541f303f3a3fad2e85fdc255d812bea1e8c2c6e8eaf4f72df29e1d4`

**Run from source.** Python 3.12 and FFmpeg are required. The `yolov8s-face.pt` model is included in the repository. On macOS, FFmpeg can be installed with `brew install ffmpeg`.

```bash
git clone https://github.com/sirdimitry/FaceBlur-Studio.git
cd FaceBlur-Studio
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

The source setup currently targets macOS. A Windows package and its installation have not been verified. The [DMG build script](scripts/build_macos_dmg.sh) requires `create-dmg`; a successful build is not a substitute for installation testing on a clean Mac.

## Diagnostics

When run from source, the log is `debug_app.log` in the project folder. For an installed Mac app, it is `~/Library/Logs/FaceBlurStudio/debug_app.log`. Logs may contain local file paths; review them before sharing.

## Repository contents

This repository contains the source code, face detection model, [app icon](AutoBlureFace_icon.png), [banner](assets/banner.png), and a current screenshot. The DMG is attached to [GitHub Release v1.1.23](https://github.com/sirdimitry/FaceBlur-Studio/releases/tag/v1.1.23), not committed to the source tree.

## License

No separate license file has been published in this repository yet. Reuse terms for the source code and bundled models need to be clarified before redistribution or modification.
