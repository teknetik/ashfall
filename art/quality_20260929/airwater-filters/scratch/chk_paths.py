import bpy, os
print('missing', [(i.name, i.filepath) for i in bpy.data.images if i.filepath and not os.path.exists(bpy.path.abspath(i.filepath))])
print('sample', [i.filepath for i in bpy.data.images][:2])
