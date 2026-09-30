# Release checklist

This checklist applies whenever a macOS DMG or a future Windows installer is published.

1. Update the version in `main.py`, `ui/main_window.py`, `app_logging.py`, `FaceBlur.spec`, and the DMG build script.
2. Build the installer and check that it launches on a separate clean machine of the supported architecture. Check opening a video, analysis, project save/load, playback, and export with audio.
3. For a macOS public release, sign and notarize the application and DMG with Apple Developer ID, then verify the signature and Gatekeeper behavior on another Mac.
4. Check the DMG Finder window: the only visible items should be `FaceBlur Studio.app` and the `Applications` link, placed over the branded background.
5. Update **both** `README.md` (English) and `README.ru.md` (Russian). Replace the statements that no DMG or Windows installer is available when that changes. Add the real download link, supported systems, installation steps, version, and tested limitations.
6. Attach the installer to a GitHub Release rather than committing it into the source tree. Check the asset name, size, checksum, and download link.

Do not describe a platform as tested until its installer has been checked on a separate clean machine.
