"""Build the branded Windows setup with Inno Setup 6.7.3+ (no paid plugins)."""
import argparse
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler', type=Path)
    parser.add_argument('--package-dir', type=Path, default=ROOT / 'dist' / 'FaceBlur Studio')
    parser.add_argument('--rebuild-app', action='store_true')
    args = parser.parse_args()
    if args.rebuild_app:
        subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm',
                        'FaceBlur.Windows.spec'], cwd=ROOT, check=True)

    package = args.package_dir.resolve()
    for name in ('FaceBlur Studio.exe', '_internal/app_icon.ico', '_internal/yolov8s-face.onnx'):
        if not (package / name).is_file():
            parser.error(f'Incomplete application package: {package / name}')

    candidates = [
        ROOT / 'build/installer-tools/Inno Setup 6/ISCC.exe',
        ROOT / 'build/installer-tools/compiler/app/ISCC.exe',
        Path(os.environ.get('ProgramFiles(x86)', 'C:/Program Files (x86)')) / 'Inno Setup 6/ISCC.exe',
        Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'Inno Setup 7/ISCC.exe',
        Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'Programs/Inno Setup 6/ISCC.exe',
    ]
    compiler = args.compiler or next((path for path in candidates if path.is_file()), None)
    compiler = compiler or shutil.which('ISCC.exe')
    if not compiler:
        parser.error('Install Inno Setup 6.7.3+ from https://jrsoftware.org/isdl.php or pass --compiler.')

    version = re.search(r'^APP_VERSION = "([\d.]+)"',
                        (ROOT / 'main.py').read_text(encoding='utf-8'), re.MULTILINE).group(1)
    subprocess.run([str(compiler), f'/DAppVersion={version}', f'/DPackageDir={package}',
                    str(ROOT / 'installer/FaceBlurStudio.iss')], cwd=ROOT, check=True)
    setup = ROOT / 'dist/installer' / f'FaceBlur-Studio-{version}-Windows-Setup.exe'
    with setup.open('rb') as source:
        digest = hashlib.file_digest(source, 'sha256').hexdigest()
    setup.with_suffix('.exe.sha256').write_text(f'{digest}  {setup.name}\n', encoding='ascii')
    print(f'Installer: {setup}\nSize: {setup.stat().st_size / 1024**2:.1f} MiB\nSHA256: {digest}')


if __name__ == '__main__':
    main()
