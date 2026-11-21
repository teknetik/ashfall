# kit/review.py: review renders (Cycles, CPU) and contact sheets beside the reference sheets.
#
# As a module (inside a build or a family's own review script):
#   import review as RV
#   RV.studio(samples=48)                         # world, lights, render settings (call once per scene)
#   cams = RV.six_views(center, dist, ortho)      # left, right, front, back, top, threeq (the sheet's directions)
#   RV.render(path, cam, res=(1500, 1000))
#   RV.bench_cam(target), RV.close_cam(target)    # 40 degrees down / 0.6 m / 35 mm, and 0.3 m
#   restore = RV.explode(scene_parts, f=1.5)      # parts moved toward their __clear empties; restore() puts them back
#   RV.contact_sheet(paths, out, cols=3, labels=[...]);  RV.beside(sheet_png, sheet_of_renders_png, out)
#
# As a script: SH/blender.sh kit/review.py -- --family <family dir> [--glb] [--samples 48] [--only six,bench,close,exploded]
#   --warm: the bench lamp's light (3000 K key) instead of the neutral rig; file names get 'warm_' in front.
#   Renders <family>/export/<family>.blend (or the exported GLB with --glb: what a plain viewer shows) to
#   <family>/review/ and tiles the six views beside <family>/sheets/overall.png when that exists.
# Frame assumed: Z up; "front" is the -X end (the pistol's muzzle; for other families whatever faces -X).
import bpy, os, sys, math, json, subprocess
import numpy as np
from mathutils import Vector, Matrix, Quaternion

KIT = os.path.dirname(os.path.abspath(__file__))
if KIT not in sys.path:
    sys.path.insert(0, KIT)

BG = (0.18, 0.18, 0.18)


def _cam(name, loc, look, up, ortho=None, fov=None, lens=None, clip=(0.005, 50)):
    cd = bpy.data.cameras.new(name)
    cam = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(cam)
    f = Vector(look).normalized(); u = Vector(up).normalized()
    r = f.cross(u).normalized(); u = r.cross(f).normalized()
    M = Matrix((r, u, -f)).transposed().to_4x4(); M.translation = Vector(loc)
    cam.matrix_world = M
    cd.clip_start, cd.clip_end = clip
    if ortho:
        cd.type = 'ORTHO'; cd.ortho_scale = ortho
    elif lens:
        cd.lens = lens; cd.sensor_width = 36.0
    elif fov:
        cd.sensor_fit = 'VERTICAL'; cd.angle_y = math.radians(fov)
    return cam


def look_cam(name, target, offset, fov=None, lens=None, ortho=None, up=(0, 0, 1)):
    t = Vector(target); o = Vector(offset)
    if abs(o.normalized().dot(Vector(up))) > 0.98:
        up = (0, 1, 0)       # looking straight down or up: +X stays to the right, as in the left view
    cam = _cam(name, t + o, -o, up, ortho=ortho, fov=fov, lens=lens)
    cam['rv_dist'] = o.length          # how far away the subject is: render() puts the exposure cards at that depth
    return cam


def six_views(center=(0, 0, 0), dist=0.8, ortho=0.3, threeq=(-0.75, -0.9, 0.5)):
    """The sheet's directions: five orthographic elevations at one scale and a three-quarter view."""
    c = Vector(center)
    v = {'left': look_cam('cam_left', c, (0, -dist, 0), ortho=ortho),
         'right': look_cam('cam_right', c, (0, dist, 0), ortho=ortho),
         'front': look_cam('cam_front', c, (-dist, 0, 0), ortho=ortho),
         'back': look_cam('cam_back', c, (dist, 0, 0), ortho=ortho),
         'top': look_cam('cam_top', c, (0, 0, dist), ortho=ortho),
         'threeq': look_cam('cam_threeq', c, Vector(threeq).normalized() * max(0.25, ortho * 2.6), lens=70)}
    return v


