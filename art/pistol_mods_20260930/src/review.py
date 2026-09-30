# Stage B: review renders from the EXPORTED files. ScrapPistol.glb and PistolMods.glb are imported side by side, the
# mods root scaled by the same 0.13674 as the pistol (what parenting under the pistol with identity does in Unity).
# The gun rig (pistol + mods + FP hands) is placed so the in-game hip camera is level in the world.
# Usage: run_blender.sh src/review.py -- [set ...]   sets: mods, combos, fullframe (default all)
import sys, os, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector, Matrix, Euler
from bpy_extras.object_utils import world_to_camera_view
import pm_common as C

ART = C.ART
OUT = ART + 'review/'
os.makedirs(OUT, exist_ok=True)
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
SETS = set(args) or {'mods', 'combos', 'fullframe'}
SAMPLES = int(os.environ.get('PM_SAMPLES', '64'))
ONLY = os.environ.get('PM_ONLY', '')

C.reset()
pistol = C.import_pistol()
hands = C.import_hands()
new = C.import_glb(ART + 'export/PistolMods.glb')
mods = {}
for o in new:
    if o.parent is None:
        o.matrix_world = Matrix.Scale(C.S, 4) @ o.matrix_world
for o in new:
    if o.type == 'MESH':
        mods[o.name] = o
print('IMPORTED', sorted(mods))
man = json.load(open(ART + 'export/mods_manifest.json'))
# FP hands: the glb carries neutral materials (Unity assigns them in FPGripPass); use the documented v5 values
HANDCOL = {'FPHandsSkin': (.60, .43, .35), 'FPHandsGlove': (.40, .33, .25), 'FPHandsBracer': (.27, .27, .19),
           'FPHandsSleeve': (.14, .145, .14), 'FPHandsNail': (.72, .58, .52), 'FPHandsGlow': (.05, .25, .30)}
import pm_mats as PMM
for h in hands:
    for m in h.data.materials:
        key = next((k for k in HANDCOL if m and m.name.startswith(k)), None)
        if key and m.use_nodes:
            b = m.node_tree.nodes.get('Principled BSDF')
            if b:
                col = PMM.srgb(HANDCOL[key]) + (1,)
                b.inputs['Base Color'].default_value = col
                for n in m.node_tree.nodes:  # imported AO multiply: colour lives on the unlinked Mix input
                    if n.bl_idname == 'ShaderNodeMix' and n.data_type == 'RGBA':
                        for i in (6, 7):
                            if not n.inputs[i].is_linked:
                                n.inputs[i].default_value = col
                b.inputs['Roughness'].default_value = 0.55

# ---- rig: parent everything under one empty; place so the FP camera is level (5 deg down) at world eye height
rig = bpy.data.objects.new('rig', None); bpy.context.scene.collection.objects.link(rig)
for o in [pistol] + hands + list(mods.values()):
    top = o
    while top.parent:
        top = top.parent
    if top is not rig and top.parent is None:
        top.parent = rig
cam_p = C.fp_camera('hip', 'cam_fp_pistolframe')
Cp = cam_p.matrix_world.copy()
fwd = -(Cp.to_3x3() @ Vector((0, 0, 1)))
yaw = math.atan2(fwd.y, fwd.x)
EYE = Vector((0, 0, 1.62))
Cw = Matrix.Translation(EYE) @ (Euler((0, 0, yaw - math.pi / 2)).to_matrix().to_4x4() @ Euler((math.radians(90 - 5), 0, 0)).to_matrix().to_4x4())
rig.matrix_world = Cw @ Cp.inverted()
cam_p.matrix_world = Cw
cam_fp = cam_p
bpy.context.view_layer.update()
RIGM = rig.matrix_world.copy()


def W(p_metric):
    return RIGM @ Vector(p_metric)


# ---- lighting
sc = C.setup_render(res=(1600, 1000), samples=SAMPLES)
sc.view_settings.exposure = 0.0
view_dir = (Cw.to_3x3() @ Vector((0, 0, -1))).normalized()
left = (Cw.to_3x3() @ Vector((-1, 0, 0))).normalized()
C.world_sky(strength=0.9, sun_elev=38, sun_rot=math.degrees(math.atan2((-view_dir + left).y, (-view_dir + left).x)))
ground = C.ground(z=0.0, color=(0.46, 0.36, 0.26), size=60)
# sun from behind-left of the shooter, warm late-afternoon colour
sdir = (-view_dir * 0.55 + left * 0.75 + Vector((0, 0, 0.62))).normalized()
el = math.degrees(math.asin(sdir.z)); az = math.degrees(math.atan2(sdir.y, sdir.x))
sun = C.sun_lamp(elev=el, azim=az, energy=5.0, color=(1.0, 0.82, 0.6), angle=0.8)
gun_c = W((0.0, 0.0, 0.0))
blocker = C.shade_blocker(sun, dist=2.0, size=5.0)
blocker.location = gun_c + (sun.matrix_world.to_quaternion() @ Vector((0, 0, 1))) * 1.5


