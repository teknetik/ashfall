"""Ward district retrofit kit: helpers, materials and parametric components (Blender 5.2, bpy/bmesh).

Executed by build_retrofit.py. Conventions:
  * Ward/Unity world position (x, z, height y) -> Blender Vector((-x, -z, y))   (see U())
  * Components are authored in a local frame: +X along the wall/row, +Y outward/forward, +Z up,
    then moved into the world with a 4x4 matrix (frame()).
  * Every object is tagged obj['kind'] in {'structure', 'detail', 'decal', 'glow', 'collision', 'marker'}
    for the final merge; COL_* boxes become Unity BoxColliders, LIGHT_* empties become practical lights.
"""
import bpy, bmesh, math, random, json, glob
import numpy as np
from mathutils import Vector, Matrix, Euler
from pathlib import Path

ROOT = Path('/home/teknetik/code/ao2/art/ward_retrofit_20260926')
PT = ROOT / 'sources' / 'textures'; PH = ROOT / 'sources' / 'polyhaven'; TX = ROOT / 'textures'
MK = Path('/home/teknetik/code/ao2/art/karaveen_market_20260926/sources/textures')
rng = random.Random(20260926)

# ---------------------------------------------------------------- survey heightmap (Unity world, see survey/README)
_g = json.loads((ROOT / 'survey' / 'grid.json').read_text())
TOP = np.fromfile(ROOT / 'survey' / 'top.f32', dtype='<f4').reshape(_g['nz'], _g['nx'])
BLOCK = np.fromfile(ROOT / 'survey' / 'block.f32', dtype='<f4').reshape(_g['nz'], _g['nx'])


def _ij(x, z):
    return (int(round((x - _g['x0']) / _g['step'])), int(round((z - _g['z0']) / _g['step'])))


def top_at(x, z):
    i, j = _ij(x, z)
    return float(TOP[min(max(j, 0), _g['nz'] - 1), min(max(i, 0), _g['nx'] - 1)])


def region(x0, x1, z0, z1, arr=None):
    a = TOP if arr is None else arr
    i0, j0 = _ij(min(x0, x1), min(z0, z1)); i1, j1 = _ij(max(x0, x1), max(z0, z1))
    return a[max(j0, 0):j1 + 1, max(i0, 0):i1 + 1]


def blocked(x0, x1, z0, z1):
    return float(region(x0, x1, z0, z1, BLOCK).max()) > 0


def find_free(x, z, hw, hd, radius=3.5, margin=.3):
    """Nearest (x, z) within radius whose footprint (half sizes hw, hd) is clear of existing colliders."""
    best = None
    for dx in np.arange(-radius, radius + .01, .25):
        for dz in np.arange(-radius, radius + .01, .25):
            d = dx * dx + dz * dz
            if d > radius * radius or (best and d >= best[0]): continue
            if not blocked(x + dx - hw - margin, x + dx + hw + margin, z + dz - hd - margin, z + dz + hd + margin): best = (d, x + dx, z + dz)
    return best[1:] if best else None


# ---------------------------------------------------------------- scene/collections
scene = bpy.context.scene


def U(x, z, y=0.0):
    return Vector((-x, -z, y))


def new_collection(name, parent=None):
    c = bpy.data.collections.new(name)
    (parent or scene.collection).children.link(c)
    return c


CUR = {'coll': None, 'kind': 'structure', 'rec': None}


def link(ob, kind=None):
    CUR['coll'].objects.link(ob)
    ob['kind'] = kind or CUR['kind']
    if CUR['rec'] is not None: CUR['rec'].append(ob)
    return ob


class kind:
    """with kind('detail'): ... objects created inside get that tag."""
    def __init__(self, k): self.k = k
    def __enter__(self): self.prev = CUR['kind']; CUR['kind'] = self.k
    def __exit__(self, *a): CUR['kind'] = self.prev


class record:
    """Collect every object created inside the block (for transforming a component)."""
    def __enter__(self): self.prev = CUR['rec']; CUR['rec'] = []; return CUR['rec']
    def __exit__(self, *a):
        rec = CUR['rec']; CUR['rec'] = self.prev
        if self.prev is not None: self.prev.extend(rec)


def frame(ux, uz, y, nx, nz):
    """Matrix taking local component space (X along, Y outward (Unity dir nx,nz), Z up) to Blender world."""
    Y = Vector((-nx, -nz, 0)).normalized(); X = Vector((Y.y * 1, -Y.x, 0)) * -1
    X = Vector((-Y.y, Y.x, 0)) * -1
    # right-handed: X = Y x Z
    X = Y.cross(Vector((0, 0, 1)))
    m = Matrix((X, Y, Vector((0, 0, 1)))).transposed().to_4x4()
    m.translation = U(ux, uz, y)
    return m


def yaw_frame(ux, uz, y, yaw_deg):
    """Local +Y faces Unity yaw (0 = +z, 90 = +x)."""
    a = math.radians(yaw_deg)
    return frame(ux, uz, y, math.sin(a), math.cos(a))


def place(obs, M):
    bpy.context.view_layer.update()   # matrix_world is stale until the depsgraph evaluates new location/rotation
    for o in obs:
        if o.parent is None: o.matrix_world = M @ o.matrix_world


# ---------------------------------------------------------------- materials
_images = {}


def image(path, data=False):
    key = str(path)
    if key not in _images:
        im = bpy.data.images.load(key)
        if data: im.colorspace_settings.name = 'Non-Color'
        _images[key] = im
    return _images[key]


def pbr(name, diff, nor=None, rough=None, rough_val=.8, metal=0., metal_map=None, double=False, emit=None, emit_strength=1.,
        alpha=False, nor_strength=1., emit_map=False):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = image(diff)
    nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
    if alpha:
        nt.links.new(t.outputs['Alpha'], b.inputs['Alpha'])
        m.surface_render_method = 'BLENDED'
    if rough:
        r = nt.nodes.new('ShaderNodeTexImage'); r.image = image(rough, True)
        nt.links.new(r.outputs['Color'], b.inputs['Roughness'])
    else:
        b.inputs['Roughness'].default_value = rough_val
    if metal_map:
        mm = nt.nodes.new('ShaderNodeTexImage'); mm.image = image(metal_map, True)
        nt.links.new(mm.outputs['Color'], b.inputs['Metallic'])
    else:
        b.inputs['Metallic'].default_value = metal
    if nor:
        n = nt.nodes.new('ShaderNodeTexImage'); n.image = image(nor, True)
        nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = nor_strength
        nt.links.new(n.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    if emit_map:
        nt.links.new(t.outputs['Color'], b.inputs['Emission Color']); b.inputs['Emission Strength'].default_value = emit_strength
    elif emit:
        b.inputs['Emission Color'].default_value = (*emit, 1); b.inputs['Emission Strength'].default_value = emit_strength
    m.use_backface_culling = not double
    return m


def flat(name, rgb, rough=.7, metal=0., emit=None, emit_strength=4., alpha=1., double=False):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*rgb, 1); b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if emit:
        b.inputs['Emission Color'].default_value = (*emit, 1); b.inputs['Emission Strength'].default_value = emit_strength
    if alpha < 1:
        b.inputs['Alpha'].default_value = alpha; m.surface_render_method = 'BLENDED'
    m.use_backface_culling = not double
    return m


