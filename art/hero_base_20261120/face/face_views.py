"""Hero face pass, step 1 (headless Blender 5.2, Cycles CPU): orthographic flat base-colour views of the head.
Usage: blender.sh face_views.py -- <model.glb> <out dir> [--ortho 0.28] [--dz -0.014] [--diffuse override.png]
Writes view_<name>.png (2048 x 2048, emission only, no lighting) and cams.json (camera matrices and ortho scale) so the
repainted images can be projected back through exactly the same cameras by face_project.py."""
import bpy, sys, json, math
from pathlib import Path
from mathutils import Vector
import numpy as np
args = sys.argv[sys.argv.index('--') + 1:]
GLB = Path(args[0]); OUT = Path(args[1]); OUT.mkdir(parents=True, exist_ok=True)
OVERRIDE = Path(args[args.index('--diffuse') + 1]) if '--diffuse' in args else None
RES = 2048
ORTHO = float(args[args.index('--ortho') + 1]) if '--ortho' in args else 0.42
DZ = float(args[args.index('--dz') + 1]) if '--dz' in args else 0.0
VIEWS = {'front': 0, 'left45': 45, 'right45': -45}   # yaw in degrees; the model's front is -Y after import
if '--views' in args:   # e.g. --views front:0,left100:100,back:180
    VIEWS = {k: float(v) for k, v in (kv.split(':') for kv in args[args.index('--views') + 1].split(','))}
if '--res' in args: RES = int(args[args.index('--res') + 1])

bpy.ops.wm.read_factory_settings(use_empty=True)
s = bpy.context.scene
s.render.engine = 'CYCLES'; s.cycles.device = 'CPU'; s.cycles.samples = 16; s.cycles.use_denoising = False
s.cycles.filter_width = 1.0
s.view_settings.view_transform = 'Standard'; s.render.film_transparent = True
s.render.image_settings.file_format = 'PNG'; s.render.image_settings.color_mode = 'RGBA'
w = bpy.data.worlds.new('w'); s.world = w
bpy.ops.import_scene.gltf(filepath=str(GLB))
mesh = max((o for o in bpy.data.objects if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
co = np.empty(len(mesh.data.vertices) * 3, np.float32); mesh.data.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
mw = np.array(mesh.matrix_world); co = co @ mw[:3, :3].T + mw[:3, 3]
lo, hi = co.min(0), co.max(0); H = float(hi[2] - lo[2])
# head centre: the vertices in the top 14 % of the height
head = co[co[:, 2] > lo[2] + H * .86]
hc = Vector((float((head[:, 0].min() + head[:, 0].max()) / 2), float((head[:, 1].min() + head[:, 1].max()) / 2), float(lo[2] + H * .915) + DZ))

mat = mesh.data.materials[0]; nt = mat.node_tree
bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'); out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
base = bsdf.inputs['Base Color'].links[0].from_node
if OVERRIDE:
    base.image = bpy.data.images.load(str(OVERRIDE)); base.image.colorspace_settings.name = 'sRGB'
emit = nt.nodes.new('ShaderNodeEmission'); nt.links.new(base.outputs['Color'], emit.inputs['Color'])
nt.links.new(emit.outputs[0], out.inputs['Surface'])

cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); s.collection.objects.link(cam); s.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = ORTHO; cam.data.clip_start = .01; cam.data.clip_end = 10
s.render.resolution_x = s.render.resolution_y = RES; s.render.resolution_percentage = 100
rec = {'res': RES, 'ortho_scale': ORTHO, 'head_centre': list(hc), 'height': H, 'low_z': float(lo[2]), 'views': {}}
for name, yaw_deg in VIEWS.items():
    yaw = math.radians(yaw_deg)
    cam.location = hc + Vector((math.sin(yaw) * 2.0, -math.cos(yaw) * 2.0, 0))
    cam.rotation_euler = (hc - cam.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.view_layer.update()
    s.render.filepath = str(OUT / f'view_{name}.png'); bpy.ops.render.render(write_still=True)
    rec['views'][name] = {'yaw': yaw_deg, 'matrix_world': [list(r) for r in cam.matrix_world]}
(OUT / 'cams.json').write_text(json.dumps(rec, indent=1))
print('VIEWS OK', rec['head_centre'])
