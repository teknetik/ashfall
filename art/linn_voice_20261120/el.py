"""Tiny ElevenLabs helper for the Linn voice pass. Reads the key from the repo .env; never prints it.
python3 el.py GET /v1/user/subscription [out.json]"""
import json, re, sys, urllib.request, urllib.error
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
def key():
    m = re.search(r"^\s*(?:export\s+)?ELEVENLABS_API_KEY\s*=\s*(.+)$", (ROOT / ".env").read_text(), re.M)
    return m.group(1).strip().strip("\"'")
def call(method, path, body=None, raw=False):
    k = key()
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request("https://api.elevenlabs.io" + path, data=data, method=method,
                                 headers={"xi-api-key": k, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            b = r.read(); h = dict(r.headers)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"HTTP {e.code}: {e.read().decode(errors='replace')[:600].replace(k, '[REDACTED]')}")
    return (b, h) if raw else json.loads(b)
if __name__ == "__main__":
    out = call(sys.argv[1], sys.argv[2])
    s = json.dumps(out, indent=2)
    if len(sys.argv) > 3: Path(sys.argv[3]).write_text(s)
    else: print(s[:4000])
