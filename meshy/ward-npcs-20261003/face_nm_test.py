import bpy, sys, math
from mathutils import Vector
args = sys.argv[sys.argv.index('--') + 1:]
import numpy as np
src=open('/home/teknetik/code/ao2/meshy/ward-npcs-20261003/inspect_npc.py').read()
exec(src[src.index('def reset'):src.index('s = reset()')])
s = reset(); arm, mesh, objs = load(args[0])
import numpy as np
co = world_verts(mesh); lo, hi = co.min(0), co.max(0); H = hi[2]-lo[2]; cx, cy = (lo[0]+hi[0])/2, (lo[1]+hi[1])/2
hz = lo[2] + H*.93
OUT = __import__('pathlib').Path(args[1]); WHICH='nm'
def shot(name):
    cam = s.camera; cam.data.lens = 85; s.render.resolution_x = s.render.resolution_y = 900
    cam.location = Vector((cx+.15, cy-.75, hz)); cam.rotation_euler = (Vector((cx, cy, hz-.02)) - cam.location).to_track_quat('-Z','Y').to_euler()
    s.render.filepath = str(OUT / name); bpy.ops.render.render(write_still=True)
shot('face_nm_on.png')
mat = mesh.data.materials[0]; nt = mat.node_tree
bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
for l in list(bsdf.inputs['Normal'].links): nt.links.remove(l)
shot('face_nm_off.png')
