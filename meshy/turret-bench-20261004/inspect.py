import bpy, sys, os, math, mathutils, json
out=sys.argv[sys.argv.index('--')+1]
res={}
for f in sorted(os.listdir('source')):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath='source/'+f)
    objs=[o for o in bpy.context.scene.objects if o.type=='MESH']
    dg=bpy.context.evaluated_depsgraph_get()
    mn=mathutils.Vector((1e9,)*3); mx=-mn
    tris=0
    for o in objs:
        for c in o.bound_box:
            w=o.matrix_world@mathutils.Vector(c); mn=mathutils.Vector(map(min,mn,w)); mx=mathutils.Vector(map(max,mx,w))
        me=o.evaluated_get(dg).to_mesh(); me.calc_loop_triangles(); tris+=len(me.loop_triangles)
    mats=[ (m.name,[ (n.image.name,n.image.size[:]) for n in m.node_tree.nodes if n.type=='TEX_IMAGE']) for m in bpy.data.materials if m.node_tree]
    res[f]=dict(objs=[o.name for o in objs],min=list(mn),max=list(mx),size=list(mx-mn),tris=tris,mats=mats)
    # render 4 views
    ctr=(mn+mx)/2; r=(mx-mn).length
    sc=bpy.context.scene; sc.render.engine='BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'
    sc.render.resolution_x=800; sc.render.resolution_y=800
    w=bpy.data.worlds.new('w'); sc.world=w; w.use_nodes=True; w.node_tree.nodes['Background'].inputs[0].default_value=(0.6,0.6,0.65,1); w.node_tree.nodes['Background'].inputs[1].default_value=1.0
    sun=bpy.data.objects.new('sun',bpy.data.lights.new('sun','SUN')); sun.data.energy=3; sun.rotation_euler=(math.radians(50),0,math.radians(30)); sc.collection.objects.link(sun)
    cam=bpy.data.objects.new('cam',bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera=cam
    for i,a in enumerate([30,120,210,300]):
        t=math.radians(a); d=r*1.6
        cam.location=ctr+mathutils.Vector((math.cos(t)*d,math.sin(t)*d,d*0.45))
        cam.rotation_euler=(ctr-cam.location).to_track_quat('-Z','Y').to_euler()
        sc.render.filepath=f'{out}/{f[:-4]}_{i}.png'; bpy.ops.render.render(write_still=True)
json.dump(res,open(out+'/inspect.json','w'),indent=1)
