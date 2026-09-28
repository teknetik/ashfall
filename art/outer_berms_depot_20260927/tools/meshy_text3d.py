#!/usr/bin/env python3
"""Meshy text-to-3D (preview -> PBR refine -> GLB) for the Outer Berms depot pass (27 Sep 2026).

Usage: python3 meshy_text3d.py NAME "prompt" "texture prompt" [polycount] [texture_res]
Key: MESHY_API_KEY from the project-root .env (never printed or written). Records every request option,
task id, status and reported credits in meshy/outer-berms-depot-20260927/NAME/task.json; downloads model.glb,
the texture maps and the thumbnail beside it. Re-running resumes from the recorded task ids.
"""
import json, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
env = dict(l.split("=", 1) for l in (ROOT / ".env").read_text().splitlines() if "=" in l)
KEY = env["MESHY_API_KEY"].strip()
API = "https://api.meshy.ai/openapi/v2/text-to-3d"


def call(method, url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None, method=method,
                                 headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode()[:500]}")


def wait(tid, label):
    while True:
        t = call("GET", f"{API}/{tid}")
        print(label, t["status"], t.get("progress"), flush=True)
        if t["status"] == "SUCCEEDED":
            return t
        if t["status"] in ("FAILED", "CANCELED", "EXPIRED"):
            sys.exit(f"{label} {t['status']}: {t.get('task_error')}")
        time.sleep(10)


def fetch(url, dest):
    dest.write_bytes(urllib.request.urlopen(url, timeout=300).read())


def main():
    name, prompt, tex_prompt = sys.argv[1], sys.argv[2], sys.argv[3]
    poly = int(sys.argv[4]) if len(sys.argv) > 4 else 40000
    res = sys.argv[5] if len(sys.argv) > 5 else "4k"
    out = ROOT / "meshy/outer-berms-depot-20260927" / name
    out.mkdir(parents=True, exist_ok=True)
    recp = out / "task.json"
    rec = json.loads(recp.read_text()) if recp.exists() else {}
    save = lambda: recp.write_text(json.dumps(rec, indent=1))
    if "preview_task" not in rec:
        opts = dict(mode="preview", prompt=prompt, ai_model="latest", topology="triangle", target_polycount=poly,
                    should_remesh=True, art_style="realistic")
        rec.update(asset=name, preview_options=opts, started=time.strftime("%Y-%m-%dT%H:%M:%S"))
        rec["preview_task"] = call("POST", API, opts)["result"]; save()
    p = wait(rec["preview_task"], name + " preview")
    rec["preview_credits"] = p.get("consumed_credits"); rec["preview_thumbnail"] = p.get("thumbnail_url"); save()
    if "refine_task" not in rec:
        opts = dict(mode="refine", preview_task_id=rec["preview_task"], enable_pbr=True, texture_resolution=res,
                    remove_lighting=True, texture_prompt=tex_prompt)
        rec["refine_options"] = opts
        rec["refine_task"] = call("POST", API, opts)["result"]; save()
    r = wait(rec["refine_task"], name + " refine")
    rec["refine_credits"] = r.get("consumed_credits"); rec["status"] = "SUCCEEDED"
    fetch(r["model_urls"]["glb"], out / "model.glb")
    if r.get("thumbnail_url"):
        fetch(r["thumbnail_url"], out / "thumbnail.png")
    tex = (r.get("texture_urls") or [{}])[0]
    for k, v in tex.items():
        if isinstance(v, str) and v.startswith("http"):
            fetch(v, out / f"texture_{k}.png")
    rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S"); rec["texture_maps"] = sorted(tex.keys()); save()
    print("DONE", out)


if __name__ == "__main__":
    main()
