"""Install into an isolated QA folder, smoke-test, upgrade, then uninstall."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import winreg

import cv2
import numpy as np
from PIL import ImageGrab

ROOT = Path(__file__).resolve().parents[1]
UNINSTALL_KEY = r'Software\Microsoft\Windows\CurrentVersion\Uninstall\{D214BBF1-A626-4D17-8DD9-63FE6AD6EC03}_is1'


def registered():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY):
            return True
    except FileNotFoundError:
        return False


def sha256(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def install_and_capture(setup, arguments, output):
    """Capture only our setup window; do not inject any desktop input."""
    process = subprocess.Popen([str(setup), *arguments, f'/LOG={output / "install.log"}'])
    started = time.monotonic()
    deadline = started + 180
    captured = False
    while process.poll() is None:
        if time.monotonic() > deadline:
            process.kill()
            raise TimeoutError('Installer timed out')
        if not captured and time.monotonic() - started >= 5:
            windows = []
            user32 = ctypes.windll.user32
            @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
            def collect(hwnd, _):
                title = ctypes.create_unicode_buffer(512)
                user32.GetWindowTextW(hwnd, title, len(title))
                if title.value.endswith('FaceBlur Studio') and '\u2014' in title.value and user32.IsWindowVisible(hwnd):
                    windows.append(hwnd)
                return True
            user32.EnumWindows(collect, 0)
            if len(windows) == 1:
                ImageGrab.grab(window=windows[0]).save(output / 'setup-progress-preview.png')
                captured = True
        time.sleep(.25)
    if process.returncode:
        raise subprocess.CalledProcessError(process.returncode, process.args)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('setup', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT / 'build/verification/installer-roundtrip')
    args = parser.parse_args()
    if registered():
        parser.error('An installed FaceBlur Studio already exists; refusing to replace it for QA.')
    output = args.output.resolve()
    if output.exists():
        parser.error('Use a fresh output directory to preserve previous QA results.')
    output.mkdir(parents=True)
    install = output / 'Установка с пробелами'
    group = 'FaceBlur Studio'
    shortcut = Path(os.environ['APPDATA']) / 'Microsoft/Windows/Start Menu/Programs' / group / 'FaceBlur Studio.lnk'
    assert not shortcut.exists(), 'QA shortcut already exists'
    settings = Path(os.environ['LOCALAPPDATA']) / 'FaceBlurStudio/config.json'
    settings_before = settings.read_bytes() if settings.exists() else None
    setup = args.setup.resolve()
    arguments = ['/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/LANG=russian',
                 f'/DIR={install}', f'/GROUP={group}', '/TASKS=']
    result = {'setup': str(setup), 'sha256': sha256(setup)}
    try:
        # SILENT displays installation progress, allowing a real visual QA capture.
        install_and_capture(setup, ['/SILENT', *arguments[1:]], output)
        assert registered(), 'Missing uninstall registration'
        assert shortcut.is_file(), 'Missing Start Menu shortcut'
        package = ROOT / 'dist/FaceBlur Studio'
        files = [path for path in package.rglob('*') if path.is_file()]
        for source in files:
            target = install / source.relative_to(package)
            assert target.is_file(), f'Missing installed file: {target}'
            assert sha256(source) == sha256(target), f'Installed file differs: {target}'
        result['installed_files_verified'] = len(files)

        # Verify that a second install performs an in-place upgrade and preserves user files.
        user_file = install / 'user-created-project.fbp'
        user_file.write_text('QA user data must survive reinstall and uninstall.', encoding='utf-8')
        subprocess.run([str(setup), *arguments, f'/LOG={output / "upgrade.log"}'], check=True, timeout=180)
        assert user_file.read_text(encoding='utf-8').startswith('QA user data')
        result['upgrade_preserves_user_files'] = True

        video = output / 'smoke-input.mp4'
        writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*'mp4v'), 10, (320, 240))
        assert writer.isOpened()
        for index in range(12):
            frame = np.full((240, 320, 3), index * 16, dtype=np.uint8)
            writer.write(frame)
        writer.release()
        report = output / 'app-smoke.json'
        subprocess.run([str(install / 'FaceBlur Studio.exe'), '--smoke-test', str(video), str(report), '12'],
                       cwd=output, check=True, timeout=90)
        result['installed_app'] = json.loads(report.read_text(encoding='utf-8'))
        assert result['installed_app']['frames'] == 12
    finally:
        uninstaller = install / 'unins000.exe'
        if uninstaller.exists():
            subprocess.run([str(uninstaller), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
                            f'/LOG={output / "uninstall.log"}'], cwd=output, check=True, timeout=180)
    assert not (install / 'FaceBlur Studio.exe').exists(), 'Application not removed'
    assert not registered(), 'Uninstall registration not removed'
    assert not shortcut.exists(), 'Shortcut not removed'
    assert user_file.exists(), 'User-created project removed'
    settings_after = settings.read_bytes() if settings.exists() else None
    assert settings_before == settings_after, 'Existing user settings changed'
    result['uninstall_preserves_user_files_and_settings'] = True
    result['uninstall_removes_application_shortcuts_and_registration'] = True
    (output / 'report.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