def bench_cam(target=(0, 0, 0), dist=0.6, down=40.0, lens=35.0, yaw=-90.0, name='cam_bench'):
    """The bench camera of DESIGN.md section 4: about 40 degrees down, 0.6 m away, 35 mm. yaw: where the player stands
    (degrees about Z from +X; -90 = looking along +Y, standing on the -Y side)."""
    e, a = math.radians(down), math.radians(yaw)
    off = Vector((math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e))) * dist
    return look_cam(name, target, off, lens=lens)


def close_cam(target=(0, 0, 0), dist=0.3, down=30.0, lens=35.0, yaw=-70.0, name='cam_close', fit=None):
    """The 0.3 m view. fit: the size of the thing (metres); the lens is then lengthened so it fills the frame, which
    is a crop of what the player sees from 0.3 m (same perspective, more pixels on the part)."""
    if fit:
        lens = max(35.0, min(240.0, dist * 36.0 / (fit * 1.5)))
    return bench_cam(target, dist, down, lens, yaw, name)


WARM = False       # set by --warm, or review.WARM = True before studio(): the bench lamp (about 3000 K) as the key
CARDS = True       # a white (albedo 0.8) and a mid-grey (0.18) diffuse card in the bottom left corner of every frame

# Light energies (W) and sky strength of the two rigs. Calibrated with kit/calibrate_rig.py (SEAM.md section 8): a
# white diffuse card of albedo 0.8 facing the key reads about 0.9 in scene-linear (largest channel), so nothing diffuse
# clips under AgX and a bright albedo keeps its hue. Before 20 Nov 19:40 the same card read about 3 (neutral) and 4.5
# (warm): every colour judged on an older render is void.
# Measured before (kit/rig_calibration_before.json): neutral 55 / 30 / 8 W and sky 1.0 gave 2.33; warm 95 / 8 / 4 W and
# sky 0.25 gave 4.02. The warm rig's surroundings are now warm and a fifth of the light (they were 3 %), so metal has
# something to reflect, as it has in the look target's lit room.
RIG = {
    'neutral': {'key': 19.5, 'rim': 10.5, 'fill': 5.0, 'sky': 0.43, 'sky_col': (0.95, 0.97, 1.0)},
    'warm': {'key': 16.6, 'rim': 3.0, 'fill': 3.0, 'sky': 0.336, 'sky_col': (1.0, 0.84, 0.66)},
}


