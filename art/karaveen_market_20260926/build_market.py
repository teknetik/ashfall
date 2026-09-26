"""Karaveen caravan market: Blender-authored stalls stocked with CC0 Poly Haven goods.

Run headless:  blender -b --factory-startup -P build_market.py
Authors the market in Ward world space (Unity x/z, metres) so the GLB can be
placed at the scene origin. Unity = (-bx, bz, -by); see U() below.
Each stall exports as <Stall>/Structure (timber, canvas, signs) and
<Stall>/Goods (stock; LOD-culled in Unity) plus COL_* collision boxes and
LIGHT_/SMOKE_ marker nodes consumed by the Unity install pass.
"""
import bpy, bmesh, math, random, json, glob
from mathutils import Vector, Matrix, Euler, noise
from pathlib import Path

ROOT = Path('/home/teknetik/code/ao2/art/karaveen_market_20260926')
PH = ROOT / 'sources' / 'polyhaven'; PT = ROOT / 'sources' / 'textures'; TX = ROOT / 'textures'
OUT_GLB = Path('/home/teknetik/code/ao2/unity/AthenHill/Assets/AthenHill/Art/KaraveenMarket/KaraveenMarket.glb')
OUT_BLEND = ROOT / 'karaveen-market-v1.blend'
rng = random.Random(20260926)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'


def U(x, z, y=0.0):
    """Ward/Unity world position (x, z, height y) to Blender coordinates."""
    return Vector((-x, -z, y))


def yaw_facing(dx, dz):
    """Blender Z rotation that turns a stall's local front (-Y) toward Unity direction (dx, dz)."""
    return math.atan2(-dx, dz)


def new_collection(name, parent=None):
    c = bpy.data.collections.new(name)
    (parent or scene.collection).children.link(c)
    return c


LIBC = new_collection('LIB')
MARKET = new_collection('KaraveenMarket')

# ---------------------------------------------------------------- materials
_images = {}


def image(path, data=False):
    key = str(path)
    if key not in _images:
        im = bpy.data.images.load(key)
        if data: im.colorspace_settings.name = 'Non-Color'
        _images[key] = im
    return _images[key]


def pbr(name, diff, nor=None, rough=None, rough_val=.85, metal=0., double=False, emit=None):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = image(diff)
    nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
    if rough:
        r = nt.nodes.new('ShaderNodeTexImage'); r.image = image(rough, True)
        nt.links.new(r.outputs['Color'], b.inputs['Roughness'])
    else:
        b.inputs['Roughness'].default_value = rough_val
    b.inputs['Metallic'].default_value = metal
    if nor:
        n = nt.nodes.new('ShaderNodeTexImage'); n.image = image(nor, True)
        nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = 1.0
        nt.links.new(n.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    if emit:
        b.inputs['Emission Color'].default_value = (*emit, 1); b.inputs['Emission Strength'].default_value = 1.0
    m.use_backface_culling = not double
    return m


def flat(name, rgb, rough=.8, metal=0., emit=None):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*rgb, 1); b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if emit:
        b.inputs['Emission Color'].default_value = (*emit, 1); b.inputs['Emission Strength'].default_value = 2.0
    return m


LIN_N = PT / 'rough_linen/rough_linen_nor_gl_1k.jpg'; LIN_R = PT / 'rough_linen/rough_linen_rough_1k.jpg'
M = {
    'timber': pbr('Market_Timber', PT / 'weathered_planks/weathered_planks_diff_2k.jpg', PT / 'weathered_planks/weathered_planks_nor_gl_2k.jpg', PT / 'weathered_planks/weathered_planks_rough_2k.jpg'),
    'timber_dark': pbr('Market_TimberDark', PT / 'rough_wood/rough_wood_diff_1k.jpg', PT / 'rough_wood/rough_wood_nor_gl_1k.jpg', PT / 'rough_wood/rough_wood_rough_1k.jpg'),
    'corrugated': pbr('Market_CorrugatedRust', PT / 'rusty_corrugated_iron/rusty_corrugated_iron_diff_2k.jpg', PT / 'rusty_corrugated_iron/rusty_corrugated_iron_nor_gl_2k.jpg', PT / 'rusty_corrugated_iron/rusty_corrugated_iron_rough_2k.jpg', metal=.55, double=True),
    'rust': pbr('Market_RustMetal', PT / 'rusty_metal_02/rusty_metal_02_diff_1k.jpg', PT / 'rusty_metal_02/rusty_metal_02_nor_gl_1k.jpg', PT / 'rusty_metal_02/rusty_metal_02_rough_1k.jpg', metal=.6),
    'rope': pbr('Market_Rope', PT / 'hessian_230/hessian_230_diff_1k.jpg', PT / 'hessian_230/hessian_230_nor_gl_1k.jpg', rough_val=.95),
    'hessian': pbr('Market_Hessian', PT / 'hessian_230/hessian_230_diff_1k.jpg', PT / 'hessian_230/hessian_230_nor_gl_1k.jpg', PT / 'hessian_230/hessian_230_rough_1k.jpg'),
    'leather': pbr('Market_Leather', PT / 'brown_leather/brown_leather_albedo_1k.jpg', PT / 'brown_leather/brown_leather_nor_gl_1k.jpg', PT / 'brown_leather/brown_leather_rough_1k.jpg', double=True),
    'jerky': pbr('Market_Jerky', TX / 'jerky.jpg', PT / 'brown_leather/brown_leather_nor_gl_1k.jpg', rough_val=.55),
    'lantern_glow': flat('Market_LanternGlow', (1., .62, .28), rough=.4, emit=(1., .55, .22)),
}
for c in ['cream', 'rust', 'ochre', 'indigo', 'olive', 'stripe']:
    M['canvas_' + c] = pbr('Market_Canvas_' + c, TX / f'canvas_{c}.jpg', LIN_N, LIN_R, double=True)
for c in ['crimson', 'indigo', 'ochre']:
    M['rug_' + c] = pbr('Market_Rug_' + c, TX / f'rug_{c}.jpg', PT / 'dirty_carpet/dirty_carpet_nor_gl_1k.jpg', PT / 'dirty_carpet/dirty_carpet_rough_1k.jpg', double=True)
for s in ['produce', 'water', 'tools', 'cloth', 'rations', 'chow']:
    M['sign_' + s] = pbr('Market_Sign_' + s, TX / f'sign_{s}.jpg', rough_val=.8)
for s in 'abc':
    M['slate_' + s] = pbr('Market_Slate_' + s, TX / f'slate_{s}.jpg', rough_val=.9)
CANVAS_TINTS = ['canvas_cream', 'canvas_rust', 'canvas_ochre', 'canvas_indigo', 'canvas_olive']

# ---------------------------------------------------------------- mesh helpers
CUR = {'coll': None, 'kind': 'structure'}   # objects are tagged structure/goods for the final merge


def link(ob, kind=None):
    CUR['coll'].objects.link(ob)
    ob['kind'] = kind or CUR['kind']
    return ob


def mesh_obj(name, bm, mat, smooth=False, kind=None):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for layer in me.uv_layers: layer.name = 'UVMap'   # match Poly Haven meshes so joins keep one UV set
    if smooth:
        for p in me.polygons: p.use_smooth = True
    me.materials.append(mat)
    return link(bpy.data.objects.new(name, me), kind)


