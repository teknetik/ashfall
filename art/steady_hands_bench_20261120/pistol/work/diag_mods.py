# Which part of the pistol do the other mods' vertices sit inside, and how deep? Staged build against the accepted one.
import bpy, sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..')); sys.path.insert(0, os.path.join(HERE, '..', '..', 'kit'))      # the kit first: pistol/ has its own measure.py
import measure as ME
import pframe as PF
from mathutils import Vector

out = {}
for tag, blend in (('staged', os.path.join(HERE, 'stage', 'pistol', 'export', 'pistol.blend')), ('accepted', os.path.join(HERE, '..', 'export', 'pistol.blend'))):
    bpy.ops.wm.open_mainfile(filepath=blend)
    parts = [o for o in bpy.data.objects if o.type == 'MESH' and 'sh_id' in o and 'card' not in o.name]
    trees = {o.name: ME.world_bvh([o])[0] for o in parts}
    alltree, _ = ME.world_bvh(parts)
    mods = PF.import_mods()
    res = {}
    for nm, o in sorted(mods.items()):
        V = [o.matrix_world @ v.co for v in o.data.vertices]
        rows = []
        for p in V:
            nn = alltree.find_nearest(p, 0.03)
            if nn[0] is None:
                continue
            if (p - nn[0]).dot(nn[1]) < 0 and nn[3] > 0.0003:
                best = None
                for n, t in trees.items():
                    q = t.find_nearest(p, 0.03)
                    if q[0] is not None and (best is None or q[3] < best[1]):
                        best = (n, q[3], q[1])
                # is the point really inside that part? count crossings of a ray
                t = trees[best[0]]
                hits = 0
                org = Vector(p); d = Vector((0.317, 0.611, 0.725)).normalized()
                for _ in range(40):
                    h = t.ray_cast(org, d, 1.0)
                    if h[0] is None:
                        break
                    hits += 1; org = h[0] + d * 1e-6
                rows.append((round(nn[3] * 1000, 2), best[0], hits % 2 == 1, [round(x * 1000, 1) for x in p]))
        rows.sort(reverse=True)
        byp = {}
        for r in rows:
            k = (r[1], r[2]); byp[k] = byp.get(k, 0) + 1
        res[nm] = {'count': len(rows), 'by_part_and_really_inside': {'%s inside=%s' % k: v for k, v in byp.items()}, 'deepest': rows[:6]}
        print('DIAG', tag, nm, len(rows), {'%s inside=%s' % k: v for k, v in byp.items()}, rows[:4], flush=True)
    out[tag] = res
json.dump(out, open(os.path.join(HERE, 'diag_mods.json'), 'w'), indent=1)