def cards(cam):
    """Two small diffuse cards in the bottom left corner of the camera's frame: white (albedo 0.8) and mid-grey (0.18).
    Each stands on whatever is seen at its place in the frame (the ground, the bench, the part itself): a ray from the
    camera finds that surface and the card is set just clear of it, facing the camera, so it is lit as the scene is
    there and nothing hides it. Where the ray meets nothing the card floats at the subject's depth. They cast no
    shadow and are not seen in reflections. Read the exposure of any review frame off them: the white one must not
    clip (it reads about 0.9 in scene-linear where it faces the key)."""
    sc = bpy.context.scene
    for n in ('rv_card_white', 'rv_card_grey'):
        o = bpy.data.objects.get(n)
        if o:
            bpy.data.objects.remove(o, do_unlink=True)
    if not CARDS or cam is None:
        return
    d = float(cam.get('rv_dist', 0.5))
    rx, ry = sc.render.resolution_x, sc.render.resolution_y
    asp = rx / ry
    cd = cam.data
    if cd.type == 'ORTHO':
        big = cd.ortho_scale
    elif cd.sensor_fit == 'VERTICAL':
        big = None
        h = 2 * d * math.tan(cd.angle_y / 2); w = h * asp
    else:
        big = d * cd.sensor_width / cd.lens
    if big is not None:
        w, h = (big, big / asp) if asp >= 1 else (big * asp, big)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    Mc = cam.matrix_world.copy()
    R = Mc.to_3x3()
    right, up, fwd = (R @ Vector((1, 0, 0))).normalized(), (R @ Vector((0, 1, 0))).normalized(), (R @ Vector((0, 0, -1))).normalized()
    s0 = 0.04 * w                      # the card's size at the subject's depth: 4 % of the frame's width
    for i, (n, alb) in enumerate((('rv_card_white', 0.8), ('rv_card_grey', 0.18))):
        fx, fy = -w / 2 + s0 * (0.75 + 1.12 * i), -h / 2 + s0 * 0.75          # where it goes in the frame, at depth d
        if cd.type == 'ORTHO':
            org = Mc @ Vector((fx, fy, 0)); dirv = fwd
        else:
            org = Mc.translation.copy(); dirv = (R @ Vector((fx, fy, -d))).normalized()
        hit = None
        o2 = org.copy()
        for _ in range(8):             # the first thing the render will show there
            try:
                ok, loc, nrm, idx, ob, mat = sc.ray_cast(dg, o2, dirv)
            except Exception:
                ok = False
            if not ok:
                break
            if ob is None or ob.hide_render or ob.type != 'MESH':
                o2 = loc + dirv * 1e-5
                continue
            hit = (loc.copy(), nrm.copy())
            break
        centre = Mc @ Vector((fx, fy, -d)); s = s0
        if hit is not None:
            loc, nrm = hit
            if nrm.dot(dirv) > 0:
                nrm = -nrm
            t = (loc - Mc.translation).dot(fwd)
            if cd.type != 'ORTHO':
                s = s0 * max(t, 1e-4) / d
            centre = loc + nrm * (s / 2 * (abs(up.dot(nrm)) + abs(right.dot(nrm))) + 0.0005)
        me = bpy.data.meshes.new(n)
        q = s / 2
        me.from_pydata([(-q, -q, 0), (q, -q, 0), (q, q, 0), (-q, q, 0)], [], [(0, 1, 2, 3)])
        o = bpy.data.objects.new(n, me)
        sc.collection.objects.link(o)
        m = bpy.data.materials.get(n) or bpy.data.materials.new(n)
        m.use_nodes = True
        nt = m.node_tree; nt.nodes.clear()
        out = nt.nodes.new('ShaderNodeOutputMaterial'); df = nt.nodes.new('ShaderNodeBsdfDiffuse')
        df.inputs['Color'].default_value = (alb, alb, alb, 1); nt.links.new(df.outputs[0], out.inputs[0])
        me.materials.append(m)
        Mo = R.to_4x4(); Mo.translation = centre
        o.matrix_world = Mo
        for a in ('visible_shadow', 'visible_glossy', 'visible_diffuse', 'visible_transmission'):
            try:
                setattr(o, a, False)
            except Exception:
                pass


def studio(samples=48, res=(1500, 1000), strength=1.0, ground_z=None, ground_col=(0.05, 0.05, 0.052), transparent=False, threads=16,
           warm=None):
    """Neutral studio: grey backdrop for the camera, a soft sky gradient for light, a key and a cool rim.
    warm (or review.WARM): the accepted look of the bench is under one warm work lamp, about 3000 K, and hues judged
    under the neutral rig mislead (SEAM.md section 8). The warm rig has a 3000 K key from above, a dim neutral fill
    and a quarter of the sky."""
    warm = WARM if warm is None else warm
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    except Exception:
        pass
    sc.cycles.max_bounces = 6
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = transparent
    sc.render.threads_mode = 'FIXED'; sc.render.threads = threads
    sc.view_settings.view_transform = 'AgX'
    try:
        sc.view_settings.look = 'AgX - Base Contrast'
    except Exception:
        pass
    sc.render.image_settings.file_format = 'PNG'
    w = bpy.data.worlds.new('studio'); sc.world = w
    w.use_nodes = True
    nt = w.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld')
    tc = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Generated'], sep.inputs[0])
    ramp = nt.nodes.new('ShaderNodeMapRange'); ramp.clamp = True
    ramp.inputs['From Min'].default_value = -0.4; ramp.inputs['From Max'].default_value = 1.0
    ramp.inputs['To Min'].default_value = 0.10; ramp.inputs['To Max'].default_value = 1.0
    nt.links.new(sep.outputs['Z'], ramp.inputs['Value'])
    R = RIG['warm' if warm else 'neutral']
    light = nt.nodes.new('ShaderNodeBackground'); light.inputs[0].default_value = (*R['sky_col'], 1)
    mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = strength * R['sky']
    nt.links.new(ramp.outputs[0], mul.inputs[0]); nt.links.new(mul.outputs[0], light.inputs[1])
    cam = nt.nodes.new('ShaderNodeBackground'); cam.inputs[0].default_value = (*BG, 1); cam.inputs[1].default_value = 1.0
    lp = nt.nodes.new('ShaderNodeLightPath'); mix = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(lp.outputs['Is Camera Ray'], mix.inputs[0])
    nt.links.new(light.outputs[0], mix.inputs[1]); nt.links.new(cam.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])
    rigs = (('key', (-0.5, -0.9, 1.1), R['key'], (1.0, 0.95, 0.88), 0.9), ('rim', (0.8, 0.9, 0.7), R['rim'], (0.85, 0.92, 1.0), 0.7),
            ('fill', (0.6, -0.8, -0.3), R['fill'], (1, 1, 1), 1.2))
    if warm:        # 3000 K in linear sRGB is about (1.0, 0.71, 0.42)
        rigs = (('key', (-0.25, -0.55, 1.25), R['key'], (1.0, 0.71, 0.42), 0.5), ('rim', (0.8, 0.9, 0.7), R['rim'], (1.0, 0.8, 0.6), 0.7),
                ('fill', (0.6, -0.8, -0.3), R['fill'], (1, 0.9, 0.8), 1.2))
    for nm, loc, energy, col, size in rigs:
        ld = bpy.data.lights.new(nm, 'AREA'); ld.energy = energy; ld.color = col; ld.size = size
        lo = bpy.data.objects.new('light_' + nm, ld); sc.collection.objects.link(lo)
        lo.location = loc
        lo.rotation_euler = Vector(loc).to_track_quat('Z', 'Y').to_euler()
    if ground_z is not None:
        ground(ground_z, ground_col)
    return sc


