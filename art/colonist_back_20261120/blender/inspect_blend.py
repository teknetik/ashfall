import bpy, sys
p = sys.argv[sys.argv.index('--') + 1]
bpy.ops.wm.open_mainfile(filepath=p)
for o in bpy.data.objects:
    extra = ''
    if o.type == 'MESH': extra = f'tris={sum(len(f.vertices)-2 for f in o.data.polygons)} mats={[m.name for m in o.data.materials if m]} parent={o.parent and o.parent.name} uv={[u.name for u in o.data.uv_layers]}'
    print('OBJ', o.name, o.type, extra)
for i in bpy.data.images: print('IMG', i.name, i.filepath, tuple(i.size))
