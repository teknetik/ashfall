# pistol/prev.py: the pistol's own review renders (model-pistol-surface). Frames on the parts' bounds, under the warm
# bench lamp and under the kit's neutral rig, standing as the kit shows it and lying on the mat as the player finds it.
#
#   SH/blender.sh pistol/prev.py -- --src DIR/pistol.blend | --glb DIR/pistol.glb  --out DIR [--tag x_]
#        [--light warm,neutral] [--cams close,close_rear,m_recv,m_grip,m_muzzle,m_right,m_top,bench,bench85,lie,lie85,lie_close]
#        [--res 1400x933] [--samples 32]
# --src renders the procedural materials (what the bake starts from); --glb what the exported file holds.
import bpy, os, sys, json, math
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'kit'))
import review as RV
import measure as ME

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []


def opt(k, d=None):
    return argv[argv.index(k) + 1] if k in argv else d


out = os.path.abspath(opt('--out', os.path.join(HERE, 'review')))
tag = opt('--tag', '')
lights = opt('--light', 'warm').split(',')
cams = opt('--cams', 'close,lie85').split(',')
res = tuple(int(x) for x in opt('--res', '1400x933').split('x'))
samples = int(opt('--samples', '32'))
# SEAM.md section 8: the kit's rigs are about 1.6 EV hot until review.py is fixed; a white card (albedo 0.8) must not clip.
# Pass --exp 0 --expn 0 once kit/review.py studio() is corrected.
# The kit's fix changes review.RIG (key 55 W neutral, 95 W warm before it) and adds its own cards: follow it.
_rig = getattr(RV, 'RIG', None)
HOT = (_rig is None) or (abs(_rig['neutral']['key'] - 55.0) < 1e-6 and abs(_rig['warm']['key'] - 95.0) < 1e-6)
exposure = {'warm': float(opt('--exp', '-2.2' if HOT else '0')), 'neutral': float(opt('--expn', '-1.6' if HOT else '0'))}
print('PREV rig', 'uncorrected: exposure %s' % exposure if HOT else 'calibrated by the kit: %s' % _rig, flush=True)
wb = float(opt('--wb', '0'))          # > 0: view white balance in kelvin (off by default: the sheets show the lamp's colour)
emit_gain = float(opt('--emit', '1.0'))      # the kit's warm rig is hot: the black mat should read black
MMv = lambda x, y, z: Vector((x, y, z)) * 0.001

if opt('--glb'):
    glb = os.path.abspath(opt('--glb'))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb)
    pj = json.load(open(os.path.join(os.path.dirname(glb), 'parts.json')))
    nodes = {p['node'] for p in pj['parts']}
    if os.path.basename(glb).startswith('pistol_hand'):
        # the in-hand copy: five merged nodes in ScrapPistol.glb units (metres / 0.13674)
        nodes = {o.name for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith('ScrapPistol')}
        for o in bpy.data.objects:
            if o.parent is None:
                o.matrix_world = Matrix.Scale(0.13674, 4) @ o.matrix_world
        bpy.context.view_layer.update()
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.name not in nodes:
            o.hide_render = True
    objs = [o for o in bpy.data.objects if o.type == 'MESH' and o.name in nodes]
    cfgdir = os.path.dirname(glb)
    for o in bpy.data.objects:          # the importer leaves the first clip playing
        if o.animation_data:
            o.animation_data.action = None
        if o.type == 'ARMATURE':
            for pb in o.pose.bones:
                pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
else:
    src = os.path.abspath(opt('--src'))
    bpy.ops.wm.open_mainfile(filepath=src)
    objs = RV.family_objects()
    cfgdir = os.path.dirname(src)
for o in list(bpy.data.objects):
    if o.type in ('CAMERA', 'LIGHT'):
        bpy.data.objects.remove(o)
cfg = {}
cp = os.path.join(cfgdir, 'review.json')
if os.path.exists(cp):
    cfg = json.load(open(cp))
hide = set(cfg.get('hide', []))
for o in objs:
    o.hide_render = o.name in hide
objs = [o for o in objs if o.name not in hide]
bpy.context.view_layer.update()

lay = bpy.data.objects.new('lay', None)
bpy.context.scene.collection.objects.link(lay)
for o in list(bpy.data.objects):
    if o.parent is None and o is not lay and o.type in ('MESH', 'ARMATURE', 'EMPTY'):
        mw = o.matrix_world.copy()
        o.parent = lay
        o.matrix_world = mw


def clear_rig():
    for o in list(bpy.data.objects):
        if o.type in ('LIGHT', 'CAMERA') or o.name.startswith('review_ground'):
            bpy.data.objects.remove(o)
    for w in list(bpy.data.worlds):
        bpy.data.worlds.remove(w)


