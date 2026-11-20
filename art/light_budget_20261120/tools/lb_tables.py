#!/usr/bin/env python3
"""Light budget tables from lb_native.py output folders (20 Nov 2026).

  lb_tables.py views OUT_DIR            lights in view off/on and frame/face luminance (measure.py) per camera
  lb_tables.py walk OUT_DIR             per-segment walk table (fps, p50, p95, max lights in view off/on)
  lb_tables.py ab OUT_DIR               frame-time A/B table
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'night_readability_20261119/tools'))


def views(out):
    out = Path(out); rep = json.loads((out / 'report.json').read_text())
    from measure import measure
    m = {}
    for tag in ('views-off', 'views-on'):
        d = out / tag
        if d.exists():
            m[tag] = {'%s-h%05.2f' % (r['camera'], r['hour']): r for r in measure(d)}
    v = rep.get('views', {})
    names = sorted(set(v.get('views-on', {})) | set(v.get('views-off', {})))
    print('| camera | lights in view off | on | wanted | real / pools in view | centre p50 off → on | p95 off → on | faces off → on |')
    print('|---|---|---|---|---|---|---|---|')
    for n in names:
        a = v.get('views-off', {}).get(n, {}); b = v.get('views-on', {}).get(n, {})
        bb = b.get('budget') or {}
        fa = m.get('views-off', {}).get(n, {}); fb = m.get('views-on', {}).get(n, {})
        p50 = '%s → %s' % ((fa.get('frame') or {}).get('p50'), (fb.get('frame') or {}).get('p50'))
        p95 = '%s → %s' % ((fa.get('frame') or {}).get('p95'), (fb.get('frame') or {}).get('p95'))
        faces = []
        for act in fb.get('actors', []):
            before = next((x for x in fa.get('actors', []) if x['name'] == act['name']), None)
            if act.get('face') is not None:
                faces.append('%s %s → %s' % (act['name'].replace('npc_', ''), before.get('face') if before else '-', act['face']))
        print('| %s | %s | %s | %s | %s / %s | %s | %s | %s |' % (n, a.get('inView'), b.get('inView'), b.get('wantedInView'), bb.get('realInView'), bb.get('poolsInView'), p50, p95, '; '.join(faces)))


def walk(out):
    rep = json.loads((Path(out) / 'report.json').read_text())
    print('| segment | state | round | s | avg fps | p50 ms | p95 ms | max ms | lights in view max / mean | frames > 30 | wanted max | hard cuts | swaps |')
    print('|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for w in rep.get('walk', []):
        p, r = w['profile'], w['running']
        print('| %s | %s | %d | %s | %.1f | %.2f | %.2f | %.1f | %s / %s | %s / %s | %s | %s | %s |' % (w['segment'], w['state'], w['round'], w['seconds'], p['averageFps'], p['p50Ms'], p['p95Ms'], p['maxMs'],
              r.get('maxInView'), r.get('meanInView'), r.get('framesOver30'), r.get('frames'), r.get('maxWantedInView'), r.get('hardCuts'), (r.get('promotions') or 0) + (r.get('demotions') or 0)))
    agg = {}
    for w in rep.get('walk', []):
        a = agg.setdefault(w['state'], {'frames': 0, 'ms': 0.0, 'p50': [], 'max': 0, 'over': 0})
        n = w['profile']['frames']; a['frames'] += n; a['ms'] += n * 1000 / w['profile']['averageFps']
        a['p50'].append(w['profile']['p50Ms']); a['max'] = max(a['max'], w['running'].get('maxInView') or 0); a['over'] += w['running'].get('framesOver30') or 0
    for k, a in agg.items():
        print('\n%s: %.1f fps over %d frames, segment p50 mean %.2f ms, max lights in view %d, frames over 30: %d' % (k, a['frames'] * 1000 / a['ms'], a['frames'], sum(a['p50']) / len(a['p50']), a['max'], a['over']))


def ab(out):
    t = json.loads((Path(out) / 'ab-table.json').read_text())
    keys = sorted({k for row in t.values() for k in row})
    print('| camera | ' + ' | '.join('%s fps / p50 ms (runs) / lights' % k for k in keys) + ' |')
    print('|---|' + '---|' * len(keys))
    for c, row in t.items():
        print('| %s | %s |' % (c, ' | '.join('%.1f / %.2f (%s) / %s' % (row[k]['fps'], row[k]['p50Ms'], ', '.join('%.2f' % x for x in row[k]['p50Runs']), row[k]['inView']) if k in row else '-' for k in keys)))


{'views': views, 'walk': walk, 'ab': ab}[sys.argv[1]](sys.argv[2])
