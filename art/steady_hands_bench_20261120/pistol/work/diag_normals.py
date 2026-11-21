# Faces that can be seen from outside and point inward (they would be culled in Unity): staged build against the
# accepted one. A face is flagged when a ray along its normal crosses its own part an odd number of times and a ray
# against its normal escapes.
import bpy, sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'kit'))
import measure as ME
from mathutils import Vector

def crossings(tree, org, d):
    n = 0
    o = org + d * 2e-6
    for _ in range(60):
        h = tree.ray_cast(o, d, 2.0)
        if h[0] is None:
            break
        n += 1; o = h[0] + d * 2e-6
    return n

out = {}
for tag, blend in (('staged', sys.argv[sys.argv.index('--') + 1]), ('accepted', os.path.join(HERE, 'baseline_1755', 'pistol_accepted.blend'))):
    if not os.path.exists(blend):
        print('NORMALS', tag, 'no file', blend); continue
    bpy.ops.wm.open_mainfile(filepath=blend)
    parts = [o for o in bpy.data.objects if o.type == 'MESH' and 'sh_id' in o]
    res = {}
    for o in sorted(parts, key=lambda x: x.name):
        tree, _ = ME.world_bvh([o])
        mw = o.matrix_world; nm = mw.to_3x3().inverted().transposed()
        bad = 0; area = 0.0; tot = 0.0; ex = []
        for p in o.data.polygons:
            c = mw @ p.center; n = (nm @ p.normal).normalized()
            tot += p.area
            if crossings(tree, c, n) % 2 == 1 and crossings(tree, c, -n) == 0:
                bad += 1; area += p.area
                if len(ex) < 3:
                    ex.append([round(x * 1000, 1) for x in c])
        res[o.name] = {'faces': len(o.data.polygons), 'flipped_seen': bad, 'area_mm2': round(area * 1e6, 2), 'share': round(area / max(tot, 1e-12), 4), 'at_mm': ex}
        if bad:
            print('NORMALS', tag, o.name, res[o.name], flush=True)
    print('NORMALS', tag, 'total flipped and seen:', sum(v['flipped_seen'] for v in res.values()), 'of', sum(v['faces'] for v in res.values()), flush=True)
    out[tag] = res
json.dump(out, open(os.path.join(HERE, 'diag_normals.json'), 'w'), indent=1)