def P(asset, res='2k'):
    d = PT / asset
    f = lambda k: next(iter(sorted(d.glob(f'{asset}_{k}_{res}.jpg'))), None)
    return dict(diff=f('diff'), nor=f('nor_gl'), rough=f('rough'), metal_map=f('metal'))


def ph(name, asset, diff=None, **kw):
    p = P(asset)
    if diff: p['diff'] = diff
    p.update(kw)
    return pbr(name, **p)


M = {
    'plate_teal': ph('Retro_PlateTeal', 'blue_metal_plate', TX / 'plate_teal.jpg', metal=.35),
    'plate_bone': ph('Retro_PlateBone', 'blue_metal_plate', TX / 'plate_bone.jpg', metal=.3),
    'plate_olive': ph('Retro_PlateOlive', 'green_metal_rust', metal=.3),
    'panel': ph('Retro_PanelGraphite', 'metal_plate_02', TX / 'panel_graphite.jpg'),
    'panel_rust': ph('Retro_PanelRust', 'metal_plate_02'),
    'rust_paint': ph('Retro_RustPaint', 'rusty_painted_metal', metal=.4),
    'rust': ph('Retro_Rust', 'rusty_metal_04', metal=.55),
    'rust_sheet': ph('Retro_RustSheet', 'rusty_metal_sheet', metal=.5, double=True),
    'corrugated': ph('Retro_Corrugated', 'corrugated_iron_02', double=True),
    'corrugated_worn': ph('Retro_CorrugatedWorn', 'worn_corrugated_iron', metal=.45, double=True),
    'grate': ph('Retro_Grate', 'metal_grate_rusty'),
    'tread': ph('Retro_Tread', 'metal_plate'),
    'shutter': ph('Retro_Shutter', 'painted_metal_shutter', metal=.3),
    'concrete': ph('Retro_Concrete', 'concrete_wall_008'),
    'concrete_cracked': ph('Retro_ConcreteCracked', 'cracked_concrete_wall'),
    'concrete_ribbed': ph('Retro_ConcreteRibbed', 'ribbed_concrete_wall'),
    'rubble': ph('Retro_Rubble', 'concrete_debris'),
    'factory': ph('Retro_FactoryWall', 'factory_wall'),
    'container_rust': ph('Retro_ContainerRust', 'container_side', TX / 'container_rust.jpg', metal=.35),
    'container_blue': ph('Retro_ContainerBlue', 'container_side', TX / 'container_blue.jpg', metal=.35),
    'container_sand': ph('Retro_ContainerSand', 'container_side', TX / 'container_sand.jpg', metal=.35),
    'container_olive': ph('Retro_ContainerOlive', 'container_side', TX / 'container_olive.jpg', metal=.35),
    'hazard': pbr('Retro_Hazard', TX / 'hazard.jpg', PT / 'rusty_metal_04/rusty_metal_04_nor_gl_2k.jpg', rough_val=.7, metal=.2),
    'hesco': pbr('Retro_Hesco', TX / 'hesco.jpg', MK / 'hessian_230/hessian_230_nor_gl_1k.jpg', rough_val=.95),
    'banner': pbr('Retro_WardenBanner', TX / 'warden_banner.jpg', MK / 'rough_linen/rough_linen_nor_gl_1k.jpg', rough_val=.95, double=True),
    'tarp': pbr('Retro_Tarp', MK.parent.parent / 'textures' / 'canvas_olive.jpg', MK / 'rough_linen/rough_linen_nor_gl_1k.jpg', rough_val=.9, double=True),
    'tarp_rust': pbr('Retro_TarpRust', MK.parent.parent / 'textures' / 'canvas_rust.jpg', MK / 'rough_linen/rough_linen_nor_gl_1k.jpg', rough_val=.9, double=True),
    'steel': flat('Retro_Steel', (.34, .33, .31), rough=.42, metal=.9),
    'dark': flat('Retro_Composite', (.075, .08, .085), rough=.55, metal=.2),
    'rubber': flat('Retro_Rubber', (.035, .033, .03), rough=.85),
    'glass': flat('Retro_Glass', (.04, .06, .07), rough=.08, metal=.6),
    'solar': flat('Retro_SolarCell', (.05, .07, .12), rough=.18, metal=.5),
    'poly': flat('Retro_Polycarbonate', (.78, .82, .74), rough=.35, alpha=.42, double=True),
    'cyan': flat('Retro_CyanGlow', (.2, .8, .9), rough=.4, emit=(.25, .85, 1.0), emit_strength=6.),
    'cyan_dim': flat('Retro_CyanDim', (.1, .35, .4), rough=.4, emit=(.2, .75, .9), emit_strength=1.6),
    'amber': flat('Retro_AmberGlow', (1., .6, .25), rough=.4, emit=(1., .55, .2), emit_strength=5.),
    'red': flat('Retro_RedGlow', (.8, .1, .08), rough=.4, emit=(1., .12, .08), emit_strength=5.),
    'grow': pbr('Retro_GrowLight', TX / 'growlight.jpg', rough_val=.5, emit=(.95, .62, .9), emit_strength=2.5),
    'leaf': flat('Retro_Leaf', (.16, .3, .09), rough=.6, double=True),
    'leaf2': flat('Retro_Leaf2', (.28, .36, .1), rough=.6, double=True),
    'soil': ph('Retro_Soil', 'concrete_debris', diff=MK / 'hessian_230/hessian_230_diff_1k.jpg'),
}
M['soil'] = flat('Retro_Soil', (.16, .11, .07), rough=.95)
DECAL = {k: pbr('Decal_' + k, TX / f'{k}.png', rough_val=.85, alpha=True) for k in
         ['scorch', 'pocks', 'streaks', 'sigil', 'stencil_fab2', 'stencil_fab2b', 'stencil_aquifer', 'stencil_hydroA', 'stencil_hydroB',
          'stencil_node', 'stencil_proc', 'stencil_hv', 'stencil_potable', 'stencil_watch1', 'stencil_watch2', 'stencil_watch3', 'stencil_watch4']}
for k in ['relay', 'water', 'tools', 'salvage', 'finery', 'supply', 'repairs', 'thread']:
    M['blade_' + k] = pbr('Retro_Blade_' + k, TX / f'blade_{k}.jpg', rough_val=.3, emit_map=True, emit_strength=2.2)
M['interior'] = flat('Retro_InteriorGlow', (.9, .75, .5), rough=.6, emit=(1., .72, .42), emit_strength=1.2)
PAINTS = ['plate_teal', 'plate_bone', 'plate_olive', 'panel', 'rust_paint']

