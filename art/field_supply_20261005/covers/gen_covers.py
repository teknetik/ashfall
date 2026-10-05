#!/usr/bin/env python3
"""Cover art for Field Supply's digital magazines (5 Oct 2026): OpenAI Images (gpt-image-2, 1024x1536, high), one per
magazine, illustration only (the mastheads are set in the project's own font by make_atlas.sh, so the lettering is
authored, not generated). Key from the project .env (never written). Records: covers.json."""
import base64, json, sys, urllib.request
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[2]
env = dict(l.split("=", 1) for l in (ROOT / ".env").read_text().splitlines() if "=" in l and not l.startswith("#"))
KEY = env["OPENAI_API_KEY"].strip()
STYLE = ("Cover illustration for a printed-style colony trade magazine on the desert world Tir: painterly realistic, warm dusty"
         " light, worn desert colony materials, restrained cyan technology accents. Leave the top fifth of the image as a calm"
         " plain area of the cover's base colour (a masthead will be added later) and a calm strip along the bottom."
         " Absolutely no text, no letters, no numbers, no logos, no watermark anywhere. Portrait 2:3.")
COVERS = {
 "packcraft": "A sand-coloured canvas rucksack with two side pouches and a padded hip belt laid out on a workbench beside spools of webbing, a stitching awl and brass buckles; base colour warm sand and terracotta.",
 "freight": "A Karaveen caravan porter's external frame pack standing against the dunes at dusk with a long caravan line behind, faint blueprint load-chart lines overlaid; base colour dune orange with deep indigo.",
 "nanoweave": "A sleek charcoal nanoweave cargo backpack with a slim servo spine and thin cyan glow lines, floating over a faint hexagonal nanite weave pattern; base colour dark teal.",
 "armourer": "A worn Warden plate carrier vest opened to show a quilted impact liner and a ceramic chest plate, with rivets and a liner pattern on a steel workbench; base colour steel grey with a red diagonal band.",
}
rec_path = HERE / "covers.json"; rec = json.loads(rec_path.read_text()) if rec_path.exists() else {}
for name in sys.argv[1:] or COVERS:
    out = HERE / f"{name}_art.png"
    if out.exists(): continue
    prompt = f"{COVERS[name]} {STYLE}"
    body = json.dumps({"model": "gpt-image-2", "prompt": prompt, "size": "1024x1536", "quality": "high", "n": 1}).encode()
    req = urllib.request.Request("https://api.openai.com/v1/images/generations", data=body, method="POST",
                                 headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=600).read())
    except urllib.error.HTTPError as e:
        msg = e.read().decode()[:400]
        if "gpt-image-2" in msg or e.code == 400:
            body = json.dumps({"model": "gpt-image-1", "prompt": prompt, "size": "1024x1536", "quality": "high", "n": 1}).encode()
            req = urllib.request.Request("https://api.openai.com/v1/images/generations", data=body, method="POST",
                                         headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
            d = json.loads(urllib.request.urlopen(req, timeout=600).read()); d["_model"] = "gpt-image-1"
        else:
            raise SystemExit(f"{e.code} {msg}")
    out.write_bytes(base64.b64decode(d["data"][0]["b64_json"]))
    rec[name] = {"model": d.get("_model", "gpt-image-2"), "size": "1024x1536", "quality": "high", "prompt": prompt, "usage": d.get("usage")}
    rec_path.write_text(json.dumps(rec, indent=1)); print("saved", out.name, flush=True)
