"""Carve the two saved shop porches through the live Blender MCP addon.

Run only after the root agent exports the current renderers to
threshold-source.json. This creates an isolated Blender scene; it never edits
Unity assets, source records, colliders, or another Blender scene. Geometry is
metres in Unity world space. U(B(p)) is identity and triangle winding is retained.

Input: list (or {parts: list}) with name, path/sourcePath, positions, indices,
and optional family. Export only the intended porch/approach/door threshold
renderers. Rows marked referenceOnly are displayed but excluded from output.
Output: versioned threshold replacements, additions, manifest and source blend.
V2 supersedes V1's regularly spaced pits below a clean lip. The first script,
exports, Blender source and rejection review remain preserved.
"""
import bpy
import bmesh
import hashlib
import json
import math
import random
from pathlib import Path
from mathutils import Vector

ROOT = Path('/home/teknetik/code/ao2')
OUT = ROOT / 'art/reference_street_20260909'
SOURCE = OUT / 'threshold-source.json'
VERSION = str(globals().get('THRESHOLD_VERSION', 'v2'))
BLEND = OUT / ('reference-thresholds-' + VERSION + '.blend')
assert SOURCE.is_file(), 'Root must export the current saved threshold renderers first.'
assert not BLEND.exists(), 'Preserve previous authoring; choose a new THRESHOLD_VERSION.'
document = json.loads(SOURCE.read_text())
rows = document if isinstance(document, list) else document['parts']
assert rows and all(r.get('path', r.get('sourcePath')) for r in rows)


def B(p):
    return Vector((p[0], -p[2], p[1]))


def U(p):
    return [round(p[0], 6), round(p[2], 6), round(-p[1], 6)]


assert U(B((2, 3, 5))) == [2, 3, 5]
scene = bpy.data.scenes.new('Reference street thresholds ' + VERSION)
scene.unit_settings.system = 'METRIC'
bpy.context.window.scene = scene
rng = random.Random(9091938)


def material():
    m = bpy.data.materials.new('Reference threshold mineral stone ' + VERSION)
    m.use_nodes = True
    nt = m.node_tree
    bs = nt.nodes.get('Principled BSDF')
    bs.inputs['Roughness'].default_value = .91
    p = ROOT / 'art/facade_materials_20260909/textures/Stone'
    for filename, socket, linear in [('BaseColor.png', 'Base Color', False),
                                      ('Roughness.png', 'Roughness', True),
                                      ('Normal.png', 'Normal', True)]:
        if not (p / filename).exists():
            continue
        tex = nt.nodes.new('ShaderNodeTexImage')
        tex.image = bpy.data.images.load(str(p / filename), check_existing=True)
        if linear:
            tex.image.colorspace_settings.name = 'Non-Color'
        if socket == 'Normal':
            normal = nt.nodes.new('ShaderNodeNormalMap')
            nt.links.new(tex.outputs['Color'], normal.inputs['Color'])
            nt.links.new(normal.outputs['Normal'], bs.inputs['Normal'])
        else:
            nt.links.new(tex.outputs['Color'], bs.inputs[socket])
    return m


STONE = material()


def own(obj):
    for collection in list(obj.users_collection):
        collection.objects.unlink(obj)
    scene.collection.objects.link(obj)
    return obj


def bounds(row):
    return ([min(v[k] for v in row['positions']) for k in range(3)],
            [max(v[k] for v in row['positions']) for k in range(3)])


def input_object(row):
    ii = row['indices']
    me = bpy.data.meshes.new(row['name'] + ' retained source geometry')
    me.from_pydata([B(p) for p in row['positions']], [],
                   [ii[i:i + 3] for i in range(0, len(ii), 3)])
    me.update()
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=.000002)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(row['name'], me)
    scene.collection.objects.link(obj)
    obj['source_path'] = row.get('path', row.get('sourcePath'))
    obj['export_name'] = row['name']
    obj['material_key'] = 'Stone'
    obj['family'] = row.get('family', 'finery' if 'w_01' in obj['source_path']
                            or 'finery' in obj['source_path'].lower() else 'field_supply')
    me.materials.append(STONE)
    return obj