def ground(z, col=(0.05, 0.05, 0.052), size=4.0, rough=0.85):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, z))
    g = bpy.context.active_object; g.name = 'review_ground'
    m = bpy.data.materials.new('review_ground'); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*col, 1); b.inputs['Roughness'].default_value = rough
    g.data.materials.append(m)
    return g


def render(path, cam, res=None, samples=None):
    sc = bpy.context.scene
    sc.camera = cam
    if res:
        sc.render.resolution_x, sc.render.resolution_y = res
    if samples:
        sc.cycles.samples = samples
    sc.render.filepath = path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cards(cam)
    bpy.ops.render.render(write_still=True)
    return path


def clay(objs, col=(0.55, 0.55, 0.55), rough=0.6):
    """Grey clay on every object (for reference renders of a skin and for form checks)."""
    m = bpy.data.materials.new('clay'); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*col, 1); b.inputs['Roughness'].default_value = rough
    for o in objs:
        if o.type == 'MESH':
            o.data.materials.clear(); o.data.materials.append(m)
            for p in o.data.polygons:
                p.material_index = 0
    return m


def explode(objs, f=1.5, extra=None):
    """Move every object that has a '<name>__clear' empty toward (and past, f > 1) that pose. extra: {name: Vector}
    additional world offsets (also for parts with no clear pose). Returns restore().
    Parts are unparented while they are apart: setting the world matrix of a bone-parented object is off by the bone's
    length, and an imported GLB gives its bones other lengths (a cell flew a metre away, 20 Nov)."""
    vl = bpy.context.view_layer
    vl.update()
    todo = []
    for o in objs:
        c = bpy.data.objects.get(o.name + '__clear')
        if c is None and not (extra and o.name in extra):
            continue
        mw = o.matrix_world.copy()
        new = mw.copy()
        if c is not None:
            cw = c.matrix_world.copy()
            if f >= 1:
                new = Matrix.LocRotScale(mw.translation + (cw.translation - mw.translation) * f, cw.to_quaternion(), mw.to_scale())
            else:
                new = Matrix.LocRotScale(mw.translation.lerp(cw.translation, f), mw.to_quaternion().slerp(cw.to_quaternion(), f), mw.to_scale())
        if extra and o.name in extra:
            new.translation = new.translation + Vector(extra[o.name])
        todo.append((o, new))
    saved = []
    kids = {}
    for o, new in todo:        # children keep their world pose unless they are moved themselves
        for ch in o.children:
            kids.setdefault(ch.name, ch.matrix_world.copy())
    for o, new in todo:
        saved.append((o, o.parent, o.parent_type, o.parent_bone, o.matrix_parent_inverse.copy(), o.matrix_basis.copy()))
        o.parent = None
        o.matrix_world = new
    vl.update()
    moved = {o.name for o, _ in todo}
    kid_saved = []
    for name, mw in kids.items():
        if name in moved:
            continue
        ch = bpy.data.objects[name]
        kid_saved.append((ch, ch.matrix_basis.copy()))
        ch.matrix_world = mw
    vl.update()

    def restore():
        for ch, mb in kid_saved:
            ch.matrix_basis = mb
        for o, par, pt, pb, mpi, mb in saved:
            o.parent = par
            o.parent_type = pt
            if pt == 'BONE':
                o.parent_bone = pb
            o.matrix_parent_inverse = mpi
            o.matrix_basis = mb
        vl.update()
    return restore


