import bpy, numpy as np
for f in ['meshy/turret-bench-20261004/source/Meshy_AI_Cybernetic_Bench_1004174020_texture.glb','unity/AthenHill/Assets/AthenHill/Art/StreetDressing/Props/bench_painted/bench_painted_LOD0.glb']:
    bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=f)
    for o in [o for o in bpy.context.scene.objects if o.type=='MESH']:
        v=np.array([(o.matrix_world@x.co)[:] for x in o.data.vertices]); z0=v[:,2].min(); h=v[:,2].max()-z0
        hi=v[v[:,2]>z0+0.8*h]; mid=v[(v[:,2]>z0+0.5*h)&(v[:,2]<z0+0.75*h)]
        print('RES',f.split('/')[-1],o.name,'ext',(v.max(0)-v.min(0)).round(3),'high-y mean %.3f range %.3f..%.3f'%(hi[:,1].mean(),hi[:,1].min(),hi[:,1].max()),'y range %.3f..%.3f'%(v[:,1].min(),v[:,1].max()))
