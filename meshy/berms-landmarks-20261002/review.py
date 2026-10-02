"""Berms landmarks: Blender 5.2 headless inspection (Cycles CPU, small renders). Run through the capped wrapper:
  ~/.local/state/ward-programme/blender.sh /abs/review.py -- source <subject> <attempt> [yaw]
  ~/.local/state/ward-programme/blender.sh /abs/review.py -- prepared <LandmarkId>

source:   the Meshy download <subject>/<attempt>/model.glb as delivered. Writes <subject>/<attempt>/review/stats.json
          (triangles, loose parts, open/non-manifold edges, degenerate faces, images, source bounds, the footprint
          alignment yaw) and renders, after aligning the footprint to the axes (+ optional extra yaw) and scaling
          uniformly to the subject's nominal size: four axis views (labelled by the side they look at: -Y, +X, +Y, -X),
          two three-quarter views, two player-height views (eye 1.7 m) at 6 m and 2.5 m with a 1.8 m figure, a
          back-face check (back faces red) and a far-silhouette read at 300 m on a sand plane.
prepared: the Unity-ready LOD GLBs and extracted maps (Art/BermsExpanse/Landmarks/<Id>/), assembled as in the prefab:
          LOD0/LOD1/LOD2 side by side at near and far distances, player-height views, the collider boxes from the
          manifest drawn over the model, and far reads at 200 and 400 m.
Renders are 960 px wide JPEGs (renders/ stays untracked)."""
import bpy, bmesh, json, math, sys
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix
sys.path.insert(0, str(Path(__file__).resolve().parent))
from landmark_lib import import_join, coords, footprint_yaw  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
UNITY = ROOT / 'unity/AthenHill/Assets/AthenHill/Art/BermsExpanse/Landmarks'
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
MODE = args[0] if args else ""
# nominal sizes for inspection only: (axis, metres) — 'len' = longest horizontal extent, 'z' = height
NOMINAL = {'hauler': ('len', 10.5), 'derrick': ('z', 13.0), 'pylon': ('z', 14.0), 'tube': ('len', 10.0)}


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def stats(ob):
    me = ob.data
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    bm = bmesh.new(); bm.from_mesh(me)
    split_verts = len(bm.verts)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bm.verts.ensure_lookup_table(); bm.verts.index_update()
    open_edges = sum(1 for e in bm.edges if e.is_boundary)
    nonman = sum(1 for e in bm.edges if not e.is_manifold and not e.is_boundary)
    degenerate = sum(1 for f in bm.faces if f.calc_area() < 1e-12)
    co = np.array([v.co[:] for v in bm.verts]); parent = np.arange(len(bm.verts))

    def find(a):
        r = a
        while parent[r] != r: r = parent[r]
        while parent[a] != r: parent[a], a = r, parent[a]
        return r
    for e in bm.edges:
        ra, rb = find(e.verts[0].index), find(e.verts[1].index)
        if ra != rb: parent[ra] = rb
    roots = np.array([find(i) for i in range(len(parent))])
    ids, counts = np.unique(roots, return_counts=True)
    parts = []
    zmin = co[:, 2].min()
    for i, n in sorted(zip(ids, counts), key=lambda x: -x[1]):
        p = co[roots == i]
        parts.append({'verts': int(n), 'min': p.min(0).round(3).tolist(), 'max': p.max(0).round(3).tolist(),
                      'lifted_m': round(float(p[:, 2].min() - zmin), 3)})
    bm.free()
    imgs = {i.name: list(i.size) for i in bpy.data.images}
    return {'triangles': tris, 'vertices_split': split_verts, 'vertices_welded': len(co), 'loose_parts': len(parts),
            'parts_lt_50_verts': sum(1 for p in parts if p['verts'] < 50), 'largest_parts': parts[:15],
            'open_edges': open_edges, 'non_manifold_edges': nonman, 'degenerate_faces': degenerate,
            'materials': sorted({s.material.name for s in ob.material_slots if s.material}), 'images': imgs}


