"""Compose labelled side-by-side review JPGs from raw Cycles renders (PIL).

python compose_review.py truck|tree
Each sheet: source | LOD(s) | amplified |source - LOD| difference of the last panel.
Far views are also written as native-pixel crops (no resampling) plus a 2x nearest
zoom so the actual in-game pixel coverage is judged, not a downscaled thumbnail.
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = "/home/teknetik/code/ao2/art/optimization_20260929"
REVIEW = f"{ROOT}/review"
os.makedirs(REVIEW, exist_ok=True)


def font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def label(img, text, sub=None):
    d = ImageDraw.Draw(img)
    f = font(max(18, img.height // 30))
    fs = font(max(14, img.height // 42))
    pad = 10
    box_h = f.size + (fs.size + 6 if sub else 0) + 2 * pad
    d.rectangle([0, 0, img.width, box_h], fill=(0, 0, 0))
    d.text((pad, pad), text, fill=(255, 255, 255), font=f)
    if sub:
        d.text((pad, pad + f.size + 6), sub, fill=(200, 200, 200), font=fs)
    return img


def diff(a, b, gain=4.0):
    x = np.asarray(a.convert("RGB"), np.float32)
    y = np.asarray(b.convert("RGB"), np.float32)
    dd = np.clip(np.abs(x - y).mean(axis=2) * gain, 0, 255).astype(np.uint8)
    heat = np.stack([dd, (dd * 0.6).astype(np.uint8), (255 - dd) // 3], 2)
    return Image.fromarray(heat), float(np.abs(x - y).mean())


def sheet(panels, out_path, max_width=None, quality=90):
    w = sum(p.width for p in panels)
    h = max(p.height for p in panels)
    s = Image.new("RGB", (w, h), (30, 30, 30))
    x = 0
    for p in panels:
        s.paste(p, (x, 0))
        x += p.width
    if max_width and s.width > max_width:
        s = s.resize((max_width, int(s.height * max_width / s.width)), Image.LANCZOS)
    s.save(out_path, quality=quality)
    return out_path


def crop_box(img, frac_w, frac_h, cx=0.5, cy=0.5):
    w, h = img.size
    cw, ch = int(w * frac_w), int(h * frac_h)
    x0 = int(w * cx - cw / 2)
    y0 = int(h * cy - ch / 2)
    return (x0, y0, x0 + cw, y0 + ch)


def compose(kind, spec, tri_counts):
    raw = f"{ROOT}/cache/renders/{kind}"
    written = []
    metrics = {}
    for view, variants, crop in spec:
        imgs = {v: Image.open(f"{raw}/{kind}_{view}_{v}.png").convert("RGB") for v in variants}
        base = imgs[variants[0]]
        panels = []
        for v in variants:
            im = imgs[v]
            if crop:
                im = im.crop(crop_box(im, *crop))
            panels.append(label(im.copy(), f"{v} - {view}", tri_counts.get(v, "")))
        d_img, mad = diff(base, imgs[variants[-1]])
        if crop:
            d_img = d_img.crop(crop_box(d_img, *crop))
        panels.append(label(d_img, f"|{variants[0]} - {variants[-1]}| x4", f"mean abs diff {mad:.2f}/255"))
        metrics[f"{view}:{variants[0]}-vs-{variants[-1]}"] = round(mad, 3)
        name = f"{kind}_{view}_{'_vs_'.join(v.replace('+', '_') for v in variants)}.jpg"
        written.append(sheet(panels, f"{REVIEW}/{name}", max_width=None if crop else 3840))
        if crop:
            zoom = [p.resize((p.width * 2, p.height * 2), Image.NEAREST) for p in panels[:-1]]
            written.append(sheet(zoom, f"{REVIEW}/{name[:-4]}_zoom2x.jpg"))
    return written, metrics


def main():
    kind = sys.argv[1]
    if kind == "truck":
        rep = json.load(open(f"{ROOT}/truck/truck-lod-report.json"))
        tris = {"source": f"{rep['sourceMesh']['triangles']:,} tris",
                "LOD0": f"{rep['LOD0_exact']['triangles']:,} tris (UV-exact)",
                "LOD1": f"{rep['LOD1']['trianglesWritten']:,} tris (baked 2k)",
                "LOD2": f"{rep['LOD2']['trianglesWritten']:,} tris (baked 1k)",
                "LOD0+ShadowNear": f"LOD0 visible (no shadows), {rep['ShadowNear']['triangles']:,}-tri ShadowNear casts",
                "LOD1+ShadowProxy": f"LOD1 visible (no shadows), {rep['ShadowProxy']['triangles']:,}-tri inset proxy casts"}
        spec = [("02m", ["source", "LOD0"], None),
                ("08m", ["source", "LOD0", "LOD1"], None),
                ("16m", ["source", "LOD1"], (0.5, 0.5)),
                ("30m", ["source", "LOD1", "LOD2"], (0.34, 0.34)),
                ("45m", ["source", "LOD2"], (0.25, 0.25)),
                ("shadownear", ["source", "LOD0+ShadowNear"], None),
                ("shadowmid", ["source", "LOD1+ShadowProxy"], (0.5, 0.5))]
    else:
        rep = json.load(open(f"{ROOT}/tree/tree-lod-report.json"))
        tris = {"source": "LOD0 3,748,776 tris (all casting)",
                "LOD1": "LOD1 1,845,603 tris",
                "LOD2": f"LOD2 {rep['LOD2_triangles']['total']:,} tris",
                "proxy": f"LOD0 visible, shadow proxy {rep['ShadowProxy_triangles']['total']:,} tris casts"}
        spec = json.load(open(f"{ROOT}/cache/renders/tree/spec.json"))
        spec = [(s[0], s[1], tuple(s[2]) if s[2] else None) for s in spec]
    written, metrics = compose(kind, spec, tris)
    with open(f"{REVIEW}/{kind}-review-metrics.json", "w") as fh:
        json.dump({"meanAbsDiff": metrics, "files": [os.path.basename(p) for p in written]}, fh, indent=1)
    print("\n".join(written))


main()
