"""Hero base: check renders of the exported player file (headless Blender 5.2, Cycles CPU).
Usage: blender.sh check_hero.py -- <colonist.glb> <out dir>
Imports the GLB as the engine will see it and renders: the rest pose (front, back quarter), a lit face close-up,
both hands with every finger joint curled +45 degrees about local X (the game's grip code does exactly that), a relaxed
curl of 15 degrees, and frames of the embedded idle, walk and run seen from the front quarter and from behind."""
import bpy, sys, math, json
from pathlib import Path
from mathutils import Vector, Matrix
import numpy as np
args = sys.argv[sys.argv.index('--') + 1:]
GLB = Path(args[0]); OUT = Path(args[1]); OUT.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
s = bpy.context.scene; s.render.fps = 30
s.render.engine = 'CYCLES'; s.cycles.device = 'CPU'; s.cycles.samples = 24; s.cycles.use_denoising = True
s.view_settings.view_transform = 'AgX'
w = bpy.data.worlds.new('w'); s.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs[0].default_value = (.55, .58, .62, 1); w.node_tree.nodes['Background'].inputs[1].default_value = .8
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); s.collection.objects.link(sun)
sun.data.energy = 3.0; sun.rotation_euler = (math.radians(50), 0, math.radians(-35))
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); s.collection.objects.link(cam); s.camera = cam
bpy.ops.import_scene.gltf(filepath=str(GLB), bone_heuristic='BLENDER')
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
mesh = max((o for o in bpy.data.objects if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
acts = {a.name: a for a in bpy.data.actions}
rep = {'armature': arm.name, 'mesh': mesh.name, 'bones': len(arm.data.bones), 'actions': {n: list(a.frame_range) for n, a in acts.items()},
       'materials': [m.name for m in mesh.data.materials], 'tris': sum(len(p.vertices) - 2 for p in mesh.data.polygons)}
if arm.animation_data:
    arm.animation_data.action = None
    for t in arm.animation_data.nla_tracks: t.mute = True


def verts():
    dg = bpy.context.evaluated_depsgraph_get(); ev = mesh.evaluated_get(dg); me = ev.to_mesh()
    co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    mw = np.array(ev.matrix_world); co = co @ mw[:3, :3].T + mw[:3, 3]; ev.to_mesh_clear(); return co


def shoot(name, target, dist, yaw_deg, pitch_deg=0, lens=50, res=(560, 840)):
    cam.data.lens = lens; s.render.resolution_x, s.render.resolution_y = res
    yaw = math.radians(yaw_deg); p = math.radians(pitch_deg)
    cam.location = Vector(target) + Vector((math.sin(yaw) * math.cos(p) * dist, -math.cos(yaw) * math.cos(p) * dist, math.sin(p) * dist))
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    s.render.filepath = str(OUT / f'{name}.png'); bpy.ops.render.render(write_still=True)


def reset_pose():
    for pb in arm.pose.bones: pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()


def body(name, yaw):
    co = verts(); lo, hi = co.min(0), co.max(0); mid = (lo + hi) / 2; H = max(float(hi[2] - lo[2]), 1.7)
    shoot(name, mid, H * 1.65, yaw)


def bone(n): return arm.matrix_world @ arm.pose.bones[n].head


reset_pose(); co = verts(); lo, hi = co.min(0), co.max(0); H = float(hi[2] - lo[2]); rep['rest_height'] = round(H, 4); rep['rest_low'] = round(float(lo[2]), 4)
body('rest_front', 0); body('rest_back', 150)
hd = bone('Head'); shoot('face_lit', (hd.x, hd.y, hd.z + .09), .75, 0, lens=85, res=(900, 900)); shoot('face_lit_q', (hd.x, hd.y, hd.z + .09), .75, 40, lens=85, res=(900, 900))
FING = [f'{d}_0{j}_{sd}' for sd in 'lr' for d in ('index', 'middle', 'ring', 'pinky', 'thumb') for j in (1, 2, 3)]
for tag, ang in (('fist45', 45), ('relaxed15', 15)):
    reset_pose()
    for n in FING:
        pb = arm.pose.bones[n]; pb.rotation_mode = 'XYZ'; pb.rotation_euler = (math.radians(ang * (.55 if n.startswith('thumb') else 1)), 0, 0)
    bpy.context.view_layer.update()
    for sd, side in (('l', 'Left'), ('r', 'Right')):
        c = (bone(side + 'Hand') + bone(f'middle_02_{sd}')) / 2
        sign = 1 if sd == 'l' else -1
        shoot(f'hand_{sd}_{tag}_out', c, .42, 90 * sign, 15, lens=70, res=(700, 700))      # from outside the hand
        shoot(f'hand_{sd}_{tag}_front', c, .42, 20 * sign, 5, lens=70, res=(700, 700))     # from the front (palm side in A-pose)
reset_pose()
for n, a in acts.items():
    arm.animation_data.action = a; f0, f1 = a.frame_range
    for frac in (0.0, .25, .5, .75):
        s.frame_set(int(round(f0 + (f1 - f0) * frac))); bpy.context.view_layer.update()
        body(f'{n}_f{int(frac * 100):02d}_front', 35); body(f'{n}_f{int(frac * 100):02d}_back', 160)
    arm.animation_data.action = None; reset_pose()
(OUT / 'check.json').write_text(json.dumps(rep, indent=1)); print('CHECK OK', json.dumps(rep))