# ---------------------------------------------------------------- mesh primitives


def mesh_obj(name, bm, mat, smooth=False, k=None):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for layer in me.uv_layers: layer.name = 'UVMap'
    if smooth:
        for p in me.polygons: p.use_smooth = True
    if isinstance(mat, (list, tuple)):
        for mm in mat: me.materials.append(mm)
    else:
        me.materials.append(mat)
    return link(bpy.data.objects.new(name, me), k)


def box_uv(ob, scale=.5, offset=None):
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


def box(name, size, mat, loc=(0, 0, 0), rot=(0, 0, 0), bevel=.01, uv=.5, k=None, seg=1):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    if bevel > 0 and min(size) > bevel * 3:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=seg, affect='EDGES', profile=.5)
    ob = mesh_obj(name, bm, mat, k=k)
    box_uv(ob, uv)
    ob.location = loc; ob.rotation_euler = rot
    return ob


def span(name, p1, p2, w, h, mat, bevel=.008, roll=0., uv=.5, k=None):
    """Box member between two points (local X width, Y height, Z along)."""
    p1, p2 = Vector(p1), Vector(p2); d = p2 - p1; L = d.length
    ob = box(name, (w, h, L), mat, bevel=bevel, uv=uv, k=k)
    q = d.normalized().to_track_quat('Z', 'Y')
    ob.rotation_mode = 'QUATERNION'; ob.rotation_quaternion = q @ Euler((0, 0, roll)).to_quaternion()
    ob.location = (p1 + p2) / 2
    return ob


def ibeam(name, p1, p2, h=.3, w=.18, t=.022, mat=None, k=None):
    """Steel I-section: two flanges and a web (the silhouette that reads as structural steel)."""
    mat = mat or M['rust']
    p1, p2 = Vector(p1), Vector(p2); d = (p2 - p1)
    q = d.normalized().to_track_quat('Z', 'Y')
    obs = []
    for off, size in (((0, h / 2 - t / 2), (w, t)), ((0, -h / 2 + t / 2), (w, t)), ((0, 0), (t * .8, h - 2 * t))):
        o = box(name, (size[0], size[1], d.length), mat, bevel=.004, uv=.6, k=k)
        o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = q
        o.location = (p1 + p2) / 2 + q @ Vector((off[0], off[1], 0))
        obs.append(o)
    return obs


def cyl(name, r, h, mat, loc=(0, 0, 0), rot=(0, 0, 0), sides=20, caps=True, uv=.5, k=None, r2=None, smooth=True):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=caps, cap_tris=False, segments=sides, radius1=r, radius2=r if r2 is None else r2, depth=h)
    bmesh.ops.translate(bm, vec=(0, 0, h / 2), verts=bm.verts)
    uvl = bm.loops.layers.uv.verify(); circ = 2 * math.pi * r
    for f in bm.faces:
        for l in f.loops:
            co = l.vert.co
            if abs(f.normal.z) > .9: l[uvl].uv = (co.x * uv, co.y * uv)
            else: l[uvl].uv = ((math.atan2(co.y, co.x) / (2 * math.pi) + .5) * circ * uv, co.z * uv)
    # fix seam wrap
    for f in bm.faces:
        if abs(f.normal.z) < .9:
            us = [l[uvl].uv.x for l in f.loops]
            if max(us) - min(us) > circ * uv * .5:
                for l in f.loops:
                    if l[uvl].uv.x < circ * uv * .5: l[uvl].uv.x += circ * uv
    ob = mesh_obj(name, bm, mat, smooth=False, k=k)
    if smooth:
        for p in ob.data.polygons: p.use_smooth = abs(p.normal.z) < .9
    ob.location = loc; ob.rotation_euler = rot
    return ob


def cyl_between(name, p1, p2, r, mat, sides=16, caps=True, k=None, uv=.5):
    p1, p2 = Vector(p1), Vector(p2); d = p2 - p1
    o = cyl(name, r, d.length, mat, sides=sides, caps=caps, k=k, uv=uv)
    o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = d.normalized().to_track_quat('Z', 'Y')
    o.location = p1
    return o


def tube(name, pts, radius, mat, sides=10, uv_len=1.0, k=None, caps=False):
    bm = bmesh.new(); rings = []; acc = 0.
    uvl = bm.loops.layers.uv.verify(); vcoords = []
    prev_a = None
    for i, p in enumerate(pts):
        p = Vector(p)
        t = (Vector(pts[min(i + 1, len(pts) - 1)]) - Vector(pts[max(i - 1, 0)])).normalized()
        if prev_a is None: a = t.orthogonal().normalized()
        else: a = (prev_a - t * prev_a.dot(t)).normalized()   # parallel transport: no twisting
        prev_a = a; b = t.cross(a)
        if i: acc += (p - Vector(pts[i - 1])).length
        rings.append([bm.verts.new(p + (a * math.cos(2 * math.pi * kk / sides) + b * math.sin(2 * math.pi * kk / sides)) * radius) for kk in range(sides)])
        vcoords.append(acc)
    for i in range(len(rings) - 1):
        for kk in range(sides):
            f = bm.faces.new((rings[i][kk], rings[i][(kk + 1) % sides], rings[i + 1][(kk + 1) % sides], rings[i + 1][kk]))
            for l, (ri, q) in zip(f.loops, ((i, kk), (i, kk + 1), (i + 1, kk + 1), (i + 1, kk))):
                l[uvl].uv = (q / sides * 2 * math.pi * radius * uv_len, vcoords[ri] * uv_len)
    if caps:
        for ring in (rings[0][::-1], rings[-1]):
            bm.faces.new(ring)
    bm.normal_update()
    return mesh_obj(name, bm, mat, smooth=True, k=k)


def fillet(pts, r):
    """Round polyline corners (pipe bends) with a few points on each corner."""
    pts = [Vector(p) for p in pts]
    if len(pts) < 3: return pts
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        a, b, c = pts[i - 1], pts[i], pts[i + 1]
        d1 = (a - b); d2 = (c - b); rr = min(r, d1.length * .45, d2.length * .45)
        s = b + d1.normalized() * rr; e = b + d2.normalized() * rr
        for k in range(5):
            t = k / 4; out.append((1 - t) ** 2 * s + 2 * (1 - t) * t * b + t ** 2 * e)
    out.append(pts[-1])
    return out


def sag_curve(a, b, sag, n=18):
    a, b = Vector(a), Vector(b)
    return [a.lerp(b, i / (n - 1)) - Vector((0, 0, sag * 4 * (i / (n - 1)) * (1 - i / (n - 1)))) for i in range(n)]


def cable(a, b, sag=.3, r=.018, mat=None, name='Cable'):
    return tube(name, sag_curve(a, b, sag, 18), r, mat or M['rubber'], sides=6, uv_len=2.)


