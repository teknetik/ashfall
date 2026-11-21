# review_tl.py: model-tools review renders (21 Nov 2026), on the kit's review module. For each tool: a top view laid
# out as the sheets are, and two close views at 0.3 m, under the kit's calibrated warm rig (--warm, the bench lamp) or
# the neutral one; a compare image with the crop of the reference sheet on the left.
#   SH/blender.sh tools/src/review_tl.py -- [--only strippers,drill] [--samples 32] [--warm] [--glb] [--tag x]
# Without --glb the source .blend is rendered (procedural authoring materials: the look before a bake); with --glb the
# exported GLB as a plain viewer shows it (baked textures).
import bpy, os, sys, json, math, subprocess
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mbk
from mbk import PROG
import review as RV

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []


def opt(k, d=None, cast=str):
    return cast(argv[argv.index(k) + 1]) if k in argv else d


ONLY = opt('--only'); ONLY = ONLY.split(',') if ONLY else None
SAMPLES = opt('--samples', 32, int)
GLB = '--glb' in argv
WARM = '--warm' in argv
RV.WARM = WARM
FDIR = os.path.join(PROG, 'tools')
OUT = os.path.join(FDIR, 'review', 'mt'); os.makedirs(OUT, exist_ok=True)
TAG = opt('--tag', '') + ('glb_' if GLB else 'src_') + ('warm_' if WARM else '')
SH = os.path.join(FDIR, 'sheets')
# key: (node prefixes, sheet, crop WxH+X+Y of the sheet, poses {rig: {param: v}} or None)
TABLE = {
    'strippers': (['tools_strippers'], 'tools_hand_turn.png', '470x140+40+500', {'tools_strippers_rig': {'strippers_jaws': 1.0}}),
    'wirebrush': (['tools_wirebrush'], 'tools_hand_turn.png', '660x110+820+510', None),
    'pick': (['tools_pick'], 'tools_hand_turn.png', '680x150+30+650', None),
    'scribe': (['tools_scribe'], 'tools_hand_turn.png', '700x100+20+810', None),
    'files': (['tools_file_flat', 'tools_file_round'], 'tools_bench_turn.png', '700x250+760+40', None),
    'snips': (['tools_snips'], 'tools_bench_turn.png', '620x200+90+330', {'tools_snips_rig': {'snips_jaws': 1.0}}),
    'drill': (['tools_drill'], 'tools_bench_turn.png', '720x360+760+330', {'tools_drill_rig': {'drill_chuck': 1.0}}),
    'iron': (['tools_iron', 'tools_iron_stand', 'tools_solder_reel'], 'tools_bench_turn.png', '520x180+40+560', None),
    'thirdhand': (['tools_thirdhand'], 'tools_bench_turn.png', '460x210+30+750', None),
    'applicator': (['tools_applicator'], 'tools_bench_turn.png', '400x160+780+780', None),
    'pliers': (['tools_pliers'], 'tools_hand_turn.png', '720x320+40+250', None),
    'cutters': (['tools_cutters'], 'tools_hand_turn.png', '650x320+840+250', None),
    'screwdriver': (['tools_screwdriver', 'tools_bit', 'tools_bitblock'], 'tools_hand_turn.png', '1440x240+40+40', None),
    'punch': (['tools_punch'], 'tools_hand_turn.png', '420x160+840+690', None),
    'mallet': (['tools_mallet'], 'tools_bench_turn.png', '600x210+120+40', None),
    'dropper': (['tools_oil'], 'tools_bench_turn.png', '220x180+500+750', None),
    'roll': (['tools_roll'], 'tools_roll_turn.png', '1536x1024+0+0', None),
    'kit': (['tools_roll', 'tools_screwdriver', 'tools_bit', 'tools_bitblock', 'tools_pliers', 'tools_cutters', 'tools_punch', 'tools_strippers', 'tools_wirebrush', 'tools_pick', 'tools_scribe'], 'tools_roll_turn.png', '1536x1024+0+0', None),
}


def import_glb(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        if o.animation_data:
            o.animation_data_clear()
        if o.type == 'ARMATURE':
            for pb in o.pose.bones:
                pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0); pb.scale = (1, 1, 1)
    bpy.context.view_layer.update()


if GLB:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    import_glb(os.path.join(FDIR, 'export', 'tools.glb'))
else:
    bpy.ops.wm.open_mainfile(filepath=os.path.join(FDIR, 'export', 'tools.blend'))
for o in list(bpy.data.objects):
    if o.type in ('CAMERA', 'LIGHT'):
        bpy.data.objects.remove(o)
sc = RV.studio(samples=SAMPLES, res=(1200, 800))
if not GLB:
    mbk.rest_all()
ALL = [o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith('Icosphere')]


