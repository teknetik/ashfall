"""Rig and animate the Meshy mining droid (meshy/mining-droid-20260926/model.glb) for Unity legacy playback.

Run:  blender -b --factory-startup -P rig_droid.py
Writes unity/AthenHill/Assets/AthenHill/Art/WardRetrofit/MiningDroid.glb and mining-droid-rig.blend.

Meshy auto-rigging supports humanoid bipeds only, so this quadruped gets a hand-built rig. It is a hard-surface
machine, so skinning is rigid (each vertex follows exactly one bone): Body, and per leg a swing bone pivoting at
the knee disc plus a foot bone that keeps the pad level. Actions: 'walk' (diagonal-pair trot, 1.2 s loop, foot lift,
body drop that keeps stance feet planted) and 'idle' (servo settle / slow body sway). Uniformly scaled to 3.4 m tall;
front (lens) faces glTF +Z = Unity forward.
"""
import bpy, math, json
import numpy as np
from mathutils import Vector, Matrix
from pathlib import Path

SRC = Path('/home/teknetik/code/ao2/meshy/mining-droid-20260926/model.glb')
OUT = Path('/home/teknetik/code/ao2/unity/AthenHill/Assets/AthenHill/Art/WardRetrofit/MiningDroid.glb')
ROOT = Path('/home/teknetik/code/ao2/art/ward_retrofit_20260926')
HEIGHT = 3.4
FPS, WALK_FRAMES, IDLE_FRAMES = 30, 36, 96
SWING = math.radians(17)   # leg swing amplitude
LIFT = .12                 # foot lift during swing (m)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene; scene.render.fps = FPS
bpy.ops.import_scene.gltf(filepath=str(SRC))
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
for o in meshes:
    mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
for o in [o for o in bpy.data.objects if o.type != 'MESH']: bpy.data.objects.remove(o)
bpy.ops.object.select_all(action='DESELECT')
for o in meshes: o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
if len(meshes) > 1: bpy.ops.object.join()
body = bpy.context.view_layer.objects.active; body.name = 'MiningDroid'; body.rotation_mode = 'XYZ'
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# source-space classification (thresholds measured from slices of the Meshy mesh; front legs y<0)
Vs = np.array([v.co[:] for v in body.data.vertices])
mn, mx = Vs.min(0), Vs.max(0)
s = HEIGHT / (mx[2] - mn[2])
LEGS = {'FL': (-1, -1), 'FR': (1, -1), 'RL': (-1, 1), 'RR': (1, 1)}   # (sign x, sign y); -y = front


def leg_of(p):
    x, y, z = p
    if z < -.3 and abs(x) > .12: return ('R' if y > 0 else 'F') + ('L' if x < 0 else 'R')
    if z < .12 and abs(x) > .38 and abs(abs(y) - .55) < .33: return ('R' if y > 0 else 'F') + ('L' if x < 0 else 'R')
    return None


assign = []
for p in Vs:
    lg = leg_of(p)
    assign.append('Body' if lg is None else (('Foot_' if p[2] < -.8 else 'Leg_') + lg))
# knee pivots: centre of each leg's knee-disc vertices
pivots = {}
for k, (sx, sy) in LEGS.items():
    pts = np.array([p for p, a in zip(Vs, assign) if a == 'Leg_' + k and p[2] > -.32])
    if len(pts) < 20: pts = np.array([p for p, a in zip(Vs, assign) if a == 'Leg_' + k])
    lo, hi = pts.min(0), pts.max(0)
    pivots[k] = Vector(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2 if len(pts) else -.1))
ankles = {}
for k in LEGS:
    pts = np.array([p for p, a in zip(Vs, assign) if a == 'Foot_' + k])
    lo, hi = pts.min(0), pts.max(0)
    ankles[k] = Vector(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, hi[2]))

# normalise: uniform scale, feet on z=0, centred in plan
M = Matrix.Translation((-(mn[0] + mx[0]) / 2 * s, -(mn[1] + mx[1]) / 2 * s, -mn[2] * s)) @ Matrix.Scale(s, 4)
body.data.transform(M)
pivots = {k: M @ v for k, v in pivots.items()}; ankles = {k: M @ v for k, v in ankles.items()}
counts = {n: assign.count(n) for n in set(assign)}

# armature
arm_data = bpy.data.armatures.new('MiningDroidRig'); arm = bpy.data.objects.new('MiningDroidRig', arm_data)
scene.collection.objects.link(arm); bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
eb = arm_data.edit_bones
root = eb.new('Root'); root.head = (0, 0, 0); root.tail = (0, .5, 0)
bb = eb.new('Body'); bb.head = (0, 0, HEIGHT * .55); bb.tail = (0, 0, HEIGHT * .75); bb.parent = root
for k in LEGS:
    lb = eb.new('Leg_' + k); lb.head = pivots[k]; lb.tail = ankles[k]; lb.parent = bb; lb.roll = 0
    fb = eb.new('Foot_' + k); fb.head = ankles[k]; fb.tail = ankles[k] - Vector((0, 0, ankles[k].z * .9)); fb.parent = lb; fb.use_connect = False
