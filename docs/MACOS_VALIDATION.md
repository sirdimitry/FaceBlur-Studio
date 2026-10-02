# macOS 1.1.28 validation

Validated on the development Apple Silicon Mac on 2026-10-03.

- PyInstaller build and DMG creation completed successfully.
- `codesign --verify --deep --strict` passed for the built app and the app mounted from the final DMG.
- `hdiutil verify` passed for the final DMG.
- Bundle version: 1.1.28; architecture: arm64; bundled Python, face model and FFmpeg.
- Seven bundle localizations: English, Russian, Simplified Chinese, Arabic, Serbian, Greek and Spanish.
- Packaged GUI launched in English on this system.
- Pipeline verification passed both from the build and from the mounted DMG: 30 frames of a 1920×1080 H.264 video, Apple Metal face detection, selective blur, project roundtrip, frame seeking, exports with and without audio, and FFmpeg decoding of both exports.
- With-audio export contains H.264 video and AAC audio; without-audio export contains H.264 video only.
- Source checks: 25 tests passed; two Windows-only checks were skipped. Multilingual documentation freshness and whitespace checks passed.

This is a preliminary release. The signature is ad hoc; no Developer ID certificate or Apple notarization is available. Gatekeeper assessment rejected the app. A separate clean-Mac installation test and native Windows validation were not performed. The existing Windows download remains version 1.1.27.

DMG: `FaceBlur_Studio_v1.1.28_Apple_Silicon.dmg` (307,678,315 bytes).

SHA-256: `9ba0cc0fd5c9dfba8a58c90ba0f4e16e2f4460efcc725131505016deb547ed1d`.
