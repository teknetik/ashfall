"""Render quick Blender review stills of the saved market source (not final Unity evidence)."""
import bpy, math, sys
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath='/home/teknetik/code/ao2/art/karaveen_market_20260926/karaveen-market-v1.blend')
sc = bpy.context.scene
for o in sc.objects:
    if o.name.startswith('COL_'): o.hide_render = True
sc.render.engine = 'BLENDER_EEVEE'; sc.render.resolution_x = 1280; sc.render.resolution_y = 720
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = (.55, .5, .42, 1); w.node_tree.nodes['Background'].inputs['Strength'].default_value = .8
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sc.collection.objects.link(sun)
sun.data.energy = 4; sun.rotation_euler = (math.radians(50), 0, math.radians(200)); sun.data.color = (1, .88, .72)
bpy.ops.mesh.primitive_plane_add(size=80, location=(40, 0, 0)); bpy.context.object.data.materials.append(bpy.data.materials['Market_Hessian'])
def U(x, z, y=0): return Vector((-x, -z, y))
def shot(name, eye, target, lens=30):
    cam = bpy.data.objects.new(name, bpy.data.cameras.new(name)); sc.collection.objects.link(cam)
    cam.location = eye; cam.data.lens = lens
    cam.rotation_euler = (target - eye).to_track_quat('-Z', 'Y').to_euler(); sc.camera = cam
    sc.render.filepath = f'/home/teknetik/code/ao2/art/karaveen_market_20260926/review/{name}.png'; bpy.ops.render.render(write_still=True)
shot('overview', U(-26, 2, 9), U(-38, 0, 0), 24)
shot('produce', U(-36.2, 12.5, 1.7), U(-40, 12, 1.0), 28)
shot('pottery', U(-36.4, 4.2, 1.7), U(-39.7, 5.2, 1.0), 28)
shot('tools', U(-36.3, -10.2, 1.7), U(-39.8, -10.8, 1.2), 28)
shot('cloth', U(-34.5, 12.8, 1.7), U(-34.0, 16.6, 1.2), 28)
shot('rations', U(-33.3, -12.5, 1.7), U(-34, -16.2, 1.1), 28)
shot('cookfire', U(-32.2, -1.5, 1.8), U(-35, -3, .6), 30)
