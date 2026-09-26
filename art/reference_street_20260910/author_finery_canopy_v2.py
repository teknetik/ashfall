"""Finery canopy revision 2. Execute once through the live Blender MCP.

This authors an independent collection and saves a NEW source blend. It does not
open, clear, or save over another author's file, and it does not install in Unity.
Part JSON uses ReferenceStreetPass's world-Unity-metres contract. Retain the
existing iron side spars, diagonal braces and crossbar in the saved Unity scene.

The membrane is a designed static equilibrium approximation, not a cloth solve:
gravity sag is bounded by the actual perimeter supports; irregular tension fans
converge on attachment stations; flat sewn seams add local stiffness. A physically
small fabric normal supplies weave, rather than adding large woven geometry.
"""
import bpy
import json
import math
import random
import hashlib
from pathlib import Path
from mathutils import Vector, noise

ROOT = Path('/home/teknetik/code/ao2')
OUT = ROOT / 'art/reference_street_20260910/canopy-v2'
OUT.mkdir(parents=True, exist_ok=True)
if (OUT / 'finery-canopy-v2.blend').exists():
    raise RuntimeError('Preserve this source revision; use a new dated version for another audition.')
COLLECTION = 'Finery tensioned canopy 20260910 v2'
if bpy.data.collections.get(COLLECTION):
    raise RuntimeError('This authoring collection already exists; do not duplicate a partial run.')
coll = bpy.data.collections.new(COLLECTION)
source_scene = bpy.data.scenes.new(COLLECTION + ' source scene')
source_scene.collection.children.link(coll)
bpy.context.window.scene = source_scene
rng = random.Random(910413)
MAIN_PATH = 'Courtyard reference pass/Canopy/Ochre red courtyard awning'
SEAMS = (.218, .492, .757)
STATIONS = (.023, .131, .239, .351, .468, .577, .691, .799, .908, .979)
PARTS = []
TUBE_CACHE = {}


def B(v):
    return Vector((v[0], -v[2], v[1]))


def U(v):
    return [round(float(v[0]), 6), round(float(v[2]), 6), round(float(-v[1]), 6)]


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def gauss(x, w):
    return math.exp(-(x / w) ** 2)


def spar_y(u):
    # The existing side spar has a real kink at (14.5, 3.84), not a straight line.
    # The fabric sits just above its 35 mm radius on the two side boundaries.
    mid = (16.82 - 14.5) / 4.58
    if u < mid:
        return 4.117 + (3.877 - 4.117) * u / mid
    return 3.877 + (3.455 - 3.877) * (u - mid) / (1 - mid)


