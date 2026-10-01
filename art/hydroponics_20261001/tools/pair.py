"""Side-by-side comparison sheet: pair.py <dirA> <dirB> <out.jpg> [name,name,...] (PNG names without extension)."""
import sys, glob, os
from PIL import Image, ImageDraw
a, b, out = sys.argv[1], sys.argv[2], sys.argv[3]
names = sys.argv[4].split(',') if len(sys.argv) > 4 else sorted(os.path.basename(f)[:-4] for f in glob.glob(b + '/*.png'))
W, H = 800, 450
sheet = Image.new('RGB', (W * 2, (H + 18) * len(names)), 'black')
d = ImageDraw.Draw(sheet)
for i, n in enumerate(names):
    for j, src in enumerate((a, b)):
        f = f'{src}/{n}.png'
        if os.path.exists(f):
            sheet.paste(Image.open(f).convert('RGB').resize((W, H)), (j * W, i * (H + 18) + 18))
    d.text((4, i * (H + 18) + 3), n + f'   (left: {os.path.basename(a)}, right: {os.path.basename(b)})', fill='white')
sheet.save(out, quality=85)