# ------------------------------------------------------------------ scene
def scene_setup(res=(960, 640), samples=24):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = samples; sc.cycles.use_denoising = True
    sc.render.threads_mode = 'FIXED'; sc.render.threads = 8
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.image_settings.file_format = 'JPEG'; sc.render.image_settings.quality = 88
    sc.view_settings.view_transform = 'AgX'
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[0].default_value = (0.58, 0.66, 0.78, 1)
    w.node_tree.nodes['Background'].inputs[1].default_value = 0.9
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sc.collection.objects.link(sun)
    sun.data.energy = 3.6; sun.data.angle = math.radians(1.5)
    sun.rotation_euler = (math.radians(50), 0, math.radians(-40))
    bpy.ops.mesh.primitive_plane_add(size=4000, location=(0, 0, 0))
    g = bpy.context.active_object; g.name = 'ground'
    gm = bpy.data.materials.new('ground'); gm.use_nodes = True
    b = gm.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (0.50, 0.40, 0.29, 1); b.inputs['Roughness'].default_value = 0.92
    g.data.materials.append(gm)
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.clip_end = 5000
    return sc, cam


def figure(loc):
    bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=0.2, depth=1.55, location=(loc[0], loc[1], 0.775))
    f = bpy.context.active_object
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.13, location=(loc[0], loc[1], 1.67))
    h = bpy.context.active_object
    fm = bpy.data.materials.new('figure'); fm.use_nodes = True
    fm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.8, 0.18, 0.12, 1)
    for o in (f, h): o.data.materials.append(fm)
    return [f, h]


