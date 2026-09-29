import bpy
print('IMAGES')
for im in bpy.data.images:
    print(im.name, im.filepath, im.size[:], im.has_data, im.packed_file is not None)
print('MATS')
for m in bpy.data.materials:
    print(m.name, [n.type for n in m.node_tree.nodes] if m.use_nodes else None)
print('LIGHTS/CAM', [(o.name, o.type) for o in bpy.data.objects if o.type in ('LIGHT', 'CAMERA', 'EMPTY')][:20])
print('world', bpy.context.scene.world)
print('engine', bpy.context.scene.render.engine)
