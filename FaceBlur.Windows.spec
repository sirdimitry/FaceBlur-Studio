# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller recipe for the self-contained Windows distribution."""

from imageio_ffmpeg import get_ffmpeg_exe
from PyInstaller.utils.hooks import collect_all


block_cipher = None

# CustomTkinter needs its themes and other package data at runtime.
ctk_datas, ctk_binaries, ctk_hiddenimports = collect_all("customtkinter")

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=(
        ctk_binaries
        + [(get_ffmpeg_exe(), ".")]
    ),
    datas=[
        ("yolov8s-face.onnx", "."),
        ("AutoBlureFace_icon.png", "."),
        ("app_icon.ico", "."),
    ] + ctk_datas,
    hiddenimports=[
        "PIL._tkinter_finder",
        "customtkinter",
        "lap",
        "onnxruntime",
    ] + ctk_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib",
        "polars",
        "sympy",
        "torch",
        "torchvision",
        "ultralytics",
    ],
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