def shoot(sc, cam, out, name, pos, target, lens=35.0, res=None):
    if res: sc.render.resolution_x, sc.render.resolution_y = res
    cam.location = pos
    cam.rotation_euler = (Vector(target) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()
    cam.data.type = 'PERSP'; cam.data.lens = lens
    sc.render.filepath = str(out / f'{name}.jpg')
    bpy.ops.render.render(write_still=True)
    print('render', sc.render.filepath, flush=True)


def backface_material(ob):
    """Front faces grey, back faces red (normals check)."""
    m = bpy.data.materials.new('backface'); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    geo = nt.nodes.new('ShaderNodeNewGeometry'); mix = nt.nodes.new('ShaderNodeMixRGB')
    mix.inputs[1].default_value = (0.6, 0.6, 0.6, 1); mix.inputs[2].default_value = (0.9, 0.05, 0.05, 1)
    nt.links.new(geo.outputs['Backfacing'], mix.inputs[0]); nt.links.new(mix.outputs[0], b.inputs['Base Color'])
    saved = [s.material for s in ob.material_slots]
    for s in ob.material_slots: s.material = m
    return saved


def standard_views(sc, cam, out, size, tag=''):
    """size = (x extent, y extent, height) of the object centred at the origin, base at z = 0."""
    sx, sy, h = size
    span = max(sx, sy, h * 1.4)
    d = span * 1.6 + 4
    mid = (0, 0, h * 0.5)
    for name, v in (('view_negY', (0, -1)), ('view_posX', (1, 0)), ('view_posY', (0, 1)), ('view_negX', (-1, 0))):
        shoot(sc, cam, out, tag + name, (v[0] * d, v[1] * d, h * 0.45 + 1.5), mid)
    shoot(sc, cam, out, tag + 'tq_front_left', (-d * 0.7, -d * 0.75, h * 0.6 + 3), (0, 0, h * 0.45))
    shoot(sc, cam, out, tag + 'tq_rear_right', (d * 0.7, d * 0.75, h * 0.6 + 3), (0, 0, h * 0.45))


def player_views(sc, cam, out, size, tag=''):
    sx, sy, h = size
    # 6 m from the -Y face, eye height 1.7 m, figure beside the object
    fy = -sy / 2
    figs = figure((sx * 0.25, fy - 1.2))
    shoot(sc, cam, out, tag + 'player_6m', (-1.5, fy - 6.0, 1.7), (0.5, 0, min(h * 0.4, 3.0)), lens=24)
    shoot(sc, cam, out, tag + 'player_2m5', (sx * 0.15, fy - 2.5, 1.7), (sx * 0.05, 0, 1.4), lens=24)
    shoot(sc, cam, out, tag + 'player_side_6m', (sx / 2 + 6.0, 1.0, 1.7), (0, 0, min(h * 0.4, 3.0)), lens=24)
    for f in figs: bpy.data.objects.remove(f, do_unlink=True)


def far_read(sc, cam, out, h, dist, tag='', yaw_deg=35):
    a = math.radians(-90 - yaw_deg)
    pos = (math.cos(a) * dist, math.sin(a) * dist, 1.7)
    # 60 degree vertical FOV at 16:9-ish framing, as in game; render small, as it would appear
    cam.data.sensor_fit = 'VERTICAL'; cam.data.sensor_height = 24
    lens = 24 / (2 * math.tan(math.radians(30)))
    shoot(sc, cam, out, f'{tag}far_{int(dist)}m', pos, (0, 0, h * 0.5), lens=lens, res=(960, 540))
    # the same position through an 8x lens: the silhouette as it reads at that distance, magnified
    shoot(sc, cam, out, f'{tag}far_{int(dist)}m_zoom8', pos, (0, 0, h * 0.5), lens=lens * 8, res=(960, 540))
    cam.data.sensor_fit = 'AUTO'; cam.data.sensor_width = 36


# ------------------------------------------------------------------ modes
def source(subject, attempt, extra_yaw):
    src = HERE / subject / attempt
    out = src / 'review'; out.mkdir(exist_ok=True)
    clear()
    ob = import_join(src / 'model.glb')
    me = ob.data
    co = coords(me)
    st = stats(ob)
    st['source_bounds'] = {'min': co.min(0).round(4).tolist(), 'max': co.max(0).round(4).tolist()}
    yaw = footprint_yaw(co) + extra_yaw
    me.transform(Matrix.Rotation(math.radians(yaw), 4, 'Z'))
    co = coords(me); mn, mx = co.min(0), co.max(0)
    axis, metres = NOMINAL[subject]
    ext = mx - mn
    s = metres / (max(ext[0], ext[1]) if axis == 'len' else ext[2])
    me.transform(Matrix.Scale(s, 4) @ Matrix.Translation((-(mn[0] + mx[0]) / 2, -(mn[1] + mx[1]) / 2, -mn[2])))
    me.update()
    co = coords(me); size = (co.max(0) - co.min(0)).round(3).tolist()
    st.update(align_yaw_deg=round(yaw, 2), extra_yaw_deg=extra_yaw, inspection_scale=round(s, 5), inspection_size_xyz_blender=size,
              nominal=list(NOMINAL[subject]))
    (out / 'stats.json').write_text(json.dumps(st, indent=1))
    print(json.dumps({k: v for k, v in st.items() if k != 'largest_parts'}), flush=True)
    sc, cam = scene_setup()
    standard_views(sc, cam, out, size)
    player_views(sc, cam, out, size)
    far_read(sc, cam, out, size[2], 300)
    saved = backface_material(ob)
    sc.render.resolution_x, sc.render.resolution_y = 960, 640
    d = max(size[0], size[1], size[2] * 1.4) * 1.6 + 4
    shoot(sc, cam, out, 'normals_tq_front_left', (-d * 0.7, -d * 0.75, size[2] * 0.6 + 3), (0, 0, size[2] * 0.45))
    shoot(sc, cam, out, 'normals_tq_rear_right', (d * 0.7, d * 0.75, size[2] * 0.6 + 3), (0, 0, size[2] * 0.45))
    for slot, m in zip(ob.material_slots, saved): slot.material = m


def U2B(u):
    """Unity local point -> Blender (glTF +Y up export, glTFast negates X): x = -ux, y = -uz, z = uy."""
    return Vector((-u[0], -u[2], u[1]))


def load_prepared(lid, man, lod, offset=(0, 0, 0)):
    """Import every part's LOD glb with its extracted maps (base colour, normal, URP mask -> metal/rough)."""
    e = man[lid]; objs = []
    for part in e['parts']:
        d = UNITY / lid
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=str(d / part['lods'][lod]))
        new = [o for o in set(bpy.data.objects) - before if o.type == 'MESH']
        m = bpy.data.materials.get('prep_' + part['name'])
        if m is None:
            m = bpy.data.materials.new('prep_' + part['name']); m.use_nodes = True
            nt = m.node_tree; b = nt.nodes['Principled BSDF']
            tb = nt.nodes.new('ShaderNodeTexImage'); tb.image = bpy.data.images.load(str(d / part['maps']['BaseColor']))
            nt.links.new(tb.outputs[0], b.inputs['Base Color'])
            tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = bpy.data.images.load(str(d / part['maps']['Normal']))
            tn.image.colorspace_settings.name = 'Non-Color'
            nm = nt.nodes.new('ShaderNodeNormalMap'); nt.links.new(tn.outputs[0], nm.inputs[1]); nt.links.new(nm.outputs[0], b.inputs['Normal'])
            tm = nt.nodes.new('ShaderNodeTexImage'); tm.image = bpy.data.images.load(str(d / part['maps']['Mask']))
            tm.image.colorspace_settings.name = 'Non-Color'
            sep = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(tm.outputs[0], sep.inputs[0])
            nt.links.new(sep.outputs[0], b.inputs['Metallic'])
            inv = nt.nodes.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
            nt.links.new(tm.outputs['Alpha'], inv.inputs[1]); nt.links.new(inv.outputs[0], b.inputs['Roughness'])
        for o in new:
            for s in o.material_slots: s.material = m
            o.location = Vector(o.location) + Vector(offset)
        objs += new
    return objs


