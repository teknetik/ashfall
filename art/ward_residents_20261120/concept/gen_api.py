"""Concept turnaround sheets via the OpenAI Images API (gpt-image-2, 1536x1024, high), used because `codex exec` hit its
ChatGPT usage limit on 19 Nov 2026. Prompt = p_<name>.txt minus the codex-specific first and last sentences.
Key from the project .env (never written or printed). Records: concepts.json. Usage: gen_api.py name [suffix]"""
import base64, json, sys, urllib.request, urllib.error
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[2]
env = dict(l.split("=", 1) for l in (ROOT / ".env").read_text().splitlines() if "=" in l and not l.startswith("#"))
KEY = env["OPENAI_API_KEY"].strip().strip('"\'')
name = sys.argv[1]; suffix = sys.argv[2] if len(sys.argv) > 2 else "v1"
out = HERE / f"{name}_sheet_{suffix}.png"
if out.exists(): sys.exit(f"{out.name} exists")
text = (HERE / f"p_{name}.txt").read_text().replace("Use your image generation tool. ", "")
prompt = "\n".join(l for l in text.splitlines() if not l.startswith("Save as")).strip()
body = json.dumps({"model": "gpt-image-2", "prompt": prompt, "size": "1536x1024", "quality": "high", "n": 1}).encode()
req = urllib.request.Request("https://api.openai.com/v1/images/generations", data=body, method="POST",
                             headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
try: d = json.loads(urllib.request.urlopen(req, timeout=600).read())
except urllib.error.HTTPError as e: sys.exit(f"{e.code} {e.read().decode()[:400]}")
out.write_bytes(base64.b64decode(d["data"][0]["b64_json"]))
rp = HERE / "concepts.json"; rec = json.loads(rp.read_text()) if rp.exists() else {}
rec[out.name] = {"model": "gpt-image-2", "size": "1536x1024", "quality": "high", "prompt_file": f"p_{name}.txt", "usage": d.get("usage")}
rp.write_text(json.dumps(rec, indent=1) + "\n"); print("saved", out.name, flush=True)
