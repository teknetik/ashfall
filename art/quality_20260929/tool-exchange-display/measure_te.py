"""Measured dimensions, attachment positions and clearances for the Tool Exchange display/shutter modules (29 Sep 2026).

    sh bl.sh --python measure_te.py
Writes measurements.json.  Geometric facts about the source; not a Unity collision test.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Vector

OUT = Path('/home/teknetik/code/ao2/art/quality_20260929/tool-exchange-display')
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'tool-exchange-display-source-v1.blend'))
col = bpy.data.collections['TE display and shutter (new)']
sc = bpy.data.scenes[0]
A = lambda v: (v.x, v.z, -v.y)
UNITY_PIVOT = (-20.6, .5, 9.0)      # building pivot; prefab yaw 90 deg; +A X -> Unity local -X (glTFast flip)
rep = {'parts': {}, 'clearances': {}, 'attachments': {}}
allv = {}
for o in sorted(col.objects, key=lambda o: o.name):
    vs = [A(o.matrix_world @ v.co) for v in o.data.vertices]
    allv[o.name] = vs
    xs, ys, zs = zip(*vs)
    o.data.calc_loop_triangles()
    pv = o['pivotAuthoring']
    rep['parts'][o.name] = {
        'tris': len(o.data.loop_triangles), 'verts': len(o.data.vertices),
        'boundsA': {'min': [round(min(xs), 4), round(min(ys), 4), round(min(zs), 4)], 'max': [round(max(xs), 4), round(max(ys), 4), round(max(zs), 4)]},
        'sizeMetres_XYZ': [round(max(xs) - min(xs), 4), round(max(ys) - min(ys), 4), round(max(zs) - min(zs), 4)],
        'pivotAuthoring_A': [round(x, 4) for x in pv],
        'pivotUnityLocalToBuilding': [round(-pv[0], 4), round(pv[1], 4), round(pv[2], 4)],
        'materials': [m.get('ward_slot') for m in o.data.materials],
        'objectScale': [round(x, 6) for x in o.scale], 'determinant': round(o.matrix_world.determinant(), 6)}
flat = [v for vs in allv.values() for v in vs]
xs, ys, zs = zip(*flat)
rep['overall'] = {'minA': [round(min(xs), 4), round(min(ys), 4), round(min(zs), 4)], 'maxA': [round(max(xs), 4), round(max(ys), 4), round(max(zs), 4)],
                  'totalTris': sum(p['tris'] for p in rep['parts'].values())}

# --- display: everything behind the existing glazing (rear face of glass z = 2.543) and inside the dressed opening
disp = [n for n in allv if n not in ('TE_ShutterGuide_L', 'TE_ShutterGuide_R', 'TE_ShutterHardware', 'TE_DisplayGlazing')]
dz = max(v[2] for n in disp for v in allv[n])
rep['clearances']['displayFrontMostZ'] = round(dz, 4)
rep['clearances']['glassRearFaceZ'] = 2.543
rep['clearances']['gapDisplayToGlassRear_m'] = round(2.543 - dz, 4)
rep['clearances']['displayInsideOpeningXY'] = all(-2.9 - 1e-4 <= v[0] <= -1.4 + 1e-4 and .78 - 1e-4 <= v[1] <= 2.2 + 1e-4 for n in disp for v in allv[n])
rep['clearances']['displayMaxDepthBehindWallFace_m'] = round(2.45 - min(v[2] for n in disp for v in allv[n]), 4)
# --- protrusion of the shutter hardware relative to existing colliders and the old lift handles
sh = [v for n in ('TE_ShutterHardware', 'TE_ShutterGuide_L', 'TE_ShutterGuide_R') for v in allv[n]]
rep['clearances']['shutterHardwareFrontMostZ'] = round(max(v[2] for v in sh), 4)
rep['clearances']['oldRevision04ShutterFrontMostZ'] = 2.763       # lift handle
rep['clearances']['frontClosedShopWallColliderFaceZ'] = 2.70       # centre 2.55, depth 0.30 (collider-proxies.json)
rep['clearances']['hardwareProtrusionBeyondColliderFace_m'] = round(max(v[2] for v in sh) - 2.70, 4)
rep['clearances']['hardwareProtrusionBeyondOldRevision04_m'] = round(max(v[2] for v in sh) - 2.763, 4)
# --- tools versus their fixings: minimum distance in z from board face for the three hung tools
for n in ('TE_ToolPipeWrench', 'TE_ToolLumpHammer', 'TE_ToolBoltCutters'):
    zz = [v[2] for v in allv[n]]
    rep['clearances'][n + '_zRange'] = [round(min(zz), 4), round(max(zz), 4)]
    rep['clearances'][n + '_standoffFromBoardFace_m'] = round(min(zz) - 2.042, 4)
# --- eye-height legibility: angular size of each tool from 1.6 m eye at 2.5 m from the glass (z = 5.043) and from the avenue kerb 6 m out
for n, key in (('TE_ToolPipeWrench', 'wrench'), ('TE_ToolLumpHammer', 'hammer'), ('TE_ToolBoltCutters', 'cutters')):
    vs = allv[n]
    L = max(math.hypot(a[0] - b[0], a[1] - b[1]) for a in vs[::7] for b in vs[::7])
    rep['clearances'][key + '_longestSpan_m'] = round(L, 3)
    rep['clearances'][key + '_angularSize_deg_at_2p5m'] = round(math.degrees(2 * math.atan(L / 2 / 4.5)), 2)   # 2.0 m viewer-to-glass + glass-to-tool 0.5 +
    rep['clearances'][key + '_angularSize_deg_at_6m'] = round(math.degrees(2 * math.atan(L / 2 / 8.5)), 2)
# --- attachment positions
pegs = json.loads((OUT / 'build-stats-raw.json').read_text()).get('pegs', {})
rep['attachments'] = {
    'pipeWrench': {'hungOn': 'board peg through the 33 mm eyelet', 'pegA_xy': pegs.get('wrench'), 'boardFaceZ': 2.042},
    'lumpHammer': {'restsOn': 'two curl rest pegs under the haft', 'pegsA_xy': pegs.get('hammer')},
    'boltCutters': {'restsOn': 'two curl rest pegs under the lower/upper arms (arms rest on the pegs, tag hangs on a twine loop round the lower arm)', 'pegsA_xy': pegs.get('cutters')},
    'pegRail': {'fixedTo': 'shadow board face, six countersunk screws', 'railCentreY': 1.955, 'x': [-2.86, -1.44]},
    'benchTools': {'restOn': 'bench top y = 0.962', 'clampA_xz': [-2.44, 2.22], 'whetstoneA_xz': [-1.80, 2.235], 'fileA_xz': [-1.74, 2.36]},
    'displayLamp': {'fixedTo': 'soffit y = 2.185 (plate 0.10 x 0.06); lamp head at y 2.010..2.10, x = -1.78; NO light source or emissive in the asset'},
    'shutterGuides': {'fixedTo': 'masonry reveal faces x = -0.70 (left) and x = 2.75 (right); channel retains the slat edges (slat z 2.595..2.655)'},
    'shutterHardware': {'fixedTo': 'front face of the slat surface z = 2.655; handle plates at x = 0.475 and 1.575, lock box x = 1.025, y = 0.82'},
}
(OUT / 'measurements.json').write_text(json.dumps(rep, indent=2))
print(json.dumps(rep['clearances'], indent=1))
print('total tris', rep['overall']['totalTris'])
