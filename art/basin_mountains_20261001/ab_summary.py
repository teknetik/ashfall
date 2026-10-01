"""Summarise the alternating A/B runs written by ab_runs.sh (copied from art/perimeter_walls_20261001): per camera and arm,
p50/p95/p99/max frame time, triangles and draws (NativeQa profile counters). Usage: python3 ab_summary.py <ab dir> [out.json]"""
import json, re, statistics, sys
from pathlib import Path

root = Path(sys.argv[1])
rows = {}
for d in sorted(p for p in root.iterdir() if p.is_dir()):
    m = re.match(r"(.+)-(on|off)-(\d+)$", d.name)
    if not m:
        continue
    lb = d / "lookbook.json"
    if not lb.exists():
        continue
    prof = json.loads(lb.read_text()).get("profiles", {})
    for key, p in prof.items():
        rows.setdefault((m.group(1), m.group(2)), []).append(dict(run=int(m.group(3)), **p))
out = {}
for (cam, arm), rs in sorted(rows.items()):
    def mean(k, sub=None):
        vals = [(r[k][sub] if sub else r[k]) for r in rs if r.get(k) is not None]
        return round(statistics.mean(vals), 2) if vals else None
    out.setdefault(cam, {})[arm] = dict(runs=len(rs), averageFps=mean("averageFps"), p50Ms=mean("p50Ms"), p95Ms=mean("p95Ms"),
                                        p99Ms=mean("p99Ms"), maxMs=mean("maxMs"), tris=mean("tris", "mean"), draws=mean("draws", "mean"),
                                        perRunFps=[round(r["averageFps"], 1) for r in sorted(rs, key=lambda r: r["run"])])
for cam, arms in out.items():
    if "on" in arms and "off" in arms:
        arms["deltaP50Ms"] = round(arms["on"]["p50Ms"] - arms["off"]["p50Ms"], 2)
        arms["deltaFps"] = round(arms["on"]["averageFps"] - arms["off"]["averageFps"], 1)
print(json.dumps(out, indent=1))
if len(sys.argv) > 2:
    Path(sys.argv[2]).write_text(json.dumps(out, indent=1))
