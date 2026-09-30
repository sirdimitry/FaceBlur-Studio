<p align="center"><img src="assets/banner.svg" alt="FaceBlur Studio" width="100%"></p>

# FaceBlur Studio

<p align="center"><img src="AutoBlureFace_icon.png" alt="FaceBlur Studio app icon" width="72"></p>

<p align="center"><strong>Local video face blurring</strong><br>Preview, face tracking, and control over which faces are blurred.</p>

<p align="center"><a href="README.md">Русский</a> · <strong>English</strong></p>

> **Download status:** no installer has been published on GitHub yet. [Releases](https://github.com/sirdimitry/FaceBlur-Studio/releases) is empty. A DMG for Apple Silicon Macs is planned after review. A Windows version is planned, but there is no Windows installer yet.

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

**Prebuilt installer.** Not available yet. The current source and a local 1.1.23 DMG were exercised on an Apple Silicon Mac, but the DMG has not been published as a Release or tested on a separate clean Mac. Trouble-free installation on every Mac cannot be guaranteed. Standard macOS distribution also needs [Apple Developer ID signing and notarization](https://developer.apple.com/documentation/technologyoverviews/distribution); without them, Gatekeeper may block the first launch.

**Run from source.** Python 3.12 and FFmpeg are required. The `yolov8s-face.pt` model is included in the repository. On macOS, FFmpeg can be installed with `brew install ffmpeg`.

```bash
git clone https://github.com/sirdimitry/FaceBlur-Studio.git
cd FaceBlur-Studio
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

The source setup currently targets macOS. A Windows package and its installation have not been verified. The [DMG build script](scripts/build_macos_dmg.sh) can be used to build from source, but a successful build is not a substitute for installation testing on a clean Mac.

## Diagnostics

When run from source, the log is `debug_app.log` in the project folder. For an installed Mac app, it is `~/Library/Logs/FaceBlurStudio/debug_app.log`. Logs may contain local file paths; review them before sharing.

## Repository contents

This repository contains the source code, face detection model, [app icon](AutoBlureFace_icon.png), [banner](assets/banner.svg), and a current screenshot. The DMG is not checked into the repository; once reviewed, it will be attached to a GitHub Release. The local build is approximately 357 MB.

## License

No separate license file has been published in this repository yet. Reuse terms for the source code and bundled models need to be clarified before redistribution or modification.