def sheet(u, v):
    """Unity position on a 4.58 m projection × 6.50 m supported membrane."""
    u, v = clamp(u), clamp(v)
    su, sv = max(0, math.sin(math.pi * u)), max(0, math.sin(math.pi * v))
    weight = su ** .83 * sv ** .72
    y = spar_y(u) - .405 * weight * (.88 + .17 * v)
    # The seams are slightly stiffer than the surrounding cloth, not metal rods.
    for k, s in enumerate(SEAMS):
        trace = s + .005 * math.sin(math.pi * u) * (-1 if k == 1 else 1)
        y += su * (.025 * gauss(v - trace, .014) - .009 * gauss(v - trace, .046))
    # Broad diagonal tension fans, with different directions and widths. Each
    # starts at a tied front edge; no periodic corrugation is used for the drape.
    for k, s in enumerate(STATIONS):
        d = 1 - u
        direction = (.27, -.16, .19, -.28, .12, -.22, .25, -.17, .20, -.29)[k]
        trace = s + direction * d + .025 * d * d
        width = .0045 + .043 * d
        amplitude = (.047, .082, .061, .091, .049, .080, .057, .071, .051, .079)[k]
        extent = math.exp(-(d / .33) ** 2) * math.sin(math.pi * clamp(d / .40))
        y += amplitude * extent * (gauss(v - trace, width) - .37 * gauss(v - trace - width * 1.9, width * 1.35)) * sv ** .28
    # A handful of soft inherited handling creases; irregular support-constrained
    # paths and millimetre noise avoid a sine-wave board or giant rope weave.
    for c, slope, amp, width in [(.27, .12, .013, .026), (.63, -.09, -.018, .040), (.83, .06, .009, .030)]:
        trace = c + slope * (v - .5) + .023 * (v - .5) ** 2
        y += amp * gauss(u - trace, width) * weight
    # Soft diagonal handling folds persist through the central cloth, while
    # pinned perimeter points and retained supports remain exactly fixed.
    for c, slope, amp, width in [(.23, .16, .047, .019), (.44, -.21, -.061, .028), (.68, .17, .055, .023), (.79, -.11, -.037, .021)]:
        trace = c + slope * (v - .5) + .022 * math.sin(v * 6.8 + c * 7)
        y += amp * (gauss(u - trace, width) - .38 * gauss(u - trace - width * 1.8, width * 1.4)) * weight
    y += .0035 * noise.noise(Vector((u * 8.7 + 71.6, v * 11.2 - 18.7, 3.9))) * weight
    x = 16.82 - 4.58 * u + .013 * su * sv * math.sin(v * 8.7 + 1.1)
    z = -21.42 + 6.5 * v + .018 * su * sv * math.sin(u * 5.1 + .7)
    return Vector((x, y, z))


def sheet_normal(u, v):
    e = .0001
    a = sheet(clamp(u + e), v) - sheet(clamp(u - e), v)
    b = sheet(u, clamp(v + e)) - sheet(u, clamp(v - e))
    return a.cross(b).normalized()


MAT_COLOURS = {
    'CanopyRed': (.35, .095, .051),
    'CanopySeam': (.29, .073, .041),
    'CanopyRepair': (.255, .073, .043),
    'CanopyThread': (.41, .29, .18),
    'CanopyRope': (.28, .21, .135),
    'CanopyEyelet': (.155, .125, .081),
}
MATS = {}
for key, colour in MAT_COLOURS.items():
    mat = bpy.data.materials.new('Finery v2 ' + key)
    mat.diffuse_color = (*colour, 1)
    mat.use_nodes = True
    mat.use_fake_user = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*colour, 1)
    bsdf.inputs['Roughness'].default_value = .86 if key != 'CanopyEyelet' else .68
    bsdf.inputs['Metallic'].default_value = .68 if key == 'CanopyEyelet' else 0
    if 'Sheen Weight' in bsdf.inputs:
        bsdf.inputs['Sheen Weight'].default_value = .18 if 'Canopy' in key and key != 'CanopyEyelet' else 0
    MATS[key] = mat