def quad(name, p00, p10, p11, p01, mat, uv=((0, 0), (1, 0), (1, 1), (0, 1)), k=None):
    bm = bmesh.new(); vs = [bm.verts.new(Vector(p)) for p in (p00, p10, p11, p01)]
    f = bm.faces.new(vs); uvl = bm.loops.layers.uv.verify()
    for l, t in zip(f.loops, uv): l[uvl].uv = t
    return mesh_obj(name, bm, mat, k=k)


def decal(key, w, h, loc=(0, 0, 0), rot=(0, 0, 0)):
    """Alpha decal plane in local XZ facing +Y (use on walls whose outward normal is +Y)."""
    # seen from +Y, local +X is on the viewer's left, so U runs toward -X for readable lettering
    o = quad('Decal ' + key, (-w / 2, 0, -h / 2), (w / 2, 0, -h / 2), (w / 2, 0, h / 2), (-w / 2, 0, h / 2), DECAL[key],
             uv=((1, 0), (0, 0), (0, 1), (1, 1)), k='decal')
    o.location = loc; o.rotation_euler = rot
    return o


def sheet(name, fn, res, mat, uv_size, k=None, holes=0.):
    nu, nv = res; bm = bmesh.new(); uvl = bm.loops.layers.uv.verify()
    V = [[bm.verts.new(fn(i / nu, j / nv)) for i in range(nu + 1)] for j in range(nv + 1)]
    for j in range(nv):
        for i in range(nu):
            if holes and rng.random() < holes: continue
            f = bm.faces.new((V[j][i], V[j][i + 1], V[j + 1][i + 1], V[j + 1][i]))
            for l, (a, b) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                l[uvl].uv = (a / nu * uv_size[0], b / nv * uv_size[1])
    bm.normal_update()
    return mesh_obj(name, bm, mat, smooth=True, k=k)


def col_box(name, center, size, rz=0.):
    o = box('COL_' + name, size, M['dark'], center, (0, 0, rz), bevel=0, k='collision')
    return o


def light_marker(name, loc, color='cyan'):
    e = bpy.data.objects.new(f'LIGHT_{color}_{name}', None); e.location = loc
    return link(e, 'marker')


# ---------------------------------------------------------------- Poly Haven library (CC0)
LIBC = None
LIB = {}


def lib(name, part=None, target=None, key=None, path=None):
    key = key or (name + (':' + part if part else ''))
    if key in LIB: return LIB[key]
    global LIBC
    if LIBC is None:
        LIBC = new_collection('LIB')
    before = set(bpy.data.objects)
    lc = bpy.context.view_layer.layer_collection.children['LIB']
    bpy.context.view_layer.active_layer_collection = lc
    bpy.ops.import_scene.gltf(filepath=str(path) if path else glob.glob(str(PH / name / '*.gltf'))[0])
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == 'MESH' and (part is None or o.name.startswith(part))]
    if part and not meshes: raise KeyError(part)
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
    ob.name = 'LIB_' + key; ob.data.name = ob.name
    ob['dims'] = list(mx - mn)
    for l in ob.data.uv_layers: l.name = 'UVMap'
    LIB[key] = ob
    return ob


def put(key, loc, rz=0., s=1., k='detail', rx=0., ry=0.):
    src = LIB[key]; o = src.copy()
    link(o, k)
    o.rotation_mode = 'XYZ'   # glTF imports come in quaternion mode, which would ignore rotation_euler
    o.location = loc; o.rotation_euler = (rx, ry, rz); o.scale = (s, s, s)
    return o


def dims(key): return Vector(LIB[key]['dims'])


# ---------------------------------------------------------------- components (local space)

def bolts(pts, r=.022, h=.02, mat=None):
    for p in pts:
        cyl('Bolt', r, h, mat or M['steel'], loc=p, rot=(-math.pi / 2, 0, 0), sides=6, caps=True, k='detail')


def armor_panel(w, h, mat, t=.045, loc=(0, 0, 0), tilt=0., bolted=True):
    """Bolt-on plate (local wall at y=0, plate stands off +Y)."""
    x, y, z = loc
    o = box('Armor plate', (w, t, h), mat, (x, y + t / 2 + .015, z), (tilt, 0, rng.uniform(-.012, .012)), bevel=.012, uv=.45)
    if bolted:
        n = max(2, int(w / .35))
        pts = []
        for i in range(n):
            u = -w / 2 + .07 + (w - .14) * i / (n - 1)
            pts += [(x + u, y + t + .025, z + h / 2 - .06), (x + u, y + t + .025, z - h / 2 + .06)]
        bolts(pts)
    return o


def light_strip(length, loc=(0, 0, 0), glow='cyan', vertical=False):
    x, y, z = loc
    if vertical:
        box('Strip housing', (.12, .07, length), M['dark'], (x, y + .035, z), bevel=.01)
        box('Strip glow', (.05, .02, length - .08), M[glow], (x, y + .075, z), bevel=0, k='glow')
    else:
        box('Strip housing', (length, .07, .12), M['dark'], (x, y + .035, z), bevel=.01)
        box('Strip glow', (length - .08, .02, .05), M[glow], (x, y + .075, z), bevel=0, k='glow')


def wall_pipe(pts_xz, r, y, mat=None, brackets=1.6):
    """Pipe running on a wall: pts in local (x, z) at stand-off y; brackets back to the wall; flanges at joints."""
    mat = mat or M['rust']
    pts = [Vector((p[0], y, p[1])) for p in pts_xz]
    tube('Pipe', fillet(pts, r * 3), r, mat, sides=12, uv_len=.8, caps=True)
    with kind('detail'):
        for a, b in zip(pts, pts[1:]):
            L = (b - a).length; n = max(1, int(L / brackets))
            for i in range(n + 1):
                p = a.lerp(b, (i + .5) / (n + 1)) if i < n else None
                if p is None: continue
                box('Pipe bracket', (.05, y - r + .02, .05), M['steel'], (p.x, (y - r) / 2, p.z), bevel=.004)
                d = (b - a).normalized()
                cyl_between('Pipe clamp', p - d * .025, p + d * .025, r * 1.18, M['steel'], sides=12, k='detail')
        for p in pts[1:-1]:
            pass


def conduit_bundle(pts_xz, y, n=3, r=.03, spacing=.075):
    for i in range(n):
        off = (i - (n - 1) / 2) * spacing
        pts = []
        for j, p in enumerate(pts_xz):
            pts.append(Vector((p[0], y + (.0 if n == 1 else 0), p[1])))
        # offset perpendicular to run in wall plane
        d = (pts[-1] - pts[0]).normalized(); perp = Vector((d.z, 0, -d.x))
        tube('Conduit', fillet([p + perp * off for p in pts], .15), r, M['rubber'] if i % 2 else M['steel'], sides=6, uv_len=1.)


