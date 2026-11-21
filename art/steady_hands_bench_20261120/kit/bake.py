# kit/bake.py: one atlas per family. Unwrap, Cycles CPU bake from the procedural materials (mats.py), runtime
# materials, GLB export. Generalised from art/pistol_mods_20260930/src/build_all.py (our own, 30 Sep 2026).
#
#   uv = BK.unwrap(objs, size, weights={'pistol_frame': 1.3})      # smart project, one shared atlas
#   tex = BK.bake(objs, family, outdir, size=2048, spp=24)         # color, normal (OpenGL +Y), orm (glTF), emit
#   BK.assign_runtime(objs, family, tex)                           # 'M_<family>' (+ '_emissive'), passthroughs kept
#   BK.export_glb(path, select)                                    # export_yup, tangents, extras, NLA actions
#   BK.filter_animations(path, {'cell_latch_param': ['cell_latch']})   # each clip moves only its own bone
#
# Textures: <outdir>/tex/<family>_{color,normal,orm,emit}.png and, for parts with wipes, the as-found set
# <outdir>/tex/<family>__dirty_{color,normal,orm}.png (same UVs: ONE dirty atlas per family, listed under each part's
# 'wipes' in parts.json; CONTRACT.md words it per part, the file is shared because the UVs are).
# Bakes are self-only (the Bevel and AO nodes look at the object alone), so a part lifted off shows no baked shadow
# of its neighbour.
import bpy, bmesh, math, os, json, struct, time
import numpy as np
from mathutils import Vector, Matrix
import mats as MT

T0 = time.time()


def log(*a):
    print('[%6.1fs]' % (time.time() - T0), *a, flush=True)


def _select(objs, active=None):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active or objs[0]


def _align_islands(me):
    """Turn every UV island so that its smallest bounding rectangle lies along the UV axes (the packer packs boxes and
    only turns islands by quarter turns: a big face that lies at 25 degrees wastes half its box). Returns the count."""
    from bpy_extras import mesh_utils
    from mathutils import geometry
    uv = me.uv_layers.active.data
    n = 0
    for isl in mesh_utils.mesh_linked_uv_islands(me):
        li = [l for pi in isl for l in me.polygons[pi].loop_indices]
        pts = [uv[l].uv.copy() for l in li]
        if len(pts) < 3:
            continue
        try:
            a = geometry.box_fit_2d(pts)
        except Exception:
            continue
        best = None
        for ang in (0.0, a, -a):          # whichever way the angle is meant, keep the turn that gives the smaller box
            c, sn = math.cos(ang), math.sin(ang)
            q = [(p.x * c - p.y * sn, p.x * sn + p.y * c) for p in pts]
            w = max(x for x, y in q) - min(x for x, y in q); h = max(y for x, y in q) - min(y for x, y in q)
            if best is None or w * h < best[0] * 0.98:
                best = (w * h, q)
        if best[1] is not None:
            for l, (x, y) in zip(li, best[1]):
                uv[l].uv = (x, y)
            n += 1
    return n