bpy.ops.object.mode_set(mode='OBJECT')

for n in ['Body'] + [p + k for k in LEGS for p in ('Leg_', 'Foot_')]:
    body.vertex_groups.new(name=n)
groups = {g.name: g for g in body.vertex_groups}
by = {}
for i, a in enumerate(assign): by.setdefault(a, []).append(i)
for a, idx in by.items(): groups[a].add(idx, 1.0, 'REPLACE')
body.parent = arm
mod = body.modifiers.new('Armature', 'ARMATURE'); mod.object = arm

# ---------------------------------------------------------------- animation
arm.animation_data_create()
pb = arm.pose.bones
for b in pb: b.rotation_mode = 'XYZ'
PHASE = {'FL': 0., 'RR': 0., 'FR': .5, 'RL': .5}   # trot: diagonal pairs move together


def leg_axis_sign():
    """Which rotation sign about the leg bone's local X swings the foot toward the front (-Y)?"""
    b = pb['Leg_FL']; b.rotation_euler = (.3, 0, 0); bpy.context.view_layer.update()
    y = (arm.matrix_world @ b.tail).y
    b.rotation_euler = (0, 0, 0); bpy.context.view_layer.update()
    return 1 if y < (arm.matrix_world @ b.tail).y else -1


FWD = leg_axis_sign()
L = sum((pivots[k] - ankles[k]).length + ankles[k].z for k in LEGS) / 4   # pivot-to-ground reach


def key_all(frame):
    for b in pb:
        b.keyframe_insert('rotation_euler', frame=frame); b.keyframe_insert('location', frame=frame)


def make_action(name):
    act = bpy.data.actions.new(name); arm.animation_data.action = act
    return act


walk = make_action('walk')
for f in range(WALK_FRAMES + 1):
    t = f / WALK_FRAMES; drop = 0.
    for k in LEGS:
        ph = 2 * math.pi * (t + PHASE[k])
        th = SWING * math.sin(ph)                       # + = foot forward
        swinging = math.cos(ph) > 0                     # foot travelling forward = swing phase
        lift = LIFT * math.cos(ph) if swinging else 0.
        pb['Leg_' + k].rotation_euler = (FWD * th, 0, 0)
        pb['Leg_' + k].location = (0, -lift, 0)       # local +Y runs down the leg; lift pulls it up
        pb['Foot_' + k].rotation_euler = (-FWD * th, 0, 0)
        drop = max(drop, L * (1 - math.cos(th)))
    pb['Body'].location = (0, -drop * .85 + .025 * math.sin(4 * math.pi * t), 0)
    pb['Body'].rotation_euler = (0, math.radians(1.2) * math.sin(2 * math.pi * t), 0)
    key_all(f)
idle = make_action('idle')
for f in range(0, IDLE_FRAMES + 1, 4):
    t = f / IDLE_FRAMES
    for k in LEGS:
        pb['Leg_' + k].rotation_euler = (0, 0, 0); pb['Leg_' + k].location = (0, 0, 0); pb['Foot_' + k].rotation_euler = (0, 0, 0)
    pb['Body'].location = (0, .02 * math.sin(2 * math.pi * t), 0)
    pb['Body'].rotation_euler = (math.radians(.8) * math.sin(2 * math.pi * t + 1), math.radians(1.5) * math.sin(2 * math.pi * t), 0)
    key_all(f)
for act in (walk, idle):
    for fc in act.fcurves if hasattr(act, 'fcurves') else []:
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
        fc.modifiers.new('CYCLES')
    trk = arm.animation_data.nla_tracks.new(); trk.name = act.name
    trk.strips.new(act.name, 1, act); trk.mute = True
arm.animation_data.action = None

report = dict(source=str(SRC), height=HEIGHT, scale=s, vertex_assignment=counts, walk_frames=WALK_FRAMES, idle_frames=IDLE_FRAMES, fps=FPS,
              swing_deg=math.degrees(SWING), lift=LIFT, reach=L, stride_speed_mps=4 * L * math.sin(SWING) / (WALK_FRAMES / FPS),
              pivots={k: list(v) for k, v in pivots.items()}, forward_sign=FWD)
(ROOT / 'mining-droid-rig.json').write_text(json.dumps(report, indent=1))
bpy.ops.object.select_all(action='DESELECT'); arm.select_set(True); body.select_set(True)
OUT.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.export_scene.gltf(filepath=str(OUT), export_format='GLB', use_selection=True, export_yup=True, export_apply=False,
                          export_skins=True, export_animations=True, export_animation_mode='ACTIONS', export_force_sampling=True,
                          export_frame_range=False, export_image_format='AUTO', export_jpeg_quality=90)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'mining-droid-rig.blend'), compress=True)
print('RIG_DONE', json.dumps(report))
