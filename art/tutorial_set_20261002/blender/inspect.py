import bpy, json, sys
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath='/home/teknetik/code/ao2/meshy/main-char-20261002/rigged.glb')
out={}
for o in bpy.data.objects:
    out.setdefault('objects',[]).append([o.name,o.type,o.parent.name if o.parent else None,[round(v,4) for v in o.scale]])
arm=[o for o in bpy.data.objects if o.type=='ARMATURE'][0]
out['bones']={b.name:{'head':[round(v,4) for v in (arm.matrix_world@b.head_local)],'tail':[round(v,4) for v in (arm.matrix_world@b.tail_local)],'parent':b.parent.name if b.parent else None} for b in arm.data.bones}
me=[o for o in bpy.data.objects if o.type=='MESH'][0]
out['mesh']={'name':me.name,'verts':len(me.data.vertices),'groups':[g.name for g in me.vertex_groups],'mats':[m.name for m in me.data.materials],'uvs':[u.name for u in me.data.uv_layers]}
import mathutils
ws=[me.matrix_world@v.co for v in me.data.vertices]
out['bounds']=[[round(min(w[i] for w in ws),4) for i in range(3)],[round(max(w[i] for w in ws),4) for i in range(3)]]
json.dump(out,open('inspect.json','w'),indent=1)