def collider_boxes(e, offset=(0, 0, 0)):
    m = bpy.data.materials.new('collider'); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (0.1, 0.9, 0.3, 1); b.inputs['Alpha'].default_value = 0.35
    m.blend_method = 'BLEND' if hasattr(m, 'blend_method') else None
    obs = []
    for c in e['colliders']:
        bpy.ops.mesh.primitive_cube_add(size=1)
        o = bpy.context.active_object
        sz = c['size']
        o.scale = (sz[0], sz[2], sz[1])
        o.rotation_euler = (0, 0, math.radians(-c.get('yaw', 0.0)))
        o.location = U2B(c['center']) + Vector(offset)
        o.data.materials.append(m); o.visible_shadow = False
        obs.append(o)
    return obs


def prepared(lid):
    man = json.loads((UNITY / 'berms-landmarks.json').read_text())
    e = man[lid]
    out = HERE / 'renders' / lid; out.mkdir(parents=True, exist_ok=True)
    clear()
    sc, cam = scene_setup()
    sx, sh, sz = e['size']          # Unity x, y (height), z
    size = (sx, sz, sh)
    lod0 = load_prepared(lid, man, 0)
    standard_views(sc, cam, out, size, 'lod0_')
    player_views(sc, cam, out, size, 'lod0_')
    far_read(sc, cam, out, sh, 200, 'lod1_' if False else 'lod0_')
    # LOD1 / LOD2 beside LOD0 (spaced along X) at mid and far distance
    gap = sx + 4
    lod1 = load_prepared(lid, man, 1, (gap, 0, 0))
    lod2 = load_prepared(lid, man, 2, (2 * gap, 0, 0))
    span = 3 * gap
    shoot(sc, cam, out, 'lods_near', (gap, -span * 0.75, sh * 0.6 + 2), (gap, 0, sh * 0.4), lens=35, res=(1440, 640))
    shoot(sc, cam, out, 'lods_far', (gap, -span * 2.2, sh * 0.5 + 2), (gap, 0, sh * 0.4), lens=50, res=(1440, 640))
    for o in lod0 + lod2: o.hide_render = True
    for o in lod1: o.location.x -= gap
    far_read(sc, cam, out, sh, 120, 'lod1_')
    for o in lod1: o.hide_render = True
    for o in lod2: o.hide_render = False; o.location.x -= 2 * gap
    far_read(sc, cam, out, sh, 400, 'lod2_')
    for o in lod2: o.hide_render = True
    for o in lod0: o.hide_render = False
    cols = collider_boxes(e)
    d = max(size) * 1.35 + 3
    sc.render.resolution_x, sc.render.resolution_y = 960, 640
    shoot(sc, cam, out, 'colliders_tq', (-d * 0.7, -d * 0.75, sh * 0.6 + 6), (0, 0, sh * 0.3))
    shoot(sc, cam, out, 'colliders_top', (0, -0.01, max(size) * 2.2 + 5), (0, 0, 0), lens=35)
    for o in cols: bpy.data.objects.remove(o, do_unlink=True)


