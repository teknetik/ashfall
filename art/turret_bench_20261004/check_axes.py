import bpy, numpy as np
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath='unity/AthenHill/Assets/AthenHill/Art/TurretBench/sentinel_turret/sentinel_turret_LOD0.glb')
o=[o for o in bpy.context.scene.objects if o.type=='MESH'][0]
v=np.array([(o.matrix_world@x.co)[:] for x in o.data.vertices])
thin=v[(v[:,2]>1.0)&(v[:,2]<1.2)]
for ax,n in ((0,'x'),(1,'y')):
    lo=thin[thin[:,ax]<thin[:,ax].min()+0.15]; hi=thin[thin[:,ax]>thin[:,ax].max()-0.15]
    print('RES blender',n,'min end %.2f spread %.2f / max end %.2f spread %.2f'%(thin[:,ax].min(),np.ptp(lo[:,2]),thin[:,ax].max(),np.ptp(hi[:,2])))
