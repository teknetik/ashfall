"""Download library preview clips (free) for the shortlist into probe/previews/."""
import json, re, urllib.request
from pathlib import Path
vs = json.loads(Path("probe/shared_voices.json").read_text())
rough = re.compile(r'rasp|gravel|rough|weather|hoarse|grit|husky|smok|gruff|crack|deep|low', re.I)
pick = [v for v in vs if v.get("language") == "en" and (v.get("age") == "old" or (v.get("age") == "middle_aged" and rough.search((v.get("description") or "") + v["name"] + (v.get("descriptive") or ""))))]
pick += [v for v in vs if v["voice_id"] in ("fs3nd19KF2GO2hLTzkBm",)]
out = Path("probe/previews"); out.mkdir(parents=True, exist_ok=True)
index = {}
for v in pick:
    if not v.get("preview_url"): continue
    f = out / f"{v['voice_id']}.mp3"
    if not f.exists():
        try:
            with urllib.request.urlopen(urllib.request.Request(v["preview_url"], headers={"User-Agent": "Mozilla/5.0"}), timeout=60) as r: f.write_bytes(r.read())
        except Exception as e: print("fail", v["name"], e); continue
    index[v["voice_id"]] = {k: v.get(k) for k in ("name", "age", "accent", "descriptive", "use_case", "cloned_by_count", "description", "free_users_allowed")}
Path("probe/previews/index.json").write_text(json.dumps(index, indent=1))
print(len(index))
