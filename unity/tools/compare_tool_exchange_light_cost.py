"""Local frame-cost table between two Tool Exchange light captures (t_e14abefb).

  python compare_tool_exchange_light_cost.py <dirA> <dirB> <out.json> [labelA labelB]
"""
import json, sys
from pathlib import Path

A, B = Path(sys.argv[1]), Path(sys.argv[2])
la = sys.argv[4] if len(sys.argv) > 4 else 'A'; lb = sys.argv[5] if len(sys.argv) > 5 else 'B'
ra = json.loads((A / 'tool-exchange-light-captures.json').read_text()); rb = json.loads((B / 'tool-exchange-light-captures.json').read_text())
da = {d['view']: d for d in ra['dwell']}; db = {d['view']: d for d in rb['dwell']}
rows = []
def sp(x): return x['setPass']['mean'] if x.get('setPass') else None
def tri(x): return x['tris']['mean'] if x.get('tris') else None
print('%-26s %7s %7s | %6s %6s | %6s %6s | %6s %6s | %6s %6s' % ('view', 'fps ' + la, 'fps ' + lb, 'p50a', 'p50b', 'p99a', 'p99b', 'maxA', 'maxB', 'spA', 'spB'))
for v in da:
    if v not in db: continue
    a, b = da[v], db[v]
    rows.append(dict(view=v, a=dict(fps=a['averageFps'], p50=a['p50Ms'], p99=a['p99Ms'], max=a['maxMs'], setPass=sp(a), tris=tri(a)), b=dict(fps=b['averageFps'], p50=b['p50Ms'], p99=b['p99Ms'], max=b['maxMs'], setPass=sp(b), tris=tri(b))))
    print('%-26s %7.1f %7.1f | %6.2f %6.2f | %6.2f %6.2f | %6.1f %6.1f | %6s %6s' % (v, a['averageFps'], b['averageFps'], a['p50Ms'], b['p50Ms'], a['p99Ms'], b['p99Ms'], a['maxMs'], b['maxMs'], sp(a), sp(b)))
Path(sys.argv[3]).write_text(json.dumps(dict(labels=[la, lb], loadAverage={la: ra['loadAverage'], lb: rb['loadAverage']}, rows=rows, note='local only; gpuMs and draw counters unavailable in this player; 6 s uncapped dwell per view/hour'), indent=2))
print('load', ra['loadAverage'], rb['loadAverage'])
