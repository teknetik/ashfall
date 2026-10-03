import sys; sys.path.insert(0,'/home/teknetik/code/ao2/art/tutorial_set_20261002/blender')
from fitlib import *
bpy.ops.wm.open_mainfile(filepath=str(OUT/'mpfb'/'body_v2.blend'))
for o in bpy.data.objects: print('O',o.name,o.type,o.parent.name if o.parent else None,[round(x,3) for x in o.scale],[round(x,3) for x in o.location])
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
for n in ['Hips','Head','LeftHand','LeftFoot']: print('B',n,[round(x,3) for x in rig.matrix_world@rig.data.bones[n].head_local])
body=bpy.data.objects['Human']; lo,hi=eval_bounds(body); print('EB',lo,hi); lo,hi=bounds(body); print('RB',lo,hi)
