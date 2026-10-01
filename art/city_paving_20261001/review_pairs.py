"""Before/after pairs from two native lookbook folders: review_pairs.py BEFORE AFTER OUTDIR [cam,cam,...] [hour]
Writes OUTDIR/pair-<cam>-h<hour>.jpg (stacked, labelled, half size) and a 1:1 crop of the lower centre (the ground)."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw
b, a, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
hour = sys.argv[5] if len(sys.argv) > 5 else '13.00'
cams = sys.argv[4].split(',') if len(sys.argv) > 4 and sys.argv[4] else sorted({p.name.rsplit('-h', 1)[0] for p in a.glob('cam_*-h%s.png' % hour)})
for cam in cams:
    fb, fa = b / f'{cam}-h{hour}.png', a / f'{cam}-h{hour}.png'
    if not (fb.exists() and fa.exists()): print('skip', cam); continue
    ib, ia = Image.open(fb).convert('RGB'), Image.open(fa).convert('RGB')
    w, h = ib.size
    s = Image.new('RGB', (w // 2, h + 40), (16, 16, 16)); d = ImageDraw.Draw(s)
    s.paste(ib.resize((w // 2, h // 2)), (0, 20)); s.paste(ia.resize((w // 2, h // 2)), (0, h // 2 + 40))
    d.text((6, 4), f'BEFORE {cam} {hour}', fill=(240, 220, 190)); d.text((6, h // 2 + 24), f'AFTER {cam} {hour}', fill=(240, 220, 190))
    s.save(out / f'pair-{cam}-h{hour}.jpg', quality=88)
    box = (w // 2 - 480, h - 560, w // 2 + 480, h - 200)   # lower centre, above the hotbar
    c = Image.new('RGB', (960, 2 * 360 + 8), (0, 0, 0)); c.paste(ib.crop(box), (0, 0)); c.paste(ia.crop(box), (0, 368))
    c.save(out / f'crop-{cam}-h{hour}.jpg', quality=90)
    print('wrote', cam)
