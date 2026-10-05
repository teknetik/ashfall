#!/usr/bin/env python3
"""Copy selected Ashfall art into assets/originals (byte-identical, sources untouched)
and produce optimised web derivatives in assets/web (AVIF, WebP, JPEG at 2 widths).
Writes assets/manifest.json. Re-runnable; requires ImageMagick 7 (`magick`)."""
import hashlib, json, os, shutil, subprocess, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../promo-site/assets
GEN = os.path.join(ROOT, "generation")
ORIG = os.path.join(ROOT, "originals")
WEB = os.path.join(ROOT, "web")
SPEC = json.load(open(os.path.join(ROOT, "tools", "selection.json")))

def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()

def dims(p):
    out = subprocess.check_output(["magick", "identify", "-format", "%w %h %m", p + "[0]"], text=True)
    w, h, fmt = out.split()
    return int(w), int(h), fmt

os.makedirs(ORIG, exist_ok=True); os.makedirs(WEB, exist_ok=True)
items = []
for a in SPEC["assets"]:
    src = a["source_path"] if os.path.isabs(a["source_path"]) else os.path.join(GEN, a["source_path"])
    ext = os.path.splitext(src)[1].lower()
    orig = os.path.join(ORIG, a["id"] + ext)
    if not os.path.exists(orig) or sha(orig) != sha(src):
        shutil.copy2(src, orig)
    assert sha(orig) == sha(src), a["id"]
    w, h, fmt = dims(orig)
    variants = []
    for width in sorted({min(x, w) for x in a.get("widths", [1536, 768])}, reverse=True):
        for kind, args in (("avif", ["-quality", "55"]), ("webp", ["-quality", "80"]), ("jpg", ["-quality", "82", "-interlace", "Plane"])):
            out = os.path.join(WEB, f"{a['id']}-{width}.{kind}")
            if not os.path.exists(out):
                subprocess.check_call(["magick", orig + "[0]", "-strip", "-colorspace", "sRGB",
                                       "-resize", f"{width}x", *args, out])
            vw, vh, vfmt = dims(out)
            variants.append({"file": f"web/{os.path.basename(out)}", "format": vfmt.lower(), "width": vw,
                             "height": vh, "bytes": os.path.getsize(out), "sha256": sha(out)})
    item = dict(a)
    item.update({"original_file": f"originals/{os.path.basename(orig)}", "original_format": fmt.lower(),
                 "original_width": w, "original_height": h, "original_bytes": os.path.getsize(orig),
                 "original_sha256": sha(orig), "aspect_ratio": f"{w}:{h}", "web_variants": variants})
    items.append(item)

manifest = {"generated_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
            "notes": SPEC["notes"], "assets": items}
json.dump(manifest, open(os.path.join(ROOT, "manifest.json"), "w"), indent=2, ensure_ascii=False)
print(len(items), "assets;", sum(len(i["web_variants"]) for i in items), "web files")
