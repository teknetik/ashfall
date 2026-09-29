import bpy, json, math
from mathutils import Vector
sc = bpy.context.scene
o = bpy.data.objects['air_water Filter canister 0.9']
dg = bpy.context.evaluated_depsgraph_get()
prof = {}
for v in o.data.vertices:
    w = o.matrix_world @ v.co
    xA, yA, zA = 9 - w.y, w.z - .5, w.x + 20.6
    r = math.hypot(xA - .9, zA - 2.93)
    k = round(yA, 3)
    prof.setdefault(k, []).append(r)
print('canister profile (yA: min/max r)')
for k in sorted(prof):
    rs = prof[k]
    print(k, round(min(rs), 4), round(max(rs), 4), len(rs))
# retainers & brass lids
for n in ('air_water Filter retainer (0.9, 0.52)', 'air_water Filter retainer (0.9, 1.94)', 'air_water Filter wall mount 0.9'):
    ob = bpy.data.objects[n]
    pr = {}
    for v in ob.data.vertices:
        w = ob.matrix_world @ v.co
        xA, yA, zA = 9 - w.y, w.z - .5, w.x + 20.6
        pr.setdefault(round(yA, 3), []).append(math.hypot(xA - .9, zA - 2.93))
    print(n, {k: (round(min(v), 3), round(max(v), 3)) for k, v in sorted(pr.items())})
# wall face map over the bank
bad = []
sc_ = bpy.context.scene
for yA in [0.2 + .05 * i for i in range(0, 50)]:
    for xA in [0.3 + .05 * i for i in range(0, 66)]:
        og = Vector((-14.6, 9 - xA, yA + .5))
        hit, loc, nrm, idx, ob, mat = sc_.ray_cast(dg, og, Vector((-1, 0, 0)), distance=12)
        if hit and ob.name.startswith('air_water Front masonry'):
            z = loc.x + 20.6
            if abs(z - 2.73) > .004:
                bad.append((round(xA, 2), round(yA, 2), round(z, 3)))
print('non-2.73 wall samples', len(bad))
print(bad)
# bumps: what else sits proud of wall in the bank zone (decals/projectors are prefab-only)
