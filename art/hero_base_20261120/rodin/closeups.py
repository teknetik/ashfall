"""Hero base close-ups (headless Blender 5.2, Cycles CPU). Usage: blender.sh closeups.py -- <glb> <out dir> [prefix]
Flat-lit base-colour views (emission, no lighting) of the face and both hands, plus lit views of the hands, torso and
boots, so texture defects can be told apart from shading. Front of the model is -Y after glTF import."""
import bpy, sys, math
from pathlib import Path
from mathutils import Vector
import numpy as np
args = sys.argv[sys.argv.index('--') + 1:]
GLB = Path(args[0]); OUT = Path(args[1]); OUT.mkdir(parents=True, exist_ok=True); PRE = args[2] if len(args) > 2 else 'cu'

bpy.ops.wm.read_factory_settings(use_empty=True)
s = bpy.context.scene
s.render.engine = 'CYCLES'; s.cycles.device = 'CPU'; s.cycles.samples = 24; s.cycles.use_denoising = True
s.view_settings.view_transform = 'Standard'
w = bpy.data.worlds.new('w'); s.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs[0].default_value = (.55, .58, .62, 1); w.node_tree.nodes['Background'].inputs[1].default_value = .9
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); s.collection.objects.link(sun)
sun.data.energy = 2.5; sun.rotation_euler = (math.radians(55), 0, math.radians(-30))
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); s.collection.objects.link(cam); s.camera = cam
bpy.ops.import_scene.gltf(filepath=str(GLB))
mesh = max((o for o in bpy.data.objects if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
dg = bpy.context.evaluated_depsgraph_get(); ev = mesh.evaluated_get(dg); me = ev.to_mesh()
co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
mw = np.array(ev.matrix_world); co = co @ mw[:3, :3].T + mw[:3, 3]; ev.to_mesh_clear()
lo, hi = co.min(0), co.max(0); H = float(hi[2] - lo[2]); cx = float((lo[0] + hi[0]) / 2); cy = float((lo[1] + hi[1]) / 2)
# hands: the vertices furthest out in X on each side
lh = co[co[:, 0] > hi[0] - .16]; rh = co[co[:, 0] < lo[0] + .16]
hand_l = lh.mean(0); hand_r = rh.mean(0)
print('CLOSEUP bounds', lo.round(3).tolist(), hi.round(3).tolist(), 'hands', hand_l.round(3).tolist(), hand_r.round(3).tolist())

mat = mesh.data.materials[0]; nt = mat.node_tree
bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'); out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
base_link = bsdf.inputs['Base Color'].links[0].from_socket
emit = nt.nodes.new('ShaderNodeEmission'); nt.links.new(base_link, emit.inputs['Color'])


def mode(flat):
    nt.links.new((emit if flat else bsdf).outputs[0], out.inputs['Surface'])


def shoot(name, target, dist, yaw_deg, pitch_deg=0, lens=85, res=(900, 900)):
    cam.data.lens = lens; s.render.resolution_x, s.render.resolution_y = res
    yaw = math.radians(yaw_deg); p = math.radians(pitch_deg)
    off = Vector((math.sin(yaw) * math.cos(p) * dist, -math.cos(yaw) * math.cos(p) * dist, math.sin(p) * dist))
    cam.location = Vector(target) + off
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    s.render.filepath = str(OUT / f'{PRE}_{name}.png'); bpy.ops.render.render(write_still=True)


headz = lo[2] + H * .925
mode(True)
shoot('face_flat', (cx, cy, headz), .75, 0, lens=85, res=(1024, 1024))
shoot('face_flat_l', (cx, cy, headz), .75, 55, lens=85, res=(1024, 1024))
shoot('face_flat_r', (cx, cy, headz), .75, -55, lens=85, res=(1024, 1024))
shoot('hand_l_flat', hand_l, .55, 60, 10)
shoot('hand_r_flat', hand_r, .55, -60, 10)
mode(False)
shoot('face_lit', (cx, cy, headz), .75, 0, lens=85, res=(1024, 1024))
shoot('hand_l_lit', hand_l, .55, 60, 10)
shoot('hand_l_back_lit', hand_l, .55, 150, 10)
shoot('torso_lit', (cx, cy, lo[2] + H * .68), 1.6, 20, 5, lens=60)
shoot('boots_lit', (cx, cy, lo[2] + H * .07), 1.3, 25, 15, lens=60)
print('CLOSEUP OK')
