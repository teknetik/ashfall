#!/usr/bin/env python3
"""Reference sheets for the bench tools and fixtures (model-bench, Steady Hands bench programme, 20 Nov 2026).

Copied from art/salvage_cache_20260930/scripts/gen_concept.py and changed to write into a family's sheets/ folder with
the prompt beside each image. OpenAI gpt-image-2; the key is read from the repository .env and never printed.

Usage: gen_sheet.py FAMILY NAME PROMPT_FILE [--size 1536x1024] [--ref sheets/x.png ...]
  FAMILY is tools or fixtures. PROMPT_FILE is a text file; it is copied to sheets/NAME.prompt.txt.
With --ref the request goes to /v1/images/edits so close-up sheets show the same object as the overall sheet.
"""
import argparse, base64, json, mimetypes, sys, time, urllib.request, urllib.error, uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent            # .../steady_hands_bench_20261120/tools
PROG = HERE.parent
ROOT = PROG.parents[1]
env = dict(l.split("=", 1) for l in (ROOT / ".env").read_text().splitlines() if "=" in l and not l.startswith("#"))
KEY = env["OPENAI_API_KEY"].strip()

ap = argparse.ArgumentParser()
ap.add_argument("family", choices=["tools", "fixtures"]); ap.add_argument("name"); ap.add_argument("prompt_file")
ap.add_argument("--size", default="1536x1024"); ap.add_argument("--model", default="gpt-image-2")
ap.add_argument("--ref", action="append", default=[]); ap.add_argument("--quality", default="high")
a = ap.parse_args()
OUT = PROG / a.family / "sheets"
OUT.mkdir(parents=True, exist_ok=True)
prompt = Path(a.prompt_file).read_text().strip()

if a.ref:
    boundary = uuid.uuid4().hex
    parts = []
    def field(name, value):
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode())
    for k, v in (("model", a.model), ("prompt", prompt), ("size", a.size), ("quality", a.quality), ("n", "1")):
        field(k, v)
    for r in a.ref:
        p = Path(r) if Path(r).is_absolute() else PROG / r
        mime = mimetypes.guess_type(p.name)[0] or "image/png"
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"image[]\"; filename=\"{p.name}\"\r\n"
                     f"Content-Type: {mime}\r\n\r\n".encode() + p.read_bytes() + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    req = urllib.request.Request("https://api.openai.com/v1/images/edits", data=b"".join(parts), method="POST",
                                 headers={"Authorization": f"Bearer {KEY}", "Content-Type": f"multipart/form-data; boundary={boundary}"})
else:
    body = json.dumps({"model": a.model, "prompt": prompt, "size": a.size, "quality": a.quality, "n": 1}).encode()
    req = urllib.request.Request("https://api.openai.com/v1/images/generations", data=body, method="POST",
                                 headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
t0 = time.time()
try:
    with urllib.request.urlopen(req, timeout=900) as r:
        d = json.loads(r.read())
except urllib.error.HTTPError as e:
    msg = e.read().decode()[:800]
    print("HTTP", e.code, msg)
    (OUT / f"{a.name}.error.txt").write_text(f"HTTP {e.code}\n{msg}\n")
    sys.exit(1)
(OUT / f"{a.name}.png").write_bytes(base64.b64decode(d["data"][0]["b64_json"]))
(OUT / f"{a.name}.prompt.txt").write_text(prompt + "\n")
rec = OUT / "prompts.json"
r = json.loads(rec.read_text()) if rec.exists() else {}
r[a.name] = {"model": a.model, "size": a.size, "quality": a.quality, "refs": a.ref, "usage": d.get("usage"),
             "seconds": round(time.time() - t0, 1), "created": time.strftime("%Y-%m-%dT%H:%M:%S")}
rec.write_text(json.dumps(r, indent=1))
print("saved", OUT / f"{a.name}.png", d.get("usage"))