def mesh(name, points, faces, material, uvs=None, source_path=None, thickness=0):
    me = bpy.data.meshes.new(name)
    me.from_pydata([B(p) for p in points], [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    ob['family'] = 'FineryCanopy'
    ob['material'] = material
    ob['sourcePath'] = source_path or ''
    me.materials.append(MATS[material])
    uv = me.uv_layers.new(name='Material physical metres divided by 0.4 m')
    for poly in me.polygons:
        poly.use_smooth = True
        for li in poly.loop_indices:
            vi = me.loops[li].vertex_index
            p = points[vi]
            uv.data[li].uv = uvs[vi] if uvs else (float(p[0]) / .4, float(p[2]) / .4)
    if thickness:
        bpy.context.view_layer.objects.active = ob
        ob.select_set(True)
        sol = ob.modifiers.new('Three-ply canvas edge thickness', 'SOLIDIFY')
        sol.thickness = thickness
        sol.offset = -.5
        sol.use_even_offset = True
        bpy.ops.object.modifier_apply(modifier=sol.name)
        ob.select_set(False)
    PARTS.append(ob)
    return ob


def tube(name, points, radius, material, sides=6, defer=True):
    vs, fs, uv = [], [], []
    length = 0
    for j, p in enumerate(points):
        p = Vector(p)
        if j:
            length += (p - Vector(points[j - 1])).length
        tangent = (Vector(points[min(j + 1, len(points) - 1)]) - Vector(points[max(0, j - 1)])).normalized()
        a = tangent.cross(Vector((0, 1, 0)))
        if a.length < .01:
            a = tangent.cross(Vector((1, 0, 0)))
        a.normalize()
        b = tangent.cross(a).normalized()
        for k in range(sides):
            angle = math.tau * k / sides
            vs.append(p + radius * (math.cos(angle) * a + math.sin(angle) * b))
            uv.append((length / .4, math.tau * radius * k / sides / .4))
        if j:
            for k in range(sides):
                n = j * sides + k
                nn = j * sides + (k + 1) % sides
                fs.append((n - sides, nn - sides, nn, n))
    fs.extend([tuple(reversed(range(sides))), tuple((len(points) - 1) * sides + k for k in range(sides))])
    if defer:
        buffer = TUBE_CACHE.setdefault(material, {'vs': [], 'fs': [], 'uv': []})
        offset = len(buffer['vs'])
        buffer['vs'].extend(vs)
        buffer['uv'].extend(uv)
        buffer['fs'].extend(tuple(offset + i for i in f) for f in fs)
        return None
    return mesh(name, vs, fs, material, uv)


# Fine near-view membrane: ~29 mm edges capture 4–12 cm tension folds. This is
# newly authored shape detail, not subdivision used to inflate a source count.
nx, nz = 158, 224
vs, fs, uv = [], [], []
for j in range(nz + 1):
    v = j / nz
    for i in range(nx + 1):
        u = i / nx
        vs.append(sheet(u, v))
        uv.append((u * 4.58 / .4, v * 6.5 / .4))
for j in range(nz):
    for i in range(nx):
        a = j * (nx + 1) + i
        fs.append((a, a + 1, a + nx + 2, a + nx + 1))
body = mesh('Finery tensioned red membrane v2', vs, fs, 'CanopyRed', uv, MAIN_PATH, .0018)


# Narrow flat-felled seams. No cylindrical bright rails are placed on the sheet.
for k, seam in enumerate(SEAMS):
    vs, fs, uv = [], [], []
    for i in range(193):
        u = i / 192
        s = seam + .005 * math.sin(math.pi * u) * (-1 if k == 1 else 1)
        for j in range(5):
            offset = (j / 4 - .5) * .044 / 6.5
            p = sheet(u, s + offset)
            p += sheet_normal(u, s + offset) * (.0018 + .0018 * math.sin(math.pi * j / 4))
            vs.append(p)
            uv.append((u * 4.58 / .4, (s + offset) * 6.5 / .4))
        if i:
            for j in range(4):
                a = (i - 1) * 5 + j
                fs.append((a, a + 5, a + 6, a + 1))
    mesh('Finery sewn felled seam ' + str(k), vs, fs, 'CanopySeam', uv, thickness=.0012)
    # A sparse but correctly scaled lockstitch chain. These are millimetre thread
    # details; at distance they become a narrow seam, not contrasting ropes.
    for side in (-1, 1):
        for n in range(330):
            u = (n + .45) / 331
            s = seam + .005 * math.sin(math.pi * u) * (-1 if k == 1 else 1) + side * .014 / 6.5
            points = []
            for t in (0, .5, 1):
                q = u + (t - .5) * .0065 / 4.58
                p = sheet(q, s) + sheet_normal(q, s) * (.0031 + .0007 * math.sin(math.pi * t))
                points.append(p)
            tube('Finery lockstitch', points, .00055, 'CanopyThread', 4)


def hem_depth(v):
    # Uneven relaxed edge, varying by a few centimetres over metres. The minimum
    # standing clearance stays above 3.1 m even where the hem is deepest.
    return .207 + .036 * math.sin(v * 7.3 + .4) + .029 * math.sin(v * 17.1 + 2.0) + .032 * gauss(v - .66, .12)


def hem(v, w):
    depth = hem_depth(v)
    fold = 0
    for k, s in enumerate(STATIONS):
        fold += (.009 + .006 * (k % 3)) * gauss(v - s - .003 * w, .010 + .006 * w)
    # Loose bottom curls away from the rod without moving the pinned top.
    curl = (.052 * math.sin(v * 10.3 + .7) + .029 * math.sin(v * 25.7 + 1.3)) * w ** 2
    crease = 0
    for c, amp, width in [(.084, .027, .018), (.284, -.043, .024), (.416, .052, .021), (.644, -.036, .028), (.883, .041, .019)]:
        crease += amp * gauss(v - c - .013 * w, width) * w
    x = 12.184 + .022 * w * math.sin(v * 12.8 + .5) + fold * (.4 + .6 * w) + curl + crease
    y = 3.453 - depth * w
    z = -21.42 + 6.5 * v + .006 * w * math.sin(v * 22.1 + .9)
    return Vector((x, y, z))


# The membrane wraps over the retained crossbar in a rolled pocket, then hangs as
# a short loose valance. Its top follows the support, its bottom is free.
vs, fs, uv = [], [], []
nv, na = 320, 20
for j in range(nv + 1):
    v = j / nv
    for i in range(na + 1):
        a = math.pi * (i / na) * .93
        vs.append((12.231 + .047 * math.cos(a), 3.411 + .047 * math.sin(a), -21.42 + 6.5 * v))
        uv.append((a * .047 / .4, v * 6.5 / .4))
for j in range(nv):
    for i in range(na):
        a = j * (na + 1) + i
        fs.append((a, a + 1, a + na + 2, a + na + 1))
mesh('Finery rolled front rod pocket', vs, fs, 'CanopySeam', uv, thickness=.0018)

vs, fs, uv = [], [], []
nv, nw = 650, 24
for j in range(nv + 1):
    v = j / nv
    for i in range(nw + 1):
        w = i / nw
        vs.append(hem(v, w))
        uv.append((w * hem_depth(v) / .4, v * 6.5 / .4))
for j in range(nv):
    for i in range(nw):
        v, w = (j + .5) / nv, (i + .5) / nw
        p = hem(v, w)
        # Real openings under the eyelets; the bronze ring conceals the tiny
        # grid boundary. Individual lashing passes through these holes.
        if any((6.5 * (v - s)) ** 2 + (p.y - 3.393) ** 2 < .012 ** 2 for s in STATIONS):
            continue
        # Two small edge splits in the free hem. They remain confined to a few
        # centimetres, rather than making a regular decorative sawtooth border.
        if (abs(v - .325) < .0035 and w > .86) or (abs(v - .859) < .0024 and w > .72):
            continue
        a = j * (nw + 1) + i
        fs.append((a, a + nw + 1, a + nw + 2, a + 1))
mesh('Finery uneven hanging valance', vs, fs, 'CanopyRed', uv, thickness=.0018)
edge = [hem(j / 650, 1) for j in range(651)]
tube('Finery stitched free hem roll', edge, .0028, 'CanopySeam', 6)


# Actual hollow eyelets, with cord passing through and around the retained bar.
for k, s in enumerate(STATIONS):
    w = (3.453 - 3.393) / hem_depth(s)
    c = hem(s, w)
    for layer in (-.002, .002):
        points = [c + Vector((layer, .019 * math.sin(math.tau * t / 32), .019 * math.cos(math.tau * t / 32))) for t in range(33)]
        tube('Finery bronze eyelet ' + str(k), points, .0033, 'CanopyEyelet', 8)
    # A loop catches the metal crossbar and returns through the eyelet. Smooth
    # interpolated paths plus two short tail ends read as tied cord at proximity.
    knots = [
        c + Vector((-.007, 0, -.005)),
        c + Vector((-.021, .024, -.006)),
        Vector((12.187, 3.462, c.z - .005)),
        Vector((12.235, 3.482, c.z - .002)),
        Vector((12.286, 3.435, c.z + .004)),
        Vector((12.255, 3.365, c.z + .007)),
        c + Vector((.008, -.006, .005)),
        c + Vector((-.010, .005, .009)),
        c + Vector((-.022, -.010, -.002)),
    ]
    # Catmull–Rom authoring keeps the hardware curve editable in metres.
    path = []
    for i in range(len(knots) - 1):
        p0, p1 = knots[max(0, i - 1)], knots[i]
        p2, p3 = knots[i + 1], knots[min(len(knots) - 1, i + 2)]
        for n in range(7):
            t = n / 7
            path.append(.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    path.append(knots[-1])
    tube('Finery bar lashing ' + str(k), path, .0036, 'CanopyRope', 8)
    for side in (-1, 1):
        p = knots[-1] + Vector((-.002, -.002, side * .006))
        points = [p, p + Vector((-.004, -.025, side * .006)), p + Vector((.004, -.051 - (k % 3) * .006, side * .011))]
        tube('Finery lashing tail', points, .0025, 'CanopyRope', 6)


# Faded repair cloth lies on the deformed parent sheet. Its boundary is sewn and
# slightly rolled; it is not a floating flat rectangle or a random damage patch.
for k, (uc, vc, width, height, angle) in enumerate([(.68, .362, .34, .44, -.17), (.34, .814, .27, .33, .13)]):
    vs, fs, uv = [], [], []
    n = 18
    ca, sa = math.cos(angle), math.sin(angle)
    for j in range(n + 1):
        b = (j / n - .5) * height
        for i in range(n + 1):
            a = (i / n - .5) * width
            du, dv = a * ca - b * sa, a * sa + b * ca
            u, v = uc + du / 4.58, vc + dv / 6.5
            edge_lift = .0013 * (abs(i / n - .5) * 2) ** 9 + .0010 * (abs(j / n - .5) * 2) ** 9
            vs.append(sheet(u, v) + sheet_normal(u, v) * (.0021 + edge_lift))
            uv.append(((u * 4.58 + .173) / .4, (v * 6.5 + .127) / .4))
    for j in range(n):
        for i in range(n):
            a = j * (n + 1) + i
            fs.append((a, a + 1, a + n + 2, a + n + 1))
    mesh('Finery hand-sewn repair ' + str(k), vs, fs, 'CanopyRepair', uv, thickness=.0013)


# Replace the original side ropes, which previously floated as straight bright
# edging. The retained iron spars themselves remain completely unchanged.
for side in (0, 1):
    points = [sheet(i / 160, side) + sheet_normal(i / 160, side) * .004 for i in range(161)]
    ob = tube('Finery side sewn piping ' + str(side), points, .0045, 'CanopySeam', 8, defer=False)
    ob['sourcePath'] = 'Courtyard reference pass/Awning hardware/Awning edge rope ' + str(side)


for material, buffer in TUBE_CACHE.items():
    mesh('Finery canopy ' + material + ' continuous details', buffer['vs'], buffer['fs'], material, buffer['uv'])


# Join additions by material to keep the editable source modest in object count.
# The membrane and original-source replacements remain individually recoverable.
for material in MATS:
    group = [o for o in PARTS if o['material'] == material and not o['sourcePath']]
    if len(group) < 2:
        continue
    bpy.ops.object.select_all(action='DESELECT')
    for o in group:
        o.select_set(True)
    bpy.context.view_layer.objects.active = group[0]
    bpy.ops.object.join()
    ob = group[0]
    ob.name = 'Finery canopy ' + material + ' details v2'
    # All joined slots refer to the same material. Collapse duplicate slots so
    # the one-material interchange remains explicit and deterministic.
    ob.data.materials.clear()
    ob.data.materials.append(MATS[material])
    for poly in ob.data.polygons:
        poly.material_index = 0
    PARTS = [p for p in PARTS if p not in group] + [ob]


def export_part(ob):
    me = ob.data
    me.calc_loop_triangles()
    uv = me.uv_layers.active
    nm = ob.matrix_world.to_3x3().inverted().transposed()
    positions, normals, coords, indices, unique = [], [], [], [], {}
    for tri in me.loop_triangles:
        for li in tri.loops:
            loop = me.loops[li]
            p = U(ob.matrix_world @ me.vertices[loop.vertex_index].co)
            n = U((nm @ me.corner_normals[li].vector).normalized())
            tx = [round(float(q), 6) for q in uv.data[li].uv]
            key = tuple(p + n + tx)
            if key not in unique:
                unique[key] = len(positions)
                positions.append(p)
                normals.append(n)
                coords.append(tx)
            indices.append(unique[key])
    return dict(name=ob.name, sourcePath=ob['sourcePath'] or None, family='FineryCanopy',
                material=ob['material'], positions=positions, normals=normals,
                uv=coords, indices=indices, castsShadow=True)


parts = [export_part(o) for o in sorted(PARTS, key=lambda ob: ob.name)]
all_positions = [v for part in parts for v in part['positions']]
min_y = min(p[1] for p in all_positions)
assert min_y > 3.10, f'Canopy detail violates the preserved clearance: {min_y}'
for part in parts:
    assert len(part['positions']) == len(part['normals']) == len(part['uv'])
    assert len(part['indices']) % 3 == 0
    assert all(math.isfinite(v) for p in part['positions'] for v in p)
    assert all(0 <= i < len(part['positions']) for i in part['indices'])
(OUT / 'canopy-parts-v2.json').write_text(json.dumps(parts, separators=(',', ':')))

base = 'Assets/AthenHill/Art/Phase1/BasicGeneral/Revision03/Textures/'
material_contract = {
    'textureScale': [0.142857142857, 0.142857142857],
    'detailScale': [7, 7],
    'detailAlbedoScale': 0,
    'detailNormalNote': 'Installed URP Lit supports independent detail UV scale; primary color repeats every 2.8 m, woven normal every 0.4 m.',
    'uvConvention': 'UV0 is fabric-distance metres divided by 0.4; base map ST=1/7 gives 2.8 m color tile; DetailAlbedoMap ST=7 restores 0.4 m normal scale after base transform.',
    'textureReuse': 'Original full-resolution imported maps retained unchanged. Independent detail normal avoids repeating the broad color pattern every 0.4 m.',
    'materials': {
        'CanopyRed': {'shader': 'Universal Render Pipeline/Lit', 'baseMap': base + 'Canvas_BaseColor.png', 'baseColor': [.94, .90, .84, 1], 'normalMap': base + 'fabric_pattern_07_nor_gl_4k.jpg', 'normalScale': .23, 'metallic': 0, 'smoothness': .13, 'cull': 2},
        'CanopySeam': {'shader': 'Universal Render Pipeline/Lit', 'baseMap': base + 'Canvas_BaseColor.png', 'baseColor': [.78, .78, .73, 1], 'normalMap': base + 'fabric_pattern_07_nor_gl_4k.jpg', 'normalScale': .21, 'metallic': 0, 'smoothness': .12, 'cull': 2},
        'CanopyRepair': {'shader': 'Universal Render Pipeline/Lit', 'baseMap': base + 'Canvas_BaseColor.png', 'baseColor': [.68, .72, .69, 1], 'normalMap': base + 'fabric_pattern_07_nor_gl_4k.jpg', 'normalScale': .19, 'metallic': 0, 'smoothness': .11, 'cull': 2},
        'CanopyThread': {'shader': 'Universal Render Pipeline/Lit', 'baseColor': [.33, .21, .125, 1], 'metallic': 0, 'smoothness': .10, 'cull': 2},
        'CanopyRope': {'shader': 'Universal Render Pipeline/Lit', 'baseColor': [.24, .175, .105, 1], 'metallic': 0, 'smoothness': .08, 'cull': 2},
        'CanopyEyelet': {'shader': 'Universal Render Pipeline/Lit', 'baseColor': [.155, .125, .081, 1], 'metallic': .68, 'smoothness': .32, 'cull': 2},
    },
    'disableObsoleteSourcePaths': ['Courtyard reference pass/Canopy/Stitched panel seam 0.29', 'Courtyard reference pass/Canopy/Stitched panel seam 0.66'] + ['Courtyard reference pass/Canopy/Frayed canvas fibre ' + str(i) for i in range(22)],
    'preserveSourcePaths': ['Courtyard reference pass/Awning hardware/Canopy side spar ' + str(i) for i in range(2)] + ['Courtyard reference pass/Awning hardware/Canopy diagonal brace ' + str(i) for i in range(2)] + ['Courtyard reference pass/Awning hardware/Outer canopy crossbar'],
    'runtimeMotion': 'This source revision is static drape. If wind is introduced, pin all support boundaries and hardware, move only the free hem by millimetres, and keep reduced-motion behavior. Do not apply the original unpinned whole-mesh wind shader blindly.',
}
(OUT / 'canopy-material-contract-v2.json').write_text(json.dumps(material_contract, indent=2))
bpy.ops.object.select_all(action='DESELECT')
for ob in coll.objects:
    ob.select_set(True)
bpy.context.view_layer.objects.active = body
# A library write containing this independent scene includes its dependencies
# only, and does not change or overwrite the artist's currently opened file.
bpy.data.libraries.write(str(OUT / 'finery-canopy-v2.blend'), {source_scene}, fake_user=True)
manifest = {
    'revision': '20260910 canopy v2',
    'author': 'Original live Blender MCP authoring',
    'reference': 'refs/reference-street/20260909/user-target.png',
    'supersedesVisuals': MAIN_PATH,
    'sourcePreserved': 'canopy-v1 source and all installed v1 assets remain intact; revised cloth only, retained rigid supports',
    'scaleMetres': {'projection': 4.58, 'span': 6.5, 'minimumY': min_y},
    'geometry': {'parts': len(parts), 'triangles': sum(len(p['indices']) // 3 for p in parts), 'partsSummary': [{'name': p['name'], 'sourcePath': p['sourcePath'], 'material': p['material'], 'triangles': len(p['indices']) // 3} for p in parts]},
    'features': ['Actual asymmetric perimeter-constrained membrane sag', 'Local tension fans ending at ties', 'Narrow flat-felled seams with correctly scaled lockstitches', 'Loose short valance with real eyelet holes', 'Hollow eyelets and tied crossbar cord', 'Two conforming sewn repair cloths', '1.8 mm solid canvas near-source detail', 'Physical 0.4 m calibrated weave normal with no source image edits'],
    'checks': {'finiteBuffers': True, 'indicesInRange': True, 'minimumClearanceAbove3p1': True, 'runtimeOrCollisionMutation': False},
    'notYetVerified': ['Native sun/shade appearance', 'Crossbar pocket depth and underside seam inspection', 'Temporal stability and GPU cost', 'Independent critic acceptance'],
    'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file()},
}
(OUT / 'canopy-authoring-manifest-v2.json').write_text(json.dumps(manifest, indent=2))
print(json.dumps({'canopySourceReady': str(OUT), 'parts': len(parts), 'triangles': manifest['geometry']['triangles'], 'minY': min_y}))