def hvac_unit(w=1.8, d=1.2, h=1.0):
    """Rooftop air handler: panelled body, louvred sides, fan shroud with grille, rails."""
    for s in (-1, 1):
        box('HVAC rail', (w + .2, .1, .1), M['steel'], (0, s * (d / 2 - .1), .05))
    box('HVAC body', (w, d, h), M['panel'], (0, 0, .1 + h / 2), bevel=.025, uv=.6)
    with kind('detail'):
        for i in range(7):   # louvres on the front
            box('Louvre', (w * .8, .03, .06), M['steel'], (0, d / 2 + .02, .25 + i * (h - .3) / 7), (math.radians(35), 0, 0), bevel=0)
        cyl('Fan shroud', min(w, d) * .36, .22, M['dark'], loc=(w * .1, 0, .1 + h), sides=24)
        cyl('Fan hub', .08, .26, M['steel'], loc=(w * .1, 0, .1 + h), sides=10)
        R = min(w, d) * .34
        for i in range(6):
            a = math.pi * i / 6
            span('Grille bar', (w * .1 + math.cos(a) * R, math.sin(a) * R, .1 + h + .23), (w * .1 - math.cos(a) * R, -math.sin(a) * R, .1 + h + .23), .012, .012, M['steel'], bevel=0)
        box('Access panel', (.5, .02, .6), M['plate_bone'], (-w * .3, -d / 2 - .01, .1 + h * .5), bevel=.005)
        cyl('Duct', .16, .5, M['steel'], loc=(-w / 2 - .25, 0, .1 + h * .6), rot=(0, math.pi / 2, 0), sides=12)


def vent_stack(r=.18, h=1.6):
    cyl('Vent stack', r, h, M['steel'], sides=14)
    cyl('Vent cap', r * 1.7, .12, M['rust'], loc=(0, 0, h + .18), sides=14, r2=r * .3)
    for i in range(3):
        a = 2 * math.pi * i / 3
        span('Vent strut', (math.cos(a) * r, math.sin(a) * r, h - .02), (math.cos(a) * r * 1.2, math.sin(a) * r * 1.2, h + .2), .02, .02, M['steel'], k='detail')


def water_tank(r=1.0, h=2.2, mat=None, legs=.9):
    mat = mat or M['plate_bone']
    for i in range(4):
        a = math.pi / 4 + i * math.pi / 2
        ibeam('Tank leg', (math.cos(a) * r * .8, math.sin(a) * r * .8, 0), (math.cos(a) * r * .8, math.sin(a) * r * .8, legs + .05), .16, .12)
    box('Tank deck', (r * 1.9, r * 1.9, .1), M['grate'], (0, 0, legs + .05), bevel=.01)
    cyl('Tank shell', r, h, mat, loc=(0, 0, legs + .1), sides=28, uv=.4)
    cyl('Tank roof', r * 1.02, r * .35, mat, loc=(0, 0, legs + .1 + h), sides=28, r2=r * .25, uv=.4)
    with kind('detail'):
        for zz in (.35, .5 * h, h - .3):
            cyl('Tank band', r + .025, .07, M['steel'], loc=(0, 0, legs + .1 + zz), sides=28)
        # ladder
        for s in (-.2, .2):
            span('Ladder rail', (r + .12, s, legs + .1), (r + .12, s, legs + h + .3), .04, .04, M['steel'], bevel=0)
        for i in range(int(h / .3)):
            span('Rung', (r + .12, -.2, legs + .3 + i * .3), (r + .12, .2, legs + .3 + i * .3), .025, .025, M['steel'], bevel=0)
        cyl('Hatch', .3, .08, M['steel'], loc=(0, 0, legs + .1 + h + r * .35 - .02), sides=12)
        # outlet pipe
        tube('Outlet', fillet([Vector((-r * .7, 0, legs + .3)), Vector((-r * .7, 0, .25)), Vector((-r - .8, 0, .25))], .2), .09, M['rust'], sides=10)


def lattice_mast(h=7., w=.5, glow=True, dish=True, name='Mast'):
    """Triangular lattice mast with zig-zag bracing, dishes/panels, beacon."""
    legs = [Vector((math.cos(a) * w * .577, math.sin(a) * w * .577, 0)) for a in (0, 2 * math.pi / 3, 4 * math.pi / 3)]
    for L in legs:
        cyl_between(name + ' leg', L, L * .45 + Vector((0, 0, h)), .03, M['steel'], sides=8)
    n = int(h / .55)
    with kind('detail'):
        for i in range(n):
            z0 = i * h / n; z1 = (i + 1) * h / n
            s0 = 1 - .55 * z0 / h; s1 = 1 - .55 * z1 / h
            for a, b in zip(legs, legs[1:] + legs[:1]):
                p0 = a * s0 + Vector((0, 0, z0)); p1 = b * s1 + Vector((0, 0, z1))
                cyl_between('Brace', p0, p1, .012, M['steel'], sides=5, caps=False)
                if i % 3 == 0: cyl_between('Ring', a * s0 + Vector((0, 0, z0)), b * s0 + Vector((0, 0, z0)), .012, M['steel'], sides=5, caps=False)
        cyl('Whip', .015, 2.2, M['steel'], loc=(0, 0, h), sides=6)
        if dish:
            dz = h * .72
            o = cyl('Dish', .55, .16, M['plate_bone'], loc=(0, 0, 0), sides=24, r2=.12)
            o.rotation_euler = (0, math.radians(100), rng.uniform(0, 6.28)); o.location = (0, 0, dz)
            box('Panel antenna', (.25, .08, .9), M['plate_bone'], (w * .35, 0, h * .55), bevel=.01)
            box('Panel antenna', (.25, .08, .9), M['plate_bone'], (-w * .2, w * .3, h * .55), (0, 0, 2.1), bevel=.01)
    if glow:
        cyl('Beacon', .07, .12, M['red'], loc=(0, 0, h + .02), sides=10, k='glow')
        light_marker(name, Vector((0, 0, h + .1)), 'red')


def radiator_bank(n=4, w=1.1, h=1.6, tilt=35, mat=None):
    """Tilted solar/heat-exchange panels on a rail frame."""
    mat = mat or M['solar']
    t = math.radians(tilt)
    for i in range(n):
        x = (i - (n - 1) / 2) * (w + .12)
        box('Panel frame', (w, .06, h), M['steel'], (x, 0, .5 + h / 2 * math.cos(t)), (t, 0, 0), bevel=.01)
        box('Panel cells', (w - .08, .02, h - .08), mat, (x, -.035 * math.cos(t), .5 + h / 2 * math.cos(t) + .035 * math.sin(t)), (t, 0, 0), bevel=0)
        with kind('detail'):
            span('Panel leg', (x - w * .4, h * .35, 0), (x - w * .4, h * .35 * .2, .5 + h * .5), .05, .05, M['steel'], bevel=0)
            span('Panel leg', (x + w * .4, h * .35, 0), (x + w * .4, h * .35 * .2, .5 + h * .5), .05, .05, M['steel'], bevel=0)
    box('Panel rail', (n * (w + .12), .12, .1), M['steel'], (0, -h * .3, .05), bevel=.01)
    box('Panel rail', (n * (w + .12), .12, .1), M['steel'], (0, h * .35, .05), bevel=.01)


