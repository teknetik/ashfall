"""Before/after parity of the texture memory pass's isolated editor captures.
For each view in parity/before and parity/after: PSNR over the whole frame and over the asset (non-background) pixels,
the 99.9th percentile pixel error, a side-by-side pair with a x8 difference strip, and a 2x crop of the region with the
largest local difference. Usage: python compare_parity.py <evidence dir>"""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image

ev = Path(sys.argv[1]); b_dir, a_dir, out = ev / 'parity/before', ev / 'parity/after', ev / 'parity/compare'
out.mkdir(parents=True, exist_ok=True)
bg = np.array([0.55, 0.62, 0.7]) * 255
rows = {}
for bf in sorted(b_dir.glob('*.png')):
    af = a_dir / bf.name
    if not af.exists():
        continue
    b = np.asarray(Image.open(bf).convert('RGB')).astype(np.float64)
    a = np.asarray(Image.open(af).convert('RGB')).astype(np.float64)
    d = np.abs(a - b)
    mask = np.abs(b - bg).max(axis=2) > 6           # asset pixels (background is a flat colour)
    def psnr(x):
        m = (x ** 2).mean()
        return float('inf') if m == 0 else round(10 * np.log10(255 ** 2 / m), 2)
    dm = d.max(axis=2)
    # 64 px block with the largest mean difference -> crop for a close look
    h, w = dm.shape; bs = 64
    blk = dm[:h // bs * bs, :w // bs * bs].reshape(h // bs, bs, w // bs, bs).mean(axis=(1, 3))
    by, bx = np.unravel_index(np.argmax(blk), blk.shape)
    cy, cx = int(by * bs + bs // 2), int(bx * bs + bs // 2)
    y0, x0 = max(0, min(h - 240, cy - 120)), max(0, min(w - 320, cx - 160))
    rows[bf.stem] = dict(psnr_frame=psnr(d), psnr_asset=psnr(d[mask]) if mask.any() else None,
                         asset_fraction=round(float(mask.mean()), 3), p999_err=float(np.percentile(dm[mask], 99.9)) if mask.any() else 0,
                         max_err=float(dm.max()), mean_err_asset=round(float(dm[mask].mean()), 3) if mask.any() else 0,
                         worst_block=[int(cx), int(cy)])
    half = lambda arr: Image.fromarray(arr.astype(np.uint8)).resize((960, 540), Image.LANCZOS)
    diff = np.clip(d * 8, 0, 255)
    sheet = Image.new('RGB', (2880, 540 + 480))
    sheet.paste(half(b), (0, 0)); sheet.paste(half(a), (960, 0)); sheet.paste(half(diff), (1920, 0))
    crop = lambda arr: Image.fromarray(arr[y0:y0 + 240, x0:x0 + 320].astype(np.uint8)).resize((960, 480), Image.NEAREST)
    sheet.paste(crop(b), (0, 540)); sheet.paste(crop(a), (960, 540)); sheet.paste(crop(diff), (1920, 540))
    sheet.save(out / f'pair-{bf.stem}.jpg', quality=88)
json.dump(rows, open(out / 'parity.json', 'w'), indent=1)
for k, v in rows.items():
    print(f"{k:20} frame {v['psnr_frame']:>6} dB  asset {v['psnr_asset']:>6} dB  p99.9 err {v['p999_err']:5.1f}  max {v['max_err']:5.1f}")