def box_uv(ob, scale=.8, offset=None):
    """Local-space box projection; long axes map to texture V so grain follows beams."""
    me = ob.data; bm = bmesh.new(); bm.from_mesh(me)
    uv = bm.loops.layers.uv.verify()
    off = offset or (rng.random(), rng.random())
    for f in bm.faces:
        n = f.normal; ax = max(range(3), key=lambda i: abs(n[i]))
        for l in f.loops:
            p = l.vert.co
            u, v = ((p.y, p.z), (p.x, p.z), (p.x, p.y))[ax]
            l[uv].uv = (u * scale + off[0], v * scale + off[1])
    bm.to_mesh(me); bm.free()
    for layer in me.uv_layers: layer.name = 'UVMap'


def box(name, size, mat, loc=(0, 0, 0), rot=(0, 0, 0), bevel=.008, uv=.8, kind=None):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    if bevel > 0 and min(size) > bevel * 3:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=1, affect='EDGES', profile=.5)
    ob = mesh_obj(name, bm, mat, kind=kind)
    box_uv(ob, uv)
    ob.location = loc; ob.rotation_euler = rot
    return ob


def beam(name, p1, p2, w, h, mat, bevel=.01, roll=0., uv=.7, kind=None):
    """Rough timber between two points; section w x h, grain along the length."""
    p1, p2 = Vector(p1), Vector(p2); d = p2 - p1; L = d.length
    ob = box(name, (w, h, L), mat, bevel=bevel, uv=uv, kind=kind)
    q = d.normalized().to_track_quat('Z', 'Y')
    ob.rotation_mode = 'QUATERNION'; ob.rotation_quaternion = q @ Euler((0, 0, roll)).to_quaternion()
    ob.location = (p1 + p2) / 2
    return ob


def tube(name, pts, radius, mat, sides=6, uv_len=1.0, kind=None, caps=False):
    """Tube through a polyline (ropes, pipes, strings)."""
    bm = bmesh.new(); rings = []; acc = 0.
    uvl = bm.loops.layers.uv.verify(); vcoords = []
    for i, p in enumerate(pts):
        p = Vector(p)
        t = (Vector(pts[min(i + 1, len(pts) - 1)]) - Vector(pts[max(i - 1, 0)])).normalized()
        a = t.orthogonal().normalized(); b = t.cross(a)
        if i: acc += (p - Vector(pts[i - 1])).length
        rings.append([bm.verts.new(p + (a * math.cos(2 * math.pi * k / sides) + b * math.sin(2 * math.pi * k / sides)) * radius) for k in range(sides)])
        vcoords.append(acc)
    for i in range(len(rings) - 1):
        for k in range(sides):
            f = bm.faces.new((rings[i][k], rings[i][(k + 1) % sides], rings[i + 1][(k + 1) % sides], rings[i + 1][k]))
            for l, (ri, kk) in zip(f.loops, ((i, k), (i, k + 1), (i + 1, k + 1), (i + 1, k))):
                l[uvl].uv = (kk / sides * .25, vcoords[ri] * uv_len)
    if caps:
        for ring in (rings[0], rings[-1][::-1]):
            f = bm.faces.new(ring[::-1])
            for l in f.loops: l[uvl].uv = (l.vert.co.x * 2, l.vert.co.y * 2)
    bm.normal_update()
    return mesh_obj(name, bm, mat, smooth=True, kind=kind)


def sag_curve(a, b, sag, n=16):
    a, b = Vector(a), Vector(b)
    return [a.lerp(b, i / (n - 1)) - Vector((0, 0, sag * 4 * (i / (n - 1)) * (1 - i / (n - 1)))) for i in range(n)]


def rope(name, a, b, sag=.08, r=.008):
    return tube(name, sag_curve(a, b, sag, 14), r, M['rope'], sides=5, uv_len=3.)


def sheet(name, fn, res, mat, uv_size, holes=0., kind=None, skip=None):
    """Grid surface from fn(u, v) -> Vector, with texture UVs uv_size=(metres_u, metres_v)."""
    nu, nv = res; bm = bmesh.new(); uvl = bm.loops.layers.uv.verify()
    vs = [[bm.verts.new(fn(i / nu, j / nv)) for j in range(nv + 1)] for i in range(nu + 1)]
    for i in range(nu):
        for j in range(nv):
            if holes and rng.random() < holes: continue
            if skip and skip(i, j): continue
            f = bm.faces.new((vs[i][j], vs[i + 1][j], vs[i + 1][j + 1], vs[i][j + 1]))
            for l, (a, b) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                l[uvl].uv = (a / nu * uv_size[0], b / nv * uv_size[1])
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bm.normal_update()
    return mesh_obj(name, bm, mat, smooth=True, kind=kind)


def bilerp(p00, p10, p01, p11, u, v):
    return (p00 * (1 - u) + p10 * u) * (1 - v) + (p01 * (1 - u) + p11 * u) * v


def canvas(name, p00, p10, p01, p11, mat, sag=.1, sag_dir=(0, 0, -1), wrinkle=.018, res=(20, 12), holes=0., patches=2, valance=0.):
    """Sagging, wrinkled cloth between four tie points (00 back-left ... 11 front-right)."""
    p00, p10, p01, p11 = map(Vector, (p00, p10, p01, p11)); sd = Vector(sag_dir)
    seed = rng.random() * 100

    def f(u, v, lift=0.):
        p = bilerp(p00, p10, p01, p11, u, v)
        s = sag * math.sin(math.pi * v) * (.65 + .35 * math.sin(math.pi * u)) + sag * .25 * math.sin(math.pi * u) * v
        w = noise.noise(Vector((u * 4 + seed, v * 3, seed))) * wrinkle + noise.noise(Vector((u * 11, v * 9 + seed, 1))) * wrinkle * .35
        return p + sd * (s + w) - sd * lift
    W = (p10 - p00).length; D = (p01 - p00).length
    obs = [sheet(name, f, res, mat, (W / 1.1, D / 1.1), holes=holes)]
    for k in range(patches):   # darker repair patches stitched on top
        u0, v0 = rng.uniform(.1, .7), rng.uniform(.15, .7); du, dv = rng.uniform(.12, .22), rng.uniform(.15, .28)
        pm = M[rng.choice([t for t in CANVAS_TINTS if M[t] != mat])]
        obs.append(sheet(name + ' patch', lambda a, b: f(u0 + a * du, v0 + b * dv, .006), (4, 4), pm, (du * W / 1.1, dv * D / 1.1)))
    if valance > 0:            # scalloped, frayed front drop
        a, b = f(0, 1), f(1, 1)
        cuts = {rng.randrange(2, 38) for _ in range(3)}

        def fv(u, v):
            top = f(u, 1)
            scallop = .05 * abs(math.sin(u * math.pi * 7)) + noise.noise(Vector((u * 30, seed, 2))) * .015
            return top + Vector((0, 0, -(valance - scallop) * v)) + (top - f(u, .92)).normalized() * .01 * v
        obs.append(sheet(name + ' valance', fv, (40, 3), mat, ((b - a).length / 1.1, valance / 1.1),
                         skip=lambda i, j: i in cuts and j == 2))
    return obs


