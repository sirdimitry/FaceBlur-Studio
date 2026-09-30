#!/bin/bash
set -euo pipefail

project_dir="$(cd "$(dirname "$0")/.." && pwd)"
dist_dir="${FACEBLUR_DIST_DIR:-$project_dir/dist}"
app="$dist_dir/FaceBlur Studio.app"
image="$project_dir/dist/FaceBlur_Studio_v1.1.23_Apple_Silicon.dmg"
resources="$app/Contents/Resources"
background="$project_dir/assets/dmg-background.png"

command -v create-dmg >/dev/null || { echo "Install create-dmg before building the installer" >&2; exit 1; }
test -f "$background" || { echo "Missing installer background: $background" >&2; exit 1; }

for required in "$app/Contents/MacOS/FaceBlur Studio Executable" "$resources/yolov8s-face.pt" "$resources/ffmpeg-macos-aarch64-v7.1"; do
    test -f "$required" || { echo "Missing bundle resource: $required" >&2; exit 1; }
done
test -x "$resources/ffmpeg-macos-aarch64-v7.1" || { echo "Bundled FFmpeg is not executable" >&2; exit 1; }
file "$app/Contents/MacOS/FaceBlur Studio Executable" | grep -q arm64
file "$resources/ffmpeg-macos-aarch64-v7.1" | grep -q arm64
codesign --verify --deep --strict "$app"

stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT
ditto "$app" "$stage/FaceBlur Studio.app"
create-dmg \
    --volname 'FaceBlur Studio 1.1.23' \
    --volicon "$project_dir/app_icon.icns" \
    --background "$background" \
    --window-size 720 440 \
    --icon-size 112 \
    --text-size 14 \
    --icon 'FaceBlur Studio.app' 180 280 \
    --app-drop-link 540 280 \
    --hide-extension 'FaceBlur Studio.app' \
    --format UDZO \
    --overwrite \
    "$image" "$stage"
shasum -a 256 "$image"
