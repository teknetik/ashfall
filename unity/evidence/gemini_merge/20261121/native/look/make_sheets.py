"""Side-by-side before (batch-sh-real12) / after (batch-sh-gemini1) sheets from the two lookbook runs (21 Nov 2026)."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
N = Path(__file__).resolve().parent.parent
OUT = N / 'look'
font = ImageFont.load_default(size=28) if hasattr(ImageFont, 'load_default') else None
pairs = []
for part in 'ab':
    for img in sorted((N / 'gemini1' / ('look-' + part)).glob('cam_*-h*.png')):
        b = N / 'real12' / ('look-' + part) / img.name
        if b.exists(): pairs.append((img.stem, b, img))
for name, b, a in pairs:
    W, H = 1280, 720
    s = Image.new('RGB', (W * 2 + 10, H + 50), (20, 20, 20)); d = ImageDraw.Draw(s)
    s.paste(Image.open(b).convert('RGB').resize((W, H)), (0, 50)); s.paste(Image.open(a).convert('RGB').resize((W, H)), (W + 10, 50))
    d.text((10, 10), 'BEFORE real12  ' + name, fill=(255, 255, 255), font=font); d.text((W + 20, 10), 'AFTER gemini1  ' + name, fill=(255, 255, 255), font=font)
    s.save(OUT / (name + '.jpg'), quality=90)
    # full-res crop pairs for faces
print(len(pairs), 'sheets')
