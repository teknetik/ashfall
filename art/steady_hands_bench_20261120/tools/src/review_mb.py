# review_mb.py: review renders for the tools and fixtures families (Cycles, CPU), on the kit's review module.
#   SH/blender.sh tools/src/review_mb.py -- --family fixtures [--only vise,dish] [--shots views,close,bench,lamp] [--samples 32] [--glb] [--warm]
# Exposure (SEAM.md section 8): every rig is measured before it is used, with a 24 px linear render of a white card
# (albedo 0.8) lying face up beside the subject (its largest channel, as kit/calibrate_rig.py); numbers in review/exposure.json. The kit's rigs (re-lit at
# 19:46 on 20 Nov so that a card facing the key reads about 0.9 scene-linear; one lying beside the subject reads 0.6
# to 0.75, less in a tall subject's shadow) are left at exposure 0 and the reading is only recorded; the pendant of the bench shots is this script's own light and is always set so that the card reads 0.9.
# Object shots carry the kit's corner cards; the bench shots have a white and a mid-grey card lying on the rubber
# between the vise and the work mat. --warm uses the kit's warm rig for the object shots (file names get 'warm_');
# 'lamp' renders only the two bench shots under the pendant.
# Per object: review/<key>_views.png (front = the player's side, back, left, right, top, three-quarter; rigs at both
# ends of their parameter) and review/<key>_compare.jpg with the reference sheet on the left. 'bench' is the whole
# layout from the bench camera of layout.json, with the other family and the existing bench appended when they exist.
import bpy, os, sys, json, math, subprocess
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mbk
from mbk import PROG, LAYOUT, RG
import review as RV

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []


def opt(k, d=None, cast=str):
    return cast(argv[argv.index(k) + 1]) if k in argv else d


FAM = opt('--family', 'fixtures')
ONLY = opt('--only'); ONLY = ONLY.split(',') if ONLY else None
SHOTS = set((opt('--shots') or 'views,close').split(','))
SAMPLES = opt('--samples', 32, int)
GLB = '--glb' in argv
QUICK = '--quick' in argv
FDIR = os.path.join(PROG, FAM)
OUT = os.path.join(FDIR, 'review'); os.makedirs(OUT, exist_ok=True)
WARM = '--warm' in argv
RV.WARM = WARM
TAG = ('glb_' if GLB else '') + ('warm_' if WARM else '')
EXPO = {}

# key: (node name prefixes, sheet, {rig: {param: value}} poses to show beside the rest pose, close-up target or None)
TABLE = {
    'fixtures': {
        'worksurface': (['fixtures_worksurface', 'fixtures_workmat', 'fixtures_partsmat'], 'fix_mats_turn.png', None),
        'vise': (['fixtures_vise'], 'fix_vise_turn.png', {'fixtures_vise_rig': {'vise_jaw': 1.0}}),
        'dish': (['fixtures_dish'], 'fix_small_turn.png', None),
        'cradle': (['fixtures_cradle'], 'fix_small_turn.png', None),
        'pad': (['fixtures_pad'], 'fix_small_turn.png', None),
        'board': (['fixtures_board'], 'fix_tester_turn.png', None),
    },
    'tools': {
        'roll': (['tools_roll'], 'tools_roll_turn.png', [{'clips': 0.0}, {'clips': 0.33}]),
        'screwdriver': (['tools_screwdriver', 'tools_bit', 'tools_bitblock'], 'tools_hand_turn.png', None),
        'pliers': (['tools_pliers'], 'tools_hand_turn.png', {'tools_pliers_rig': {'pliers_jaws': 1.0}}),
        'cutters': (['tools_cutters'], 'tools_hand_turn.png', {'tools_cutters_rig': {'cutters_jaws': 1.0}}),
        'punch': (['tools_punch'], 'tools_hand_turn.png', None),
        'mallet': (['tools_mallet'], 'tools_bench_turn.png', None),
        'dropper': (['tools_oil'], 'tools_bench_turn.png', None),
    },
}[FAM]

