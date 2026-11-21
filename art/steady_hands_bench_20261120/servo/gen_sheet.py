#!/usr/bin/env python3
"""Reference sheets for the servo and materials families (OpenAI gpt-image-2; key read from the repository .env and
never printed). Copied and adapted from art/salvage_cache_20260930/scripts/gen_concept.py after reading it.

Usage: gen_sheet.py OUT.png PROMPT.txt [--size 1536x1024] [--quality high] [--ref img.png ...]
With --ref the request goes to /v1/images/edits so later sheets show the same object as an earlier one.
The prompt is kept beside the image as OUT.prompt.txt; model, size, refs and reported usage go to usage.json there.
"""
import argparse, base64, json, mimetypes, sys, time, urllib.request, urllib.error, uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
env = dict(l.split("=", 1) for l in (ROOT / ".env").read_text().splitlines() if "=" in l and not l.startswith("#"))
KEY = env["OPENAI_API_KEY"].strip()

ap = argparse.ArgumentParser()
ap.add_argument("out"); ap.add_argument("prompt_file")
ap.add_argument("--size", default="1536x1024"); ap.add_argument("--model", default="gpt-image-2")
ap.add_argument("--ref", action="append", default=[]); ap.add_argument("--quality", default="high")
a = ap.parse_args()
out = Path(a.out).resolve()
prompt = Path(a.prompt_file).read_text().strip()

if a.ref:
    boundary = uuid.uuid4().hex
    parts = []
    for k, v in (("model", a.model), ("prompt", prompt), ("size", a.size), ("quality", a.quality), ("n", "1")):
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
    for r in a.ref:
        p = Path(r).resolve()
        mime = mimetypes.guess_type(p.name)[0] or "image/png"
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"image[]\"; filename=\"{p.name}\"\r\n"
                     f"Content-Type: {mime}\r\n\r\n".encode() + p.read_bytes() + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    req = urllib.request.Request("https://api.openai.com/v1/images/edits", data=b"".join(parts), method="POST",
                                 headers={"Authorization": f"Bearer {KEY}",
                                          "Content-Type": f"multipart/form-data; boundary={boundary}"})
else:
    body = json.dumps({"model": a.model, "prompt": prompt, "size": a.size, "quality": a.quality, "n": 1}).encode()
    req = urllib.request.Request("https://api.openai.com/v1/images/generations", data=body, method="POST",
                                 headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
t0 = time.time()
try:
    with urllib.request.urlopen(req, timeout=900) as r:
        d = json.loads(r.read())
except urllib.error.HTTPError as e:
    print("HTTP", e.code, e.read().decode()[:800]); sys.exit(1)
out.parent.mkdir(parents=True, exist_ok=True)
out.write_bytes(base64.b64decode(d["data"][0]["b64_json"]))
out.with_suffix(".prompt.txt").write_text(prompt + "\n")
rec = out.parent / "usage.json"
u = json.loads(rec.read_text()) if rec.exists() else {}
u[out.name] = {"model": a.model, "size": a.size, "quality": a.quality, "refs": [Path(r).name for r in a.ref],
               "usage": d.get("usage"), "seconds": round(time.time() - t0, 1),
               "created": time.strftime("%Y-%m-%dT%H:%M:%S")}
rec.write_text(json.dumps(u, indent=1))
print("saved", out, d.get("usage"))