def sack(name, h=.55, r=.2, open_top=False, mat=None):
    """Lumpy hessian sack: lathe profile with a tied neck, or rolled open mouth."""
    seed = rng.random() * 50; segs = 16
    if open_top:
        prof = [(0, .0), (.8, .01), (.97, .06), (1., .2), (.98, .55), (.95, .8), (1.05, .9), (1.08, .96), (1.0, 1.)]
    else:
        prof = [(0, .0), (.82, .01), (.98, .07), (1., .25), (.97, .55), (.85, .74), (.48, .86), (.3, .9), (.42, .95), (.3, 1.)]
    bm = bmesh.new(); uvl = bm.loops.layers.uv.verify(); rings = []
    for k, (pr, pz) in enumerate(prof):
        ring = []
        for i in range(segs):
            a = 2 * math.pi * i / segs
            n = noise.noise(Vector((math.cos(a) * 1.5 + seed, math.sin(a) * 1.5, pz * 3))) * .1 if 0 < pz < 1 else 0
            rr = r * pr * (1 + n) * (1 - .12 * max(0, .3 - pz))
            ring.append(bm.verts.new((math.cos(a) * rr, math.sin(a) * rr * .85, pz * h)))
        rings.append(ring)
    for k in range(len(rings) - 1):
        for i in range(segs):
            f = bm.faces.new((rings[k][i], rings[k][(i + 1) % segs], rings[k + 1][(i + 1) % segs], rings[k + 1][i]))
            for l, (a, b) in zip(f.loops, ((i, k), (i + 1, k), (i + 1, k + 1), (i, k + 1))):
                l[uvl].uv = (a / segs * 2 * math.pi * r * 1.6, prof[b][1] * h * 1.6)
    bm.faces.new(rings[0][::-1])
    if not open_top: bm.faces.new(rings[-1])
    bm.normal_update()
    return mesh_obj(name, bm, mat or M['hessian'], smooth=True, kind='goods')


# ---------------------------------------------------------------- Poly Haven library
LIB = {}


def lib(name, target=None, scale=1.):
    if name in LIB: return LIB[name]
    before = set(bpy.data.objects)
    lc = bpy.context.view_layer.layer_collection.children['LIB']
    bpy.context.view_layer.active_layer_collection = lc
    path = glob.glob(str(PH / name / '*.gltf'))[0]
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == 'MESH']
    for o in meshes:
        mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
    bpy.ops.object.select_all(action='DESELECT')
    for o in meshes: o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1: bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for o in [o for o in bpy.data.objects if o not in before and o != ob]:
        bpy.data.objects.remove(o)
    tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    if target and tris > target:
        mod = ob.modifiers.new('dec', 'DECIMATE'); mod.ratio = target / tris
        bpy.ops.object.modifier_apply(modifier=mod.name)
    bb = [Vector(c) for c in ob.bound_box]
    mn = Vector(map(min, *bb)); mx = Vector(map(max, *bb))
    ob.data.transform(Matrix.Translation(-Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))))
    if scale != 1: ob.data.transform(Matrix.Scale(scale, 4))
    ob.name = 'LIB_' + name; ob.data.name = 'LIB_' + name
    ob['dims'] = list(Vector(map(lambda a, b: a - b, mx, mn)) * scale)
    LIB[name] = ob
    return ob


def put(name, loc, rz=0., rx=0., ry=0., s=1.):
    src = LIB[name]; o = src.copy()
    link(o, 'goods')
    o.location = loc; o.rotation_euler = (rx, ry, rz); o.scale = (s, s, s)
    return o


FRUIT = dict(food_apple_01=220, food_pomegranate_01=220, food_lime_01=180, lemon=180, yellow_onion=220, sweet_potato=180, food_avocado_01=220)
for k, t in FRUIT.items(): lib(k, t)
for k, t in dict(wicker_basket_01=2600, wicker_basket_02=2600, ceramic_vase_01=1300, ceramic_vase_02=1300, ceramic_vase_03=1300, ceramic_vase_04=1300,
                 planter_pot_clay=1200, jug_01=1200, brass_pot_01=1100, brass_pot_02=1400, brass_vase_03=1200, brass_vase_04=1200, metal_jug=1200,
                 metal_jerrycan_green=2400, plastic_jerrycan=2000, plastic_bottle_gallon=1600, can_rusted=500, russian_food_cans_01=640,
                 long_life_food=2400, cardboard_box_01=1400, wooden_crate_01=3000, wooden_crate_02=3000, wooden_bucket_01=2000,
                 barrel_03=1473, barrel_stove=5000, wooden_lantern_01=2400, folding_wooden_stool=2400, hatchet=1200, sledgehammer_01=1200,
                 rusted_hacksaw=1400, pipe_wrench=1600, adjustable_wrench=1200, crowbar_01=900, rusted_spade_01=1600, old_gas_mask=3200,
                 binoculars=2400, small_oil_can_01=2000, propane_tank=2000, ammo_box=1600, carved_wooden_plate=900, wooden_bowl_02=1000,
                 pot_enamel_01=2400, old_military_crate=6000, wooden_barrels_01=9000).items():
    lib(k, t)


def dims(name): return Vector(LIB[name]['dims'])


def heap(names, cx, cy, z0, sx, sy, layers=2, mound=1., spacing=.92):
    """Loose produce heap inside an sx*sy footprint, piled higher toward the middle."""
    obs = []
    for L in range(layers + 2):
        d = max(max(dims(n).x, dims(n).y) for n in names) * spacing
        nx, ny = max(1, int(sx / d)), max(1, int(sy / d))
        for i in range(nx):
            for j in range(ny):
                u = (i + .5) / nx - .5; v = (j + .5) / ny - .5
                if L >= layers:          # mound layers only near the centre
                    if math.hypot(u * 2, v * 2) > (1 - (L - layers + 1) * .38) * mound: continue
                x = cx + u * sx + (L % 2) * d * .5 * (1 if i < nx - 1 else 0) + rng.uniform(-.012, .012)
                y = cy + v * sy + (L % 2) * d * .5 * (1 if j < ny - 1 else 0) + rng.uniform(-.012, .012)
                n = rng.choice(names)
                z = z0 + L * dims(n).z * .78
                obs.append(put(n, (x, y, z), rng.uniform(0, 6.28), rng.uniform(-.5, .5), rng.uniform(-.5, .5), rng.uniform(.9, 1.1)))
    return obs


def slat_crate(name, w, d, h, mat=None):
    """Open slatted produce crate with local origin at its base centre."""
    mat = mat or M['timber']; obs = []
    t = .014
    for k in range(3):
        obs.append(box(name + ' floor', (w, d / 3 - .006, t), mat, (0, (k - 1) * d / 3, t / 2), bevel=.003, uv=1.5))
    for sgn in (-1, 1):
        for k in range(2):
            z = .03 + k * (h - .03) / 2 + .02
            obs.append(box(name + ' side', (w, t, h / 2 - .02), mat, (0, sgn * (d / 2 - t / 2), z + h / 4 - .02), bevel=.003, uv=1.5))
        obs.append(box(name + ' end', (t, d, h), mat, (sgn * (w / 2 - t / 2), 0, h / 2), bevel=.003, uv=1.5))
    return obs


