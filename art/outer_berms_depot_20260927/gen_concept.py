#!/usr/bin/env python3
"""OpenAI image generation for Outer Berms depot concept references (key from project .env, never logged)."""
import base64, json, sys, urllib.request
from pathlib import Path
HERE = Path(__file__).resolve().parent
env = dict(l.split("=", 1) for l in (HERE.parents[1] / ".env").read_text().splitlines() if "=" in l)
key = env["OPENAI_API_KEY"].strip()
name, prompt = sys.argv[1], sys.argv[2]
size = sys.argv[3] if len(sys.argv) > 3 else "1536x1024"
model = sys.argv[4] if len(sys.argv) > 4 else "gpt-image-1"
body = json.dumps({"model": model, "prompt": prompt, "size": size, "quality": "high", "n": 1}).encode()
req = urllib.request.Request("https://api.openai.com/v1/images/generations", data=body, method="POST",
                             headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.loads(r.read())
except urllib.error.HTTPError as e:
    print("HTTP", e.code, e.read().decode()[:600]); sys.exit(1)
out = HERE / "concept" / f"{name}.png"
out.write_bytes(base64.b64decode(d["data"][0]["b64_json"]))
rec = HERE / "concept" / "prompts.json"
r = json.loads(rec.read_text()) if rec.exists() else {}
r[name] = {"model": model, "size": size, "prompt": prompt, "usage": d.get("usage")}
rec.write_text(json.dumps(r, indent=1))
print("saved", out)
