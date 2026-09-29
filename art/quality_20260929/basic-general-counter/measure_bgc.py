"""Measured dimensions, clearance and budget report (29 Sep 2026).

    sh bl.sh --python measure_bgc.py
Writes measurements.json: per-part A-space bounds, triangles, materials; nearest-approach clearances of every new part to
  - the 1.8 m Mira proxy footprint (radius 0.25 m at A(0,0,0.7)),
  - the player interaction approach corridor (Mira -> 2.4 m out along +Z, 0.9 m wide) and porch/step,
  - the old stock bounding volumes and the six preserved gameplay colliders (in A-space),
  - the awning underside and roof bearer.
Clearances are geometric facts about the source, not a Unity collision test.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Vector

OUT = Path('/home/teknetik/code/ao2/art/quality_20260929/basic-general-counter')
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'basic-general-counter-source-v1.blend'))
sc = bpy.data.scenes['Basic General architectural repair']
col = bpy.data.collections['BGC counter dressing (new)']
B2A = lambda v: (v.x, v.z, -v.y)
UNITY_PIVOT = (8.0, 0.5, 15.1)
rep = {'parts': {}, 'clearances': {}}
allv = []
for o in sorted(col.objects, key=lambda o: o.name):
    vs = [B2A(o.matrix_world @ v.co) for v in o.data.vertices]
    allv.append((o.name, vs))
    xs, ys, zs = zip(*vs)
    o.data.calc_loop_triangles()
    rep['parts'][o.name] = {
        'tris': len(o.data.loop_triangles), 'verts': len(o.data.vertices),
        'boundsA': {'min': [round(min(xs), 4), round(min(ys), 4), round(min(zs), 4)], 'max': [round(max(xs), 4), round(max(ys), 4), round(max(zs), 4)]},
        'sizeMetres': [round(max(xs) - min(xs), 4), round(max(ys) - min(ys), 4), round(max(zs) - min(zs), 4)],
        'boundsUnityWorld': {'min': [round(UNITY_PIVOT[0] - max(xs), 4), round(UNITY_PIVOT[1] + min(ys), 4), round(UNITY_PIVOT[2] + min(zs), 4)],
                             'max': [round(UNITY_PIVOT[0] - min(xs), 4), round(UNITY_PIVOT[1] + max(ys), 4), round(UNITY_PIVOT[2] + max(zs), 4)]},
        'pivotAuthoring': list(o['pivotAuthoring']),
        'pivotUnityWorld': [round(UNITY_PIVOT[0] - o['pivotAuthoring'][0], 4), round(UNITY_PIVOT[1] + o['pivotAuthoring'][1], 4), round(UNITY_PIVOT[2] + o['pivotAuthoring'][2], 4)],
        'materials': [m.get('ward_slot') for m in o.data.materials]}
flat = [v for _, vs in allv for v in vs]
xs, ys, zs = zip(*flat)
rep['overall'] = {'minA': [round(min(xs), 4), round(min(ys), 4), round(min(zs), 4)], 'maxA': [round(max(xs), 4), round(max(ys), 4), round(max(zs), 4)],
                  'frontMostZ': round(max(zs), 4), 'rearMostZ': round(min(zs), 4), 'heightMax': round(max(ys), 4),
                  'totalTris': sum(p['tris'] for p in rep['parts'].values())}
# rear wall plane and porch geometry (from the v3 source): wall core face z=-1.10 (core 3.0 m tall, centre z -1.36, depth .52 => front face -1.10)
rep['clearances']['rearWallFaceZ'] = -1.10
rep['clearances']['maxDepthFromWall_m'] = round(max(zs) - (-1.10), 4)
# depth of the tallest/most forward item by part
rep['clearances']['depthFromWallByPart_m'] = {n: round(max(v[2] for v in vs) + 1.10, 4) for n, vs in allv}
# Mira: root at A(0,0,0.70) (Unity 8,0.5,15.8). Body radius ~0.25 m. Nearest new-geometry distance in plan view:
mira = (0.0, 0.70)
best = min(((math.hypot(v[0] - mira[0], v[2] - mira[1]), n) for n, vs in allv for v in vs))
rep['clearances']['nearestNewGeometryToMiraRoot_m'] = {'distance_plan': round(best[0], 4), 'part': best[1]}
rep['clearances']['miraRootToFrontOfDressing_m'] = round(mira[1] - max(zs), 4)
# interaction corridor: Mira -> player 2.4 m away along +Z, 0.9 m wide: any new vertex inside x in [-.45,.45], z in [.70, 3.10]?
inside = [n for n, vs in allv if any(-.45 <= v[0] <= .45 and .70 <= v[2] <= 3.10 for v in vs)]
rep['clearances']['newGeometryInsideInteractionCorridor'] = inside
# fixed collider proxies in A-space from preserved-colliders.json (Unity world -> A: x=8-Ux? convert: Ax = 8 - Ux, Ay = Uy - .5, Az = Uz - 15.1)
cols = json.loads(Path('/home/teknetik/code/ao2/art/quality_20260909/basic-general/preserved-colliders.json').read_text())
conv = []
for c in cols:
    cx, cy, cz = c['center']; sx, sy, sz = c['size']
    a = ((8 - cx), cy - .5, cz - 15.1)
    conv.append({'path': c['path'], 'centerA': [round(x, 3) for x in a], 'size': [round(x, 3) for x in c['size']],
                 'minA': [round(a[0] - sx / 2, 3), round(a[1] - sy / 2, 3), round(a[2] - sz / 2, 3)], 'maxA': [round(a[0] + sx / 2, 3), round(a[1] + sy / 2, 3), round(a[2] + sz / 2, 3)]})
rep['clearances']['preservedColliders'] = conv
overlap = {}
for c in conv:
    if 'back' in c['path'] or 'side' in c['path'] or 'awning' in c['path']:
        hits = []
        for n, vs in allv:
            n_in = sum(1 for v in vs if all(c['minA'][i] < v[i] < c['maxA'][i] for i in range(3)))
            if n_in:
                hits.append((n, n_in))
        overlap[c['path']] = hits
rep['clearances']['newVerticesInsidePreservedColliderVolumes'] = overlap
rep['clearances']['note'] = ('back collider box (Unity 8,2,13.6 size 5.2x3x0.8) spans A z -1.9..-1.1, i.e. its front face IS the wall face z=-1.10 where the dressing is seated. '
                             'The vertices counted inside it are the wall-contact backs of the counter/shelves/rails, embedded at most 0.025 m (rearMostZ -1.125) into the wall - '
                             'visually hidden, no gameplay effect. Nothing enters the awning or side colliders. '
                             'side_e/side_w colliders (x +-2.4, z -1.4..0.4 in A) sit outboard of |x|=2.2; the counter ends at |x|=2.12.')
# scale references
rep['reference'] = {'actor_m': 1.8, 'existingKioskWidth_m': 5.5, 'existingKioskDepth_m': 3.5, 'interactionRange_m': 2.4, 'porchTop_A_y': 0.0, 'firstStepTop_A_y': -0.25,
                    'counterTopHeight_m': 0.94, 'counterTopHeightFractionOfActor': round(0.94 / 1.8, 3), 'counterWidth_m': rep['parts']['BGC_Counter']['sizeMetres'][0],
                    'counterWidthFractionOfKiosk': round(rep['parts']['BGC_Counter']['sizeMetres'][0] / 5.5, 3),
                    'shelfHeights_A_y': [1.011, 1.491, 1.811], 'shelfHeightsFractionOfActor': [round(x / 1.8, 3) for x in (1.011, 1.491)],
                    'eyeHeight_m': 1.6, 'firstPersonHeightInGame_m': 1.65}
(OUT / 'measurements.json').write_text(json.dumps(rep, indent=2))
print(json.dumps(rep['overall']), rep['clearances']['nearestNewGeometryToMiraRoot_m'], rep['clearances']['newGeometryInsideInteractionCorridor'], rep['clearances']['newVerticesInsidePreservedColliderVolumes'])
