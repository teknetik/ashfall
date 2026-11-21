# Orchestrator, 20 Nov 2026: which albedo reads as the look target's Warden orange under the kit's review rigs?
# Eight flat painted plates (linear albedo candidates), a bare alloy plate and a white card, neutral and warm rigs.
import sys, os, json, bpy
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'kit'))
import review as RV
from mathutils import Vector
CANDS = [('kit_original', (0.296, 0.069, 0.012)), ('seam8_bad', (0.60, 0.20, 0.076)), ('c3', (0.40, 0.085, 0.012)),
         ('c4', (0.50, 0.10, 0.012)), ('c5', (0.45, 0.12, 0.020)), ('c6', (0.35, 0.10, 0.020)), ('c7', (0.55, 0.14, 0.020)),
         ('c8', (0.42, 0.11, 0.035)), ('alloy', (0.55, 0.53, 0.50)), ('white', (0.80, 0.80, 0.80))]
warm = '--warm' in sys.argv
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = RV.studio(samples=32, res=(1600, 400), ground_z=0.0, ground_col=(0.02, 0.02, 0.021), warm=warm)
pos = {}
for i, (name, col) in enumerate(CANDS):
    x = (i - (len(CANDS) - 1) / 2) * 0.05
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, 0, 0.001)); o = bpy.context.active_object
    o.scale = (0.04, 0.04, 0.002); o.name = name
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*col, 1); b.inputs['Roughness'].default_value = 0.5 if name == 'alloy' else 0.58
    b.inputs['Metallic'].default_value = 1.0 if name == 'alloy' else 0.0
    o.data.materials.append(m); pos[name] = x
cam = RV.look_cam('cam', (0, 0, 0), (0, -0.28, 0.42), lens=50)
out = os.path.join(HERE, ('warm' if warm else 'neutral') + '.png')
RV.render(out, cam)
# where each plate's centre lands in the picture
from bpy_extras.object_utils import world_to_camera_view
px = {n: [round(world_to_camera_view(sc, cam, Vector((x, 0, 0.002))).x * 1600), round((1 - world_to_camera_view(sc, cam, Vector((x, 0, 0.002))).y) * 400)] for n, x in pos.items()}
json.dump({'cands': CANDS, 'px': px}, open(os.path.join(HERE, ('warm' if warm else 'neutral') + '.json'), 'w'), indent=1)
print('WROTE', out)