def channels(subject, attempt):
    """Where the Meshy metallic and roughness maps put metal / gloss on the model: flat (emission) renders of the
    metallic map, the roughness map and the base colour, from the front-left and rear-right three-quarters."""
    src = HERE / subject / attempt
    out = src / 'review'; out.mkdir(exist_ok=True)
    clear()
    ob = import_join(src / 'model.glb')
    me = ob.data
    co = coords(me)
    me.transform(Matrix.Rotation(math.radians(footprint_yaw(co)), 4, 'Z'))
    co = coords(me); mn, mx = co.min(0), co.max(0)
    axis, metres = NOMINAL[subject]; ext = mx - mn
    s = metres / (max(ext[0], ext[1]) if axis == 'len' else ext[2])
    me.transform(Matrix.Scale(s, 4) @ Matrix.Translation((-(mn[0] + mx[0]) / 2, -(mn[1] + mx[1]) / 2, -mn[2]))); me.update()
    co = coords(me); size = (co.max(0) - co.min(0)).tolist()
    sc, cam = scene_setup(samples=8)
    bpy.data.objects['ground'].hide_render = True
    sc.world.node_tree.nodes['Background'].inputs[0].default_value = (0.05, 0.05, 0.3, 1)
    sc.view_settings.view_transform = 'Standard'
    m = bpy.data.materials.new('chan'); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new('ShaderNodeOutputMaterial'); em = nt.nodes.new('ShaderNodeEmission'); nt.links.new(em.outputs[0], o.inputs[0])
    tex = nt.nodes.new('ShaderNodeTexImage'); uvn = nt.nodes.new('ShaderNodeUVMap')
    nt.links.new(uvn.outputs[0], tex.inputs[0]); nt.links.new(tex.outputs[0], em.inputs[0])
    for s_ in ob.material_slots: s_.material = m
    d = max(size[0], size[1], size[2] * 1.4) * 1.6 + 4
    for chan in ('metallic', 'roughness', 'base_color'):
        img = bpy.data.images.load(str(src / 'textures' / f'0_{chan}.png'))
        if chan != 'base_color': img.colorspace_settings.name = 'Non-Color'
        tex.image = img
        shoot(sc, cam, out, f'chan_{chan}_tq_front_left', (-d * 0.7, -d * 0.75, size[2] * 0.6 + 3), (0, 0, size[2] * 0.45))
        shoot(sc, cam, out, f'chan_{chan}_tq_rear_right', (d * 0.7, d * 0.75, size[2] * 0.6 + 3), (0, 0, size[2] * 0.45))


if __name__ == '__main__':
    if MODE == 'channels':
        channels(args[1], args[2])
    elif MODE == 'source':
        source(args[1], args[2], float(args[3]) if len(args) > 3 else 0.0)
    elif MODE == 'prepared':
        prepared(args[1])
    else:
        sys.exit('mode?')
