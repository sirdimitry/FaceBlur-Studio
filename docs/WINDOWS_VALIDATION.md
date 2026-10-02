# Windows verification — 2026-10-01

This records local verification, not certification on a clean Windows machine.

## Fixes found during verification

- Projects previously saved the Gaussian kernel size as `blur_percent`, so reopening a project changed the strength. New projects use format version 2 and save the percentage. Original projects are converted on load. Regression checks cover percentages 0–100 in the original format and new project settings and face selection.
- Loading a project now restores the checkbox controlling face ID labels in exports.
- After reading a video completely, the reader now replaces approximate container frame-count metadata with the decoded count. The UI refreshes the seek range after analysis/export. Stopping a read early does not shorten the video. This fixes a reproduced overestimated/underestimated count and last-frame seeking problem.
- Diagnostic failures are logged and return exit code 1 without opening PyInstaller's interactive exception dialog.

## Repeatable packaged checks

Build on Windows with `python -m PyInstaller --noconfirm FaceBlur.Windows.spec` in the Windows build environment.

The packaged application supports optional diagnostic modes without opening a window:

- `--verify-pipeline VIDEO OUTPUT_DIRECTORY [MAX_FRAMES]`: analyze, toggle blur, save/reopen a project, seek, export with/without the source audio, and decode every exported frame. Use a video containing faces. Omitting `MAX_FRAMES` tests the entire video. Reports and exports remain in the output directory.
- `--verify-reader VIDEO REPORT_JSON`: decode the entire video, sample process working-set memory, seek, reopen, and reject a missing input.
- `--smoke-test VIDEO REPORT_JSON [MAX_FRAMES]`: detector-only check; defaults to 30 frames.

`scripts/verify_windows_package.ps1` launches these modes with only Windows system directories in PATH and removes external Python environment variables. Use a fresh output directory for every run. This checks the packaged dependencies on the current host; it does not replace a clean-machine test.

```powershell
.\scripts\verify_windows_package.ps1 -PackageDirectory '.\dist\FaceBlur Studio' -Video 'C:\Videos\sample.mp4' -OutputDirectory 'C:\Results\pipeline'
.\scripts\verify_windows_package.ps1 -PackageDirectory '.\dist\FaceBlur Studio' -Video 'C:\Videos\long.mp4' -OutputDirectory 'C:\Results\reader' -Mode reader
.\scripts\verify_windows_package.ps1 -PackageDirectory '.\dist\FaceBlur Studio' -Video 'C:\Videos\sample.mp4' -OutputDirectory 'C:\Results\cpu' -Mode smoke -Cpu
```

Run `python scripts/test_project_roundtrip.py` for project regression checks.
Run `python scripts/test_reader_frame_count.py` for complete/partial reading and last-frame seeking with inaccurate count metadata.

If the host's PowerShell policy blocks local `.ps1` files, the same inspected script can be invoked as an in-memory script block without changing the host policy:

```powershell
$verify = [scriptblock]::Create((Get-Content -LiteralPath '.\scripts\verify_windows_package.ps1' -Raw -Encoding UTF8))
& $verify -PackageDirectory '.\dist\FaceBlur Studio' -Video 'C:\Videos\sample.mp4' -OutputDirectory 'C:\Results\pipeline'
```

## Remaining manual checks

- Visual GUI verification: play/pause, seeking, replacing a video, gallery face toggles, save/open dialogs, rendered blur, splash/icon, and unreadable-file status. The Computer Use native pipe was unavailable in this session, including after retry and kernel reset.
- End-to-end installation and GUI operation on a separate clean Windows machine or VM without Python or FFmpeg. No accessible clean VM or Windows Sandbox was found on this host.
- Review face detection and tracking quality before releasing. Decoding checks do not establish that every face is anonymized.

## Local results

Host: Windows 11 Home, x64, build 26200. The final portable folder contains 1,084 files, totaling 388,980,481 bytes. Final executable SHA-256: `3907da9a5a01b3473f88db8afe940503709589f0fd39a0f81d68ba37ec7b0925` (this hashes the executable only, not the complete portable folder).

The full 1,774-frame exports were checked on the preceding rebuild, executable SHA-256 `10e5bf3ef602b5e970e94e8a06f92fd97dd01b248c92a8d42007f7ba72e32f8f`. After the frame-count fix, the final rebuild was checked again with the short CPU pipeline, DirectML detector, reader regression tests, and long-video reader.

| Check | Result | Evidence under `build/verification/` |
| --- | --- | --- |
| Original packaged detector | Passed: DirectML, 120 frames, 1,174 detections | `packaged-detector.json` |
| Rebuilt packaged full pipeline | Passed: 1,774 frames at 1916×1080, 30 fps, 31 track IDs; blur toggles and project cache/states/render preserved | `packaged-full/report.json` |
| Full MP4 with audio | Passed: all 1,774 frames decoded by OpenCV and bundled FFmpeg; H.264 video and AAC audio | `with-audio-streams.json` |
| Audio preservation | Passed: all 2,775 audio packet hashes match the original | `audio-comparison.json` |
| Full MP4 without audio | Passed: all 1,774 frames decoded; no audio stream | `without-audio-streams.json` |
| Silent input through the normal export path | Passed: 32 frames; optional audio mapping handles a source without audio | `packaged-silent/report.json` |
| Final rebuild: CPU with isolated PATH, outside the source directory | Passed: analysis, project round trip, both exports and decoding on 32 frames | `final-cpu/report.json` |
| Final rebuild: DirectML with isolated PATH | Passed: 32 frames, 315 detections | `final-directml/report.json` |
| Final rebuild: long video reading and memory | Passed: all 100,863 decodable frames of a 28-minute 1080p/60 fps video; EOF count corrected; seeking, reopening and missing-input rejection passed; sampled working set 140.2–172.7 MiB | `final-long-reader/report.json`, `long-reader-summary.json` |
| Project regression tests | Passed: 2 tests; all 101 original blur strengths migrate without changing the kernel | `scripts/test_project_roundtrip.py` |
| Reader regression tests | Passed: 2 tests; complete reads correct counts ±1 and last-frame seeking; partial reads preserve the reported length | `scripts/test_reader_frame_count.py` |
| Diagnostic error exit | Passed: a missing input exits with code 1 within 10 seconds, without hanging on an exception dialog | Application log |

The first long-reader check exposed metadata reporting 100,864 frames while OpenCV decoded 100,863. Independent `ffprobe -count_frames` confirmed 100,863 decoded frames, with no reported decoding error. The original failed report is preserved in `long-reader/report.json`; the independent count is recorded in `ffprobe-frame-count.json`. The final rebuild passed a complete repeat on the video in 465.48 seconds, including count refinement and last-frame seeking. Its decoded count matches the independent FFprobe result.

The isolated runs used a copied package under a directory containing Cyrillic characters and spaces. Python was loaded from that package's `_internal/python312.dll`. Input/output/project paths with Cyrillic characters and spaces worked. These are current-host checks; the host still has development tools installed.

Contact sheets of the original and exported frames were inspected at the beginning, middle and end. Track ID 1 was deliberately disabled for the test, so one face remains visible. This is not a claim that every face in the video is anonymized.

Performance observation: DirectML analysis of the 59-second Full HD input took 330.45 seconds. The first full export, including final decode verification, took about 8 minutes on this host. Export is substantially slower than real-time; these timings are observations, not a controlled benchmark.

Generated media and JSON reports are kept under `build/verification/` and are not committed.
