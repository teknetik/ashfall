import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'kit'))
import bpy
from mathutils import Vector
import review as RV, measure as ME
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=os.path.join(HERE, '..', 'export', 'pistol.glb'))
cfg = json.load(open(os.path.join(HERE, '..', 'export', 'review.json')))
objs = [o for o in bpy.data.objects if o.type == 'MESH' and o.name not in cfg['hide']]
print('MESHES', [o.name for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith('pistol_')], flush=True)
lo, hi = ME.bounds(objs); print('REST', [round(float(x), 3) for x in lo], [round(float(x), 3) for x in hi], flush=True)
r = RV.explode(objs, 1.0, {k: Vector(v) for k, v in cfg['explode']['extra'].items()})
for o in objs:
    a, b = ME.bounds([o])
    if max(abs(float(x)) for x in list(a) + list(b)) > 0.3:
        print('FAR', o.name, [round(float(x), 3) for x in a], [round(float(x), 3) for x in b], 'parent', o.parent.name if o.parent else None, flush=True)
lo, hi = ME.bounds(objs); print('EXPLODED', [round(float(x), 3) for x in lo], [round(float(x), 3) for x in hi], flush=True)
