#!/usr/bin/env python3
"""Field Supply display props through Meshy Image to 3D (5 Oct 2026), from each item's own icon art so the shop stock
matches the inventory icons: the five packs (the Field Backpack from refs/ui_20260908/items/pack-original.png), the
medkit and trauma kit, and the two nano recharges. Resumable: re-run to poll and download (nothing is re-submitted).
Pre-approved Meshy use (AGENTS.md section 5). Key from MESHY_API_KEY or the project .env; never written to records.
Records: props/<name>/record.json; output props/<name>/model.glb + thumb.png.
Usage: props_meshy.py [name ...]"""
import base64, json, os, sys, time, urllib.request, urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ICONS = ROOT / "art/field_supply_20261005/icons"
API = "https://api.meshy.ai/openapi/v1"
# name: (source image, target triangles, real height in metres for the record; Unity scales by measured bounds)
PROPS = {
    "pack_field":   (ROOT / "refs/ui_20260908/items/pack-original.png", 16000, 0.52),
    "pack_rucksack": (ICONS / "rucksack.png", 16000, 0.62),
    "pack_frame":   (ICONS / "frame-pack.png", 20000, 0.78),
    "pack_carrier": (ICONS / "load-carrier.png", 20000, 0.70),
    "pack_rig":     (ICONS / "cargo-rig.png", 20000, 0.62),
    "medkit":       (ROOT / "refs/ui_20260908/items/medkit-original.png", 6000, 0.20),
    "trauma_kit":   (ICONS / "trauma-kit.png", 10000, 0.22),
    "nano_cell":    (ICONS / "nano-cell.png", 5000, 0.16),
    "nano_surge":   (ICONS / "nano-surge.png", 8000, 0.18),
}


def env_key():
    k = os.environ.get("MESHY_API_KEY")
    if k:
        return k
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith("MESHY_API_KEY="):
            return line.split("=", 1)[1].strip().strip("\"'")
    sys.exit("MESHY_API_KEY missing")


KEY = env_key()


def call(method, url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None, method=method,
                                 headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    for attempt in range(8):
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            text = e.read().decode()[:600]
            if e.code == 429 or e.code >= 500:
                time.sleep(15 * (attempt + 1)); continue
            raise RuntimeError(f"{method} {url.split('/v1/')[-1]} -> {e.code} {text}")
        except (urllib.error.URLError, TimeoutError):
            time.sleep(15 * (attempt + 1))
    raise RuntimeError("failed after retries")


def fetch(url, path):
    if not path.exists():
        path.write_bytes(urllib.request.urlopen(url, timeout=600).read())


names = sys.argv[1:] or list(PROPS)
recs = {}
for n in names:
    src, tris, h = PROPS[n]
    d = HERE / "props" / n
    d.mkdir(parents=True, exist_ok=True)
    rp = d / "record.json"
    rec = json.loads(rp.read_text()) if rp.exists() else {"name": n, "source": str(src.relative_to(ROOT)), "height_m": h}
    if "task" not in rec:
        opts = {"ai_model": "latest", "should_texture": True, "enable_pbr": True, "texture_resolution": "2k", "should_remesh": True,
                "topology": "triangle", "target_polycount": tris, "target_formats": ["glb"], "origin_at": "bottom", "symmetry_mode": "auto"}
        uri = "data:image/png;base64," + base64.b64encode(src.read_bytes()).decode()
        rec["options"] = opts
        rec["task"] = call("POST", f"{API}/image-to-3d", dict(opts, image_url=uri))["result"]
        rec["submitted"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        rp.write_text(json.dumps(rec, indent=2) + "\n")
        print("submitted", n, rec["task"], flush=True)
    recs[n] = (rec, rp, d)

pending = dict(recs)
while pending:
    for n, (rec, rp, d) in list(pending.items()):
        t = call("GET", f"{API}/image-to-3d/{rec['task']}")
        if t["status"] == "SUCCEEDED":
            fetch(t["model_urls"]["glb"], d / "model.glb")
            if t.get("thumbnail_url"):
                fetch(t["thumbnail_url"], d / "thumb.png")
            rec.update(status="SUCCEEDED", consumed_credits=t.get("consumed_credits"), finished=time.strftime("%Y-%m-%dT%H:%M:%S"))
            rp.write_text(json.dumps(rec, indent=2) + "\n")
            print("done", n, "credits", t.get("consumed_credits"), flush=True)
            del pending[n]
        elif t["status"] in ("FAILED", "CANCELED", "EXPIRED"):
            rec.update(status=t["status"], error=t.get("task_error"))
            rp.write_text(json.dumps(rec, indent=2) + "\n")
            print("FAILED", n, t.get("task_error"), flush=True)
            del pending[n]
    if pending:
        time.sleep(20)
print("all done")
