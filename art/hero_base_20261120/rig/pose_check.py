"""Hero base rig check (headless Blender 5.2, Cycles CPU). Usage: blender.sh pose_check.py -- <rig dir> [clip.glb ...]
1. rigged.glb at rest: bone list, finger bones, vertex-group coverage, and stress poses set by hand on the main joints
   (arms forward and raised, elbows bent, a deep knee bend, torso twist), rendered from the front and from behind
   because the player is mostly seen from behind.
2. Each clip GLB (walk, run, library clips): three frames rendered from the front quarter and the back quarter.
Writes renders/*.png and pose_check.json."""
import bpy, sys, json, math
from pathlib import Path
from mathutils import Vector, Matrix, Euler
import numpy as np
args = sys.argv[sys.argv.index('--') + 1:]
HERE = Path(args[0]); CLIPS = [Path(a) for a in args[1:]]
OUT = HERE / 'renders'; OUT.mkdir(exist_ok=True)
report = {}


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.render.engine = 'CYCLES'; s.cycles.device = 'CPU'; s.cycles.samples = 20; s.cycles.use_denoising = True
    s.view_settings.view_transform = 'AgX'
    w = bpy.data.worlds.new('w'); s.world = w; w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[0].default_value = (.55, .58, .62, 1); w.node_tree.nodes['Background'].inputs[1].default_value = .8
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); s.collection.objects.link(sun)
    sun.data.energy = 3.0; sun.rotation_euler = (math.radians(50), 0, math.radians(-35))
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); s.collection.objects.link(cam); s.camera = cam
    return s