def boolean(obj, cutter, label):
    bpy.context.view_layer.objects.active = obj
    mod = obj.modifiers.new(label, 'BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.solver = 'EXACT'
    mod.object = cutter
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


def box(center, size):
    bpy.ops.mesh.primitive_cube_add(size=1, location=B(center))
    obj = own(bpy.context.object)
    obj.dimensions = (size[0], size[2], size[1])
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj


def groove(obj, lo, hi, axis, value, other_low, other_high, depth, width):
    """Thin, slightly wandering channel; all outer edges are subtractive."""
    # Several connected segments add old hand-cut joints without jagged sawteeth.
    other = 2 if axis == 0 else 0
    count = max(2, math.ceil((other_high - other_low) / .3))
    points = []
    for j in range(count + 1):
        t = j / count
        p = [0., hi[1] - depth / 2 + .015, 0.]
        p[axis] = value + .0025 * math.sin(t * math.pi * 3 + value * 2.3)
        p[other] = other_low + t * (other_high - other_low)
        points.append(p)
    vertices = []
    for p in points:
        for y, across in [(-depth / 2 - .02, -width / 2),
                          (-depth / 2 - .02, width / 2),
                          (depth / 2 + .03, width / 2),
                          (depth / 2 + .03, -width / 2)]:
            q = list(p)
            q[1] += y
            q[axis] += across
            vertices.append(B(q))
    faces = [(0, 3, 2, 1), tuple(range(count * 4, count * 4 + 4))]
    for j in range(count):
        for k in range(4):
            a = j * 4 + k
            b = j * 4 + (k + 1) % 4
            faces.append((a, b, b + 4, a + 4))
    me = bpy.data.meshes.new('Temporary wandering joint')
    me.from_pydata(vertices, [], faces)
    me.update()
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(me)
    bm.free()
    cut = bpy.data.objects.new('Temporary joint cutter', me)
    scene.collection.objects.link(cut)
    boolean(obj, cut, 'Shallow staggered stone joint')


def chip(obj, center, size, seed):
    """Detailed asymmetric mineral fracture, cut into existing edges only."""
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1, location=B(center))
    cut = own(bpy.context.object)
    for vertex in cut.data.vertices:
        x, y, z = vertex.co
        vertex.co *= (1 + .14 * math.sin(5 * x + 3 * z + seed)
                      + .065 * math.sin(11 * y - 3 * x + seed * .2)
                      + .025 * math.sin(23 * z + 9 * x))
    cut.scale = (size[0], size[2], size[1])
    boolean(obj, cut, 'Localized irregular mineral edge loss')


def arris_failure(obj, lo, hi, z, inward, drop, spread, seed):
    """Open an irregular loss across the top/front intersection, never a pit."""
    center = (lo[0] + .008, hi[1] + .018, z)
    chip(obj, center, (inward, drop + .021, spread), seed)
    # A smaller intersecting fracture makes one tapered, asymmetric end of the
    # broken lip. It stays inside a 12 cm edge band and off the walkable center.
    chip(obj, (lo[0] - .002, hi[1] + .023, z + spread * .78),
         (inward * .53, drop * .62 + .024, spread * .50), seed + 17)


def clean_boolean_mesh(obj):
    """Remove sub-millimetre Boolean slivers before deterministic triangulation."""
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=.000004)
    bmesh.ops.dissolve_degenerate(bm, edges=list(bm.edges), dist=.000002)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bmesh.ops.triangulate(bm, faces=list(bm.faces), quad_method='BEAUTY', ngon_method='BEAUTY')
    degenerate = [f for f in bm.faces if f.calc_area() < 1e-11]
    if degenerate:
        bmesh.ops.delete(bm, geom=degenerate, context='FACES_ONLY')
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(me)
    bm.free()
    me.update()


def shade_uv(obj):
    me = obj.data
    me.normals_split_custom_set([(0, 0, 0)] * len(me.loops))
    uv = me.uv_layers.active or me.uv_layers.new(name='UV0 four metre mineral tile')
    # Retain planar tops/risers. Small curved fracture surfaces shade smoothly.
    for face in me.polygons:
        n = U(face.normal)
        axis = max(range(3), key=lambda k: abs(n[k]))
        face.use_smooth = max(abs(v) for v in n) < .995 and face.area < .002
        for li in face.loop_indices:
            x, y, z = U(obj.matrix_world @ me.vertices[me.loops[li].vertex_index].co)
            a, b = ((z if n[0] < 0 else -z), y) if axis == 0 else (
                (x, -z if n[1] > 0 else z) if axis == 1 else
                ((x if n[2] > 0 else -x), y))
            uv.data[li].uv = (a / 4, b / 4)
    me.update()
    # Explicit per-corner normals keep every construction plane independent of
    # the many neighboring fracture slivers. Small bevel normals remain smooth.
    normals = [tuple(n.vector) for n in me.corner_normals]
    for face in me.polygons:
        n = face.normal.copy()
        axis = max(range(3), key=lambda k: abs(n[k]))
        if abs(n[axis]) > .9999:
            locked = [0., 0., 0.]
            locked[axis] = 1. if n[axis] > 0 else -1.
        elif not face.use_smooth:
            locked = tuple(n)
        else:
            continue
        for li in face.loop_indices:
            normals[li] = locked
    me.normals_split_custom_set(normals)
    me.update()