def hesco_run(length, h=1.35, d=1.05, mat=None):
    """Row of wire-mesh/geotextile barrier baskets filled with soil; slightly bulged, sagging tops."""
    n = max(1, int(round(length / d)))
    for i in range(n):
        x = -length / 2 + d * (i + .5)
        hh = h * rng.uniform(.94, 1.03)
        bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=(d * .97, d * .97, hh), verts=bm.verts)
        bmesh.ops.subdivide_edges(bm, edges=list(bm.edges), cuts=3, use_grid_fill=True)
        for v in bm.verts:
            c = v.co; zf = (c.z / hh + .5)
            bulge = (1 - (2 * zf - 1) ** 2) * .045
            if abs(c.x) < d * .48: c.y += math.copysign(bulge, c.y) * (1 - abs(c.x) / (d * .5))
            if abs(c.y) < d * .48: c.x += math.copysign(bulge, c.x) * (1 - abs(c.y) / (d * .5))
            if c.z > hh * .49: c.z -= .05 * (1 - max(abs(c.x), abs(c.y)) / (d * .5)) + rng.uniform(0, .02)
        bmesh.ops.translate(bm, vec=(x, 0, hh / 2), verts=bm.verts)
        o = mesh_obj('HESCO basket', bm, M['hesco'], smooth=True); box_uv(o, .9)
        with kind('detail'):
            for sx in (-1, 1):
                for sy in (-1, 1):
                    span('HESCO post', (x + sx * d * .49, sy * d * .49, 0), (x + sx * d * .49, sy * d * .49, hh), .025, .025, M['steel'], bevel=0)
            box('HESCO soil', (d * .9, d * .9, .06), M['rubble'], (x, 0, hh - .06), bevel=.02, uv=.6)


def container(L=6.06, W=2.44, H=2.59, mat=None, door_end=True, window=True, name='Container'):
    """ISO container shell (walls vertical corrugation), corner castings, end doors with lock rods."""
    mat = mat or M['container_rust']
    b = box(name + ' shell', (L, W, H), mat, (0, 0, H / 2), bevel=.03, uv=.42)
    with kind('detail'):
        for sx in (-1, 1):
            for sy in (-1, 1):
                for sz in (0, 1):
                    box('Corner casting', (.18, .18, .12), M['rust'], (sx * (L / 2 - .07), sy * (W / 2 - .07), .06 + sz * (H - .12)), bevel=.01)
        for sy in (-1, 1):
            box('Top rail', (L - .3, .1, .1), M['rust'], (0, sy * (W / 2 - .02), H - .06), bevel=.01)
            box('Bottom rail', (L - .3, .12, .16), M['rust'], (0, sy * (W / 2 - .02), .08), bevel=.01)
        if door_end:
            box('Door leaf', (.03, W / 2 - .06, H - .3), mat, (L / 2 + .01, -W / 4, H / 2), bevel=.01, uv=.42)
            box('Door leaf', (.03, W / 2 - .06, H - .3), mat, (L / 2 + .01, W / 4, H / 2), bevel=.01, uv=.42)
            for yy in (-W * .38, -W * .12, W * .12, W * .38):
                cyl('Lock rod', .025, H - .35, M['steel'], loc=(L / 2 + .06, yy, .18), sides=6)
        if window:
            box('Window frame', (1.2, .1, .8), M['steel'], (L * .1, -W / 2 - .03, H * .58), bevel=.01)
            box('Window glass', (1.05, .06, .66), M['glass'], (L * .1, -W / 2 - .06, H * .58), bevel=0)
            box('Window hood', (1.35, .35, .05), M['rust_sheet'], (L * .1, -W / 2 - .18, H * .58 + .5), (math.radians(-12), 0, 0), bevel=0)


def precast_column(h, s=.55, broken=0., mat=None):
    """Precast concrete column; broken>0 leaves a jagged top with bent rebar."""
    mat = mat or M['concrete']
    hh = h - broken * .5 if broken else h
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(s, s, hh), verts=bm.verts)
    if broken:
        bmesh.ops.subdivide_edges(bm, edges=[e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) < 1e-4 and e.verts[0].co.z > 0], cuts=3, use_grid_fill=True)
    bmesh.ops.bevel(bm, geom=[e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > .1], offset=.03, segments=1, affect='EDGES')
    for v in bm.verts:
        if broken and v.co.z > hh * .49: v.co.z += rng.uniform(-broken * .5, broken * .4)
    bmesh.ops.translate(bm, vec=(0, 0, hh / 2), verts=bm.verts)
    o = mesh_obj('Column', bm, mat); box_uv(o, .45)
    if broken:
        with kind('detail'):
            for i in range(5):
                p = Vector((rng.uniform(-s * .35, s * .35), rng.uniform(-s * .35, s * .35), hh - .1))
                bend = Vector((rng.uniform(-.4, .4), rng.uniform(-.4, .4), rng.uniform(.2, .6)))
                tube('Rebar', [p, p + Vector((0, 0, .35)), p + Vector((0, 0, .35)) + bend], .014, M['rust'], sides=5)
    return o


def rubble(r=2., h=.9, n=14, mat=None):
    """Heap of broken concrete chunks and slabs."""
    mat = mat or M['rubble']
    for i in range(n):
        a = rng.uniform(0, 6.28); d = r * math.sqrt(rng.random()) * .85
        s = rng.uniform(.25, .7) * (1.2 - d / r)
        cz = h * (1 - (d / r) ** 2) * .6
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.)
        for v in bm.verts: v.co = Vector((v.co.x * s * rng.uniform(.8, 1.6), v.co.y * s * rng.uniform(.8, 1.6), v.co.z * s * rng.uniform(.4, .8)))
        bmesh.ops.translate(bm, vec=(math.cos(a) * d, math.sin(a) * d, cz), verts=bm.verts)
        o = mesh_obj('Rubble chunk', bm, mat); box_uv(o, .7)
    for i in range(4):
        a = rng.uniform(0, 6.28); d = rng.uniform(.3, r * .8)
        box('Slab', (rng.uniform(.8, 1.6), rng.uniform(.5, 1.0), .16), M['concrete_cracked'], (math.cos(a) * d, math.sin(a) * d, rng.uniform(.1, h * .5)),
            (rng.uniform(-.5, .5), rng.uniform(-.5, .5), rng.uniform(0, 3)), bevel=.02, uv=.5)
    with kind('detail'):
        for i in range(6):
            p = Vector((rng.uniform(-r * .6, r * .6), rng.uniform(-r * .6, r * .6), h * .3))
            tube('Rebar', [p, p + Vector((rng.uniform(-.6, .6), rng.uniform(-.6, .6), rng.uniform(.1, .7)))], .012, M['rust'], sides=5)