def contact_sheet(paths, out, cols=3, labels=None, width=900, bg='#2e2e2e'):
    """Tile images with ImageMagick montage (labels under each tile)."""
    paths = [p for p in paths if os.path.exists(p)]
    if not paths:
        return None
    cmd = ['montage']
    for i, p in enumerate(paths):
        cmd += ['-label', (labels[i] if labels else os.path.splitext(os.path.basename(p))[0]), p]
    cmd += ['-tile', '%dx' % cols, '-geometry', '%dx+6+6' % width, '-background', bg, '-fill', 'white', '-pointsize', '22', out]
    subprocess.run(cmd, check=False)
    return out


def beside(left, right, out, height=1800, bg='#2e2e2e'):
    """Two images side by side at one height: the reference sheet on the left, our renders on the right."""
    if not (os.path.exists(left) and os.path.exists(right)):
        return None
    subprocess.run(['magick', '(', left, '-resize', 'x%d' % height, ')', '(', right, '-resize', 'x%d' % height, ')',
                    '-background', bg, '+append', out], check=False)
    return out


def family_objects():
    """Mesh objects of the family in the open scene: everything that carries the kit's 'sh_id' property."""
    return [o for o in bpy.data.objects if o.type == 'MESH' and 'sh_id' in o]


def render_family(outdir, objs=None, samples=48, only=None, center=None, size=None, tag='', bench_yaw=-90.0,
                  hero=(), explode_f=1.5, explode_extra=None, res=(1500, 1000), explode_all=None):
    """The standard review set of a family. Returns {name: path}. hero: object names that get their own 0.3 m view."""
    import kitload
    ME = kitload.load('measure')           # by file: pistol/ has a measure.py of its own
    objs = objs or family_objects()
    lo, hi = ME.bounds(objs)
    c = Vector(center) if center is not None else Vector((lo + hi) / 2)
    ext = float(max(hi - lo)) if size is None else size
    only = set(only) if only else {'six', 'bench', 'close', 'exploded'}
    out = {}
    os.makedirs(outdir, exist_ok=True)
    P = lambda n: os.path.join(outdir, '%s%s.png' % (tag, n))
    if 'six' in only:
        cams = six_views(c, dist=max(0.6, ext * 3), ortho=ext * 1.18)
        for n, cam in cams.items():
            out[n] = render(P(n), cam, res, samples)
        out['six_sheet'] = contact_sheet([out[n] for n in ('left', 'right', 'front', 'back', 'top', 'threeq')], P('six_sheet'), cols=3)
    g = None
    if only & {'bench', 'close', 'exploded'}:
        g = ground(float(lo[2]) - 0.0002)
    if 'bench' in only:
        out['bench'] = render(P('bench'), bench_cam(c, yaw=bench_yaw), res, samples)
    if 'close' in only:
        out['close'] = render(P('close'), close_cam(c, yaw=bench_yaw + 20, fit=ext), res, samples)
        out['close_rear'] = render(P('close_rear'), close_cam(c, yaw=bench_yaw + 200, name='cam_close_rear', fit=ext), res, samples)
        for h in hero:
            o = bpy.data.objects.get(h)
            if o:
                hl, hh = ME.bounds([o])
                out['close_' + h] = render(P('close_' + h), close_cam(Vector((hl + hh) / 2), yaw=bench_yaw + 20, name='cam_close_' + h,
                                                                      fit=float(max(hh - hl))), res, samples)
    if 'exploded' in only:
        if g:
            g.hide_render = True
        restore = explode(explode_all or objs, explode_f, explode_extra)
        lo2, hi2 = ME.bounds(objs)
        c2 = Vector((lo2 + hi2) / 2); e2 = float(max(hi2 - lo2))
        cam = look_cam('cam_exploded', c2, Vector((-0.55, -0.9, 0.45)).normalized() * max(0.25, e2 * 2.5), lens=60)
        out['exploded'] = render(P('exploded'), cam, res, samples)
        cam2 = look_cam('cam_exploded_side', c2, (0, -max(0.6, e2 * 3), 0), ortho=e2 * 1.2)
        out['exploded_side'] = render(P('exploded_side'), cam2, res, samples)
        restore()
        if g:
            g.hide_render = False
    return out


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []

    def opt(k, d=None, cast=str):
        return cast(argv[argv.index(k) + 1]) if k in argv else d
    fam_dir = os.path.abspath(opt('--family'))
    fam = os.path.basename(fam_dir.rstrip('/'))
    samples = opt('--samples', 48, int)
    only = opt('--only'); only = only.split(',') if only else None
    tag = opt('--tag', '')
    global WARM
    WARM = '--warm' in argv
    if WARM:
        tag = (tag or '') + 'warm_'
    if '--glb' in argv:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=os.path.join(fam_dir, 'export', fam + '.glb'))
        pj = json.load(open(os.path.join(fam_dir, 'export', 'parts.json')))
        sc = pj.get('unit_scale_m', 1.0)
        if sc != 1.0:
            for o in bpy.data.objects:
                if o.parent is None:
                    o.matrix_world = Matrix.Scale(sc, 4) @ o.matrix_world
        nodes = {p['node'] for p in pj['parts']}      # not the importer's own helpers (it adds a 1 m 'Icosphere' as a bone shape)
        for o in bpy.data.objects:
            if o.type == 'MESH' and o.name not in nodes:
                o.hide_render = True
        objs = [o for o in bpy.data.objects if o.type == 'MESH' and o.name in nodes]
        tag = (tag or '') + 'glb_'
    else:
        bpy.ops.wm.open_mainfile(filepath=os.path.join(fam_dir, 'export', fam + '.blend'))
        objs = family_objects()
    for o in bpy.data.objects:
        if o.type in ('CAMERA', 'LIGHT'):
            bpy.data.objects.remove(o)
    # <family>/export/review.json (written by Family.finish): nodes to leave out, the exploded arrangement, hero parts
    cfg = {}
    cp = os.path.join(fam_dir, 'export', 'review.json')
    if os.path.exists(cp):
        cfg = json.load(open(cp))
    hide = set(cfg.get('hide', []))
    for o in objs:
        o.hide_render = o.name in hide
    objs = [o for o in objs if o.name not in hide]
    ex = cfg.get('explode') or {}
    hero = (opt('--hero') or '').split(',') if opt('--hero') else cfg.get('hero', ())
    studio(samples=samples)
    out = render_family(os.path.join(fam_dir, 'review'), objs, samples=samples, only=only, tag=tag, hero=hero,
                        explode_f=ex.get('f', 1.5), explode_extra={k: Vector(v) for k, v in (ex.get('extra') or {}).items()} or None)
    xs = os.path.join(fam_dir, 'sheets', 'exploded.png')
    if out.get('exploded') and os.path.exists(xs):
        beside(xs, out['exploded'], os.path.join(fam_dir, 'review', tag + 'compare_exploded.jpg'), height=1200)
    sheet = os.path.join(fam_dir, 'sheets', 'overall.png')
    if out.get('six_sheet') and os.path.exists(sheet):
        beside(sheet, out['six_sheet'], os.path.join(fam_dir, 'review', tag + 'compare_overall.jpg'))
    print('REVIEW', json.dumps(out))


if __name__ == '__main__':
    main()
