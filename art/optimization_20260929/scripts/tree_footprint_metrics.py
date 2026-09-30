"""Ground-shadow footprint metrics from the top-down renders (source vs shadow proxy).

Shadow mask = pixels darker than the midpoint between the lit-ground and the
fully-shadowed luminance (estimated from the source image's 99th / 1st percentiles).
Reports shadowed-area ratio, IoU and the fraction of disagreeing pixels, at full
resolution (3.3 cm/px) and 4x4 box-filtered (13 cm/px, roughly a far-cascade texel).
"""
import json
import sys

import numpy as np
from PIL import Image

ROOT = "/home/teknetik/code/ao2/art/optimization_20260929"
out = {}
for view in ("foot55", "foot30"):
    s = np.asarray(Image.open(f"{ROOT}/cache/renders/tree/tree_{view}_source.png").convert("L"), np.float32)
    p = np.asarray(Image.open(f"{ROOT}/cache/renders/tree/tree_{view}_proxy.png").convert("L"), np.float32)
    lit, dark = np.percentile(s, 99), np.percentile(s, 1)
    thr = (lit + dark) / 2
    rec = {"litLuma": float(lit), "shadowLuma": float(dark), "threshold": float(thr)}
    for label, f in (("fullRes", 1), ("box4", 4)):
        a, b = s, p
        if f > 1:
            h, w = (a.shape[0] // f) * f, (a.shape[1] // f) * f
            a = a[:h, :w].reshape(h // f, f, w // f, f).mean((1, 3))
            b = b[:h, :w].reshape(h // f, f, w // f, f).mean((1, 3))
        ma, mb = a < thr, b < thr
        rec[label] = {"sourceShadowPx": int(ma.sum()), "proxyShadowPx": int(mb.sum()),
                      "areaRatio": round(float(mb.sum() / max(ma.sum(), 1)), 4),
                      "iou": round(float((ma & mb).sum() / max((ma | mb).sum(), 1)), 4),
                      "meanAbsLumaDiff": round(float(np.abs(a - b).mean()), 3)}
    out[view] = rec
json.dump(out, open(f"{ROOT}/review/tree-footprint-metrics.json", "w"), indent=1)
print(json.dumps(out, indent=1))
