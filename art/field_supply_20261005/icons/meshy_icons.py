#!/usr/bin/env python3
"""Field Supply item icons through Meshy Text to Image (gpt-image-2, 1:1, remove_background), 5 Oct 2026.

Codex image generation was unavailable (its ChatGPT login had expired: "refresh token was already used"), so the
icons use the Meshy route of the 30 Sep 2026 salvage icons (refs/ui_20260930/items/manifest.json): routine Meshy
generation, pre-approved in AGENTS.md section 5. Prompts: prompts.json (same item text and style as gen_icons.sh).
Every task id, option and credit use goes to provenance.json; images are saved as <icon>.png (1024 px) and then
fit_icons.sh fits them to UI/Art. The API key is read from the project .env and never printed or written.

Usage: meshy_icons.py [icon ...]   (default: every icon without a PNG yet)
"""
import json, sys, time, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "unity/tools"))
import create_meshy_prop as meshy  # the project's Meshy client (api_json)

env = dict(l.split("=", 1) for l in (ROOT / ".env").read_text().splitlines() if "=" in l and not l.startswith("#"))
KEY = env["MESHY_API_KEY"].strip()
P = json.loads((HERE / "prompts.json").read_text())
FRAME = (" Composition: exactly one complete centred item, square image with generous transparent padding, the item fills about"
         " 75 percent of the square, readable silhouette at 56-128 pixels. Background: genuinely transparent, no backdrop, no floor,"
         " no shadow outside the object. No UI border, no box around the item, no lettering, no numbers, no logos, no watermark.")
names = sys.argv[1:] or [k for k in P["items"] if not (HERE / f"{k}.png").exists()]
prov_path = HERE / "provenance.json"
prov = json.loads(prov_path.read_text()) if prov_path.exists() else {"tool": "Meshy text-to-image (gpt-image-2, aspect 1:1, remove_background)", "icons": {}}

tasks = {}
for n in names:
    prompt = f"{P['style']}.{FRAME}\nSubject: {P['items'][n]}"
    payload = {"ai_model": "gpt-image-2", "prompt": prompt, "aspect_ratio": "1:1", "remove_background": True}
    tid = meshy.api_json("POST", "/text-to-image", KEY, payload)["result"]
    tasks[n] = tid
    prov["icons"][n] = {"task_id": tid, "options": {k: v for k, v in payload.items() if k != "prompt"}, "prompt": prompt,
                        "submitted": time.strftime("%Y-%m-%dT%H:%M:%S")}
    print("submitted", n, tid, flush=True)
prov_path.write_text(json.dumps(prov, indent=1))

pending = dict(tasks)
while pending:
    time.sleep(6)
    for n, tid in list(pending.items()):
        t = meshy.api_json("GET", f"/text-to-image/{tid}", KEY)
        if t["status"] == "SUCCEEDED":
            urls = t.get("image_urls") or []
            (HERE / f"{n}.png").write_bytes(urllib.request.urlopen(urls[0], timeout=300).read())
            prov["icons"][n].update(status="SUCCEEDED", consumed_credits=t.get("consumed_credits"), finished=time.strftime("%Y-%m-%dT%H:%M:%S"),
                                    raw=f"art/field_supply_20261005/icons/{n}.png", runtime=f"unity/AthenHill/Assets/AthenHill/UI/Art/{n}.png")
            print("saved", n, "credits", t.get("consumed_credits"), flush=True)
            del pending[n]
        elif t["status"] in ("FAILED", "CANCELED", "EXPIRED"):
            prov["icons"][n].update(status=t["status"], error=t.get("task_error"))
            print("FAILED", n, t.get("task_error"), flush=True)
            del pending[n]
    prov_path.write_text(json.dumps(prov, indent=1))
print("done")
