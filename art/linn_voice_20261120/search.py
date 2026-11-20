import json, sys, urllib.parse
from el import call
from pathlib import Path
seen = {}
queries = ["raspy", "gravelly", "rough", "weathered", "hoarse", "old woman", "elderly", "grandmother", "crone", "smoky", "husky", "witch", "gritty", "aged", "wise"]
for q in queries:
    for extra in ({"age": "old"}, {}):
        params = {"page_size": 100, "gender": "female", "search": q, **extra}
        r = call("GET", "/v1/shared-voices?" + urllib.parse.urlencode(params))
        for v in r.get("voices", []):
            seen.setdefault(v["voice_id"], v)
Path("probe/shared_voices.json").write_text(json.dumps(list(seen.values()), indent=1))
print(len(seen))