def lights(mode):
    blocker.hide_render = mode != 'shade'
    sc.world.node_tree.nodes['Background'].inputs[1].default_value = 0.35 if mode == 'sun' else 1.0


def show(names):
    for n, o in mods.items():
        o.hide_render = n not in names


def gun_border(cam, objs, pad=0.06):
    xs, ys = [], []
    for o in objs:
        if o.hide_render:
            continue
        for c in o.bound_box:
            p = world_to_camera_view(sc, cam, o.matrix_world @ Vector(c))
            xs.append(p.x); ys.append(p.y)
    x0, x1 = max(0, min(xs) - pad), min(1, max(xs) + pad)
    y0, y1 = max(0, min(ys) - pad), min(1, max(ys) + pad)
    return x0, x1, y0, y1


def render_fp(path, crop=True):
    sc.camera = cam_fp
    sc.render.resolution_x, sc.render.resolution_y = (2880, 1620) if crop else (1920, 1080)
    if crop:
        objs = [pistol] + [o for o in mods.values() if not o.hide_render]
        x0, x1, y0, y1 = gun_border(cam_fp, objs, 0.02)
        # square-ish region around the gun, clamped to frame
        sc.render.use_border = True; sc.render.use_crop_to_border = True
        sc.render.border_min_x, sc.render.border_max_x = x0, x1
        sc.render.border_min_y, sc.render.border_max_y = max(0.0, y0), y1
    else:
        sc.render.use_border = False
    C.render(path, cam_fp)
    sc.render.use_border = False


def cam_look(name, target, offset, fov=26):
    return C.camera(name, target + offset, -offset, (0, 0, 1), fov_deg=fov)


def render_34(path, names, kind):
    sc.render.resolution_x, sc.render.resolution_y = 1600, 1000
    sc.render.use_border = False
    objs = [mods[n] for n in names]
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    tgt = sum(pts, Vector()) / len(pts)
    ext = max((max(p[i] for p in pts) - min(p[i] for p in pts)) for i in range(3))
    # directions in the rig's pistol frame (metric: fwd -X, up +Z, right +Y), mapped to world
    R = RIGM.to_3x3()
    dirs = {'front_left': Vector((-0.75, -0.9, 0.55)), 'rear_right_low': Vector((0.9, 0.75, -0.35)),
            'left': Vector((-0.25, -1.0, 0.35)), 'rear_left': Vector((0.85, -0.8, 0.3))}
    d = (R @ dirs[kind]).normalized()
    dist = max(0.16, ext * 2.9)
    if len(names) > 1 or kind == 'left':
        tgt = W((-0.02, 0.0, 0.0)); dist = 0.62
    cam = cam_look('c34', tgt, d * dist, fov=26)
    C.render(path, cam)
    bpy.data.objects.remove(cam, do_unlink=True)


VIEW34 = {'grip_stabilised_pistol': 'rear_right_low', 'grip_gyro_braced': 'rear_right_low',
          'barrel_bored_alloy': 'front_left', 'barrel_lattice_focused': 'front_left',
          'cell_salvaged_capacitor': 'front_left', 'cell_overclocked': 'front_left'}
if 'mods' in SETS:
    for name in VIEW34:
        if ONLY and name not in ONLY.split(','):
            continue
        show([name])
        for mode in ('sun', 'shade'):
            lights(mode)
            for h in hands:
                h.hide_render = False
            render_fp(OUT + '%s_fp_%s.png' % (name, mode))
            for h in hands:
                h.hide_render = True
            render_34(OUT + '%s_34_%s.png' % (name, mode), [name], VIEW34[name])
            for h in hands:
                h.hide_render = False
COMBOS = {'mk1': ['grip_stabilised_pistol', 'barrel_bored_alloy', 'cell_salvaged_capacitor'],
          'mk2': ['grip_gyro_braced', 'barrel_lattice_focused', 'cell_overclocked']}
if 'combos' in SETS:
    for cn, names in COMBOS.items():
        show(names)
        for mode in ('sun', 'shade'):
            lights(mode)
            for h in hands:
                h.hide_render = False
            render_fp(OUT + 'combo_%s_fp_%s.png' % (cn, mode))
            for h in hands:
                h.hide_render = True
            render_34(OUT + 'combo_%s_34_%s.png' % (cn, mode), names, 'left')
            render_34(OUT + 'combo_%s_rear_%s.png' % (cn, mode), names, 'rear_left')
if 'fullframe' in SETS:
    for h in hands:
        h.hide_render = False
    for cn, names in list(COMBOS.items()) + [('stock', [])]:
        show(names)
        lights('sun')
        render_fp(OUT + 'fullframe_%s_fp_sun.png' % cn, crop=False)