def normal_audit(part):
    large_faces = 0
    bad_faces = 0
    max_degrees = 0.
    for i in range(0, len(part['positions']), 3):
        a, b, c = [Vector(p) for p in part['positions'][i:i + 3]]
        cross = (b - a).cross(c - a)
        if cross.length / 2 < .01:
            continue
        n = cross.normalized()
        # The large floor, riser and broad fracture triangles must be flat.
        large_faces += 1
        minimum = min(n.dot(Vector(v)) for v in part['normals'][i:i + 3])
        degrees = math.degrees(math.acos(max(-1., min(1., minimum))))
        max_degrees = max(max_degrees, degrees)
        if minimum < .999:
            bad_faces += 1
    assert bad_faces == 0, 'Large construction triangle normals disagree with geometry.'
    return dict(largeTriangles=large_faces, largeTrianglesWithNormalMismatch=bad_faces,
                maximumLargeTriangleNormalAngleDegrees=max_degrees)


def export(obj, path):
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    me.calc_loop_triangles()
    uv = me.uv_layers.active
    positions, normals, coords, indices = [], [], [], []
    normal_matrix = obj.matrix_world.to_3x3().inverted().transposed()
    for tri in me.loop_triangles:
        for li in tri.loops:
            positions.append(U(obj.matrix_world @ me.vertices[me.loops[li].vertex_index].co))
            normals.append(U((normal_matrix @ me.corner_normals[li].vector).normalized()))
            coords.append(list(uv.data[li].uv))
            indices.append(len(indices))
    ev.to_mesh_clear()
    return dict(sourcePath=path, name=obj['export_name'], family=obj.get('family'),
                material='Stone', positions=positions, normals=normals, uv=coords, indices=indices)


