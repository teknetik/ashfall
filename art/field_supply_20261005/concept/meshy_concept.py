#!/usr/bin/env python3
"""Tamsin's concept turnaround through Meshy Text to Image (gpt-image-2, 3:2), 5 Oct 2026. Codex image generation was
unavailable (expired ChatGPT login). Pre-approved Meshy use (AGENTS.md section 5). Two variants; records in
concept-tasks.json (no secrets). Usage: meshy_concept.py NAME PROMPT_FILE [n]"""
import json, sys, time, urllib.request
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "unity/tools")); import create_meshy_prop as meshy
env = dict(l.split("=", 1) for l in (ROOT / ".env").read_text().splitlines() if "=" in l and not l.startswith("#"))
KEY = env["MESHY_API_KEY"].strip()
name, pfile = sys.argv[1], sys.argv[2]; n = int(sys.argv[3]) if len(sys.argv) > 3 else 2
prompt = (HERE / pfile).read_text().strip()
rec_path = HERE / "concept-tasks.json"; recs = json.loads(rec_path.read_text()) if rec_path.exists() else []
tids = []
for i in range(n):
    payload = {"ai_model": "gpt-image-2", "prompt": prompt, "aspect_ratio": "3:2"}
    tid = meshy.api_json("POST", "/text-to-image", KEY, payload)["result"]; tids.append(tid)
    recs.append({"name": f"{name}_sheet_v{i+1}", "task_id": tid, "options": {"ai_model": "gpt-image-2", "aspect_ratio": "3:2"}, "prompt_file": pfile, "submitted": time.strftime("%Y-%m-%dT%H:%M:%S")})
rec_path.write_text(json.dumps(recs, indent=1))
for i, tid in enumerate(tids):
    while True:
        t = meshy.api_json("GET", f"/text-to-image/{tid}", KEY)
        if t["status"] == "SUCCEEDED": break
        if t["status"] in ("FAILED", "CANCELED", "EXPIRED"): print("FAILED", tid, t.get("task_error")); break
        time.sleep(6)
    if t["status"] == "SUCCEEDED":
        (HERE / f"{name}_sheet_v{i+1}.png").write_bytes(urllib.request.urlopen(t["image_urls"][0], timeout=300).read())
        for r in recs:
            if r["task_id"] == tid: r.update(status="SUCCEEDED", consumed_credits=t.get("consumed_credits"))
        print("saved", f"{name}_sheet_v{i+1}.png", t.get("consumed_credits"))
rec_path.write_text(json.dumps(recs, indent=1))
