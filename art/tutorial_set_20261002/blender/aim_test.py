import sys; sys.path.insert(0,'/home/teknetik/code/ao2/art/tutorial_set_20261002/blender')
from fitlib import *
from mathutils import Matrix
arm,body=load_final()
src_path='/home/teknetik/code/ao2/meshy/main-char-20261002/aim_95.glb'
before=set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=src_path)
new=[o for o in bpy.data.objects if o not in before]; src=[o for o in new if o.type=='ARMATURE'][0]
for o in new:
    if o.type=='MESH': o.hide_render=True
act=src.animation_data.action; print('RANGE',act.frame_range)
f=int(round(act.frame_range[0]+3.59*bpy.context.scene.render.fps)); f=min(f,int(act.frame_range[1]))
bpy.context.scene.frame_set(f)
def rw(a,n): return a.matrix_world@a.data.bones[n].matrix_local
names=[b.name for b in arm.data.bones if b.name in src.data.bones]
sw={n:src.matrix_world@src.pose.bones[n].matrix for n in names}
rinv=arm.matrix_world.inverted()
for n in [b.name for b in arm.data.bones]:
    if n not in sw: continue
    pb=arm.pose.bones[n]
    rot=(sw[n].to_3x3().normalized()@rw(src,n).to_3x3().normalized().inverted())@rw(arm,n).to_3x3().normalized()
    pos=(arm.matrix_world@pb.matrix).translation
    pb.matrix=rinv@(Matrix.Translation(pos)@rot.to_4x4()); bpy.context.view_layer.update()
src.location.x+=1.2
render_views(str(OUT/'mpfb'/'aimtest'),(0.5,0,1.1),2.4,views=('front','side'),res=(700,500))