def pose(lying):
    lay.rotation_euler = (math.radians(-90), 0, 0) if lying else (0, 0, 0)
    bpy.context.view_layer.update()
    lo, hi = ME.bounds(objs)
    return Vector(lo), Vector(hi)


def cam_for(name, lo, hi):
    c = (lo + hi) / 2
    ext = float(max(hi - lo))
    if name == 'close':
        return RV.close_cam(c, yaw=-70, fit=ext)
    if name == 'close_rear':
        return RV.close_cam(c, yaw=110, name='cam_close_rear', fit=ext)
    if name == 'm_recv':
        return RV.bench_cam(MMv(8, 0, 52), 0.3, 18, 85, -82, 'cam_m_recv')
    if name == 'm_grip':
        return RV.bench_cam(MMv(90, 0, -34), 0.3, 12, 80, -78, 'cam_m_grip')
    if name == 'm_muzzle':
        return RV.bench_cam(MMv(-98, 0, 54), 0.3, 22, 85, -125, 'cam_m_muzzle')
    if name == 'm_right':
        return RV.bench_cam(MMv(25, 0, 30), 0.3, 15, 60, 75, 'cam_m_right')
    if name == 'm_top':
        return RV.bench_cam(MMv(-25, 0, 68), 0.3, 62, 70, -90, 'cam_m_top')
    if name == 'm_butt':
        return RV.bench_cam(MMv(105, 0, -70), 0.3, -25, 85, 20, 'cam_m_butt')
    if name == 'bench':
        return RV.bench_cam(c, yaw=-90)
    if name == 'bench85':
        return RV.bench_cam(c, 0.6, 40, 85, -90, 'cam_bench85')
    if name == 'lie':
        return RV.bench_cam(c, 0.6, 40, 35, -90, 'cam_lie')
    if name == 'lie85':
        return RV.bench_cam(c, 0.6, 40, 85, -90, 'cam_lie85')
    if name == 'lie_close':
        return RV.bench_cam(c + MMv(15, 0, 0), 0.3, 42, 50, -78, 'cam_lie_close')
    if name == 'lie_recv':
        return RV.bench_cam(c + MMv(-20, 40, 0), 0.3, 48, 100, -84, 'cam_lie_recv')
    if name == 'lie_grip':
        return RV.bench_cam(c + MMv(95, -40, 0), 0.3, 48, 100, -80, 'cam_lie_grip')
    raise SystemExit('no camera ' + name)


def cards(lo, hi, cam, lying):
    """A white (albedo 0.8) and a mid-grey (0.18) card on the mat on the camera's side of the pistol."""
    c = (lo + hi) / 2
    side = -1.0 if cam.location.y < c.y else 1.0
    y = (-0.060 if lying else side * 0.055)
    z = float(lo[2]) + 0.0002
    for nm, alb, x in (('review_ground_card_white', 0.8, -0.094), ('review_ground_card_grey', 0.18, -0.058)):
        bpy.ops.mesh.primitive_plane_add(size=0.03, location=(x, y, z))
        g = bpy.context.active_object; g.name = nm
        m = bpy.data.materials.new(nm); m.use_nodes = True
        b = m.node_tree.nodes['Principled BSDF']
        b.inputs['Base Color'].default_value = (alb, alb, alb, 1); b.inputs['Roughness'].default_value = 1.0
        try:
            b.inputs['Specular IOR Level'].default_value = 0.0
        except Exception:
            pass
        g.data.materials.append(m)


done = {}
for light in lights:
    for name in cams:
        clear_rig()
        lying = name.startswith('lie')
        lo, hi = pose(lying)
        RV.studio(samples=samples, res=res, warm=(light == 'warm'))
        vs = bpy.context.scene.view_settings
        vs.exposure = exposure.get(light, 0.0)
        try:                      # a camera would balance part of the lamp's colour out: 3000 K lamp seen at 4300 K
            vs.use_white_balance = (light == 'warm' and wb > 0)
            if wb > 0:
                vs.white_balance_temperature = wb
        except Exception as e:
            print('no white balance:', e)
        if emit_gain != 1.0:      # what the cell looks like when the game multiplies the emission (the GLB holds 1.0)
            for m in bpy.data.materials:
                if m.use_nodes:
                    for n in m.node_tree.nodes:
                        if n.type == 'BSDF_PRINCIPLED' and n.inputs['Emission Strength'].default_value > 0 and not n.get('px_gain'):
                            n.inputs['Emission Strength'].default_value *= emit_gain; n['px_gain'] = 1
        RV.ground(float(lo[2]) - 0.0002, col=(0.028, 0.027, 0.026), rough=0.78)
        cam = cam_for(name, lo, hi)
        if not hasattr(RV, 'cards'):
            cards(lo, hi, cam, lying)
        path = os.path.join(out, '%s%s_%s.png' % (tag, light, name))
        RV.render(path, cam, res, samples)
        done['%s_%s' % (light, name)] = path
print('PREV', json.dumps(done))
