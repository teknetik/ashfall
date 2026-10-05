import bpy, sys, numpy as np
for f in ['Meshy_AI_Cybernetic_Bench_1004174020_texture.glb','Meshy_AI_Sentinel_Turret_1004174027_texture.glb']:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath='source/'+f)
    o=[o for o in bpy.context.scene.objects if o.type=='MESH'][0]
    me=o.data; M=o.matrix_world
    v=np.array([(M@x.co)[:] for x in me.vertices])
    n=np.array([(M.to_3x3()@p.normal)[:] for p in me.polygons]); c=np.array([(M@p.center)[:] for p in me.polygons]); a=np.array([p.area for p in me.polygons])
    print(f, 'min',v.min(0).round(3),'max',v.max(0).round(3))
    # upward facing area histogram by height (seat detection)
    up=n[:,2]>0.9
    h,e=np.histogram(c[up,2],bins=40,weights=a[up])
    for i in np.argsort(h)[-6:][::-1]: print('  up-facing area %.3f m2 at z %.3f..%.3f'%(h[i],e[i],e[i+1]))
    # x slices: yz extent
    for x0 in np.linspace(v[:,0].min(),v[:,0].max(),12)[:-1]:
        s=v[(v[:,0]>=x0)&(v[:,0]<x0+0.16)]
        if len(s): print('  x %.2f: n %d y %.2f..%.2f z %.2f..%.2f'%(x0,len(s),s[:,1].min(),s[:,1].max(),s[:,2].min(),s[:,2].max()))
    # footprint at bottom
    b=v[v[:,2]<v[:,2].min()+0.03]; print('  feet y %.2f..%.2f x %.2f..%.2f'%(b[:,1].min(),b[:,1].max(),b[:,0].min(),b[:,0].max()))
