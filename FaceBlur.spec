# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
from imageio_ffmpeg import get_ffmpeg_exe
from pathlib import Path

block_cipher = None

# Автоматический сбор зависимостей, тем и ресурсов для CustomTkinter
ctk_datas, ctk_binaries, ctk_hiddenimports = collect_all('customtkinter')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=ctk_binaries + [(get_ffmpeg_exe(), ".")],
    datas=[
        ('yolov8s-face.pt', '.'),
        ('app_icon.icns', '.'),
        ('AutoBlureFace_icon.png', '.')
    ] + ctk_datas,
    hiddenimports=[
        'PIL._tkinter_finder',
        'customtkinter',
        'lap',
    ] + ctk_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FaceBlur Studio Executable',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app_icon.icns',
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

app = BUNDLE(
    coll,
    name='FaceBlur Studio.app',
    icon='app_icon.icns',
    bundle_identifier='com.sirdimitry.faceblur',
    info_plist={
        'CFBundleDevelopmentRegion': 'en',
        'CFBundleLocalizations': ['en', 'ru', 'zh-Hans', 'ar', 'sr', 'el', 'es'],
        'NSHighResolutionCapable': 'True',
        'LSBackgroundOnly': False,
        'CFBundleShortVersionString': '1.1.28',
        'CFBundleVersion': '1.1.28'
    }
)
