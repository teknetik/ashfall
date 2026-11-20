"""Words per second: Linn's installed takes against the other colonists' takes (dialogue + barks)."""
import json, re, statistics, subprocess, yaml
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; A = ROOT / "unity/AthenHill/Assets/AthenHill"
def dur(p): return float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",str(p)]).decode())
def wc(t): return len(re.findall(r"[A-Za-z0-9']+", t))
rows = {}
for asset in sorted((A / "Data").glob("npc_*.asset")):
    nodes = yaml.safe_load(asset.read_text().split("--- !u!114 &11400000", 1)[1])["MonoBehaviour"]["nodes"]
    for n in nodes:
        w = A / "Audio/ElevenLabs/NpcVoices" / f"{asset.stem}-{n['id']}.wav"
        if w.exists(): rows.setdefault(asset.stem, []).append(("dialogue", n["id"], wc(n["text"]), dur(w)))
for s in json.loads((ROOT / "art/showcase_20261119/npc_life/barks.json").read_text())["speakers"]:
    for l in s["lines"]:
        w = A / "Audio/ElevenLabs/NpcBarks" / f"{s['id']}-{l['id']}.wav"
        if w.exists(): rows.setdefault(s["id"], []).append(("bark", l["id"], wc(l["text"]), dur(w)))
out = {"per_speaker_median_wps": {}, "linn": []}
for k, r in rows.items():
    out["per_speaker_median_wps"][k] = round(statistics.median(x[2] / x[3] for x in r), 2)
for kind, i, w, d in rows["npc_linn"]:
    out["linn"].append({"kind": kind, "id": i, "words": w, "seconds": round(d, 2), "wps": round(w / d, 2)})
others = [v for k, v in out["per_speaker_median_wps"].items() if k != "npc_linn"]
out["others_range"] = [min(others), max(others)]; out["others_median"] = round(statistics.median(others), 2)
print(json.dumps(out, indent=1))
