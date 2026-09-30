#!/usr/bin/env python3
"""OpenAI image generation for the salvage-cache concept views (key read from the project .env, never printed).

Usage: gen_concept.py NAME PROMPT [--size 1536x1024] [--model gpt-image-2] [--ref concepts/x.png ...]
With --ref the request goes to /v1/images/edits so later views stay consistent with an accepted image.
Every prompt, model, size, reference and reported usage is recorded in concepts/prompts.json.
"""
import argparse, base64, json, mimetypes, sys, time, urllib.request, urllib.error, uuid
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]
env = dict(l.split("=", 1) for l in (ROOT / ".env").read_text().splitlines() if "=" in l and not l.startswith("#"))
KEY = env["OPENAI_API_KEY"].strip()

ap = argparse.ArgumentParser()
ap.add_argument("name"); ap.add_argument("prompt")
ap.add_argument("--size", default="1536x1024"); ap.add_argument("--model", default="gpt-image-2")
ap.add_argument("--ref", action="append", default=[]); ap.add_argument("--quality", default="high")
a = ap.parse_args()

if a.ref:
    boundary = uuid.uuid4().hex
    parts = []
    def field(name, value):
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode())
    for k, v in (("model", a.model), ("prompt", a.prompt), ("size", a.size), ("quality", a.quality), ("n", "1")):
        field(k, v)
    for r in a.ref:
        p = HERE / r if not Path(r).is_absolute() else Path(r)
        mime = mimetypes.guess_type(p.name)[0] or "image/png"
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"image[]\"; filename=\"{p.name}\"\r\n"
                     f"Content-Type: {mime}\r\n\r\n".encode() + p.read_bytes() + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(parts)
    req = urllib.request.Request("https://api.openai.com/v1/images/edits", data=body, method="POST",
                                 headers={"Authorization": f"Bearer {KEY}", "Content-Type": f"multipart/form-data; boundary={boundary}"})
else:
    body = json.dumps({"model": a.model, "prompt": a.prompt, "size": a.size, "quality": a.quality, "n": 1}).encode()
    req = urllib.request.Request("https://api.openai.com/v1/images/generations", data=body, method="POST",
                                 headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
t0 = time.time()
try:
    with urllib.request.urlopen(req, timeout=600) as r:
        d = json.loads(r.read())
except urllib.error.HTTPError as e:
    print("HTTP", e.code, e.read().decode()[:800]); sys.exit(1)
out = HERE / "concepts" / f"{a.name}.png"
out.write_bytes(base64.b64decode(d["data"][0]["b64_json"]))
rec = HERE / "concepts" / "prompts.json"
r = json.loads(rec.read_text()) if rec.exists() else {}
r[a.name] = {"model": a.model, "size": a.size, "quality": a.quality, "refs": a.ref, "prompt": a.prompt,
             "usage": d.get("usage"), "seconds": round(time.time() - t0, 1), "created": time.strftime("%Y-%m-%dT%H:%M:%S")}
rec.write_text(json.dumps(r, indent=1))
print("saved", out, d.get("usage"))