def load(glb):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(glb))
    new = [o for o in bpy.data.objects if o not in before]
    arm = next((o for o in new if o.type == 'ARMATURE'), None)
    mesh = max((o for o in new if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
    return arm, mesh, new


def world_verts(mesh):
    dg = bpy.context.evaluated_depsgraph_get(); ev = mesh.evaluated_get(dg); me = ev.to_mesh()
    co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    mw = np.array(ev.matrix_world); co = co @ mw[:3, :3].T + mw[:3, 3]; ev.to_mesh_clear(); return co


def shoot(name, mesh, yaw_deg, lens=50, res=(560, 840)):
    s = bpy.context.scene; cam = s.camera; cam.data.lens = lens
    s.render.resolution_x, s.render.resolution_y = res
    bpy.context.view_layer.update(); co = world_verts(mesh); lo, hi = co.min(0), co.max(0)
    mid = Vector(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2)); H = max(float(hi[2] - lo[2]), 1.7)
    yaw = math.radians(yaw_deg); dist = H * 1.65
    cam.location = mid + Vector((math.sin(yaw) * dist, -math.cos(yaw) * dist, H * .08))
    cam.rotation_euler = (mid - cam.location).to_track_quat('-Z', 'Y').to_euler()
    s.render.filepath = str(OUT / f'{name}.png'); bpy.ops.render.render(write_still=True)


# ---- 1. rest + stress poses
s = reset()
arm, mesh, objs = load(HERE / 'rigged.glb')
if arm.animation_data: arm.animation_data.action = None
names = [b.name for b in arm.data.bones]
report['bones'] = names; report['bone_count'] = len(names)
report['finger_bones'] = [n for n in names if any(k in n.lower() for k in ('thumb', 'index', 'middle', 'ring', 'pinky', 'little', 'finger'))]
report['vertex_groups'] = len(mesh.vertex_groups)
used = set()
for v in mesh.data.vertices:
    for g in v.groups:
        if g.weight > .01: used.add(mesh.vertex_groups[g.group].name)
report['weighted_groups'] = len(used); report['bones_without_weights'] = sorted(set(names) - used)
co = world_verts(mesh); report['rest_height'] = round(float(co[:, 2].max() - co[:, 2].min()), 4)
report['triangles'] = sum(len(p.vertices) - 2 for p in mesh.data.polygons)
report['root'] = arm.name; report['armature_scale'] = [round(x, 4) for x in arm.scale]
pb = arm.pose.bones


def find(*cands):
    low = {n.lower(): n for n in names}
    for c in cands:
        if c.lower() in low: return pb[low[c.lower()]]
    return None


def rot_world(bone, axis, deg):
    """Rotate a pose bone about a WORLD axis through its head (rig-agnostic)."""
    if bone is None: return False
    bpy.context.view_layer.update()
    m = arm.matrix_world @ bone.matrix; head = m.to_translation()
    R = Matrix.Translation(head) @ Matrix.Rotation(math.radians(deg), 4, axis) @ Matrix.Translation(-head)
    bone.matrix = arm.matrix_world.inverted() @ R @ m
    bpy.context.view_layer.update(); return True


def clear():
    for b in pb: b.matrix_basis = Matrix()
    bpy.context.view_layer.update()


L = dict(arm=find('LeftArm', 'LeftUpperArm'), fore=find('LeftForeArm', 'LeftLowerArm'), up=find('LeftUpLeg', 'LeftUpperLeg'), leg=find('LeftLeg', 'LeftLowerLeg'), sh=find('LeftShoulder'))
Rr = dict(arm=find('RightArm', 'RightUpperArm'), fore=find('RightForeArm', 'RightLowerArm'), up=find('RightUpLeg', 'RightUpperLeg'), leg=find('RightLeg', 'RightLowerLeg'), sh=find('RightShoulder'))
spine = find('Spine1', 'Spine01', 'Spine')
report['found'] = {k: (v.name if v else None) for k, v in dict(l_arm=L['arm'], l_fore=L['fore'], l_up=L['up'], l_leg=L['leg'], spine=spine).items()}
X, Y, Z = 'X', 'Y', 'Z'
shoot('rest_front', mesh, 0); shoot('rest_back', mesh, 180)
# arms forward (aiming height): rotate the upper arms about world Z toward the front, then about X to level them
clear()
rot_world(L['arm'], Vector((0, 1, 0)), 35); rot_world(Rr['arm'], Vector((0, 1, 0)), -35)       # lift from the A-pose to horizontal
rot_world(L['arm'], Vector((0, 0, 1)), -80); rot_world(Rr['arm'], Vector((0, 0, 1)), 80)       # swing forward
shoot('stress_arms_forward_front', mesh, 30); shoot('stress_arms_forward_back', mesh, 150)
# arms overhead
clear()
rot_world(L['arm'], Vector((0, 1, 0)), 125); rot_world(Rr['arm'], Vector((0, 1, 0)), -125)
shoot('stress_arms_up_front', mesh, 0); shoot('stress_arms_up_back', mesh, 180)
# elbows bent 100 degrees with the arms slightly forward (carry), deep knee bend
clear()
rot_world(L['fore'], Vector((1, 0, 0)), -100); rot_world(Rr['fore'], Vector((1, 0, 0)), -100)
rot_world(L['up'], Vector((1, 0, 0)), -70); rot_world(L['leg'], Vector((1, 0, 0)), 95)
shoot('stress_elbows_knee_front', mesh, 35); shoot('stress_elbows_knee_side', mesh, 90)
# torso twist
clear(); rot_world(spine, Vector((0, 0, 1)), 40)
shoot('stress_twist_front', mesh, 0); shoot('stress_twist_back', mesh, 180)
clear()

# ---- 2. clips
report['clips'] = {}
for clip in CLIPS:
    s = reset()
    a2, m2, new = load(clip)
    act = a2.animation_data.action if a2 and a2.animation_data else None
    if not act: report['clips'][clip.stem] = 'no action'; continue
    f0, f1 = act.frame_range
    rec = {'frames': [f0, f1], 'bones': len(a2.data.bones)}
    for frac in (.2, .5, .8):
        f = int(f0 + (f1 - f0) * frac); s.frame_set(f)
        shoot(f'{clip.stem}_f{int(frac * 100)}_front', m2, 35); shoot(f'{clip.stem}_f{int(frac * 100)}_back', m2, 150)
    report['clips'][clip.stem] = rec
(HERE / 'pose_check.json').write_text(json.dumps(report, indent=1))
print('POSE OK', report['bone_count'], 'bones,', len(report['finger_bones']), 'finger bones,', report['triangles'], 'tris')