def unwrap(objs, size, weights=None, angle=58.0, margin_px=5.0, shape='AABB', align=False):
    """Smart-project every object and pack them all into one atlas at one texel density. weights: {object name: factor}
    more (or less) texels for a part. align: turn each island to its smallest bounding rectangle before packing
    (Family: F.uv_align = True; off by default so a built family's atlas does not move). Returns per-object texels per
    millimetre and the fill."""
    objs = [o for o in objs if o.type == 'MESH' and len(o.data.polygons)]
    for o in objs:
        if o.data.users > 1:
            o.data = o.data.copy()
        while len(o.data.uv_layers) > 0:
            o.data.uv_layers.remove(o.data.uv_layers[0])
        o.data.uv_layers.new(name='UVMap')
    _select(objs)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.average_islands_scale()
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in objs:
        f = (weights or {}).get(o.name, 1.0)
        uv = o.data.uv_layers.active.data
        skip = [bool(m and m.get('passthrough', 0)) for m in o.data.materials] or [False]
        for p in o.data.polygons:
            k = 0.02 if skip[min(p.material_index, len(skip) - 1)] else f      # not 0: zero-area islands make the packer shrink everything
            if k != 1.0:
                for li in p.loop_indices:
                    uv[li].uv = uv[li].uv * k
        if align:
            _align_islands(o.data)
    _select(objs)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.select_all(action='SELECT')
    m = min(margin_px / size, 0.0025)      # 5 px at 2048; at 512 the same 5 px starved a family of thousands of islands
    # AABB packing: measured on the example, it fills as well as CONCAVE here and takes no time; CONCAVE and CONVEX
    # with rotation took minutes (20 Nov) and hold the shared Blender slot.
    try:
        bpy.ops.uv.pack_islands(rotate=True, margin_method='FRACTION', margin=m, shape_method=shape)
    except TypeError:
        bpy.ops.uv.pack_islands(rotate=True, margin=m)
    bpy.ops.object.mode_set(mode='OBJECT')
    out = {}
    fill = 0.0
    for o in objs:
        me = o.data
        uv = me.uv_layers.active.data
        a3 = a2 = 0.0
        for p in me.polygons:
            pts = [uv[li].uv for li in p.loop_indices]
            aa = 0.0
            for i in range(1, len(pts) - 1):
                aa += abs((pts[i] - pts[0]).cross(pts[i + 1] - pts[0])) / 2
            if aa > 0:
                a3 += p.area; a2 += aa
        fill += a2
        out[o.name] = {'uv_fraction': round(a2, 4), 'px_per_cm': round(math.sqrt(a2 * size * size / max(a3 * 1e4, 1e-12)), 1)}
    return {'size': size, 'fill': round(fill, 3), 'objects': out}


def _new_img(name, size, noncolor):
    im = bpy.data.images.new(name, size, size, alpha=True, float_buffer=False)
    im.colorspace_settings.name = 'Non-Color' if noncolor else 'sRGB'
    im.pixels.foreach_set(np.zeros(size * size * 4, np.float32))
    return im


def _mats_of(objs):
    ms = []
    for o in objs:
        for s in o.material_slots:
            m = s.material
            if m and m not in ms and not m.get('passthrough', 0):
                if not (m.use_nodes and m.node_tree.nodes.get('CH_base')):
                    raise ValueError('material %s on %s was not made by mats.make (no CH_base tap)' % (m.name, o.name))
                ms.append(m)
    return ms


def _target(ms, img):
    for m in ms:
        nt = m.node_tree
        n = nt.nodes.get('BAKE_TGT') or nt.nodes.new('ShaderNodeTexImage')
        n.name = 'BAKE_TGT'; n.image = img
        nt.nodes.active = n


def _route(ms, channel):
    for m in ms:
        nt = m.node_tree
        out = nt.nodes['OUT']
        em = nt.nodes.get('BAKE_EM') or nt.nodes.new('ShaderNodeEmission')
        em.name = 'BAKE_EM'; em.inputs['Strength'].default_value = 1.0
        for l in list(em.inputs['Color'].links):
            nt.links.remove(l)
        if channel is None:
            nt.links.new(nt.nodes['BSDF'].outputs[0], out.inputs['Surface'])
        else:
            nt.links.new(nt.nodes['CH_' + channel].outputs[0], em.inputs['Color'])
            nt.links.new(em.outputs[0], out.inputs['Surface'])


def _bake_pass(objs, ms, kind, channel, img, samples):
    sc = bpy.context.scene
    _target(ms, img)
    _route(ms, channel)
    sc.cycles.samples = samples
    for o in objs:
        _select([o])
        if kind == 'NORMAL':
            bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT', normal_r='POS_X', normal_g='POS_Y', normal_b='POS_Z',
                                margin=0, use_clear=False)
        else:
            bpy.ops.object.bake(type='EMIT', margin=0, use_clear=False)
    _route(ms, None)
    log('baked', kind, channel or '', len(objs), 'objects')


def _arr(img, size):
    a = np.empty(size * size * 4, np.float32); img.pixels.foreach_get(a)
    return a.reshape(size, size, 4)


