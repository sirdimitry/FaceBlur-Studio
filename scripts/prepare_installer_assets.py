"""Size installer artwork for Inno Setup without cropping brand text."""
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets' / 'installer'


def prepare():
    portrait = Image.open(ASSETS / 'brand-portrait.png').convert('RGB')
    sidebar = ImageOps.pad(portrait, (820, 1570), color='#080e24')
    sidebar.save(ASSETS / 'wizard-sidebar.png')

    wide = Image.open(ASSETS / 'brand-landscape.png').convert('RGB')
    ImageOps.pad(wide, (1500, 450), color='#080e24').save(ASSETS / 'progress-banner.png')

    # Keep the original application icon, including its rounded transparent corners.
    icon = Image.open(ROOT / 'AutoBlureFace_icon.png').convert('RGBA')
    mark = Image.new('RGBA', (192, 192))
    mark.alpha_composite(icon.resize((176, 176), Image.Resampling.LANCZOS), (8, 8))
    mark.save(ASSETS / 'wizard-mark.png')

    # A deliberately quiet background keeps the native wizard text readable.
    background = Image.new('RGB', (1491, 1080))
    pixels = background.load()
    for y in range(background.height):
        for x in range(background.width):
            cyan = max(0, 1 - ((x / 1491) ** 2 + (y / 1080) ** 2) ** .5)
            violet = max(0, 1 - (((1491-x) / 1491) ** 2 + ((1080-y) / 1080) ** 2) ** .5)
            pixels[x, y] = (int(13 + violet * 9), int(19 + cyan * 7), int(33 + cyan * 12 + violet * 14))
    background.save(ASSETS / 'wizard-background.png')
    print('Installer artwork prepared:', ASSETS)


if __name__ == '__main__':
    prepare()
