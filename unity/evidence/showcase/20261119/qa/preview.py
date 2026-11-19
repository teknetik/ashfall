"""Half-size JPEG previews of captures for review: preview.py OUT.jpg a.png [b.png ...] (several -> 2-column sheet)."""
import sys
from PIL import Image
out, files = sys.argv[1], sys.argv[2:]
ims = [Image.open(f).convert('RGB').resize((960, 540)) for f in files]
cols = 1 if len(ims) == 1 else 2
rows = (len(ims) + cols - 1) // cols
sheet = Image.new('RGB', (960 * cols, 540 * rows))
for i, im in enumerate(ims):
    sheet.paste(im, ((i % cols) * 960, (i // cols) * 540))
sheet.save(out, quality=82)
