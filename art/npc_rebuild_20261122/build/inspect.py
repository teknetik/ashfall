"""Review renders of a character GLB (Cycles CPU, Standard view transform, neutral sun + sky, so colours are honest).
blender.sh inspect.py -- model.glb out_prefix [--flat]"""
import bpy, sys, math
import numpy as np
from mathutils import Vector
a = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=a[0])
s = bpy.context.scene
ms = [o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith('Icosphere')]
for o in bpy.data.objects:
    if o.animation_data: o.animation_data_clear()
    if o.type == 'ARMATURE': o.data.pose_position = 'REST'
    if o.type == 'MESH' and (o not in ms or 'lod1' in o.name): o.hide_render = True
ms = [o for o in ms if not o.hide_render]
bpy.context.view_layer.update()
co = np.array([tuple(o.matrix_world @ v.co) for o in ms for v in o.data.vertices])
lo, hi = co.min(0), co.max(0); H = hi[2] - lo[2]; cx = (lo[0] + hi[0]) / 2
head = co[co[:, 2] > lo[2] + H * .87]; hc = (head.min(0) + head.max(0)) / 2
flat = '--flat' in a
if flat:
    for o in ms:
        for m in o.data.materials:
            n = m.node_tree; b = next(x for x in n.nodes if x.type == 'BSDF_PRINCIPLED')
            out = next(x for x in n.nodes if x.type == 'OUTPUT_MATERIAL')
            if b.inputs['Base Color'].links:
                e = n.nodes.new('ShaderNodeEmission')
                n.links.new(b.inputs['Base Color'].links[0].from_socket, e.inputs[0]); n.links.new(e.outputs[0], out.inputs[0])
s.render.engine = 'CYCLES'; s.cycles.device = 'CPU'; s.cycles.samples = 24; s.cycles.use_denoising = False
s.view_settings.view_transform = 'Standard'
w = bpy.data.worlds.new('w'); w.use_nodes = True
bg = w.node_tree.nodes['Background']; bg.inputs[0].default_value = (.5, .55, .62, 1); bg.inputs[1].default_value = .55; s.world = w
sun = bpy.data.objects.new('s', bpy.data.lights.new('s', 'SUN')); s.collection.objects.link(sun)
sun.data.energy = 2.2; sun.data.angle = .15; sun.rotation_euler = (math.radians(55), 0, math.radians(-28))
cam = bpy.data.objects.new('c', bpy.data.cameras.new('c')); s.collection.objects.link(cam); s.camera = cam; cam.data.type = 'ORTHO'
for name, yaw, target, size, rx, ry in (('front', 0, (cx, 0, lo[2] + H / 2), H * 1.04, 620, 820),
                                       ('quarter', 40, (cx, 0, lo[2] + H / 2), H * 1.04, 620, 820),
                                       ('back', 180, (cx, 0, lo[2] + H / 2), H * 1.04, 620, 820),
                                       ('face', 8, tuple(hc), H * .17, 620, 820),
                                       ('face_q', 45, tuple(hc), H * .17, 620, 820)):
    t = Vector(target); y = math.radians(yaw)
    cam.location = t + Vector((math.sin(y), -math.cos(y), 0)) * H * 3; cam.data.ortho_scale = size; cam.data.clip_end = 100
    cam.rotation_euler = (t - cam.location).to_track_quat('-Z', 'Y').to_euler()
    s.render.resolution_x = rx; s.render.resolution_y = ry; s.render.filepath = f'{a[1]}_{name}.png'
    bpy.ops.render.render(write_still=True)
print('INSPECT', [(o.name, len(o.data.polygons)) for o in ms], 'H', H, [(i.name, tuple(i.size)) for i in bpy.data.images])
