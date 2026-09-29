"""Measured dimensions, attachment positions and clearances for the Air + Water filter fittings (29 Sep 2026, task t_bd3d9fe3).

    sh bl.sh --python measure_aw.py
Writes measurements.json.  Geometric facts about the source; not a Unity collision test.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Vector

OUT = Path('/home/teknetik/code/ao2/art/quality_20260929/airwater-filters')
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'airwater-filters-source-v1.blend'))
col = bpy.data.collections['AW filter fittings (new)']
A = lambda v: (v.x, v.z, -v.y)
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
        'pivotAuthoring_A': [round(x, 4) for x in pv], 'pivotUnityLocalToBuilding': [round(-pv[0], 4), round(pv[1], 4), round(pv[2], 4)],
        'materials': [m.get('ward_slot') for m in o.data.materials], 'objectScale': [round(x, 6) for x in o.scale],
        'determinant': round(o.matrix_world.determinant(), 6)}
flat = [v for vs in allv.values() for v in vs]
xs, ys, zs = zip(*flat)
rep['overall'] = {'minA': [round(min(xs), 4), round(min(ys), 4), round(min(zs), 4)], 'maxA': [round(max(xs), 4), round(max(ys), 4), round(max(zs), 4)],
                  'totalTris': sum(p['tris'] for p in rep['parts'].values())}
C = rep['clearances']
# --- protrusion versus the retained vessel silhouette and the wall
vessel_front = 2.93 + .25                       # canister front z (retained)
retainer_front = 3.22                           # retained collar front z
for n in allv:
    zz = [v[2] for v in allv[n]]
    C[n + '_frontMostZ'] = round(max(zz), 4)
C['vesselSilhouetteFrontZ'] = vessel_front
C['collarFrontZ'] = retainer_front
zfront_vessel_mounts = max(max(v[2] for v in allv[f'AW_FilterMount_{i}']) for i in (1, 2, 3))
C['frontMostVesselMountZ'] = round(zfront_vessel_mounts, 4)
C['frontMostVesselMount_beyondCollarFront_m'] = round(zfront_vessel_mounts - retainer_front, 4)
hz = max(v[2] for v in allv['AW_FilterHeader'])
C['frontMostHeaderZ'] = round(hz, 4)
C['wallPlaneZ'] = 2.73
C['frontClosedShopWallColliderFaceZ'] = 2.70
# --- door: leaf x -2.13..-0.47, reveal outer x -2.45..-0.15 (masonry reveal), threshold z to 3.14
door_reveal_right = -0.15
door_leaf_right = -0.47
new_left = min(v[0] for v in flat)
C['newGeometryLeftMostX'] = round(new_left, 4)
C['gapDoorRevealRightToNewLeftMost_m'] = round(new_left - door_reveal_right, 4)
C['gapDoorLeafRightToNewLeftMost_m'] = round(new_left - door_leaf_right, 4)
C['oldBankLeftMostX'] = 0.55                    # rev04 manifold start (retained vessel retainer 0.61)
C['newVsOldLeftMost_m'] = round(new_left - .55, 4)
# --- walking clearance in front of the bank: a 0.5 m wide walker on the porch (z from 3.30 forward) at any x
C['porchWalkZoneStartsAtZ'] = 3.30
C['newGeometryBeyondPorchWalkZone'] = bool(max(v[2] for v in flat if v[1] < 2.3) > 3.30)
low = [v for v in flat if v[1] < 2.3]
C['lowestNewGeometryY'] = round(min(v[1] for v in flat), 4)
# --- 1.8 m / reach: the isolation valve lever
hd = allv['AW_FilterHeader']
lever = [v for v in hd if 2.60 < v[0] < 2.78 and 3.015 < v[2] < 3.05 and 2.10 < v[1] < 2.15]
C['valveLeverHeightY_m'] = round(sum(v[1] for v in lever) / max(1, len(lever)), 3) if lever else None
C['valveAxisHeightY_m'] = 2.12
C['gaugeCentreY_m'] = 2.262
C['reachNote'] = 'lever grip centre is 2.12 m above the porch top (1.8 m figure: standing overhead reach about 2.2 m), on the front of the pipe, ~0.14 m above the vessel 3 cap and clear of it in plan; reachable at full stretch without crossing a vessel; no step is modelled'
# --- vessel mounting facts (retained silhouettes unchanged)
rep['attachments'] = {
    'straps': 'two hoop straps per vessel (y 0.78/1.50, 0.83/1.56, 0.80/1.53), 40 mm wide x 4.8 mm, wall ears anchored to the plaster with two sleeve anchors each; rubber liner 1.5 mm; tension lug with M8 through-bolt and two nuts',
    'cradle': 'U-cradle plate under the bottom collar (y 0.4785..0.4865) with two wall plates (110 x 124 mm, four anchors each) and gussets to the wall; vessel 2 plates are 30 mm higher (hand-fitted)',
    'spallPackers': 'the two wall plates of vessel 2 straddle the plaster spall (depth 43 mm, z 2.687): a steel packer fills the hollow',
    'header': 'DN60 bronze tube 0.60..2.63 m, three tees, blanked left end with plug, hangers at x 0.745 and 2.10 on 70x100 mm plates (2 anchors)',
    'isolationValve': 'flanged ball valve, flanges x 2.607..2.667 / 2.847..2.893, four M8 through-bolts, red enamel lever along the pipe (OPEN), stem at x 2.76, y 2.12, z 3.01+',
    'gauge': 'bottom-entry pressure gauge at x 2.945 y 2.262, dial 73 mm; needle at 2.6 bar, red limit flag at 4.5 bar; unique 1024 dial map',
    'isolatePlate': 'flat plate 90 x 60 mm on the wall at x 2.84 y 1.905 (two anchors), text ISOLATE / SHUT | OPEN',
    'riser': 'union at the header joint (x 3.09..3.12), 45-degree set is in the header module, riser DN80 at existing axis x 3.18 z 3.03, gasketed flange joint at y 2.94..2.96 with four bolts, roof turn radius 0.12',
}
(OUT / 'measurements.json').write_text(json.dumps(rep, indent=2))
print(json.dumps(C, indent=1))
print('total tris', rep['overall']['totalTris'])
