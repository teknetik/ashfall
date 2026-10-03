import sys; sys.path.insert(0,'/home/teknetik/code/ao2/art/tutorial_set_20261002/blender')
from fitlib import *
from mathutils import Matrix
bpy.ops.wm.open_mainfile(filepath=str(OUT/'mpfb'/'final_v5.blend'))
rig=bpy.data.objects['Armature']
print('NLA',[t.name for t in rig.animation_data.nla_tracks], 'action', rig.animation_data.action)
for t in rig.animation_data.nla_tracks: t.mute=True
CH={'LeftUpLeg':'LeftLeg','LeftLeg':'LeftFoot','Spine02':'Spine01','LeftArm':'LeftForeArm','Hips':'Spine02'}
before=set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath='/home/teknetik/code/ao2/meshy/main-char-20261002/basic_walking.glb')
src=[o for o in bpy.data.objects if o not in before and o.type=='ARMATURE'][0]
print('SRC action', src.animation_data.action.name, src.animation_data.action.frame_range)
def j(a,n): return a.matrix_world @ a.pose.bones[n].head
def jr(a,n): return a.matrix_world @ a.data.bones[n].head_local
bpy.context.scene.frame_set(1)
for n,c in CH.items():
    print('REST',n, (jr(src,c)-jr(src,n)).normalized(), (jr(rig,c)-jr(rig,n)).normalized())
    print('POSE',n, (j(src,c)-j(src,n)).normalized())
# rest-pose world matrices sanity: pose matrix at rest vs matrix_local
pb=src.pose.bones['LeftUpLeg']; print('SRC basis', pb.matrix_basis)
rig.animation_data.action=bpy.data.actions['walk']
for f in (0,5):
    bpy.context.scene.frame_set(f); sf=f+1
    bpy.context.view_layer.update()
    tdir={n:(j(rig,c)-j(rig,n)).normalized() for n,c in CH.items()}
    bpy.context.scene.frame_set(sf)
    for n,c in CH.items():
        sd=(j(src,c)-j(src,n)).normalized(); print('CMP',f,n,'angle %.1f'%__import__('math').degrees(sd.angle(tdir[n])))
print('FC', [(fc.data_path, fc.array_index, len(fc.keyframe_points)) for fc in bpy.data.actions['walk'].fcurves][:8] if hasattr(bpy.data.actions['walk'],'fcurves') else 'layered')