def _dilate(a, iters=16):
    """Grow baked texels into the gutters (so mips do not bleed the background in)."""
    rgb = a[..., :3].copy()
    filled = a[..., 3] > 0.5
    for _ in range(iters):
        if filled.all():
            break
        acc = np.zeros_like(rgb); cnt = np.zeros(filled.shape, np.float32)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            sf = np.roll(np.roll(filled, dy, 0), dx, 1)
            acc += np.roll(np.roll(rgb, dy, 0), dx, 1) * sf[..., None]; cnt += sf
        new = (~filled) & (cnt > 0)
        rgb[new] = acc[new] / cnt[new][:, None]
        filled = filled | new
    if filled.any() and not filled.all():
        rgb[~filled] = rgb[filled].mean(0)
    return rgb


def _save(name, rgb, path, size, noncolor, alpha=None):
    out = np.ones((size, size, 4), np.float32)
    out[..., :3] = np.clip(rgb, 0, 1)
    if alpha is not None:
        out[..., 3] = alpha
    old = bpy.data.images.get(name)
    if old:
        bpy.data.images.remove(old)
    im = bpy.data.images.new(name, size, size, alpha=True, float_buffer=False)
    im.colorspace_settings.name = 'Non-Color' if noncolor else 'sRGB'
    im.pixels.foreach_set(out.ravel())
    im.filepath_raw = path; im.file_format = 'PNG'
    im.save()
    im.filepath = path
    return im