def import_glb(path):
    """A GLB as a plain viewer shows it at rest: clips dropped, bones at rest (the roll unrolled, the vise open)."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        if o.animation_data:
            o.animation_data_clear()
        if o.type == 'ARMATURE':
            for pb in o.pose.bones:
                pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0); pb.scale = (1, 1, 1)
        elif o.type in ('EMPTY', 'MESH'):
            pass
    bpy.context.view_layer.update()
    return new


if GLB:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    import_glb(os.path.join(FDIR, 'export', FAM + '.glb'))
else:
    bpy.ops.wm.open_mainfile(filepath=os.path.join(FDIR, 'export', FAM + '.blend'))
for o in list(bpy.data.objects):
    if o.type in ('CAMERA', 'LIGHT'):
        bpy.data.objects.remove(o)
sc = RV.studio(samples=SAMPLES, res=(900, 620) if QUICK else (1100, 760))
ALL = [o for o in bpy.data.objects if o.type == 'MESH']
if not GLB:
    mbk.rest_all()                       # custom rigs at rest: the roll unrolled, the bulb full


def card(name, loc, size, albedo):
    bpy.ops.mesh.primitive_plane_add(size=size, location=loc)
    o = bpy.context.active_object; o.name = name
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (albedo, albedo, albedo, 1); b.inputs['Roughness'].default_value = 1.0
    for k in ('Specular IOR Level', 'Specular'):
        if k in b.inputs:
            b.inputs[k].default_value = 0.0
    o.data.materials.append(m)
    return o


def cards(p, size=0.03, step=(1.1, 0.0)):
    """A white card (albedo 0.8) and a mid-grey card (0.18) lying at p, face up."""
    return [card('card_white', (p[0], p[1], p[2]), size, 0.8),
            card('card_grey', (p[0] + size * step[0], p[1] + size * step[1], p[2]), size, 0.18)]


def calibrate(white, label, rig, force=True):
    """Measure a white card lying at the subject and set the exposure so that its largest channel reads 0.9 in scene-linear
    (SEAM.md section 8). force=False: a kit rig, whose own exposure stands; the reading is only recorded."""
    keep = (sc.render.resolution_x, sc.render.resolution_y, sc.cycles.samples)
    cam = RV._cam('cam_cal', tuple(white.location + Vector((0, 0, 0.25))), (0, 0, -1), (0, 1, 0), ortho=white.dimensions.x * 0.55)
    sc.render.image_settings.file_format = 'OPEN_EXR'; sc.render.image_settings.color_depth = '32'
    p = os.path.join(OUT, '_cal_%s.exr' % TAG)
    RV.render(p, cam, res=(24, 24), samples=48)
    img = bpy.data.images.load(p); px = list(img.pixels); n = len(px) // 4
    r, g, b = sum(px[0::4]) / n, sum(px[1::4]) / n, sum(px[2::4]) / n
    bpy.data.images.remove(img); os.remove(p)
    lum = max(r, g, b)                 # the kit's measure: the largest channel of the white card
    ev = math.log2(0.9 / max(lum, 1e-6))
    off = ev
    if not force:
        ev = 0.0                       # a kit rig: its own exposure stands; the reading is only recorded
    sc.view_settings.exposure = ev
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_depth = '8'
    sc.render.resolution_x, sc.render.resolution_y, sc.cycles.samples = keep
    bpy.data.objects.remove(cam)
    EXPO[TAG + label] = {'rig': rig, 'card_reads_ev_from_0.9': round(-off, 2), 'white_card_scene_linear_rgb': [round(r, 3), round(g, 3), round(b, 3)], 'largest_channel_before': round(lum, 3),
                         'exposure_ev_set': round(ev, 2), 'white_card_largest_channel_at_that_exposure': round(lum * 2 ** ev, 3)}
    print('EXPOSURE', TAG + label, rig, 'white card', round(lum, 3), '-> EV', round(ev, 2), flush=True)
    return ev


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


def set_pose(pose):
    """pose: {rig: {param: value}} for the kit's driven rigs, or {'clips': v} to sample every clip of the custom rigs."""
    if not pose or GLB:
        return
    if 'clips' in pose:
        for o in bpy.data.objects:
            if o.type == 'ARMATURE' and o.animation_data and len(o.animation_data.nla_tracks):
                mbk.sample_clip(o, [t.name for t in o.animation_data.nla_tracks], pose['clips'])
        return
    for rig, vals in pose.items():
        arm = bpy.data.objects.get(rig)
        if arm is not None:
            RG.set_params(arm, vals)


def unpose(pose):
    if not pose or GLB:
        return
    if 'clips' in pose:
        mbk.rest_all()
        return
    set_pose({r: {k: 0.0 for k in vals} for r, vals in pose.items()})


