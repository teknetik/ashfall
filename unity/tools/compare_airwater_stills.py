"""Side-by-side before|after sheets for the Air + Water filter-bank pass (native 1920x1080 originals stay in before-native/ and after-native/).

  python compare_airwater_stills.py <evidence-dir>
Also writes localised-cost-comparison.json (6 s dwells at noon, uncapped; host load recorded, so a local comparison, never qualification).
"""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw
R = Path(sys.argv[1])
fixed = ['cam_audit_air_water_front', 'cam_audit_air_water_door', 'cam_audit_air_water_side_right', 'cam_audit_air_water_side_left']
players = ['fp_front_lane', 'fp_door_approach', 'fp_close_1p6', 'fp_label', 'fp_joints_shoulder', 'fp_valve', 'fp_oblique_left', 'fp_oblique_right']
(R / 'comparison').mkdir(exist_ok=True)
for v in fixed + players:
    for h in (8, 12, 16):
        n = '%s-h%02d.png' % (v, h)
        b = Image.open(R / 'before-native' / n).convert('RGB'); a = Image.open(R / 'after-native' / n).convert('RGB')
        sheet = Image.new('RGB', (1920, 540 + 26), (16, 16, 16)); d = ImageDraw.Draw(sheet)
        sheet.paste(b.resize((960, 540)), (0, 26)); sheet.paste(a.resize((960, 540)), (960, 26))
        d.text((8, 6), 'BEFORE (scene 79e2cf11, dev build 8cfd2e44)  %s  %02d:00' % (v, h), fill=(230, 230, 230))
        d.text((968, 6), 'AFTER (filter fittings, scene 06123dca)', fill=(230, 230, 230))
        sheet.save(R / 'comparison' / ('%s-h%02d-before-after.jpg' % (v, h)), quality=90)

def load(p): return json.loads((R / p).read_text())
rows = []; loads = {}
for st in ('fixed', 'players'):
    b = load('before-native/airwater-captures-%s.json' % st); a = load('after-native/airwater-captures-%s.json' % st)
    loads[st] = dict(before=b['loadAverage'], after=a['loadAverage'])
    bd = {d['view']: d for d in b['dwell']}
    for d in a['dwell']:
        x = bd[d['view']]
        sp = lambda q: q['setPass']['mean'] if q.get('setPass') else None
        tr = lambda q: q['tris']['mean'] if q.get('tris') else None
        rows.append(dict(view=d['view'], before=dict(fps=x['averageFps'], p50=x['p50Ms'], p99=x['p99Ms'], max=x['maxMs'], setPass=sp(x), tris=tr(x), frames=x['frames']),
                         after=dict(fps=d['averageFps'], p50=d['p50Ms'], p99=d['p99Ms'], max=d['maxMs'], setPass=sp(d), tris=tr(d), frames=d['frames']),
                         deltaP50Ms=d['p50Ms'] - x['p50Ms'], deltaP99Ms=d['p99Ms'] - x['p99Ms'], deltaFpsPct=100 * (d['averageFps'] / x['averageFps'] - 1)))
(R / 'localised-cost-comparison.json').write_text(json.dumps(dict(loadAverages=loads, rows=rows, note='noon, 6 s uncapped dwell per view; gpuMs and draw counters unavailable in this player; tris are submitted triangles across passes, not visible geometry'), indent=2))
print('%-32s %7s %7s %6s | %6s %6s | %6s %6s | %6s %6s' % ('view', 'fps b', 'fps a', 'd%', 'p50 b', 'p50 a', 'p99 b', 'p99 a', 'setP b', 'setP a'))
for r in rows:
    print('%-32s %7.1f %7.1f %5.1f%% | %6.2f %6.2f | %6.2f %6.2f | %6.0f %6.0f' % (r['view'], r['before']['fps'], r['after']['fps'], r['deltaFpsPct'], r['before']['p50'], r['after']['p50'], r['before']['p99'], r['after']['p99'], r['before']['setPass'] or 0, r['after']['setPass'] or 0))
print(json.dumps(loads))