def bake(objs, family, outdir, size=2048, spp=24, threads=16, dilate=16):
    """Bake the family atlas. Returns {'color': image, 'normal': .., 'orm': .., 'emit': .. or None, 'dirty': {..} or
    None, 'stats': {...}}. objs must be unwrapped (unwrap) and carry mats.make materials."""
    objs = [o for o in objs if o.type == 'MESH' and len(o.data.polygons)]
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.use_adaptive_sampling = False
    sc.cycles.use_denoising = False
    sc.render.threads_mode = 'FIXED'; sc.render.threads = threads
    sc.render.bake.margin = 0
    sc.render.bake.use_clear = False
    tex = os.path.join(outdir, 'tex'); os.makedirs(tex, exist_ok=True)
    ms = _mats_of(objs)
    MT.set_dirty(ms, 0.0)
    res = {'stats': {'size': size, 'spp': spp}}

    def run(tag, obs, with_emit):
        IM = {'color': _new_img('_b_color', size, False), 'orm': _new_img('_b_orm', size, True), 'normal': _new_img('_b_normal', size, True)}
        mm = _mats_of(obs)
        _bake_pass(obs, mm, 'EMIT', 'base', IM['color'], spp)
        _bake_pass(obs, mm, 'EMIT', 'orm', IM['orm'], max(spp, 24))
        _bake_pass(obs, mm, 'NORMAL', None, IM['normal'], spp)
        emit_objs = [o for o in obs if any(s.material and s.material.get('emissive', 0) for s in o.material_slots)]
        if with_emit and emit_objs:
            IM['emit'] = _new_img('_b_emit', size, False)
            _bake_pass(emit_objs, _mats_of(emit_objs), 'EMIT', 'emit', IM['emit'], max(8, spp // 2))
        out = {}
        cover = None
        for k, im in IM.items():
            a = _arr(im, size)
            if cover is None:
                cover = float((a[..., 3] > 0.5).mean())
            rgb = _dilate(a, dilate)
            del a
            if k == 'emit':
                rgb[_arr(IM['emit'], size)[..., 3] < 0.5] = 0.0      # black outside the emitters
            out[k] = _save('%s%s_%s' % (family, tag, k), rgb, os.path.join(tex, '%s%s_%s.png' % (family, tag, k)), size, k != 'color' and k != 'emit')
            bpy.data.images.remove(im)
            del rgb
        return out, cover

    clean, cover = run('', objs, True)
    res.update(clean); res.setdefault('emit', None)
    res['stats']['coverage'] = round(cover, 3)
    wipe_objs = [o for o in objs if any(s.material and s.material.get('wipe', 0) for s in o.material_slots)]
    res['dirty'] = None
    if wipe_objs:
        MT.set_dirty(ms, 1.0)
        dirty, _ = run('__dirty', wipe_objs, False)
        MT.set_dirty(ms, 0.0)
        res['dirty'] = dirty
        res['stats']['dirty_objects'] = [o.name for o in wipe_objs]
    log('textures saved', res['stats'])
    return res


def _runtime_mat(name, tex, emissive):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    tb = nt.nodes.new('ShaderNodeTexImage'); tb.image = tex['color']
    nt.links.new(tb.outputs['Color'], b.inputs['Base Color'])
    to = nt.nodes.new('ShaderNodeTexImage'); to.image = tex['orm']
    sp = nt.nodes.new('ShaderNodeSeparateColor')
    nt.links.new(to.outputs['Color'], sp.inputs[0])
    nt.links.new(sp.outputs['Green'], b.inputs['Roughness'])
    nt.links.new(sp.outputs['Blue'], b.inputs['Metallic'])
    tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = tex['normal']
    nm = nt.nodes.new('ShaderNodeNormalMap')
    nt.links.new(tn.outputs['Color'], nm.inputs['Color'])
    nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    grp = bpy.data.node_groups.get('glTF Material Output')
    if not grp:      # the exporter reads occlusion from a group of this name
        grp = bpy.data.node_groups.new('glTF Material Output', 'ShaderNodeTree')
        grp.interface.new_socket('Occlusion', in_out='INPUT', socket_type='NodeSocketFloat')
    gn = nt.nodes.new('ShaderNodeGroup'); gn.node_tree = grp
    nt.links.new(sp.outputs['Red'], gn.inputs['Occlusion'])
    if emissive and tex.get('emit'):
        te = nt.nodes.new('ShaderNodeTexImage'); te.image = tex['emit']
        nt.links.new(te.outputs['Color'], b.inputs['Emission Color'])
        b.inputs['Emission Strength'].default_value = 8.0      # mats.make stores colour x strength / 8
    m.use_backface_culling = True
    return m


def assign_runtime(objs, family, tex):
    """Replace the authoring materials by 'M_<family>' and 'M_<family>_emissive' (same atlas); passthrough materials
    (glass) stay. Returns triangles per runtime material."""
    M0 = _runtime_mat('M_' + family, tex, False)
    M1 = _runtime_mat('M_%s_emissive' % family, tex, True) if tex.get('emit') else None
    count = {}
    for o in objs:
        if o.type != 'MESH':
            continue
        me = o.data
        old = [s.material for s in o.material_slots]
        new, remap = [], {}
        for i, m in enumerate(old):
            if m is not None and m.get('passthrough', 0):
                tgt = m
            elif m is not None and m.get('emissive', 0) and M1:
                tgt = M1
            else:
                tgt = M0
            if tgt not in new:
                new.append(tgt)
            remap[i] = new.index(tgt)
        idx = [remap.get(p.material_index, 0) for p in me.polygons]
        me.materials.clear()
        for m in new or [M0]:
            me.materials.append(m)
        for p, i in zip(me.polygons, idx):
            p.material_index = i
            nm = me.materials[i].name
            count[nm] = count.get(nm, 0) + len(p.vertices) - 2
    return count


def export_glb(path, objs, animations=False):
    """Export the given objects (meshes, helper empties, the rig) as one GLB: Y up, tangents, extras, applied modifiers,
    and with animations=True every NLA track as its own clip."""
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.hide_set(False); o.hide_viewport = False
        o.select_set(True)
    bpy.context.view_layer.objects.active = next((o for o in objs if o.type == 'MESH'), objs[0])
    kw = dict(filepath=path, export_format='GLB', use_selection=True, export_apply=True, export_yup=True,
              export_texcoords=True, export_normals=True, export_tangents=True, export_materials='EXPORT',
              export_image_format='AUTO', export_extras=True, export_cameras=False, export_lights=False,
              export_animations=animations)
    if animations:
        kw.update(export_animation_mode='NLA_TRACKS', export_force_sampling=True, export_optimize_animation_size=True,
                  export_optimize_animation_keep_anim_armature=False, export_def_bones=False, export_frame_range=False,
                  export_anim_slide_to_zero=True, export_bake_animation=False)
    try:
        bpy.ops.export_scene.gltf(**kw)
    except TypeError as e:      # an option this Blender does not have: fall back to the essentials
        log('export option not accepted (%s); retrying with the essentials' % e)
        for k in ('export_optimize_animation_keep_anim_armature', 'export_anim_slide_to_zero', 'export_bake_animation', 'export_frame_range'):
            kw.pop(k, None)
        bpy.ops.export_scene.gltf(**kw)
    log('exported', path, os.path.getsize(path) // 1024, 'KB')
    return path


def read_glb(path):
    d = open(path, 'rb').read()
    magic, ver, total = struct.unpack('<III', d[:12])
    n, t = struct.unpack('<II', d[12:20])
    js = json.loads(d[20:20 + n].decode('utf8'))
    rest = d[20 + n:]
    return js, rest


def write_glb(path, js, rest):
    body = json.dumps(js, separators=(',', ':')).encode('utf8')
    body += b' ' * ((4 - len(body) % 4) % 4)
    total = 12 + 8 + len(body) + len(rest)
    with open(path, 'wb') as f:
        f.write(struct.pack('<III', 0x46546C67, 2, total))
        f.write(struct.pack('<II', len(body), 0x4E4F534A))
        f.write(body); f.write(rest)


def filter_animations(path, keep):
    """Make each clip move only its own nodes. keep: {clip name: [node names]}. A sampled export writes a channel for
    every bone into every clip, so sampling one parameter's clip would reset the others. Returns {clip: channels kept}."""
    js, rest = read_glb(path)
    names = {i: n.get('name', '') for i, n in enumerate(js.get('nodes', []))}
    out = {}
    for an in js.get('animations', []):
        allowed = keep.get(an.get('name'))
        if allowed is None:
            continue
        ch = [c for c in an['channels'] if names.get(c['target'].get('node')) in allowed]
        used = sorted({c['sampler'] for c in ch})
        remap = {s: i for i, s in enumerate(used)}
        an['samplers'] = [an['samplers'][s] for s in used]
        for c in ch:
            c['sampler'] = remap[c['sampler']]
        an['channels'] = ch
        out[an['name']] = len(ch)
    write_glb(path, js, rest)
    return out


def glb_summary(path):
    """Node, mesh, material, image and animation facts read straight from the GLB's JSON (no import)."""
    js, _ = read_glb(path)
    acc = js.get('accessors', [])
    anims = {}
    for an in js.get('animations', []):
        tmax = 0.0
        for s in an['samplers']:
            a = acc[s['input']]
            tmax = max(tmax, (a.get('max') or [0])[0])
        anims[an.get('name')] = {'channels': len(an['channels']), 'seconds': round(tmax, 4),
                                 'nodes': sorted({js['nodes'][c['target']['node']].get('name', '') for c in an['channels']})}
    return {'nodes': len(js.get('nodes', [])), 'meshes': len(js.get('meshes', [])),
            'materials': [m.get('name') for m in js.get('materials', [])],
            'images': len(js.get('images', [])), 'animations': anims,
            'node_names': [n.get('name', '') for n in js.get('nodes', [])],
            'extras_nodes': [n.get('name') for n in js.get('nodes', []) if n.get('extras')]}


def export_merged(path, groups, scale=1.0):
    """A few-node copy of a family for where it is only looked at (in the hand): each group of parts joined into one
    node with an identity transform, mesh data multiplied by `scale` (1 / 0.13674 puts a pistol part into
    ScrapPistol.glb units). Call after the bake, when the parts carry the runtime materials. groups: {node name: [objects]}.
    Returns {node name: triangles}."""
    made = []
    for name, objs in groups.items():
        dups = []
        bpy.context.view_layer.update()
        for o in objs:
            mw = o.evaluated_get(bpy.context.evaluated_depsgraph_get()).matrix_world.copy()
            d = o.copy(); d.data = o.data.copy()
            bpy.context.scene.collection.objects.link(d)
            d.parent = None
            d.matrix_world = Matrix.Identity(4)
            d.data.transform(Matrix.Scale(scale, 4) @ mw)
            for k in list(d.keys()):
                del d[k]
            dups.append(d)
        _select(dups)
        if len(dups) > 1:
            bpy.ops.object.join()
        j = bpy.context.view_layer.objects.active
        j.name = name; j.data.name = name
        made.append(j)
    export_glb(path, made, animations=False)
    out = {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in made}
    for o in made:
        bpy.data.objects.remove(o, do_unlink=True)
    return out
