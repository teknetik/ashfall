import bpy, sys
bpy.ops.wm.open_mainfile(filepath=sys.argv[sys.argv.index('--') + 1])
print('[openclose] opened', len(bpy.data.materials), 'materials', flush=True)