def views(key, objs, pose):
    lo, hi = bounds(objs)
    c = (lo + hi) / 2; ext = max(hi - lo)
    d = max(0.6, ext * 3)
    g = RV.ground(lo.z - 0.0003, (0.16, 0.16, 0.16))
    cams = [('front', RV.look_cam('c_f', c, (0, -d, 0), ortho=ext * 1.2)), ('back', RV.look_cam('c_b', c, (0, d, 0), ortho=ext * 1.2)),
            ('left', RV.look_cam('c_l', c, (-d, 0, 0), ortho=ext * 1.2)), ('right', RV.look_cam('c_r', c, (d, 0, 0), ortho=ext * 1.2)),
            ('top', RV.look_cam('c_t', c, (0, 0, d), ortho=ext * 1.2)),
            ('threeq', RV.look_cam('c_q', c, Vector((0.65, -0.9, 0.55)).normalized() * max(0.3, ext * 2.4), lens=70))]
    if QUICK:
        cams = [c_ for c_ in cams if c_[0] in ('front', 'back', 'top', 'threeq')]
    paths, labels = [], []
    for n, cam in cams:
        p = os.path.join(OUT, '_%s%s_%s.png' % (TAG, key, n))
        RV.render(p, cam); paths.append(p); labels.append(n if n != 'front' else 'front (player side)')
    for pi, ps in enumerate(pose if isinstance(pose, list) else ([pose] if pose else [])):
        if GLB:
            break
        set_pose(ps)
        for n in (('threeq', 'front') if QUICK else ('front', 'threeq', 'top')):
            cam = dict(cams)[n]
            p = os.path.join(OUT, '_%s%s_%s_posed%d.png' % (TAG, key, n, pi))
            RV.render(p, cam); paths.append(p); labels.append(n + ' ' + json.dumps(ps).replace('"', ''))
        unpose(ps)
    sheet = os.path.join(OUT, '%s%s_views.png' % (TAG, key))
    RV.contact_sheet(paths, sheet, cols=2 if QUICK else 3, labels=labels, width=700)
    for p in paths:
        os.remove(p)
    bpy.data.objects.remove(g)
    return sheet


def close(key, objs):
    lo, hi = bounds(objs)
    c = (lo + hi) / 2; ext = max(hi - lo)
    g = RV.ground(lo.z - 0.0003, (0.045, 0.043, 0.041))
    out = []
    for i, yaw in enumerate((-70, -125)):
        cam = RV.close_cam(c, dist=0.3, down=38, yaw=yaw, name='cc%d' % i, fit=min(ext, 0.22))
        p = os.path.join(OUT, '%s%s_close%d.png' % (TAG, key, i))
        RV.render(p, cam, res=(1500, 1000)); out.append(p)
    bpy.data.objects.remove(g)
    return out


