#!/usr/bin/env python3
"""Meshy Text-to-Image / Image-to-Image for the salvage-cache concept views (30 Sep 2026).

The OpenAI account had no remaining credit (HTTP 429 credit_balance_exhausted), so concepts go through Meshy's
image endpoints (same gpt-image-2 family, billed as routine Meshy generation, pre-approved in AGENTS.md section 5).

Usage:
  meshy_image.py NAME "prompt" [--model gpt-image-2] [--aspect 3:2] [--multi-view] [--ref concepts/x.png ...]
                                [--ref-task TASK_ID] [--no-bg]
Every option, task id, status and reported credit use is appended to meshy/image-tasks.json; images are saved
to concepts/NAME[_i].png. The API key is read from the project .env and never printed or written.
"""
import argparse, base64, json, mimetypes, sys, time, urllib.request, urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "unity/tools"))
import create_meshy_prop as meshy  # reuse the project's Meshy client helpers (api_json, data_uri)

env = dict(l.split("=", 1) for l in (ROOT / ".env").read_text().splitlines() if "=" in l and not l.startswith("#"))
KEY = env["MESHY_API_KEY"].strip()

ap = argparse.ArgumentParser()
ap.add_argument("name"); ap.add_argument("prompt")
ap.add_argument("--model", default="gpt-image-2"); ap.add_argument("--aspect", default=None)
ap.add_argument("--multi-view", action="store_true"); ap.add_argument("--ref", action="append", default=[])
ap.add_argument("--ref-task", default=None); ap.add_argument("--no-bg", action="store_true")
a = ap.parse_args()

payload = {"ai_model": a.model, "prompt": a.prompt}
if a.multi_view: payload["generate_multi_view"] = True
elif a.aspect: payload["aspect_ratio"] = a.aspect
if a.no_bg: payload["remove_background"] = True
if a.ref or a.ref_task:
    endpoint = "/image-to-image"
    if a.ref_task: payload["input_task_id"] = a.ref_task
    else: payload["reference_image_urls"] = [meshy.data_uri(HERE / r) for r in a.ref]
else:
    endpoint = "/text-to-image"

rec_path = HERE / "meshy" / "image-tasks.json"
records = json.loads(rec_path.read_text()) if rec_path.exists() else []
entry = {"name": a.name, "endpoint": endpoint, "options": {k: v for k, v in payload.items() if k != "reference_image_urls"},
         "refs": a.ref, "submitted": time.strftime("%Y-%m-%dT%H:%M:%S")}
tid = meshy.api_json("POST", endpoint, KEY, payload)["result"]
entry["task_id"] = tid
print("task", tid, flush=True)
while True:
    t = meshy.api_json("GET", f"{endpoint}/{tid}", KEY)
    if t["status"] == "SUCCEEDED": break
    if t["status"] in ("FAILED", "CANCELED", "EXPIRED"):
        entry.update(status=t["status"], error=t.get("task_error"))
        records.append(entry); rec_path.write_text(json.dumps(records, indent=1)); sys.exit(f"failed: {t.get('task_error')}")
    time.sleep(4)
entry.update(status="SUCCEEDED", consumed_credits=t.get("consumed_credits"), finished=time.strftime("%Y-%m-%dT%H:%M:%S"))
files = []
for i, url in enumerate(t.get("image_urls") or []):
    fn = f"{a.name}.png" if len(t["image_urls"]) == 1 else f"{a.name}_{i}.png"
    (HERE / "concepts" / fn).write_bytes(urllib.request.urlopen(url, timeout=300).read())
    files.append(fn)
entry["files"] = files
records.append(entry); rec_path.write_text(json.dumps(records, indent=1))
print("saved", files, "credits", t.get("consumed_credits"))
