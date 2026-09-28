# Blender 5.2 headless: colonist mesh without armature, 1024 px textures, for a Meshy re-rig upload.
import bpy, sys
src, out = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
for o in list(bpy.data.objects):
    if o.type == 'MESH':
        for m in list(o.modifiers):
            if m.type == 'ARMATURE': o.modifiers.remove(m)
        o.parent = None
        o.vertex_groups.clear()
for o in list(bpy.data.objects):
    if o.type != 'MESH': bpy.data.objects.remove(o, do_unlink=True)
for img in bpy.data.images:
    if img.size[0] > 1024: img.scale(1024, 1024)
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', export_animations=False, export_skins=False)
