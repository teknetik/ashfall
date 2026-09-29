"""Matched before/after localised cost table for the Tool Exchange display pass (29 Sep 2026).

  python compare_tool_exchange_cost.py <evidence-dir> <out.json>

Before = before-native (players) + before-native-fixed-dwell (fixed); after = after-native (both). Host load is recorded per run:
a loaded host makes this a local comparison, never qualification.
"""
import json, sys
from pathlib import Path

E = Path(sys.argv[1])
def load(p): return json.loads(Path(p).read_text())
before = {d['view']: d for d in load(E / 'before-native-fixed-dwell/tool-exchange-captures-fixed.json')['dwell'] + load(E / 'before-native/tool-exchange-captures-players.json')['dwell']}
after = {d['view']: d for d in load(E / 'after-native/tool-exchange-captures-fixed.json')['dwell'] + load(E / 'after-native/tool-exchange-captures-players.json')['dwell']}
loads = dict(
    before_fixed=load(E / 'before-native-fixed-dwell/tool-exchange-captures-fixed.json')['loadAverage'], before_players=load(E / 'before-native/tool-exchange-captures-players.json')['loadAverage'],
    after_fixed=load(E / 'after-native/tool-exchange-captures-fixed.json')['loadAverage'], after_players=load(E / 'after-native/tool-exchange-captures-players.json')['loadAverage'])
rows = []
for view in before:
    if view not in after: continue
    b, a = before[view], after[view]
    def sp(x): return x['setPass']['mean'] if x.get('setPass') else None
    def tri(x): return x['tris']['mean'] if x.get('tris') else None
    rows.append(dict(view=view, before=dict(fps=b['averageFps'], p50=b['p50Ms'], p99=b['p99Ms'], max=b['maxMs'], setPass=sp(b), tris=tri(b), frames=b['frames']),
                     after=dict(fps=a['averageFps'], p50=a['p50Ms'], p99=a['p99Ms'], max=a['maxMs'], setPass=sp(a), tris=tri(a), frames=a['frames']),
                     deltaP99Ms=a['p99Ms'] - b['p99Ms'], deltaP50Ms=a['p50Ms'] - b['p50Ms'], deltaFpsPct=100 * (a['averageFps'] / b['averageFps'] - 1)))
Path(sys.argv[2]).write_text(json.dumps(dict(loadAverages=loads, rows=rows, note='gpuMs and draw counters unavailable in this player; tris are submitted triangles across passes, not visible geometry'), indent=2))
print('%-32s %8s %8s %7s | %7s %7s | %7s %7s | %9s %9s' % ('view', 'fps b', 'fps a', 'd%', 'p50 b', 'p50 a', 'p99 b', 'p99 a', 'setP b', 'setP a'))
for r in rows:
    print('%-32s %8.1f %8.1f %6.1f%% | %7.2f %7.2f | %7.2f %7.2f | %9s %9s' % (r['view'], r['before']['fps'], r['after']['fps'], r['deltaFpsPct'], r['before']['p50'], r['after']['p50'], r['before']['p99'], r['after']['p99'],
          '%.0f' % r['before']['setPass'] if r['before']['setPass'] else '-', '%.0f' % r['after']['setPass'] if r['after']['setPass'] else '-'))
print(json.dumps(loads))
