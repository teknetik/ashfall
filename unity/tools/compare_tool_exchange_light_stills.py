"""Luminance stats of matched stills, whole frame and a crop, between two evidence folders (t_e14abefb).

  python compare_tool_exchange_light_stills.py <dirA> <dirB> <out-dir> [label-a label-b]

Crops (fractions of 1920x1080) approximate the display alcove per view. Writes side-by-side sheets (A left, B right, brightened x1 and x4) and prints mean/p95 luma.
"""
import sys
from pathlib import Path
from PIL import Image, ImageStat

A, B, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
la = sys.argv[4] if len(sys.argv) > 4 else 'before'
lb = sys.argv[5] if len(sys.argv) > 5 else 'after'
OUT.mkdir(parents=True, exist_ok=True)
CROPS = {'fp_front_lane': (.20, .22, .42, .58), 'fp_door_porch': (.20, .10, .80, .95), 'fp_display_close': (.28, .12, .76, .80)}


def luma(im):
    g = im.convert('L'); st = ImageStat.Stat(g); h = g.histogram(); tot = sum(h); acc = 0; p95 = 0
    for i, c in enumerate(h):
        acc += c
        if acc >= .95 * tot: p95 = i; break
    return st.mean[0], p95


for pa in sorted(A.glob('fp_*-h*.png')):
    pb = B / pa.name
    if not pb.exists(): continue
    view = pa.name.split('-h')[0]
    ia, ib = Image.open(pa).convert('RGB'), Image.open(pb).convert('RGB')
    box = tuple(int(v * s) for v, s in zip(CROPS[view], (1920, 1080, 1920, 1080)))
    ca, cb = ia.crop(box), ib.crop(box)
    (ma, pa95), (mb, pb95) = luma(ca), luma(cb)
    print('%-28s crop mean %s %.1f -> %s %.1f | p95 %d -> %d' % (pa.stem, la, ma, lb, mb, pa95, pb95))
    for gain in (1, 4):
        w, h = ca.size
        sheet = Image.new('RGB', (w * 2 + 8, h), (255, 0, 255))
        for k, im in enumerate((ca, cb)):
            im = im.point(lambda v: min(255, int(v * gain))) if gain != 1 else im
            sheet.paste(im, (k * (w + 8), 0))
        sheet.save(OUT / ('%s-x%d.jpg' % (pa.stem, gain)), quality=88)