def bounds(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
    for o in objs:
        oe = o.evaluated_get(dg)
        for c in oe.bound_box:
            p = oe.matrix_world @ Vector(c)
            lo = Vector((min(lo.x, p.x), min(lo.y, p.y), min(lo.z, p.z))); hi = Vector((max(hi.x, p.x), max(hi.y, p.y), max(hi.z, p.z)))
    return lo, hi


def show_only(objs):
    s = set(objs)
    for o in ALL:
        o.hide_render = o not in s


def set_params(pose, v):
    if not pose or GLB:
        return
    for rig, vals in pose.items():
        arm = bpy.data.objects.get(rig)
        if arm is not None:
            mbk.RG.set_params(arm, {k: v * x for k, x in vals.items()})


done = []
for key, (prefixes, sheet, crop, pose) in TABLE.items():
    if ONLY and key not in ONLY:
        continue
    objs = [o for o in ALL if any(o.name == p or o.name.startswith(p + '_') or o.name.startswith(p + '.') for p in prefixes)]
    if key == 'drill':
        objs = [o for o in ALL if o.name.startswith('tools_drill')]
    if not objs:
        print('REVIEW skip', key); continue
    show_only(objs)
    lo, hi = bounds(objs)
    c = (lo + hi) / 2; ext = max(hi - lo)
    g = RV.ground(lo.z - 0.0002, (0.045, 0.043, 0.041))
    paths, labels = [], []
    top = RV._cam('c_top', (c.x, c.y, c.z + 1.0), (0, 0, -1), (-1, 0, 0) if (hi - lo).y > (hi - lo).x else (0, 1, 0), ortho=ext * 1.15)
    p = os.path.join(OUT, '_%s_top.png' % key); RV.render(p, top, res=(1500, 1000)); paths.append(p); labels.append('top (as the sheet)')
    for i, yaw in enumerate((-70, -125)):
        cam = RV.close_cam(c, dist=0.3, down=38, yaw=yaw, name='cc%d' % i, fit=min(ext, 0.24))
        p = os.path.join(OUT, '_%s_close%d.png' % (key, i)); RV.render(p, cam, res=(1500, 1000)); paths.append(p); labels.append('0.3 m, yaw %d' % yaw)
    if key == 'kit' and not GLB:
        arm = bpy.data.objects.get('tools_roll_rig')
        mbk.sample_clip(arm, [t.name for t in arm.animation_data.nla_tracks], 1.0)
        c2 = arm.matrix_world.translation.copy() + Vector((0, 0, 0.01))
        for nm, cam in (('open roll from above', RV._cam('c_kit', (c2.x, c2.y, c2.z + 1.0), (0, 0, -1), (0, 1, 0), ortho=0.62)),
                        ('open roll, bench camera angle', RV.close_cam(c2, dist=0.55, down=40, yaw=-90, name='ckit2', fit=0.5))):
            p = os.path.join(OUT, '_kit_%d.png' % len(paths)); RV.render(p, cam, res=(1500, 1000)); paths.append(p); labels.append(nm)
        paths_keep = list(paths)
    if key == 'roll' and not GLB:
        arm = bpy.data.objects.get('tools_roll_rig')
        for v, nm in ((0.82, 'unrolled'), (1.0, 'flap open')):
            mbk.sample_clip(arm, [t.name for t in arm.animation_data.nla_tracks], v)
            lo2, hi2 = bounds(objs); c2 = (lo2 + hi2) / 2
            cam = RV.close_cam(c2, dist=0.3, down=42, yaw=-90, name='ccr', fit=0.30)
            p = os.path.join(OUT, '_roll_%s.png' % nm.replace(' ', '_')); RV.render(p, cam, res=(1500, 1000)); paths.append(p); labels.append('roll ' + nm)
            top2 = RV._cam('c_top2', (c2.x, c2.y, c2.z + 1.0), (0, 0, -1), (0, 1, 0), ortho=0.62)
            p = os.path.join(OUT, '_roll_%s_top.png' % nm.replace(' ', '_')); RV.render(p, top2, res=(1500, 1000)); paths.append(p); labels.append('roll ' + nm + ', top')
        mbk.sample_clip(arm, [t.name for t in arm.animation_data.nla_tracks], 0.0)
    if pose and not GLB:
        set_params(pose, 1.0)
        cam = RV.close_cam(c, dist=0.3, down=50, yaw=-90, name='ccp', fit=min(ext, 0.24))
        p = os.path.join(OUT, '_%s_posed.png' % key); RV.render(p, cam, res=(1500, 1000)); paths.append(p); labels.append('posed ' + json.dumps(pose).replace('"', ''))
        set_params(pose, 0.0)
    views = os.path.join(OUT, '%s%s_views.png' % (TAG, key))
    RV.contact_sheet(paths, views, cols=2, labels=labels, width=900)
    for p in paths:
        os.remove(p)
    bpy.data.objects.remove(g)
    cp = os.path.join(OUT, '_crop_%s.png' % key)
    subprocess.run(['magick', os.path.join(SH, sheet), '-crop', crop, '+repage', cp], check=False)
    RV.beside(cp, views, os.path.join(OUT, '%s%s_compare.jpg' % (TAG, key)), height=1400)
    if os.path.exists(cp):
        os.remove(cp)
    done.append(key)
    print('REVIEW done', key, flush=True)
print('REVIEW DONE', done)
