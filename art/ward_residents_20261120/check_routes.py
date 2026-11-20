"""Route clearance check for the residents (read-only, offline): every route segment against the saved scene's colliders
(survey.json AABBs, ignoring ground-level ones below 0.15 m), the talking colonists' standing spots (3 m), the other
walkers' lanes (1.2 m), the Lattice ring approach box (|x| < 4.4, z 21-39) and stairs. Writes route_check.json and
route maps. Usage: python3 check_routes.py"""
import json, math, subprocess
HERE = '/home/teknetik/code/ao2/art/ward_residents_20261120'
S = json.load(open('/home/teknetik/code/ao2/unity/evidence/showcase_phase2/20261120/residents/survey.json'))
R = {k: v for k, v in json.load(open(HERE + '/routes.json')).items() if not k.startswith('_')}
BODY = .28   # body half-width; a collider closer than this to the line is a clash
def seg_box(a, b, mn, mx):
    """Min distance from segment ab to an axis-aligned box in xz (sampled)."""
    n = max(2, int(math.dist(a, b) / .05)); best = 1e9
    for i in range(n + 1):
        t = i / n; x = a[0] + (b[0] - a[0]) * t; z = a[1] + (b[1] - a[1]) * t
        dx = max(mn[0] - x, 0, x - mx[0]); dz = max(mn[2] - z, 0, z - mx[2]); best = min(best, math.hypot(dx, dz))
    return best
def seg_pt(a, b, p):
    ax, az = b[0] - a[0], b[1] - a[1]; L = ax * ax + az * az
    t = 0 if L == 0 else max(0, min(1, ((p[0] - a[0]) * ax + (p[1] - a[1]) * az) / L))
    return math.hypot(a[0] + ax * t - p[0], a[1] + az * t - p[1])
cols = [c for c in S['colliders'] if c['max'][1] > .15 and 'Ground' not in c['p'] and 'COL_ENV_floor' not in c['p']]
report = {}; ok = True
lanes = [[(q[0], q[2]) for q in w['waypoints']] for w in S['walkers'] if w['active']]
npcs = [(n['id'], (n['pos'][0], n['pos'][2])) for n in S['npcs'] if n['active']]
for key, r in R.items():
    pts = r['points']; rows = []; length = 0
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]; length += math.dist(a, b)
        near = sorted(((seg_box(a, b, c['min'], c['max']), c['p']) for c in cols), key=lambda x: x[0])[:3]
        clash = [f'{d:.2f} {p}' for d, p in near if d < BODY]
        npc = [f'{i_} {min(seg_pt(a, b, p), 99):.1f}' for i_, p in npcs if seg_pt(a, b, p) < 3]
        lane = [f'{min(seg_pt(a, b, q) for q in l):.2f}' for l in lanes for q in l[:1] if min(seg_pt(a, b, q) for q in l) < 1.2]
        lattice = any(abs(a[0] + (b[0] - a[0]) * t / 10) < 4.4 and 21 < a[1] + (b[1] - a[1]) * t / 10 < 39 for t in range(11))
        rows.append({'segment': i, 'from': a, 'to': b, 'nearest': [f'{d:.2f} {p[-50:]}' for d, p in near], 'clash': clash, 'npcWithin3m': npc, 'walkerLaneWithin1.2m': lane, 'latticeApproach': lattice})
        ok &= not clash and not npc and not lattice
    stop_time = sum(s['seconds'] for s in r['stops'])
    report[key] = {'length': round(length, 1), 'lapSeconds': round(length / r['speed'] + stop_time, 1), 'stopSeconds': stop_time, 'segments': rows}
report['ok'] = ok
json.dump(report, open(HERE + '/route_check.json', 'w'), indent=1)
for key, r in R.items():
    for row in report[key]['segments']:
        flag = ('CLASH ' + '; '.join(row['clash'])) if row['clash'] else ''
        flag += (' NPC ' + ','.join(row['npcWithin3m'])) if row['npcWithin3m'] else ''
        flag += ' LATTICE' if row['latticeApproach'] else ''
        print(key, row['segment'], row['from'], '->', row['to'], 'nearest', row['nearest'][0], flag)
    print(key, 'length', report[key]['length'], 'lap', report[key]['lapSeconds'])
print('OK' if ok else 'PROBLEMS')
