# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller recipe for the self-contained Windows distribution."""

from imageio_ffmpeg import get_ffmpeg_exe
from PyInstaller.utils.hooks import collect_all, is_module_satisfiable


block_cipher = None

# CustomTkinter needs its themes and other package data at runtime.
ctk_datas, ctk_binaries, ctk_hiddenimports = collect_all("customtkinter")

# Ultralytics loads tracker YAML files and some modules dynamically.
yolo_datas, yolo_binaries, yolo_hiddenimports = collect_all("ultralytics")
dml_hiddenimports = ["torch_directml"] if is_module_satisfiable("torch_directml") else []


a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=(
        ctk_binaries
        + yolo_binaries
        + [(get_ffmpeg_exe(), ".")]
    ),
    datas=[
        ("yolov8s-face.pt", "."),
        ("AutoBlureFace_icon.png", "."),
    ] + ctk_datas + yolo_datas,
    hiddenimports=[
        "PIL._tkinter_finder",
        "customtkinter",
        "lap",
    ] + ctk_hiddenimports + yolo_hiddenimports + dml_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FaceBlur Studio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon="app_icon.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="FaceBlur Studio",
)
