"""Crown colour statistics, before vs after, for cam_bc_4b_crown at 13:00 (editor captures): non-sky pixels of the
crown above the roofline (x 740-1200, y 140-580). HSV saturation/value plus Rec.709 luminance of the display-referred
pixels. Run: $O/heavy.sh uv run --with pillow --with numpy python crown_stats.py <before.png> <after.png> <out.json>"""
import sys, json, colorsys
import numpy as np
from PIL import Image
out = {}
for tag, p in [("before", sys.argv[1]), ("after", sys.argv[2])]:
    a = np.asarray(Image.open(p).convert("RGB")).astype(float)[140:580, 740:1200] / 255
    m = a[..., 2] < a[..., 1] - 0.03
    px = a[m]
    hsv = np.array([colorsys.rgb_to_hsv(*c) for c in px[::7]])
    luma = px @ np.array([0.2126, 0.7152, 0.0722])
    out[tag] = dict(pixels=int(m.sum()), meanRGB=px.mean(0).round(3).tolist(), hue_deg=round(float(np.median(hsv[:, 0])) * 360, 1),
                    sat=round(float(hsv[:, 1].mean()), 3), val=round(float(hsv[:, 2].mean()), 3), luma=round(float(luma.mean()), 3),
                    luma_p90=round(float(np.percentile(luma, 90)), 3), hue_std_deg=round(float(hsv[:, 0].std()) * 360, 1))
b, a = out["before"], out["after"]
out["change"] = {k: round(a[k] / b[k] - 1, 3) for k in ("sat", "val", "luma", "luma_p90")}
out["note"] = "cam_bc_4b_crown 13:00 editor capture, crown above the roofline, non-sky pixels"
json.dump(out, open(sys.argv[3], "w"), indent=1)
print(json.dumps(out, indent=1))
