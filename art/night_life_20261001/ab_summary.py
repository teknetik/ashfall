"""Summarise the alternating A/B profile runs (unity/evidence/night-life/20261001/ab/<tag>-<cam>-<arm>-<i>/lookbook.json)
into ab/summary.json and a markdown table on stdout. Usage: python3 ab_summary.py [tag]"""
import json, statistics, sys
from pathlib import Path

EV = Path(__file__).resolve().parents[2] / "unity/evidence/night-life/20261001/ab"
tag = sys.argv[1] if len(sys.argv) > 1 else "3"
runs = {}
for d in sorted(EV.glob(f"{tag}-*")):
    f = d / "lookbook.json"
    if not f.exists():
        continue
    name = d.name[len(tag) + 1:]
    cam, arm, i = name.rsplit("-", 2)
    rep = json.loads(f.read_text())
    for key, p in rep.get("profiles", {}).items():
        hour = key.split("-h")[-1]
        runs.setdefault((cam, hour), {}).setdefault(arm, []).append(dict(run=int(i), **p))
out = {}
print("| Camera | Hour | On: avg fps / p50 / p95 / p99 / max (ms) | Off: avg fps / p50 / p95 / p99 / max | Δ p50 | Δ mean frame | Δ draws | Δ tris |")
print("| --- | --- | --- | --- | --- | --- | --- | --- |")
for (cam, hour), arms in sorted(runs.items()):
    row = {}
    for arm in ("on", "off"):
        rs = arms.get(arm, [])
        if not rs:
            continue
        m = lambda k: statistics.mean(r[k] for r in rs if r.get(k) is not None)
        row[arm] = dict(n=len(rs), averageFps=m("averageFps"), meanMs=1000 / m("averageFps"), p50Ms=m("p50Ms"), p95Ms=m("p95Ms"),
                        p99Ms=m("p99Ms"), maxMs=max(r["maxMs"] for r in rs), perRunFps=[round(r["averageFps"], 1) for r in sorted(rs, key=lambda r: r["run"])],
                        draws=statistics.mean(r["draws"]["mean"] for r in rs if r.get("draws")) if any(r.get("draws") for r in rs) else None,
                        tris=statistics.mean(r["tris"]["mean"] for r in rs if r.get("tris")) if any(r.get("tris") for r in rs) else None,
                        cpuMs=statistics.mean(r["cpuMs"]["mean"] for r in rs if r.get("cpuMs")) if any(r.get("cpuMs") for r in rs) else None)
    out[f"{cam}@{hour}"] = row
    if "on" in row and "off" in row:
        a, b = row["on"], row["off"]
        fmt = lambda r: f"{r['averageFps']:.1f} / {r['p50Ms']:.2f} / {r['p95Ms']:.2f} / {r['p99Ms']:.2f} / {r['maxMs']:.2f}"
        dd = f"{a['draws'] - b['draws']:+.0f}" if a["draws"] and b["draws"] else "n/a"
        dt = f"{(a['tris'] - b['tris']) / 1000:+.0f}k" if a["tris"] and b["tris"] else "n/a"
        print(f"| {cam} | {hour} | {fmt(a)} | {fmt(b)} | {a['p50Ms'] - b['p50Ms']:+.2f} ms | {a['meanMs'] - b['meanMs']:+.2f} ms | {dd} | {dt} |")
(EV / f"summary-{tag}.json").write_text(json.dumps(out, indent=1))
for k, v in out.items():
    print(k, {arm: v[arm]["perRunFps"] for arm in v})