def bench():
    """Everything on the bench from the bench camera, under one warm lamp (the look target), and under the studio."""
    other = 'tools' if FAM == 'fixtures' else 'fixtures'
    ob = os.path.join(PROG, other, 'export', other + '.blend')
    extra = []
    og = os.path.join(PROG, other, 'export', other + '.glb')
    if GLB and os.path.exists(og):
        extra = import_glb(og)
    if os.path.exists(ob) and not GLB:
        with bpy.data.libraries.load(ob, link=False) as (src, dst):
            dst.objects = [n for n in src.objects]
        for o in dst.objects:
            if o is not None and o.type in ('MESH', 'ARMATURE', 'EMPTY'):
                bpy.context.scene.collection.objects.link(o); extra.append(o)
    if not GLB:
        mbk.rest_all()        # the appended family too: its custom rigs come in sampled at frame 1 (the roll rolled up)
    ss = os.path.join(os.path.dirname(os.path.dirname(PROG)), 'unity/AthenHill/Assets/AthenHill/Art/SalvageShop/Props/SS_Workbench/')
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=ss + 'SS_Workbench_LOD0.glb')
    for o in set(bpy.data.objects) - before:
        if o.parent is None:
            o.matrix_world = Matrix.Translation((0, 0, -0.8637)) @ o.matrix_world
        if o.type == 'MESH':
            m = bpy.data.materials.new('bench'); m.use_nodes = True
            b = m.node_tree.nodes['Principled BSDF']
            t = m.node_tree.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(ss + 'SS_Workbench_BaseColor.jpg')
            m.node_tree.links.new(t.outputs['Color'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = 0.75
            o.data.materials.clear(); o.data.materials.append(m)
    for o in bpy.data.objects:
        if o.type == 'MESH':
            o.hide_render = False
    cam = LAYOUT['camera']
    e = math.radians(cam['pitch_down_deg'])
    c = RV._cam('cam_layout', cam['eye'], (0, math.cos(e), -math.sin(e)), (0, 0, 1), lens=cam['lens_mm'])
    c2 = RV._cam('cam_layout_wide', (0, -1.45, 0.786), (0, math.cos(e), -math.sin(e)), (0, 0, 1), lens=28)
    RV.CARDS = False                                                  # the kit's corner cards hang in the air by the camera
    cs = cards((-0.205, -0.235, 0.0086), 0.03, step=(0.0, -1.1))     # on the rubber between the vise and the work mat
    if 'bench' in SHOTS:
        calibrate(cs[0], 'bench_studio', 'kit warm rig' if WARM else 'kit neutral rig', force=False)
        RV.render(os.path.join(OUT, '%sbench_studio.png' % TAG), c, res=(1920, 1080))
        RV.render(os.path.join(OUT, '%sbench_wide_studio.png' % TAG), c2, res=(1920, 1080))
        top = RV._cam('cam_plan', (0, 0, 0.56), (0, 0, -1), (0, 1, 0), ortho=2.4)
        RV.render(os.path.join(OUT, '%sbench_plan.png' % TAG), top, res=(1800, 1000))
    # the shop's own light: one warm pendant over the bench, little else
    for o in bpy.data.objects:
        if o.type == 'LIGHT':
            o.hide_render = True
    sc.world.node_tree.nodes['Math'].inputs[1].default_value = 0.06
    ld = bpy.data.lights.new('pendant', 'SPOT'); ld.energy = 260; ld.color = (1.0, 0.72, 0.42); ld.spot_size = math.radians(120); ld.spot_blend = 0.6
    ld.shadow_soft_size = 0.06
    lo = bpy.data.objects.new('pendant', ld); sc.collection.objects.link(lo)
    lo.location = (0.0, -0.20, 1.05); lo.rotation_euler = (0, 0, 0)
    # the room: sandstone walls round the bench, so that metal has something lit to reflect (the look target's wall)
    rm = bpy.data.materials.new('room'); rm.use_nodes = True
    rb = rm.node_tree.nodes['Principled BSDF']
    rb.inputs['Base Color'].default_value = (0.30, 0.20, 0.11, 1); rb.inputs['Roughness'].default_value = 0.9
    for nm, loc, rot, sz in (('wall_back', (0, 0.66, 0.4), (math.radians(90), 0, 0), (4.0, 3.0)), ('wall_left', (-1.7, -0.8, 0.4), (0, math.radians(90), 0), (3.0, 4.0)),
                             ('wall_right', (1.7, -0.8, 0.4), (0, math.radians(90), 0), (3.0, 4.0)), ('wall_front', (0, -2.6, 0.4), (math.radians(90), 0, 0), (4.0, 3.0)),
                             ('ceiling', (0, -0.8, 1.75), (0, 0, 0), (4.0, 4.0)), ('floor', (0, -0.8, -0.8637), (0, 0, 0), (4.0, 4.0))):
        bpy.ops.mesh.primitive_plane_add(size=1.0, location=loc, rotation=rot)
        w = bpy.context.active_object; w.name = 'room_' + nm; w.scale = (sz[0], sz[1], 1.0); w.data.materials.append(rm)
    bl = bpy.data.lights.new('bulb', 'POINT'); bl.energy = 35; bl.color = (1.0, 0.72, 0.42); bl.shadow_soft_size = 0.03
    bo = bpy.data.objects.new('bulb', bl); sc.collection.objects.link(bo); bo.location = (0.0, -0.20, 1.0)     # the bare bulb's spill on the walls
    calibrate(cs[0], 'bench_lamp', 'one 3000 K pendant 1.05 m over the mat and its spill in a sandstone room, sky at 0.06')
    RV.render(os.path.join(OUT, '%sbench_lamp.png' % TAG), c, res=(1920, 1080))
    RV.render(os.path.join(OUT, '%sbench_wide_lamp.png' % TAG), c2, res=(1920, 1080))


for key, (prefixes, sheet, pose) in TABLE.items():
    if (ONLY and key not in ONLY) or not ({'views', 'close'} & SHOTS):
        continue
    objs = [o for o in ALL if any(o.name == p or o.name.startswith(p + '_') or o.name.startswith(p + '.') for p in prefixes)]
    if not objs:
        print('REVIEW skip', key, '(not built)'); continue
    show_only(objs)
    lo_, hi_ = bounds(objs)
    cs_ = [card('cal_white', (hi_.x + 0.03, lo_.y + 0.015, lo_.z + 0.0004), 0.022, 0.8)]
    calibrate(cs_[0], key, 'kit warm rig' if WARM else 'kit neutral rig', force=False)
    bpy.data.objects.remove(cs_.pop())
    if 'views' in SHOTS:
        s = views(key, objs, pose)
        sp = os.path.join(FDIR, 'sheets', sheet)
        RV.beside(sp, s, os.path.join(OUT, '%s%s_compare.jpg' % (TAG, key)), height=1400)
    if 'close' in SHOTS:
        close(key, objs)
    for o_ in cs_:
        bpy.data.objects.remove(o_)
    print('REVIEW done', key, flush=True)
if 'bench' in SHOTS or 'lamp' in SHOTS:
    bench()
ep = os.path.join(OUT, 'exposure.json')
ex = json.load(open(ep)) if os.path.exists(ep) else {}
ex.update(EXPO)
json.dump(ex, open(ep, 'w'), indent=1)
print('REVIEW DONE')
