"""Diagnostic: renders Unity's baked LOD0 (WardWalkerInstall dumpmesh OBJ) with the walker's glTF material, face close-up.
Usage: blender.sh render_dump.py -- <walker folder> <obj> <out png>"""
import bpy, sys, math
from mathutils import Vector
a = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
s = bpy.context.scene; s.render.engine = 'CYCLES'; s.cycles.device = 'CPU'; s.cycles.samples = 16
w = bpy.data.worlds.new('w'); s.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[1].default_value = 1.0
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); s.collection.objects.link(sun); sun.data.energy = 3; sun.rotation_euler = (math.radians(50), 0, math.radians(-35))
bpy.ops.import_scene.gltf(filepath=a[0] + '/rigged_fixed.glb')
mat = next(m for m in bpy.data.materials if m.users)
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.wm.obj_import(filepath=a[1], forward_axis='NEGATIVE_Z', up_axis='Y')
o = bpy.context.selected_objects[0]; o.data.materials.clear(); o.data.materials.append(mat)
zs = [v.co for v in o.data.vertices]; lo = Vector([min(c[i] for c in zs) for i in range(3)]); hi = Vector([max(c[i] for c in zs) for i in range(3)])
ax = max(range(3), key=lambda i: hi[i] - lo[i]); print('DUMP bbox', lo, hi, 'tall axis', ax)
k = float(a[3]) / (hi[ax] - lo[ax]) if len(a) > 3 else 1.0; o.scale = (k, k, k); bpy.context.view_layer.update()
co = [o.matrix_world @ v.co for v in o.data.vertices]; top = max(c.z for c in co)
head = [c for c in co if c.z > top - .25]; cx = sum(c.x for c in head) / len(head); cy = sum(c.y for c in head) / len(head)
front = min(head, key=lambda c: c.y)  # face side (most -Y or +Y); try both
cam = bpy.data.objects.new('c', bpy.data.cameras.new('c')); s.collection.objects.link(cam); s.camera = cam; cam.data.lens = 85
s.render.resolution_x = s.render.resolution_y = 640
for i, sign in enumerate((-1, 1)):
    cam.location = Vector((cx, cy + sign * 1.0, top - .14)); d = Vector((cx, cy, top - .16)) - cam.location
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    s.render.filepath = a[2].replace('.png', f'_{i}.png'); bpy.ops.render.render(write_still=True)
print('DUMP OK')