def pratt_truss(L, D, mat=None, broken_at=None):
    """Planar roof truss in local XZ from x=0..L, depth D (top chord higher at mid). broken_at: fraction where it snaps."""
    mat = mat or M['rust']
    n = max(4, int(L / 1.5)); pts_b = []; pts_t = []
    for i in range(n + 1):
        x = L * i / n
        pts_b.append(Vector((x, 0, 0)))
        pts_t.append(Vector((x, 0, D * (.55 + .45 * (1 - abs(2 * i / n - 1))))))
    stop = n if broken_at is None else int(n * broken_at)
    for i in range(stop):
        span('Chord', pts_b[i], pts_b[i + 1], .1, .12, mat, bevel=.004)
        span('Chord', pts_t[i], pts_t[i + 1], .1, .12, mat, bevel=.004)
        with kind('detail'):
            span('Web', pts_b[i], pts_t[i], .05, .06, mat, bevel=0)
            span('Web', pts_b[i + 1] if i < n / 2 else pts_b[i], pts_t[i] if i < n / 2 else pts_t[i + 1], .045, .05, mat, bevel=0)
    return pts_t[:stop + 1]


def banner(w=.9, h=2.4, loc=(0, 0, 0)):
    """Hanging Warden banner on a pole (local wall normal +Y)."""
    x, y, z = loc
    cyl_between('Banner pole', (x - w / 2 - .08, y + .12, z), (x + w / 2 + .08, y + .12, z), .02, M['steel'], sides=6)
    def f(u, v):
        return Vector((x - w / 2 + u * w, y + .14 + .03 * math.sin(u * 9 + v * 3) + v * .05, z - v * h + .03 * math.sin(u * 3.1) * v))
    sheet('Warden banner', f, (8, 12), M['banner'], (1, 1), k='structure')


def scrap_turret():
    """Jury-rigged defence mount: armoured drum on a post with twin barrels and sensor."""
    cyl('Turret post', .12, 1.1, M['steel'], sides=10)
    cyl('Turret drum', .38, .45, M['plate_olive'], loc=(0, 0, 1.1), sides=16)
    box('Turret shield', (.8, .06, .5), M['rust_paint'], (0, .42, 1.35), (math.radians(-10), 0, 0), bevel=.01)
    with kind('detail'):
        for s in (-.1, .1):
            cyl('Barrel', .04, 1.0, M['dark'], loc=(s, .3, 1.32), rot=(-math.pi / 2, 0, 0), sides=8)
        box('Sensor', (.16, .12, .12), M['dark'], (.26, .2, 1.62), bevel=.01)
        cyl('Sensor lens', .035, .03, M['red'], loc=(.26, .26, 1.62), rot=(-math.pi / 2, 0, 0), sides=10, k='glow')


# ---------------------------------------------------------------- building-scale retrofit modules

def cladding(w, h, mat, seam=.02, missing=.08, depth=.06):
    """Grid of bolted composite panels over a masonry wall (local wall y=0, panels stand off +Y); a few missing."""
    nx = max(1, int(round(w / 1.25))); nz = max(1, int(round(h / 1.1)))
    pw, ph_ = w / nx, h / nz
    box('Cladding rail', (w, .05, .06), M['steel'], (0, .03, 0), bevel=0)
    box('Cladding rail', (w, .05, .06), M['steel'], (0, .03, h), bevel=0)
    for i in range(nx):
        for j in range(nz):
            if rng.random() < missing: continue
            x = -w / 2 + pw * (i + .5); z = ph_ * (j + .5)
            box('Clad panel', (pw - seam, depth, ph_ - seam), mat, (x, .05 + depth / 2 + rng.uniform(0, .012), z), (rng.uniform(-.01, .01), 0, 0), bevel=.012, uv=.45)
    with kind('detail'):
        for i in range(nx + 1):
            box('Clad mullion', (.05, .09, h), M['steel'], (-w / 2 + pw * i, .045, h / 2), bevel=.005)


def roof_module(w, d, h, mat, glow_side=True, door=True):
    """Prefab rooftop cabin: raised on a steel skid, chamfered cap, window band with lit interior, door and railing."""
    box('Module skid', (w + .2, d + .2, .25), M['steel'], (0, 0, .125), bevel=.01)
    box('Module body', (w, d, h), mat, (0, 0, .25 + h / 2), bevel=.05, uv=.45)
    box('Module cap', (w + .25, d + .25, .22), M['panel'], (0, 0, .25 + h + .11), bevel=.06)
    box('Window band', (w * .7, .06, .55), M['glass'], (-w * .08, d / 2 + .01, .25 + h * .62), bevel=0)
    box('Window frame', (w * .7 + .12, .08, .08), M['steel'], (-w * .08, d / 2 + .02, .25 + h * .62 + .31), bevel=0)
    box('Window frame', (w * .7 + .12, .08, .08), M['steel'], (-w * .08, d / 2 + .02, .25 + h * .62 - .31), bevel=0)
    box('Interior glow', (w * .66, .02, .45), M['interior'], (-w * .08, d / 2 - .06, .25 + h * .62), bevel=0, k='glow')
    if glow_side: light_strip(d * .8, loc=(0, 0, 0)) if False else None
    if door:
        box('Module door', (.9, .06, 2.0), M['panel'], (w / 2 - .7, d / 2 + .02, .25 + 1.0), bevel=.01)
    with kind('detail'):
        box('Vent', (.5, .5, .25), M['steel'], (-w / 3, -d / 4, .25 + h + .35), bevel=.02)
        cyl('Stack', .07, .7, M['steel'], loc=(w / 3, -d / 4, .25 + h + .2), sides=8)
        for x in np.linspace(-w / 2 - .6, w / 2 + .6, 6):   # front railing on the roof edge
            span('Rail post', (x, d / 2 + 1.1, 0), (x, d / 2 + 1.1, 1.05), .04, .04, M['steel'], bevel=0)
        span('Rail', (-w / 2 - .6, d / 2 + 1.1, 1.05), (w / 2 + .6, d / 2 + 1.1, 1.05), .05, .05, M['hazard'], bevel=0)
        span('Rail', (-w / 2 - .6, d / 2 + 1.1, .55), (w / 2 + .6, d / 2 + 1.1, .55), .035, .035, M['steel'], bevel=0)


def blade_sign(key, h=2.6, w=.55, t=.16):
    """Projecting vertical lit sign on a bracket (local wall y=0; sign stands out along +Y)."""
    for z in (h * .15, h * .85):
        span('Blade bracket', (0, 0, z), (0, .5, z), .06, .08, M['steel'], bevel=0)
    box('Blade case', (t, w + .08, h + .08), M['dark'], (0, .5 + w / 2, h / 2), bevel=.02)
    for s in (-1, 1):   # lettered faces on both sides of the case, wound to face +/-X
        x = s * (t / 2 + .005); y0, y1 = (.5, .5 + w) if s > 0 else (.5 + w, .5)
        quad('Blade face', (x, y0, 0), (x, y1, 0), (x, y1, h), (x, y0, h), M['blade_' + key], uv=((0, 0), (1, 0), (1, 1), (0, 1)), k='glow')
    light_marker('blade_' + key, Vector((0, .5 + w / 2, h * .5)), 'cyan')


