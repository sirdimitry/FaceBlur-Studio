# Windows port handoff

## Start here

Repository: https://github.com/sirdimitry/FaceBlur-Studio

The current `main` branch contains FaceBlur Studio 1.1.23 and the Apple Silicon preview release. The macOS DMG, its release tag, and `scripts/build_macos_dmg.sh` must stay intact while Windows work proceeds. Build the Windows package on Windows: PyInstaller does not cross-compile between macOS and Windows.

Use a separate branch so work on both computers can continue safely:

```powershell
git clone https://github.com/sirdimitry/FaceBlur-Studio.git
cd FaceBlur-Studio
git switch -c windows-port
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

If dependency installation fails, record the exact error and adjust Windows-specific requirements rather than changing macOS versions blindly. Push `windows-port` and open a pull request when it is ready. Do not force-push `main` or overwrite the existing Mac release.

## Known platform-specific code

- `FaceBlur.spec` is a macOS bundle recipe: it uses `.icns` and `BUNDLE`. Create a separate Windows spec or a platform-aware spec. Produce a Windows `.exe` with the app model, icons, and FFmpeg included. Use the existing `AutoBlureFace_icon.png` to make a Windows `.ico` without changing the Mac icon.
- `core/ffmpeg_path.py` looks for a bundled file named `ffmpeg-macos-aarch64-v7.1`. Resolve the actual bundled Windows `ffmpeg.exe` from the PyInstaller resource directory; verify that export with audio works without a system FFmpeg installation. `ffprobe` is optional for metadata: the video reader already falls back to OpenCV's FourCC.
- `app_logging.py` and `ui/main_window.py` use `~/Library/...` for installed-app logs and settings. On Windows use a writable per-user location such as `%LOCALAPPDATA%\FaceBlurStudio`, while preserving the current macOS paths.
- `main.py` sets `MPLCONFIGDIR` under `~/Library/Caches`. Give Windows a writable cache path. Keep `multiprocessing.freeze_support()` before creating the Tk interface in a frozen build.
- `requirements.txt` was pinned in a Mac environment. Check whether all pinned wheels install on Windows and separate platform-specific dependencies if needed.
- `ui/dialogs.py` shows a stale version string (`1.1.0`). Update it when setting the Windows release version. The interface is currently in Russian; do not describe it as fully translated in documentation.

## Verify before calling it installable

1. Run from source on Windows, then run the packaged app on another clean Windows machine or VM without Python or FFmpeg installed.
2. Open a supported video, play, seek, choose another video, and confirm the old preview disappears. Check the red status message for an unreadable video.
3. Analyze faces, toggle a face's blur, save and reopen a `.fbp` project, and export MP4 both with and without audio. Review the exported video end to end.
4. Check a longer video to confirm frames are read on demand and memory does not grow with the entire uncompressed video.
5. Check icon, splash screen, window behavior, paths containing Cyrillic characters/spaces, and the error log on Windows.
6. Package an installer with only the files needed by users. Record its SHA-256 and whether Windows SmartScreen warns on first run. Do not claim a warning-free installation without signing and testing it.

When a Windows installer is actually published, update **both** `README.md` and `README.ru.md` with its real download link, version, supported Windows versions, installation instructions, and tested limitations. Keep the macOS DMG link and Apple Silicon caveat accurate. See also [RELEASE.md](RELEASE.md).

## Ready-to-paste task for the Windows assistant

> Port FaceBlur Studio from the current `main` branch to Windows. Read `docs/WINDOWS_HANDOFF.md` and work on a separate `windows-port` branch. Preserve the existing macOS build and GitHub release. Make paths, FFmpeg bundling, packaging, and logs work on Windows; build and test a native Windows installer on Windows. Verify source run and packaged run, including video preview, analysis, projects, and export with audio. Push the branch and open a PR with test results and remaining limitations. Do not publish a Windows release or change the README download claims until the installer has been tested and is ready for publication.
