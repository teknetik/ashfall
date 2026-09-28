"""Eevee review stills of the retrofit source (not in-game evidence).
blender -b ward-retrofit-v1.blend -P review_retrofit.py -- name:ex,ez,ey,tx,tz,ty [...]  (Unity coordinates)"""
import bpy, sys, math
from mathutils import Vector
from pathlib import Path
OUT = Path('/home/teknetik/code/ao2/art/ward_retrofit_20260926/review'); OUT.mkdir(exist_ok=True)
U = lambda x, z, y: Vector((-x, -z, y))
sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE'; sc.render.resolution_x = 1280; sc.render.resolution_y = 720
w = bpy.data.worlds.new('W'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs[0].default_value = (.55, .5, .45, 1); w.node_tree.nodes['Background'].inputs[1].default_value = .9
sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN')); sc.collection.objects.link(sun)
sun.data.energy = 4.5; sun.rotation_euler = (math.radians(55), 0, math.radians(35)); sun.data.color = (1, .9, .78)
bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, 0))
g = bpy.context.object; mat = bpy.data.materials.new('G'); mat.use_nodes = True
mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.45, .36, .26, 1); g.data.materials.append(mat)
for c in [c for c in bpy.data.collections if c.name == 'LIB']:
    for o in c.objects: o.hide_render = True
for o in bpy.data.objects:
    if o.name.startswith('COL_'): o.hide_render = True
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 24
for arg in sys.argv[sys.argv.index('--') + 1:]:
    name, v = arg.split(':'); ex, ez, ey, tx, tz, ty = map(float, v.split(','))
    cam.location = U(ex, ez, ey)
    d = U(tx, tz, ty) - cam.location
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = str(OUT / f'{name}.png'); bpy.ops.render.render(write_still=True)