replacements, additions, review = [], [], []
large_porches = []
for row in rows:
    obj = input_object(row)
    if row.get('referenceOnly'):
        obj['reference_only'] = True
        continue
    lo, hi = bounds(row)
    sx, sy, sz = [hi[k] - lo[k] for k in range(3)]
    name = row['name'].lower()
    assert any(word in name for word in ('porch', 'step', 'tread', 'threshold', 'plinth')), 'Unexpected source renderer.'
    assert hi[1] < 1.2 and sy < .85 and min(sx, sz) > .15, 'Unexpected threshold envelope.'
    count_before = len(row['indices']) // 3
    is_porch = sx > 3 and sz > 3
    joints = 0
    front_joints = []
    failures = []
    if is_porch:
        # Both shops face the avenue toward -X. The rear is under the building.
        exposed = min(sx, 2.28 if obj['family'] == 'finery' else 3.29)
        xcuts = [lo[0], lo[0] + .77, lo[0] + 1.66, lo[0] + exposed]
        xcuts = sorted(set(min(lo[0] + exposed, x) for x in xcuts))
        for x in xcuts[1:-1]:
            groove(obj, lo, hi, 0, x, lo[2] - .05, hi[2] + .05, .022, .018)
            joints += 1
        for ix, (xa, xb) in enumerate(zip(xcuts, xcuts[1:])):
            z = lo[2] + (.83 if ix % 2 == 0 else .42)
            while z < hi[2] - .2:
                groove(obj, lo, hi, 2, z, xa - .025, xb + .025,
                       min(sy + .10, .72) if ix == 0 else .024, .018)
                joints += 1
                if ix == 0:
                    front_joints.append(z)
                z += rng.uniform(.79, 1.16)
        # Uneven joint-related losses leave long intact stretches between them.
        # Centering cutters above the arris guarantees an open broken top edge.
        chosen = [0, 3, len(front_joints) - 2]
        for j, index in enumerate(sorted(set(i for i in chosen if 0 <= i < len(front_joints)))):
            z = front_joints[index] + rng.uniform(-.034, .047)
            inward, drop, spread = rng.uniform(.051, .079), rng.uniform(.037, .069), rng.uniform(.102, .167)
            arris_failure(obj, lo, hi, z, inward, drop, spread, j + 31)
            failures.append(dict(z=z, inward=inward, drop=drop, spread=spread, atJoint=True))
        # One shorter non-joint scar varies the silhouette without a repeated beat.
        z = lo[2] + sz * (.36 if obj['family'] == 'finery' else .69)
        arris_failure(obj, lo, hi, z, .042, .033, .081, 57)
        failures.append(dict(z=z, inward=.042, drop=.033, spread=.081, atJoint=False))
        for j, z in enumerate([lo[2] + .026, hi[2] - .031]):
            arris_failure(obj, lo, hi, z, .071 + .008 * j, .065 - .014 * j, .105, j + 81)
            failures.append(dict(z=z, inward=.071 + .008 * j, drop=.065 - .014 * j, spread=.105, corner=True))
        large_porches.append((obj, lo, hi))
    else:
        if sz > 1.6 and sx < 2:
            z = lo[2] + .77
            while z < hi[2] - .2:
                groove(obj, lo, hi, 2, z, lo[0] - .04, hi[0] + .04,
                       sy + .10, .014)
                joints += 1
                front_joints.append(z)
                z += rng.uniform(.80, 1.11)
        # Existing courtyard approach stones already have their detailed source
        # bevels. Restrict this revision to several local edge losses.
        locations = [front_joints[0], front_joints[-1]] if front_joints else [lo[2] + sz * .23]
        for j, z in enumerate(locations):
            arris_failure(obj, lo, hi, z + .025, .052 + j * .015, min(.045, sy * .2), .092 + j * .019, j + 141)
            failures.append(dict(z=z + .025, inward=.052 + j * .015, drop=min(.045, sy * .2), spread=.092 + j * .019, atJoint=True))
    bpy.context.view_layer.objects.active = obj
    bevel = obj.modifiers.new('Small mineral fracture arrises', 'BEVEL')
    bevel.width = .0032
    bevel.segments = 3
    bevel.limit_method = 'ANGLE'
    bevel.angle_limit = .70
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    clean_boolean_mesh(obj)
    shade_uv(obj)
    part = export(obj, obj['source_path'])
    out_lo, out_hi = bounds(part)
    assert all(out_lo[k] >= lo[k] - .0001 and out_hi[k] <= hi[k] + .0001 for k in range(3)), 'Replacement escaped the original envelope.'
    assert abs(out_hi[1] - hi[1]) < .0001, 'Original step top must remain.'
    replacements.append(part)
    review.append(dict(sourcePath=obj['source_path'], sourceBounds=dict(min=lo, max=hi),
                       outputBounds=dict(min=out_lo, max=out_hi), joints=joints,
                       arrisFailures=failures, normals=normal_audit(part),
                       sourceTriangles=count_before, triangles=len(part['indices']) // 3))
    print('Threshold authored:', obj['source_path'], len(part['indices']) // 3, flush=True)

# Sparse tiny chips at the two ends of each porch; no new collider or obstacle.
# These sit outside the retained footprint, clear of the avenue and door centers.
for obj, lo, hi in large_porches:
    for end, z in enumerate([lo[2] + .18, hi[2] - .18]):
        for j in range(9):
            radius = rng.uniform(.018, .063)
            center = (lo[0] - rng.uniform(.055, .23), .004,
                      z + rng.uniform(-.15, .15))
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1, location=B(center))
            fragment = own(bpy.context.object)
            fragment.name = obj['family'] + ' foot grit ' + str(end) + '-' + str(j)
            fragment['export_name'] = fragment.name
            fragment['family'] = obj['family']
            for v in fragment.data.vertices:
                x, y, zz = v.co
                v.co *= 1 + .17 * math.sin(x * 7 + y * 5 + j) + .08 * math.sin(zz * 13)
                v.co.x *= radius
                v.co.y *= radius * rng.uniform(.68, 1.13)
                v.co.z *= min(.025, radius * .48)
            fragment.rotation_euler.z = rng.random() * math.tau
            fragment.data.materials.append(STONE)
            shade_uv(fragment)
            additions.append(export(fragment, None))

manifest = dict(source=str(SOURCE.relative_to(ROOT)), sourceSha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                version=VERSION, blender=bpy.app.version_string, sourceBlend=BLEND.name,
                replacements=len(replacements), additions=len(additions), tileMetres=4,
                replacementTriangles=sum(len(p['indices']) // 3 for p in replacements),
                addedTriangles=sum(len(p['indices']) // 3 for p in additions),
                unchangedColliderRequirement=True, reviews=review,
                notes=['Existing source geometry carved subtractively; world transforms and envelope retained.',
                       'Original top elevation retained; joint grooves are shallow except front riser joints.',
                       'V2 replaces V1 repeated pits with sparse joint-related top/front arris failures.',
                       'Boolean slivers cleaned and deterministically triangulated; large-face corner normals explicitly locked and audited.',
                       'Large planes remain flat shaded; only small mineral fracture bevels shade smoothly.',
                       'Tiny grit occupies porch ends, clear of entrance centers; no colliders requested.',
                       'Native Unity review and real-input porch traversal required before acceptance.'])
for stem, data in [('threshold-replacements-', replacements), ('threshold-additions-', additions),
                   ('threshold-manifest-', manifest)]:
    path = OUT / (stem + VERSION + '.json')
    assert not path.exists(), 'Preserve previous export.'
    path.write_text(json.dumps(data, indent=2 if 'manifest' in stem else None,
                               separators=None if 'manifest' in stem else (',', ':')))
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
print(json.dumps({k: v for k, v in manifest.items() if k != 'reviews'}, indent=2))
