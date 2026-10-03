import sys; sys.path.insert(0,'/home/teknetik/code/ao2/art/tutorial_set_20261002/blender')
from fitlib import *
bpy.ops.wm.open_mainfile(filepath=str(OUT/'mpfb'/'body_v2.blend'))
u=bpy.context.scene.unit_settings; print('UNITS',u.system,u.scale_length,u.length_unit)
objs=import_glb(RIG)
for o in objs: print('I',o.name,o.type,[round(x,4) for x in o.scale], o.parent.name if o.parent else None)
rig=bpy.data.objects['Human.rig']; marm=[o for o in objs if o.type=='ARMATURE'][0]
for n in ['Hips','LeftForeArm']:
    for a in (rig,marm):
        b=a.data.bones[n]; print('W',a.name,n,[round(x,3) for x in a.matrix_world@b.head_local],[round(x,3) for x in a.matrix_world@b.tail_local], round(b.length,3))
