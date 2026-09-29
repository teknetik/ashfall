"""Probe the saved-scene source of Air + Water (surface-pass v2 blend, Unity-world coordinates) around the filter bank.
A-space mapping (verified by canister centres): xA = 9 - By, yA = Bz - 0.5, zA = Bx + 20.6.
"""
import bpy, json, math
from mathutils import Vector

dg = None
HIDE = ('Filter canister', 'Filter manifold', 'Filter retainer', 'Filter wall mount', 'Roof to filter', 'Feed ', 'Awning', 'Lower awning', 'Pipe clamp', 'Rainwater pipe')
hidden = []
for o in bpy.data.objects:
    if any(k in o.name for k in HIDE):
        o.hide_viewport = True
        hidden.append(o.name)
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
sc = bpy.context.scene


def A(v):
    return (round(9 - v.y, 4), round(v.z - .5, 4), round(v.x + 20.6, 4))


res = {}
zs = []
rows = []
for yA in [0.2 + .1 * i for i in range(0, 25)]:
    row = []
    for xA in [0.3 + .1 * i for i in range(0, 32)]:
        o = Vector((-20.6 + 6.0, 9 - xA, yA + .5))
        d = Vector((-1, 0, 0))
        hit, loc, nrm, idx, ob, mat = sc.ray_cast(dg, o, d, distance=12)
        if hit:
            row.append((round(loc.x + 20.6, 4), ob.name))
        else:
            row.append((None, None))
    rows.append(row)
allz = [z for r in rows for z, n in r if z is not None]
print('wall-face z samples', len(allz), 'min', min(allz), 'max', max(allz), 'mean', round(sum(allz) / len(allz), 4))
from collections import Counter
print(Counter(n for r in rows for z, n in r if n).most_common(8))
# histogram of face z
h = Counter(round(z, 2) for z in allz)
print(sorted(h.items()))
# z along the vessel centre lines at three heights
for xA in (.9, 1.7, 2.5, 1.3, 2.1, 2.9):
    for yA in (.5, .9, 1.3, 1.7, 2.1):
        o = Vector((-14.6, 9 - xA, yA + .5))
        hit, loc, nrm, idx, ob, mat = sc.ray_cast(dg, o, Vector((-1, 0, 0)), distance=12)
        print('face at x', xA, 'y', yA, '->', round(loc.x + 20.6, 4) if hit else None, ob.name if hit else '')
# ground / porch / step in front: rays downward at several z values
for xA in (0.2, 0.9, 1.7, 2.5, 3.2):
    for zA in (2.9, 3.3, 3.6, 4.2, 5.0):
        o = Vector((zA - 20.6, 9 - xA, 3.0))
        hit, loc, nrm, idx, ob, mat = sc.ray_cast(dg, o, Vector((0, 0, -1)), distance=8)
        print('ground at x', xA, 'z', zA, '->', round(loc.z - .5, 4) if hit else None, ob.name if hit else '')
# everything in front of the wall near the bank (unhide to list)
for n in hidden:
    bpy.data.objects[n].hide_viewport = False
print('--- objects intersecting box x[-0.2,3.5] y[0,2.5] z[2.7,4.6]')
for o in bpy.data.objects:
    if o.type != 'MESH' or 'air_water' not in o.name:
        continue
    bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
    xa = [9 - v.y for v in bb]; ya = [v.z - .5 for v in bb]; za = [v.x + 20.6 for v in bb]
    if max(xa) > -.2 and min(xa) < 3.5 and max(ya) > 0 and min(ya) < 2.5 and max(za) > 2.7 and min(za) < 4.6 and 'anchor' not in o.name:
        print(o.name, [round(min(xa), 3), round(min(ya), 3), round(min(za), 3)], [round(max(xa), 3), round(max(ya), 3), round(max(za), 3)], len(o.data.polygons))
