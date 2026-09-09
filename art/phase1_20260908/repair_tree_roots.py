"""Join and reshape the existing root flare through live Blender MCP.

Retains untouched source objects and the existing upper crown. The output is a
separate detailed near mesh, with metre-scaled bark coordinates and sealed joins.
"""
import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Vector

ROOT = Path('/home/teknetik/code/ao2')
OUT = ROOT / 'art/phase1_20260908'
assert bpy.data.filepath == str(OUT / 'tree-audition.blend')
assert not bpy.data.objects.get('Ward connected root flare'), 'Review existing work before rerunning.'
originals = [o for o in bpy.data.objects if o.name == 'TREE_gnarled_trunk' or o.name.startswith('TREE_root_')]
assert len(originals) == 12
source = bpy.data.collections.new('Original trunk and roots — retained')
bpy.context.scene.collection.children.link(source)
copies = []
for o in originals:
    copy = o.copy()
    copy.data = o.data.copy()
    bpy.context.scene.collection.objects.link(copy)
    copies.append(copy)
    for col in list(o.users_collection):
        col.objects.unlink(o)
    source.objects.link(o)
source.hide_render = True
source.hide_viewport = True

# Buttress volumes bridge the old open-looking root/trunk intersections. Their
# long axes point outward, keeping the existing root tips and route footprint.
for i in range(11):
    angle = i * math.tau / 11 + .18
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16,
        location=(1.32 * math.cos(angle), -1.32 * math.sin(angle), 2.04))
    o = bpy.context.object
    o.name = 'Root junction volume %02d' % i
    o.scale = (1.02, .43, .76)
    o.rotation_euler.z = -angle
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    copies.append(o)
bpy.ops.object.select_all(action='DESELECT')
for o in copies:
    o.select_set(True)
bpy.context.view_layer.objects.active = copies[0]
bpy.ops.object.join()
o = bpy.context.object
o.name = 'Ward connected root flare'
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
remesh = o.modifiers.new('Connected trunk and buttress volume', 'REMESH')
remesh.mode = 'VOXEL'
remesh.voxel_size = .038
remesh.use_smooth_shade = True
remesh.use_remove_disconnected = False
bpy.ops.object.modifier_apply(modifier=remesh.name)
smooth = o.modifiers.new('Soften joined root cambium', 'SMOOTH')
smooth.factor = .45
smooth.iterations = 5
bpy.ops.object.modifier_apply(modifier=smooth.name)
me = o.data
for face in me.polygons:
    face.use_smooth = True
uv = me.uv_layers.active or me.uv_layers.new(name='Bark metres')

def coordinate(p, root_angle=None):
    # Blender Z is Unity Y. Texture's documented physical width is 2.2 metres.
    x, z, height = p.x, -p.y, p.z
    radius = math.hypot(x, z)
    if root_angle is None:
        return [math.atan2(z, x) * 1.40 / 2.2, height / 2.2], math.tau * 1.40 / 2.2
    along = x * math.cos(root_angle) + z * math.sin(root_angle)
    across = -x * math.sin(root_angle) + z * math.cos(root_angle)
    axis_height = max(1.53, 2.4 - .35 * along)
    return [math.atan2(height - axis_height, across) * .32 / 2.2, along / 2.2], math.tau * .32 / 2.2

for face in me.polygons:
    center = o.matrix_world @ face.center
    radius = math.hypot(center.x, center.y)
    angle = None
    if center.z < 2.45 and radius > 1.4:
        a = math.atan2(-center.y, center.x)
        angle = round((a - .18) / (math.tau / 11)) * math.tau / 11 + .18
    coords = [coordinate(o.matrix_world @ me.vertices[me.loops[i].vertex_index].co, angle) for i in face.loop_indices]
    anchor = coords[0][0][0]
    for li, (value, period) in zip(face.loop_indices, coords):
        value[0] += round((anchor - value[0]) / period) * period
        uv.data[li].uv = value
bm = bmesh.new()
bm.from_mesh(me)
boundary_edges = sum(1 for edge in bm.edges if edge.is_boundary)
nonmanifold_edges = sum(1 for edge in bm.edges if not edge.is_manifold)
bm.free()
assert boundary_edges == 0 and nonmanifold_edges == 0, 'Root union must be closed.'
me.calc_loop_triangles()
positions, normals, tex, indices, unique = [], [], [], [], {}
def unity(v):
    return [round(v.x, 6), round(v.z, 6), round(-v.y, 6)]
for triangle in me.loop_triangles:
    for li in triangle.loops:
        loop = me.loops[li]
        p = unity(o.matrix_world @ me.vertices[loop.vertex_index].co)
        n = unity(o.matrix_world.to_3x3() @ me.corner_normals[li].vector)
        t = [round(float(v), 6) for v in uv.data[li].uv]
        key = tuple(p + n + t)
        if key not in unique:
            unique[key] = len(positions)
            positions.append(p); normals.append(n); tex.append(t)
        indices.append(unique[key])
data = dict(name=o.name, positions=positions, normals=normals, uv=tex, indices=indices)
(OUT / 'tree-root-mesh.json').write_text(json.dumps(data, separators=(',', ':')))
report = dict(source='Live Blender MCP', replacedSourceObjects=[x.name for x in originals],
              sourceTriangles=sum(len(x.data.polygons) for x in originals),
              triangles=len(indices)//3, vertices=len(positions), voxelMetres=.038,
              boundaryEdges=boundary_edges, nonmanifoldEdges=nonmanifold_edges,
              preserved='Original objects, root tips, upper branching/crown and gameplay collision',
              uv='UV0; root/trunk flow coordinates at documented 2.2 metre bark scale')
(OUT / 'tree-root-report.json').write_text(json.dumps(report, indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'tree-root-repaired.blend'))
bpy.ops.object.select_all(action='DESELECT')
o.select_set(True)
bpy.context.view_layer.objects.active = o
bpy.ops.export_scene.fbx(filepath=str(OUT / 'tree-root-repaired.fbx'), use_selection=True,
                        axis_forward='-Z', axis_up='Y', add_leaf_bones=False, bake_anim=False)
print(json.dumps(report))