def transform(obs, M4):
    for o in obs:
        o.matrix_basis = M4 @ o.matrix_basis   # matrix_world is stale until a depsgraph update
    return obs

# ---------------------------------------------------------------- stall construction (local frame: front = -Y)
W, D = 3.4, 2.2
FY, BY = -1.0, 1.0            # post rows


def frame(hf=2.3, hb=2.55, post=.11):
    obs = []
    lean = lambda: (rng.uniform(-.025, .025), rng.uniform(-.025, .025))
    tops = {}
    for sx in (-1, 1):
        for y, h in ((FY, hf), (BY, hb)):
            dx, dy = lean(); base = Vector((sx * W / 2, y, 0)); top = Vector((sx * W / 2 + dx * h, y + dy * h, h + .08))
            obs.append(beam('Post', base, top, post, post * rng.uniform(.9, 1.1), M['timber'], roll=rng.uniform(-.1, .1)))
            obs.append(box('Post foot', (.26, .26, .12), M['rust'], (base.x, base.y, .06), (0, 0, rng.uniform(0, 1)), bevel=.01, uv=1.2))
            tops[(sx, y)] = top
    for y, h in ((FY, hf), (BY, hb)):   # front/back top beams
        a = tops[(-1, y)] + Vector((-.18, 0, -.05)); b = tops[(1, y)] + Vector((.18, 0, -.05))
        obs.append(beam('Top beam', a, b, .1, .13, M['timber'], roll=rng.uniform(-.05, .05)))
    for sx in (-1, 1):                  # side rails and knee braces
        obs.append(beam('Side rail', tops[(sx, FY)] + Vector((0, -.12, -.14)), tops[(sx, BY)] + Vector((0, .12, -.14)), .08, .1, M['timber']))
        for y in (FY, BY):
            t = tops[(sx, y)]
            obs.append(beam('Knee brace', t + Vector((-sx * .02, 0, -.62)), t + Vector((-sx * .5, 0, -.12)), .06, .07, M['timber_dark']))
            for dz in (-.16, -.2):      # rope lashings at the joints
                obs.append(tube('Lashing', [t + Vector((math.cos(a) * .075, math.sin(a) * .075, dz + a * .004)) for a in [i * .7 for i in range(10)]], .007, M['rope'], sides=4))
    return obs, tops


def counter(w=3.1, y0=-.98, y1=-.24, h=.88):
    obs = []; d = y1 - y0; n = 5
    for k in range(n):                 # plank top with gaps and height jitter
        pw = d / n - .01
        obs.append(box('Counter plank', (w + rng.uniform(-.04, .08), pw, .038), M['timber'],
                       (rng.uniform(-.03, .03), y0 + (k + .5) * d / n, h - .019 + rng.uniform(-.004, .004)), (rng.uniform(-.006, .006), 0, rng.uniform(-.006, .006)), bevel=.006, uv=.9))
    for sx in (-1, 1):                 # trestles
        x = sx * (w / 2 - .22)
        for yy in (y0 + .08, y1 - .08):
            obs.append(beam('Trestle leg', (x - .12, yy, 0), (x + .02, yy, h - .04), .07, .07, M['timber_dark']))
            obs.append(beam('Trestle leg', (x + .12, yy, 0), (x - .02, yy, h - .04), .07, .07, M['timber_dark']))
        obs.append(beam('Trestle rail', (x, y0 + .02, h * .45), (x, y1 - .02, h * .45), .05, .06, M['timber_dark']))
    x = -w / 2 + .02                   # ragged front apron boards
    while x < w / 2 - .06:
        bw = rng.uniform(.13, .22)
        if rng.random() > .12:
            bh = h - .09 - rng.uniform(0, .12)
            obs.append(box('Apron board', (bw - .012, .022, bh), M['timber'], (x + bw / 2, y0 - .02, .06 + bh / 2), (0, rng.uniform(-.02, .02), rng.uniform(-.01, .01)), bevel=.005, uv=.9))
        x += bw
    return obs, h + .02


def shelves(levels=(1.0, 1.45), w=3.0, y=.78, depth=.32):
    obs = []
    for z in levels:
        obs.append(box('Shelf', (w, depth, .03), M['timber'], (0, y, z), (0, 0, rng.uniform(-.01, .01)), bevel=.005, uv=.9))
        for sx in (-1, 0, 1):
            obs.append(beam('Shelf bracket', (sx * (w / 2 - .1), y + depth / 2, z - .25), (sx * (w / 2 - .1), y - depth / 2 + .03, z - .02), .035, .04, M['timber_dark']))
    obs.append(beam('Shelf upright', (0, y + depth / 2 + .02, 0), (0, y + depth / 2 + .02, levels[-1] + .1), .07, .07, M['timber_dark']))
    return obs


def awning(tops, mat, valance=.32, overhang=.55, back_curtain=None):
    a = tops[(-1, BY)] + Vector((-.22, .08, .02)); b = tops[(1, BY)] + Vector((.22, .08, .02))
    c = tops[(-1, FY)] + Vector((-.25, -overhang, -.12)); d = tops[(1, FY)] + Vector((.25, -overhang, -.12))
    obs = canvas('Awning', a, b, c, d, mat, sag=.13, holes=.004, patches=rng.randint(1, 3), valance=valance)
    obs += [rope('Tie rope', c + Vector((0, 0, -.02)), tops[(-1, FY)] + Vector((0, 0, -.1)), .02), rope('Tie rope', d + Vector((0, 0, -.02)), tops[(1, FY)] + Vector((0, 0, -.1)), .02)]
    if back_curtain:
        p00 = tops[(-1, BY)] + Vector((-.05, .08, -.1)); p10 = tops[(1, BY)] + Vector((.05, .08, -.1))
        obs += canvas('Back curtain', p00, p10, Vector((p00.x, p00.y + .05, .35)), Vector((p10.x, p10.y + .05, .35)), back_curtain, sag=.08, sag_dir=(0, 1, 0), wrinkle=.03, res=(16, 10), patches=1)
    return obs


def corrugated_roof(tops):
    obs = []; a_y = BY + .25; b_y = FY - .6
    za = tops[(-1, BY)].z + .06; zb = tops[(-1, FY)].z - .06
    x = -W / 2 - .3
    while x < W / 2 + .2:
        sw = rng.uniform(.8, .95); x0 = x; tilt = rng.uniform(-.015, .015); lift = rng.uniform(0, .025)

        def f(u, v, x0=x0, sw=sw, tilt=tilt, lift=lift):
            px = x0 + u * sw; py = a_y + (b_y - a_y) * v
            pz = za + (zb - za) * v + .018 * math.sin(u * sw / .076 * 2 * math.pi) + tilt * u + lift + (.04 * v * v if u > .85 else 0)
            return Vector((px, py, pz))
        obs.append(sheet('Corrugated sheet', f, (int(sw / .076 * 4), 3), M['corrugated'], (sw / 1.0, abs(a_y - b_y) / 1.0)))
        x += sw - .09
    for y in (a_y - .15, (a_y + b_y) / 2, b_y + .2):   # purlins
        z = za + (zb - za) * ((y - a_y) / (b_y - a_y)) - .06
        obs.append(beam('Purlin', (-W / 2 - .3, y, z), (W / 2 + .3, y, z), .06, .08, M['timber_dark']))
    return obs


