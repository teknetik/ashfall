#!/usr/bin/env python3
"""Meshy Multi-Image to 3D for the salvage cache (30 Sep 2026).

Reuses unity/tools/create_meshy_prop.py (api_json / wait_for_task / download / data_uri) with salvage-cache options
and file names. Usage: meshy_multi3d.py RUN_NAME img1 [img2 ...] [--poly 60000] [--tex 4k] [--geo 2k]
Writes meshy/RUN_NAME/{task.json, model.glb, pre_remeshed.glb, texture_*.png, thumbnail*.png}. Key from .env only.
"""
import argparse, json, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "unity/tools"))
import create_meshy_prop as meshy

env = dict(l.split("=", 1) for l in (ROOT / ".env").read_text().splitlines() if "=" in l and not l.startswith("#"))
KEY = env["MESHY_API_KEY"].strip()

ap = argparse.ArgumentParser()
ap.add_argument("run"); ap.add_argument("images", nargs="+")
ap.add_argument("--poly", type=int, default=60000); ap.add_argument("--tex", default="4k"); ap.add_argument("--geo", default="2k")
ap.add_argument("--texture-prompt", default=None); ap.add_argument("--model", default="latest")
ap.add_argument("--resume", default=None, help="existing task id to wait for / download")
a = ap.parse_args()

out = HERE / "meshy" / a.run
out.mkdir(parents=True, exist_ok=True)
rec_path = out / "task.json"
rec = json.loads(rec_path.read_text()) if rec_path.exists() else {}
save = lambda: rec_path.write_text(json.dumps(rec, indent=1))

payload = {
    "ai_model": a.model, "geometry_resolution": a.geo, "should_texture": True, "enable_pbr": True,
    "texture_resolution": a.tex, "should_remesh": True, "topology": "triangle", "target_polycount": a.poly,
    "save_pre_remeshed_model": True, "remove_lighting": True, "image_enhancement": True,
    "target_formats": ["glb"], "auto_size": False, "origin_at": "bottom", "multi_view_thumbnails": True,
}
if a.texture_prompt: payload["texture_prompt"] = a.texture_prompt
if a.resume:
    tid = a.resume
else:
    payload_send = dict(payload, image_urls=[meshy.data_uri(HERE / p) for p in a.images])
    tid = meshy.api_json("POST", "/multi-image-to-3d", KEY, payload_send)["result"]
    rec.update(run=a.run, endpoint="/openapi/v1/multi-image-to-3d", images=a.images, options=payload, task_id=tid,
               submitted=time.strftime("%Y-%m-%dT%H:%M:%S")); save()
print("task", tid, flush=True)
t = meshy.wait_for_task(tid, KEY, 3600)
rec.update(status=t["status"], consumed_credits=t.get("consumed_credits"), finished=time.strftime("%Y-%m-%dT%H:%M:%S"),
           returned_models=sorted((t.get("model_urls") or {}).keys())); save()
files = []
def get(url, fn):
    if url and not (out / fn).exists():
        meshy.download(url, out / fn); files.append(fn)
mu = t.get("model_urls") or {}
get(mu.get("glb"), "model.glb"); get(mu.get("pre_remeshed_glb"), "pre_remeshed.glb")
for tex in t.get("texture_urls") or []:
    for k, v in tex.items():
        if isinstance(v, str): get(v, f"texture_{k}.png")
get(t.get("thumbnail_url"), "thumbnail.png")
for k, v in (t.get("thumbnail_urls") or {}).items(): get(v, f"thumbnail_{k}.png")
rec["files"] = sorted(p.name for p in out.iterdir() if p.name != "task.json"); save()
print("done", rec["files"], "credits", t.get("consumed_credits"))
