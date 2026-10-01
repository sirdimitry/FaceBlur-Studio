"""Generate Windows icon resolutions from the original application logo."""
from pathlib import Path
from PIL import Image
root=Path(__file__).resolve().parents[1]
image=Image.open(root/'AutoBlureFace_icon.png').convert('RGBA')
image.save(root/'app_icon.ico',sizes=[(16,16),(20,20),(24,24),(32,32),(40,40),(48,48),(64,64),(128,128),(256,256)])
