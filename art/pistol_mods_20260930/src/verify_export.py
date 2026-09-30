# Re-import check: PistolMods.glb next to ScrapPistol.glb (both via Blender's glTF importer), mods root scaled by the
# pistol's in-game 0.13674, compared against the metric source objects saved in source/pistol_mods_v1.blend.
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
import pm_common as C

ART = C.ART
bpy.ops.wm.open_mainfile(filepath=ART + 'source/pistol_mods_v1.blend')
names = ['grip_stabilised_pistol', 'grip_gyro_braced', 'barrel_bored_alloy', 'barrel_lattice_focused', 'cell_salvaged_capacitor', 'cell_overclocked']
src = {n: bpy.data.objects[n] for n in names}
g = bpy.data.node_groups.get('glTF Material Output')
if g:  # our export-only group lacks the importer's sockets; keep it out of the importer's way
    g.name = 'glTF Material Output (export)'
for o in src.values():
    o.name = 'SRC_' + o.name
pist = C.import_pistol()
new = C.import_glb(ART + 'export/PistolMods.glb')
for o in new:
    if o.parent is None:
        o.matrix_world = Matrix.Scale(C.S, 4) @ o.matrix_world
bpy.context.view_layer.update()
res = {}
for n in names:
    o = bpy.data.objects[n]
    s = src[n]
    bm = bmesh.new(); bm.from_mesh(s.data); bm.transform(s.matrix_world)
    tree = BVHTree.FromBMesh(bm); bm.free()
    dmax = 0.0
    for v in o.data.vertices:
        p = o.matrix_world @ v.co
        dmax = max(dmax, tree.find_nearest(p)[3])
    res[n] = {'node_parent': o.parent.name if o.parent else None, 'local_matrix_identity': o.matrix_local == Matrix.Identity(4) or o.parent is None,
              'tris': sum(len(p.vertices) - 2 for p in o.data.polygons), 'materials': [m.name for m in o.data.materials],
              'max_dev_mm_vs_source': round(dmax * 1000, 4), 'has_uv': len(o.data.uv_layers) > 0}
    print('VERIFY', n, res[n])
json.dump(res, open(ART + 'export/verify_reimport.json', 'w'), indent=1)
