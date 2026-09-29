import bpy
SRC = '/home/teknetik/code/ao2/art/quality_20260909/basic-general/basic-general-source-v3.blend'
bpy.ops.wm.open_mainfile(filepath=SRC)
print('SCENES', [s.name for s in bpy.data.scenes], 'CTX', bpy.context.scene.name if bpy.context.scene else None, 'WIN', bpy.context.window)
sc = bpy.data.scenes['Basic General architectural repair']
print('objs', len(sc.objects), 'engine', sc.render.engine, 'cam', sc.camera.name, sc.camera.data.lens, sc.render.resolution_x, sc.render.resolution_y)
print('collections', [c.name for c in bpy.data.collections], 'root objs', len(sc.collection.objects))
print('mats', len(bpy.data.materials), 'images', len(bpy.data.images))
missing = [i.name for i in bpy.data.images if i.source == 'FILE' and not bpy.path.abspath(i.filepath) or (i.source == 'FILE' and not __import__('os').path.exists(bpy.path.abspath(i.filepath)))]
print('missing images', missing[:10])
print('world', sc.world, 'view transform', sc.view_settings.view_transform)
# does an override-based modifier apply work for an object in a non-context scene?
o = [o for o in sc.objects if o.name == 'Counter repair fascia'][0]
print('fascia mods', [m.name for m in o.modifiers], 'tris', len(o.data.polygons))
import bpy_types
print(bpy.app.version_string)