def sign_board(tops, key, w=1.7, h=.64, raise_by=0.):
    y = BY + .02; z = tops[(-1, BY)].z + .05 + raise_by
    obs = [box('Sign board', (w, .035, h), M['sign_' + key], (0, y, z + .35 + h / 2), bevel=0)]
    sb = obs[0]                              # map the painted face once across the front
    me = sb.data; bm = bmesh.new(); bm.from_mesh(me); uvl = bm.loops.layers.uv.verify()
    for f in bm.faces:
        for l in f.loops:
            l[uvl].uv = ((l.vert.co.x / w + .5) if f.normal.y < 0 else (-l.vert.co.x / w + .5), l.vert.co.z / h + .5)
    bm.to_mesh(me); bm.free()
    for sx in (-1, 1):
        obs.append(beam('Sign post', (sx * (w / 2 - .12), y + .05, z - .35), (sx * (w / 2 - .12), y + .05, z + .35 + h), .06, .06, M['timber_dark']))
    return obs


def slate(key, loc, rz=0.):
    s = box('Price slate', (.36, .02, .27), M['slate_' + key], bevel=0)
    me = s.data; bm = bmesh.new(); bm.from_mesh(me); uvl = bm.loops.layers.uv.verify()
    for f in bm.faces:
        for l in f.loops: l[uvl].uv = ((l.vert.co.x if f.normal.y < 0 else -l.vert.co.x) / .36 + .5, l.vert.co.z / .27 + .5)
    bm.to_mesh(me); bm.free()
    s.location = loc; s.rotation_euler = (-.28, 0, rz); s['kind'] = 'goods'
    return s


def lantern_on(p, name='LIGHT_lantern'):
    put('wooden_lantern_01', p - Vector((0, 0, .5)), rng.uniform(0, 6.28), s=.85)
    rope('Lantern cord', p, p - Vector((0, 0, .05)), 0, .005)
    e = bpy.data.objects.new(name, None); link(e, 'marker'); e.location = p - Vector((0, 0, .32))


def string_of(name, top, n, drop=.75):
    """Braided onion / garlic string hanging from a beam."""
    rope('String', top, top - Vector((0, 0, drop)), 0, .006)
    for k in range(n):
        z = top.z - .12 - k * (drop - .12) / n
        a = k * 2.2
        put(name, Vector((top.x + math.cos(a) * .035, top.y + math.sin(a) * .035, z - .04)), rng.uniform(0, 6.28), rng.uniform(1.2, 1.9), rng.uniform(-.3, .3), rng.uniform(.9, 1.15))


def jerky_row(y, z, x0, x1, n):
    tube('Jerky line', sag_curve((x0, y, z), (x1, y, z), .05, 10), .005, M['rope'], sides=4)
    for k in range(n):
        x = x0 + (k + .5) * (x1 - x0) / n
        L = rng.uniform(.22, .38)
        o = box('Jerky', (rng.uniform(.035, .05), .012, L), M['jerky'], (x, y, z - .04 - L / 2), (rng.uniform(-.1, .1), rng.uniform(-.15, .15), rng.uniform(0, 3)), bevel=.004, uv=3, kind='goods')


def hanging_rug(mat, a, b, h, bulge=.05, kind='goods'):
    a, b = Vector(a), Vector(b); n = (b - a).cross(Vector((0, 0, 1))).normalized(); seed = rng.random() * 9

    def f(u, v):
        p = a.lerp(b, u) - Vector((0, 0, h * v))
        return p + n * (math.sin(u * math.pi * 3 + seed) * bulge * (.3 + v) + noise.noise(Vector((u * 5, v * 4, seed))) * .02)
    return sheet('Hanging rug', f, (10, 14), mat, (1, 1), kind=kind)


def ground_rug(mat, cx, cy, w, d, rz=0.):
    seed = rng.random() * 9

    def f(u, v):
        x, y = (u - .5) * w, (v - .5) * d
        edge = max(0, abs(u - .5) * 2 - .92) + max(0, abs(v - .5) * 2 - .92)
        return Vector((x, y, .006 + edge * .15 + noise.noise(Vector((u * 4, v * 4, seed))) * .006))
    o = sheet('Ground rug', f, (12, 16), mat, (1, 1), kind='structure')
    o.location = (cx, cy, 0); o.rotation_euler = (0, 0, rz)
    return o


def col_box(name, center, size, rz=0.):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0); bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    o = mesh_obj('COL_' + name, bm, M['rope'], kind='collision')
    o.location = center; o.rotation_euler = (0, 0, rz)
    return o


def stall_colliders(extra=()):
    col_box('counter', (0, -.61, .5), (3.2, .8, 1.0))
    col_box('back', (0, .75, .75), (3.2, .5, 1.5))
    for sx in (-1, 1):
        for y in (FY, BY): col_box('post', (sx * W / 2, y, 1.2), (.16, .16, 2.4))
    for c, s in extra: col_box('goods', c, s)

# ---------------------------------------------------------------- stall contents


def produce_stall():
    obs, tops = frame(); counter(); shelves()
    awning(tops, M['canvas_stripe'], back_curtain=M['canvas_cream']); sign_board(tops, 'produce')
    top = .9 + .02
    for x, names in ((-1.12, ['food_apple_01']), (-.38, ['food_pomegranate_01']), (.36, ['lemon', 'food_lime_01']), (1.1, ['food_apple_01', 'food_pomegranate_01'])):
        CUR['kind'] = 'structure'; crate = slat_crate('Display crate', .66, .44, .15)
        CUR['kind'] = 'goods'; fr = heap(names, 0, 0, .02, .6, .38, layers=1, mound=1.1)
        CUR['kind'] = 'structure'
        transform(crate + fr, Matrix.Translation((x, -.6, top + .07)) @ Matrix.Rotation(-.3, 4, 'X'))
        box('Crate wedge', (.62, .1, .1), M['timber_dark'], (x, -.4, top + .05), bevel=.005)
    slate('a', Vector((1.35, -.93, top + .16)), .15)
    # ground stock in front of the counter
    for x, n in ((-1.05, 'yellow_onion'), (-.35, 'sweet_potato')):
        sack('Open sack', .42, .22, open_top=True).location = (x, -1.42, 0)
        heap([n], x, -1.42, .3, .3, .26, layers=1, mound=1.2)
    put('wicker_basket_02', (.55, -1.4, 0), .4); heap(['food_avocado_01'], .59, -1.4, .07, .2, .16, layers=1)
    c = put('wooden_crate_01', (1.35, -1.45, 0), 1.57 + .1, s=.85); heap(['food_apple_01', 'food_pomegranate_01'], 1.35, -1.45, .26, .28, .6, layers=1)
    # back shelves and stock
    for i, x in enumerate((-1.1, -.35, .45, 1.15)):
        put('wicker_basket_01', (x, .78, 1.015), rng.uniform(-.2, .2), s=.9)
        heap([['lemon', 'food_lime_01', 'yellow_onion', 'sweet_potato'][i]], x, .78, 1.03, .26, .18, layers=1)
    put('wooden_crate_02', (-1.0, .45, 0), 1.57, s=.9); put('wooden_crate_02', (-.95, .45, .42), 1.62, s=.9)
    put('barrel_03', (1.2, .45, 0), s=.8)
    for x in (-1.45, 1.45): string_of('yellow_onion', Vector((x, FY - .02, 2.2)), 9)
    lantern_on(Vector((0, FY - .05, 2.25)))
    stall_colliders([((-.7, -1.43, .25), (1.3, .5, .5)), ((1.0, -1.43, .25), (1.2, .7, .5))])


