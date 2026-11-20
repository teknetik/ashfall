import json, urllib.parse
from el import call
from pathlib import Path
seen = {v["voice_id"]: v for v in json.loads(Path("probe/shared_voices.json").read_text())}
for age in ("old", "middle_aged"):
    for desc in ("raspy", "husky", "deep", "gritty", "rough", "wise", "mature", "grumpy", ""):
        for page in range(3):
            params = {"page_size": 100, "gender": "female", "age": age, "language": "en", "page": page}
            if desc: params["descriptives"] = desc
            r = call("GET", "/v1/shared-voices?" + urllib.parse.urlencode(params))
            for v in r.get("voices", []): seen.setdefault(v["voice_id"], v)
            if not r.get("has_more"): break
Path("probe/shared_voices.json").write_text(json.dumps(list(seen.values()), indent=1))
print(len(seen))
