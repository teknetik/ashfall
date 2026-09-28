"""Report dimensions/triangles (and mesh-object names) of the downloaded Poly Haven models."""
import bpy, glob, json
from pathlib import Path
from mathutils import Vector
ROOT = Path(__file__).parent if '__file__' in dir() else Path('.')
ROOT = Path('/home/teknetik/code/ao2/art/ward_retrofit_20260926')
out = {}
for d in sorted((ROOT / 'sources/polyhaven').iterdir()):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glob.glob(str(d / '*.gltf'))[0])
    ms = [o for o in bpy.data.objects if o.type == 'MESH']
    pts = [o.matrix_world @ Vector(c) for o in ms for c in o.bound_box]
    mn = Vector(map(min, *pts)); mx = Vector(map(max, *pts))
    out[d.name] = dict(dims=[round(v, 2) for v in mx - mn], tris=sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in ms),
                       parts=[o.name for o in ms][:14], nparts=len(ms))
(ROOT / 'source-audit.json').write_text(json.dumps(out, indent=1))