def pottery_stall():
    obs, tops = frame(2.25, 2.5); counter(); shelves((.95, 1.4, 1.85))
    awning(tops, M['canvas_indigo'], back_curtain=M['canvas_olive']); sign_board(tops, 'water')
    top = .9 + .02
    row = ['ceramic_vase_04', 'jug_01', 'brass_pot_01', 'ceramic_vase_02', 'metal_jug', 'brass_vase_03', 'ceramic_vase_03', 'planter_pot_clay', 'brass_vase_04', 'ceramic_vase_01']
    x = -1.42
    for n in row:
        w = max(dims(n).x, dims(n).y) * 1.0
        put(n, (x + w / 2, -.6 + rng.uniform(-.12, .12), top), rng.uniform(0, 6.28))
        x += w + .05
        if x > 1.4: break
    put('brass_pot_02', (.9, -.35, top), .4)
    slate('b', Vector((-1.35, -.93, top + .16)), -.1)
    for z in (.965, 1.415, 1.865):
        x = -1.35
        while x < 1.3:
            n = rng.choice(['ceramic_vase_02', 'ceramic_vase_04', 'jug_01', 'planter_pot_clay', 'brass_pot_01', 'metal_jug', 'wooden_bowl_02'])
            s = rng.uniform(.75, 1.0); w = max(dims(n).x, dims(n).y) * s
            if dims(n).z * s > .4: continue
            put(n, (x + w / 2, .78, z), rng.uniform(0, 6.28), s=s); x += w + .04
    # water and big clay on the ground
    for i, x in enumerate((-1.3, -.9, -.5)):
        put('metal_jerrycan_green', (x, -1.35, 0), 1.57 + rng.uniform(-.15, .15))
    put('plastic_jerrycan', (0.0, -1.35, 0), .2); put('plastic_jerrycan', (.35, -1.3, 0), -.3)
    put('planter_pot_clay', (.85, -1.4, 0), .5, s=1.7); put('ceramic_vase_01', (1.35, -1.35, 0), .9, s=2.1)
    c = put('wooden_crate_01', (1.95, -.2, 0), 1.57, s=.9)
    for k in range(4): put('plastic_bottle_gallon', (1.92 + (k % 2 - .5) * .17, -.42 + k // 2 * .3, .3), rng.uniform(0, 6.28))
    put('barrel_03', (2.0, .6, 0), s=.95); put('jug_01', (2.0, .6, .88), 1.2)
    lantern_on(Vector((-1.2, FY - .05, 2.2)))
    stall_colliders([((-.2, -1.35, .3), (2.5, .5, .6)), ((1.2, -1.37, .5), (.8, .6, 1.0)), ((1.98, .2, .5), (.7, 1.3, 1.0))])


def tools_stall():
    obs, tops = frame(2.25, 2.5, .12); counter()
    corrugated_roof(tops); sign_board(tops, 'tools', raise_by=.4)
    # plank pegboard back wall
    x = -W / 2 + .1
    while x < W / 2 - .1:
        bw = rng.uniform(.16, .24); bh = rng.uniform(1.75, 2.05)
        box('Back board', (bw - .01, .025, bh), M['timber'], (x + bw / 2, BY - .05, .25 + bh / 2), (0, rng.uniform(-.02, .02), 0), bevel=.005, uv=.9)
        x += bw
    for z in (.9, 2.0): beam('Wall rail', (-W / 2, BY - .09, z), (W / 2, BY - .09, z), .05, .06, M['timber_dark'])
    hang = [('sledgehammer_01', 1.3), ('rusted_spade_01', 1.3), ('old_gas_mask', 1.3), ('hatchet', 1.6), ('pipe_wrench', 1.55), ('rusted_hacksaw', 1.45), ('adjustable_wrench', 1.6), ('crowbar_01', 1.45)]
    x = -1.4
    for n, zc in hang:   # zc = centre height on the wall; tools are modelled standing on +Z
        d = dims(n)
        if d.x > .3:     # the hacksaw lies along X already
            put(n, (x + .25, BY - .11, zc - d.z / 2)); x += .6
        else:
            put(n, (x, BY - .11 - min(d.x, d.y) / 2, zc - d.z / 2), (1.57 if d.x < d.y else 0) + rng.uniform(-.08, .08), 0, rng.uniform(-.08, .08)); x += .36
    # second row of stock on the wall: small tools and a tin shelf
    x = -1.35
    for n in ['hatchet', 'adjustable_wrench', 'pipe_wrench', 'hatchet', 'adjustable_wrench', 'crowbar_01']:
        d = dims(n); put(n, (x, BY - .11 - min(d.x, d.y) / 2, 1.0 - d.z / 2 + .25), (1.57 if d.x < d.y else 0) + rng.uniform(-.1, .1), 0, rng.uniform(-.12, .12)); x += .5
    box('Tin shelf', (1.1, .22, .03), M['timber'], (.95, BY - .2, 1.82), bevel=.005)
    for k in range(6): put(rng.choice(['can_rusted', 'small_oil_can_01', 'metal_jug']), (.52 + k * .17, BY - .2, 1.835), rng.uniform(0, 6), s=.8)
    top = .9 + .02
    put('small_oil_can_01', (-1.2, -.55, top), .6); put('binoculars', (-.7, -.62, top), .3)
    put('ammo_box', (.35, -.6, top), 1.57); put('ammo_box', (.36, -.6, top + .18), 1.5)
    for k in range(5): put('can_rusted', (.75 + (k % 3) * .14, -.72 + (k // 3) * .16, top), rng.uniform(0, 6.28))
    put('adjustable_wrench', (1.3, -.5, top + .02), .8, 1.57); put('pipe_wrench', (-.2, -.45, top + .02), 1.3, 1.57)
    for x in (-1.25, -.85): put('propane_tank', (x, -1.4, 0), rng.uniform(0, 6))
    put('metal_jerrycan_green', (-.35, -1.35, 0), 1.3)
    put('wooden_bucket_01', (.3, -1.4, 0)); put('crowbar_01', (.3, -1.4, .55), 0, .25); put('rusted_spade_01', (.38, -1.35, .55), .5, -.2)
    put('old_military_crate', (2.1, .1, 0), 1.57, s=.7)
    lantern_on(Vector((1.2, FY - .05, 2.2)))
    stall_colliders([((-.5, -1.4, .3), (2.0, .5, .6)), ((2.1, .1, .15), (.8, 1.4, .3))])


def cloth_stall():
    obs, tops = frame(2.35, 2.6); counter()
    awning(tops, M['canvas_ochre'])
    sign_board(tops, 'cloth')
    beam('Rug rail', tops[(-1, BY)] + Vector((0, -.1, -.35)), tops[(1, BY)] + Vector((0, -.1, -.35)), .05, .05, M['timber_dark'])
    for i, (m, x0, x1) in enumerate((('rug_crimson', -1.6, -.5), ('rug_indigo', -.55, .55), ('rug_ochre', .5, 1.6))):
        hanging_rug(M[m], (x0, BY - .1 + i * .02, 2.2), (x1, BY - .1 + i * .02, 2.2), 1.75)
    for sx in (-1, 1):                 # side rail with a draped hide and rug
        beam('Side hang rail', (sx * (W / 2 + .07), FY, 1.9), (sx * (W / 2 + .07), BY, 1.9), .045, .045, M['timber_dark'])
    hanging_rug(M['leather'], (-W / 2 - .07, -.3, 1.88), (-W / 2 - .07, .5, 1.88), 1.1, .03)
    hanging_rug(M['rug_indigo'], (W / 2 + .07, .5, 1.88), (W / 2 + .07, -.4, 1.88), 1.4)
    top = .9 + .02
    x = -1.4
    while x < 1.25:                    # folded cloth stacks
        n = rng.randint(3, 6); cw = rng.uniform(.34, .44)
        for k in range(n):
            box('Folded cloth', (cw + rng.uniform(-.02, .02), .3 + rng.uniform(-.02, .02), .055), M[rng.choice(CANVAS_TINTS + ['rug_crimson'])],
                (x + cw / 2 + rng.uniform(-.015, .015), -.6, top + .03 + k * .056), (0, 0, rng.uniform(-.06, .06)), bevel=.018, uv=2.5, kind='goods')
        x += cw + .08
    for k in range(4):                 # bolts leaning on the counter front
        a = Vector((-1.4 + k * .26, -1.25, 0)); b = Vector((-1.3 + k * .26, -1.05, .95))
        tube('Fabric bolt', [a, b], .075, M[CANVAS_TINTS[k]], sides=10, uv_len=.8, kind='goods', caps=True)
    ground_rug(M['rug_crimson'], .1, -2.3, 1.6, 2.3, .06)
    put('wicker_basket_02', (1.2, -1.45, 0), .3)
    for k in range(3): tube('Rolled cloth', [Vector((1.12 + k * .06, -1.45, .05)), Vector((1.1 + k * .07, -1.4, .55))], .045, M[CANVAS_TINTS[k + 1]], sides=8, kind='goods', caps=True)
    lantern_on(Vector((-.9, FY - .05, 2.3))); lantern_on(Vector((.9, FY - .05, 2.3)), 'LIGHT_lantern_b')
    stall_colliders([((-1.0, -1.15, .5), (1.2, .5, 1.0))])


def rations_stall():
    obs, tops = frame(2.3, 2.55); counter(); shelves((1.0, 1.5))
    awning(tops, M['canvas_olive'], back_curtain=M['canvas_rust']); sign_board(tops, 'rations')
    top = .9 + .02
    x = -1.45
    for k in range(4):                 # stacked tins
        for j in range(3):
            put('russian_food_cans_01', (x, -.72 + j * .09, top), 1.57 + rng.uniform(-.08, .08), s=1.3)
            put('russian_food_cans_01', (x, -.72 + j * .09, top + .112), 1.57 + rng.uniform(-.08, .08), s=1.3)
        x += .22
    put('long_life_food', (.1, -.55, top), .05)
    for k in range(3): put('wooden_bowl_02', (.7 + k * .17, -.75, top), rng.uniform(0, 6))
    put('carved_wooden_plate', (1.25, -.55, top), .3); put('cardboard_box_01', (1.25, -.55, top + .04), .2, s=.55)
    slate('c', Vector((-.05, -.93, top + .16)), .05)
    for z in (1.015, 1.515):
        x = -1.35
        while x < 1.2:
            n = rng.choice(['can_rusted', 'russian_food_cans_01', 'cardboard_box_01', 'long_life_food'])
            s = .5 if n == 'cardboard_box_01' else (.8 if n == 'long_life_food' else 1.)
            w = dims(n).x * s
            put(n, (x + w / 2, .78, z), rng.uniform(-.1, .1), s=s); x += w + .05
    jerky_row(FY - .05, 2.1, -1.4, -.2, 9); jerky_row(FY - .05, 2.1, .2, 1.4, 8)
    for i, (x, y, z, rz) in enumerate(((-1.15, -1.45, 0, .2), (-.75, -1.5, 0, -.3), (-.95, -1.45, .5, 1.2), (.1, -1.45, 0, .5))):
        o = sack('Grain sack', .52, .23); o.location = (x, y, z); o.rotation_euler = (0, 0, rz)
    put('wooden_crate_02', (.9, -1.5, 0), 0, s=.85); put('cardboard_box_01', (.9, -1.5, .4), .1, s=.9)
    put('wooden_barrels_01', (2.6, .4, 0), 1.57, s=.55)
    lantern_on(Vector((0, FY - .05, 2.25)))
    stall_colliders([((-.5, -1.45, .4), (1.8, .6, .8)), ((.9, -1.5, .5), (.7, 1.0, 1.0)), ((2.6, .4, .3), (1.9, 2.5, .6))])


def cookfire():
    put('barrel_stove', (0, 0, 0)); put('pot_enamel_01', (0, 0, .86), .4)
    for k in range(3):
        a = k * 2.2 + .4
        put('folding_wooden_stool', (math.cos(a) * 1.25, math.sin(a) * 1.25, 0), a + 1.57)
    put('wooden_crate_01', (-1.1, .9, 0), .6, s=.8)
    box('Chow table', (1.2, .6, .04), M['timber'], (1.1, -.9, .74), (0, 0, .3), bevel=.006)
    for sx in (-1, 1):
        for sy in (-1, 1):
            beam('Chow table leg', Vector((1.1, -.9, 0)) + Matrix.Rotation(.3, 3, 'Z') @ Vector((sx * .52, sy * .24, 0)), Vector((1.1, -.9, .72)) + Matrix.Rotation(.3, 3, 'Z') @ Vector((sx * .52, sy * .24, 0)), .05, .05, M['timber_dark'])
    for k in range(3): put('wooden_bowl_02', (0.8 + k * .22, -.95 + k * .08, .76), rng.uniform(0, 6))
    put('carved_wooden_plate', (1.4, -.75, .76), .5)
    put('wooden_bucket_01', (-.8, -.6, 0), .2)
    # lantern pole with the HOT CHOW board
    beam('Chow pole', (-.9, -1.2, 0), (-.92, -1.22, 2.6), .1, .1, M['timber'])
    beam('Chow arm', (-.92, -1.22, 2.45), (-.2, -1.2, 2.45), .07, .07, M['timber_dark'])
    lantern_on(Vector((-.3, -1.2, 2.42)), 'LIGHT_chow')
    b = box('Chow sign', (1.1, .03, .42), M['sign_chow'], (-.9, -1.3, 1.7), bevel=0)
    me = b.data; bm = bmesh.new(); bm.from_mesh(me); uvl = bm.loops.layers.uv.verify()
    for f in bm.faces:
        for l in f.loops: l[uvl].uv = ((l.vert.co.x if f.normal.y < 0 else -l.vert.co.x) / 1.1 + .5, l.vert.co.z / .42 + .5)
    bm.to_mesh(me); bm.free()
    for nm, z in (('SMOKE_chow', 1.0), ('LIGHT_fire', .7)):
        e = bpy.data.objects.new(nm, None); link(e, 'marker'); e.location = (0, 0, z)
    col_box('stove', (0, 0, .45), (.7, .7, .9)); col_box('table', (1.1, -.9, .4), (1.3, .7, .8), .3); col_box('pole', (-.9, -1.2, 1.3), (.15, .15, 2.6))

# ---------------------------------------------------------------- assembly


def merge_group(coll, root, stall_name):
    """Join structure and goods into one mesh each, parented under the stall root."""
    for kind in ('structure', 'goods'):
        obs = [o for o in coll.objects if o.get('kind') == kind and o.type == 'MESH']
        if not obs: continue
        bpy.ops.object.select_all(action='DESELECT')
        for o in obs:
            o.data = o.data.copy() if o.data.users > 1 else o.data
            o.select_set(True)
        bpy.context.view_layer.objects.active = obs[0]
        bpy.ops.object.join()
        j = bpy.context.view_layer.objects.active
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        j.name = f'{stall_name} {kind.title()}'; j.data.name = j.name
        j.parent = root
    for o in list(coll.objects):
        if o.get('kind') in ('collision', 'marker'): o.parent = root


def build(stall_name, fn, ux, uz, face):
    coll = new_collection(stall_name, MARKET)
    CUR['coll'] = coll; CUR['kind'] = 'structure'
    fn()
    root = bpy.data.objects.new(stall_name, None); coll.objects.link(root)
    merge_group(coll, root, stall_name)
    root.location = U(ux, uz); root.rotation_euler = (0, 0, yaw_facing(*face))
    bpy.context.view_layer.update()
    return root


STALLS = [
    ('Stall Produce', produce_stall, -40.0, 12.0, (1, 0)),
    ('Stall Pottery Water', pottery_stall, -39.7, 5.2, (1, 0)),
    ('Stall Scrap Tools', tools_stall, -39.8, -10.8, (1, 0)),
    ('Stall Cloth Rugs', cloth_stall, -34.0, 16.6, (0, -1)),
    ('Stall Rations', rations_stall, -34.0, -16.2, (0, 1)),
    ('Cookfire', cookfire, -35.0, -3.0, (1, 0)),
]
roots = {n: build(n, f, x, z, face) for n, f, x, z, face in STALLS}


def world_top(root, sx, y, h):
    return root.matrix_world @ Vector((sx * W / 2, y, h))


# bunting across the lane between stall tops and two salvaged pipe masts
coll = new_collection('Bunting', MARKET); CUR['coll'] = coll; CUR['kind'] = 'structure'
masts = [U(-33.0, 8.5), U(-33.0, -8.0)]
for i, m in enumerate(masts):
    tube('Mast', [m, m + Vector((.03, -.02, 4.3))], .06, M['rust'], sides=8, uv_len=.6)
    box('Mast foot', (.5, .5, .35), M['timber_dark'], m + Vector((0, 0, .175)), (0, 0, .3), bevel=.02)
    lantern_on(m + Vector((.25, 0, 3.0)), f'LIGHT_mast_{i}')
    beam('Mast arm', m + Vector((0, 0, 3.05)), m + Vector((.3, 0, 3.05)), .04, .04, M['rust'])
    col_box(f'mast_{i}', m + Vector((0, 0, 1.5)), (.5, .5, 3.0))
mt = [m + Vector((0, 0, 4.2)) for m in masts]
runs = [(world_top(roots['Stall Produce'], 1, FY, 2.45), mt[0]), (world_top(roots['Stall Pottery Water'], -1, FY, 2.4), mt[0]),
        (mt[0], world_top(roots['Stall Cloth Rugs'], -1, FY, 2.5)), (mt[0], mt[1]),
        (world_top(roots['Stall Scrap Tools'], 1, FY, 2.4), mt[1]), (mt[1], world_top(roots['Stall Rations'], 1, FY, 2.45)),
        (world_top(roots['Stall Pottery Water'], 1, FY, 2.4), world_top(roots['Stall Produce'], -1, FY, 2.45))]
for a, b in runs:
    L = (b - a).length; sag = .12 * L
    pts = sag_curve(a, b, sag, 24)
    tube('Bunting line', pts, .006, M['rope'], sides=4, uv_len=3)
    n = int(L / .42)
    for k in range(1, n):
        t = k / n; p = Vector(a).lerp(Vector(b), t) - Vector((0, 0, sag * 4 * t * (1 - t)))
        d = (Vector(b) - Vector(a)).normalized(); side = d.cross(Vector((0, 0, 1))).normalized()
        tw = rng.uniform(-.25, .25)
        q0 = p - d * .11; q1 = p + d * .11; tip = p + Vector((0, 0, -.27)) + side * tw * .1
        bm = bmesh.new(); vs = [bm.verts.new(v) for v in (q0, q1, tip)]; f = bm.faces.new(vs)
        uvl = bm.loops.layers.uv.verify()
        for l, uv in zip(f.loops, ((0, 1), (1, 1), (.5, 0))): l[uvl].uv = (uv[0] * .25, uv[1] * .3)
        mesh_obj('Pennant', bm, M[rng.choice(CANVAS_TINTS + ['canvas_stripe'])])
root = bpy.data.objects.new('Bunting', None); coll.objects.link(root)
merge_group(coll, root, 'Bunting')

# caravan overflow by the truck
coll = new_collection('Caravan stock', MARKET); CUR['coll'] = coll
put('wooden_barrels_01', U(-45.2, 6.3), yaw_facing(1, .4), s=.8)
put('wooden_crate_02', U(-43.6, -7.6), .4); put('wooden_crate_02', U(-43.5, -7.55, .47), .5); put('wooden_crate_01', U(-44.6, -8.4), 1.1)
put('old_military_crate', U(-46.0, -8.6), .3, s=.8)
for k in range(4): put('metal_jerrycan_green', U(-42.8 + k * .22, 3.6), .1 + rng.uniform(-.1, .1))
col_box('barrels', U(-45.2, 6.3, .45), (4.0, 3.0, .9), yaw_facing(1, .4))
col_box('crates', U(-44.3, -8.0, .5), (2.8, 2.0, 1.0), .4)
col_box('cans', U(-42.45, 3.6, .25), (1.1, .4, .5))
root = bpy.data.objects.new('Caravan stock', None); coll.objects.link(root)
merge_group(coll, root, 'Caravan stock')

# ---------------------------------------------------------------- report + export
report = {}
for o in MARKET.all_objects:
    if o.type == 'MESH':
        report[o.name] = dict(tris=sum(len(p.vertices) - 2 for p in o.data.polygons), materials=len(o.data.materials))
report['_total_tris'] = sum(v['tris'] for k, v in report.items() if not k.startswith('COL_') and isinstance(v, dict))
(ROOT / 'geometry-report.json').write_text(json.dumps(report, indent=1))
bpy.context.view_layer.layer_collection.children['LIB'].exclude = True
bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection.children['KaraveenMarket']
OUT_GLB.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.export_scene.gltf(filepath=str(OUT_GLB), export_format='GLB', use_active_collection=True, use_active_collection_with_nested=True,
                          export_apply=True, export_yup=True, export_lights=False, export_cameras=False, export_image_format='AUTO', export_jpeg_quality=88)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND), compress=True)
print('MARKET_DONE', report['_total_tris'])