def balcony(L, depth=1.2, mat=None):
    """Cantilevered steel walkway with grate deck, knee brackets and railing (local wall y=0, at local z=0)."""
    box('Balcony deck', (L, depth, .08), M['grate'], (0, depth / 2, 0), bevel=.005, uv=.8)
    box('Balcony edge', (L, .08, .2), mat or M['rust_paint'], (0, depth, -.06), bevel=.01)
    for x in np.linspace(-L / 2 + .2, L / 2 - .2, max(2, int(L / 1.6) + 1)):
        span('Knee brace', (x, 0, -1.0), (x, depth * .9, -.05), .07, .07, M['steel'], bevel=0)
        with kind('detail'):
            span('Rail post', (x, depth - .05, 0), (x, depth - .05, 1.05), .05, .05, M['steel'], bevel=0)
    span('Top rail', (-L / 2, depth - .05, 1.05), (L / 2, depth - .05, 1.05), .06, .06, mat or M['rust_paint'], bevel=0)
    with kind('detail'):
        span('Mid rail', (-L / 2, depth - .05, .55), (L / 2, depth - .05, .55), .04, .04, M['steel'], bevel=0)
        box('Kick plate', (L, .02, .15), M['steel'], (0, depth - .05, .1), bevel=0)


def scaffold(w, h, bays=None):
    """Tube-and-clamp scaffold against a wall with plank lifts and a torn tarp (local wall y=0)."""
    nb = bays or max(2, int(w / 2.0)); lifts = [z for z in np.arange(2.0, h, 2.0)]
    for i in range(nb + 1):
        x = -w / 2 + w * i / nb
        for y in (.35, 1.35):
            cyl_between('Standard', (x, y, 0), (x, y, h + 1.0), .024, M['steel'], sides=6)
    for z in lifts + [h + .9]:
        for y in (.35, 1.35):
            cyl_between('Ledger', (-w / 2, y, z), (w / 2, y, z), .022, M['steel'], sides=6)
        if z <= h:
            box('Plank lift', (w, .9, .05), M['rust_sheet'] if rng.random() > .5 else M['tread'], (0, .85, z + .03), bevel=0, uv=.6)
    with kind('detail'):
        for i in range(nb):
            x0 = -w / 2 + w * i / nb; x1 = -w / 2 + w * (i + 1) / nb
            cyl_between('Diagonal', (x0, 1.35, 0), (x1, 1.35, min(h, 4.0)), .02, M['steel'], sides=5)
    def f(u, v):
        return Vector((-w / 2 + u * w * .6, 1.42 + .08 * math.sin(u * 7 + v * 2), h + .9 - v * (h * .55) + .06 * math.sin(u * 4)))
    sheet('Scaffold tarp', f, (10, 8), M['tarp'], (3, 2), holes=.06)


def condenser_tower(h=5.5, r=.9):
    """Atmospheric moisture condenser: vaned drum on a braced stand, drip collar and feed pipe."""
    for i in range(4):
        a = math.pi / 4 + i * math.pi / 2
        span('Stand leg', (math.cos(a) * r * 1.05, math.sin(a) * r * 1.05, 0), (math.cos(a) * r * .7, math.sin(a) * r * .7, 1.6), .1, .1, M['steel'])
    cyl('Collector basin', r * 1.1, .35, M['plate_teal'], loc=(0, 0, 1.6), sides=24, r2=r * .95)
    cyl('Condenser core', r * .45, h - 1.6, M['dark'], loc=(0, 0, 1.95), sides=16)
    n = 14
    for i in range(n):   # radial vanes
        a = 2 * math.pi * i / n
        box('Vane', (r * .55, .025, h - 2.3), M['plate_bone'], (math.cos(a) * r * .72, math.sin(a) * r * .72, 1.95 + (h - 2.3) / 2), (0, 0, a), bevel=0)
    for z in (2.3, 1.95 + (h - 2.3) - .2):
        cyl('Vane ring', r * 1.0, .08, M['steel'], loc=(0, 0, z), sides=24, caps=False)
    cyl('Cap', r * 1.05, .3, M['plate_teal'], loc=(0, 0, h - .3), sides=24, r2=r * .3)
    cyl('Status ring', r * .47, .06, M['cyan'], loc=(0, 0, h - .45), sides=16, k='glow')
    tube('Condensate line', fillet([Vector((r * .9, 0, 1.7)), Vector((r * 1.4, 0, 1.7)), Vector((r * 1.4, 0, 0.05))], .2), .06, M['plate_teal'], sides=8)


def jib_crane(reach=3.0, h=2.4):
    """Salvaged hoist jib cantilevered off a roof edge (reach along +Y)."""
    ibeam('Jib mast', (0, 0, 0), (0, 0, h), .22, .16, mat=M['rust_paint'])
    ibeam('Jib boom', (0, -.4, h - .15), (0, reach, h - .15), .22, .14, mat=M['rust_paint'])
    cyl_between('Jib tie', (0, 0, h + .1), (0, reach * .85, h - .05), .025, M['steel'], sides=6)
    box('Hoist block', (.25, .3, .3), M['hazard'], (0, reach - .3, h - .45), bevel=.02)
    tube('Hoist chain', [Vector((0, reach - .3, h - .6)), Vector((0, reach - .28, h - 2.2))], .015, M['steel'], sides=5)
    box('Hoist hook', (.08, .16, .2), M['steel'], (0, reach - .28, h - 2.3), bevel=.01)


def lookout_nest(w=3.2, d=3.2):
    """Roof-top Warden lookout: HESCO parapet on three sides, turret, banner pole."""
    for (x, y, L, rot) in ((0, d / 2, w, 0), (-w / 2, 0, d - 1.0, math.pi / 2), (w / 2, 0, d - 1.0, math.pi / 2)):
        with record() as obs:
            hesco_run(L, h=1.0, d=.8)
        bpy.context.view_layer.update()
        for o in obs:
            if o.parent is None: o.matrix_world = Matrix.Translation((x, y, 0)) @ Matrix.Rotation(rot, 4, 'Z') @ o.matrix_world
    with record() as obs:
        scrap_turret()
    bpy.context.view_layer.update()
    for o in obs:
        if o.parent is None: o.matrix_world = Matrix.Translation((0, .6, 0)) @ o.matrix_world
    cyl('Banner mast', .04, 4.0, M['steel'], loc=(-w / 2 + .3, -d / 2 + .3, 0), sides=8)
    def f(u, v):
        return Vector((-w / 2 + .35 + u * 1.1, -d / 2 + .3 + .05 * math.sin(u * 6 + v * 2), 3.9 - v * 1.6 + .04 * math.sin(u * 4)))
    sheet('Lookout banner', f, (8, 10), M['banner'], (1, 1))
