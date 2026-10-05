"""Non-destructive player polish. Run in Blender 5.2 via live MCP.
The original final_m0.25.blend and retained GLB stay unchanged. Same rest rig and UVs.
Writes a candidate GLB for inspection before installing. No gameplay/runtime overrides.
"""
import bpy, math, json
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion
ROOT=Path('/home/teknetik/code/ao2')
OUT=ROOT/'art/character_polish_20261005'
# Open the source in a separate MCP call first (opening a file invalidates the live context).
rig=bpy.data.objects['Armature']; char=bpy.data.objects['char1']; scene=bpy.context.scene
for track in rig.animation_data.nla_tracks: track.mute=True
names=[b.name for b in rig.pose.bones]
report={'source':'final_m0.25.blend','bind_pose_changed':False,'clips':{}}
# Capture each source independently before authoring; tracks remain muted.
samples={}
for name in ['idle','walk','run']:
 action=bpy.data.actions[name];rig.animation_data.action=action; rows=[]
 for f in range(int(action.frame_range[1])+1):
  scene.frame_set(f); bpy.context.view_layer.update()
  de=char.evaluated_get(bpy.context.evaluated_depsgraph_get());me=de.to_mesh()
  floor=min(v.co.z for v in me.vertices);de.to_mesh_clear()
  rows.append({'q':{p.name:p.rotation_quaternion.copy() for p in rig.pose.bones},
   'm':{p.name:p.matrix.copy() for p in rig.pose.bones},'hip':rig.pose.bones['Hips'].location.copy(),
   'floor':floor})
 samples[name]=rows
base_floor=samples['idle'][0]['floor']
shoulders=['LeftShoulder','RightShoulder']
neutral={n:samples['idle'][0]['q'][n] for n in shoulders}
def average(qs):
 ref=qs[0]; v=[0.,0.,0.,0.]
 for q in qs:
  sign=1 if q.dot(ref)>=0 else -1
  for k in range(4):v[k]+=q[k]*sign
 return Quaternion(v).normalized()
def solve_leg(side,target,rotation,knee_hint):
 upper=rig.pose.bones[side+'UpLeg']; lower=rig.pose.bones[side+'Leg']; foot=rig.pose.bones[side+'Foot']
 a=(lower.head-upper.head).length; b=(foot.head-lower.head).length
 delta=target-upper.head; d=max(abs(a-b)+1e-5,min(delta.length,a+b-1e-5)); direction=delta.normalized()
 bend=knee_hint-upper.head; bend-=direction*bend.dot(direction)
 if bend.length<1e-5:bend=Vector((0,-1,0))-direction*direction.dot(Vector((0,-1,0)))
 bend.normalize();along=(a*a+d*d-b*b)/(2*d)
 knee=upper.head+direction*along+bend*math.sqrt(max(0,a*a-along*along))
 q=(lower.head-upper.head).rotation_difference(knee-upper.head);upper.matrix=Matrix.Translation(upper.head)@q.to_matrix().to_4x4()@Matrix.Translation(-upper.head)@upper.matrix
 bpy.context.view_layer.update()
 q=(foot.head-lower.head).rotation_difference(target-lower.head);lower.matrix=Matrix.Translation(lower.head)@q.to_matrix().to_4x4()@Matrix.Translation(-lower.head)@lower.matrix
 bpy.context.view_layer.update();foot.matrix=Matrix.Translation(foot.head)@rotation.to_matrix().to_4x4();bpy.context.view_layer.update()
for name in ['walk','run']:
 rows=samples[name];original=bpy.data.actions[name]; original.name=name+'_source'
 action=bpy.data.actions.new(name);rig.animation_data.action=action
 mean={n:average([r['q'][n] for r in rows]) for n in shoulders}
 hipz=sum(r['m']['Hips'].translation.z for r in rows)/len(rows)
 hipx=sum(r['m']['Hips'].translation.x for r in rows)/len(rows)
 grounded=min(r['floor'] for r in rows)
 data=[]
 for f,row in enumerate(rows):
  scene.frame_set(f)
  for p in rig.pose.bones:p.rotation_mode='QUATERNION';p.rotation_quaternion=row['q'][p.name];p.location=row['hip'] if p.name=='Hips' else Vector((0,0,0));p.scale=(1,1,1)
  bpy.context.view_layer.update()
  # Remove retargeted floor offset. Walking stays grounded; running retains its airborne interval.
  drop=(row['floor'] if name=='walk' else grounded)-base_floor
  h=rig.pose.bones['Hips']; m=h.matrix.copy();pos=m.translation.copy();pos.z-=drop
  pos.z+=(hipz-row['m']['Hips'].translation.z)*(0.45 if name=='walk' else 0.18)
  pos.x+=(hipx-pos.x)*.25;m.translation=pos;h.matrix=m;bpy.context.view_layer.update()
  for side in ['Left','Right']:
   n=side+'Shoulder';delta=mean[n].inverted()@row['q'][n]
   rig.pose.bones[n].rotation_quaternion=neutral[n]@Quaternion().slerp(delta,.22 if name=='walk' else .38)
   bpy.context.view_layer.update()
   # Preserve arm swing in world space; only the joint attachment gets repaired.
   arm=rig.pose.bones[side+'Arm'];arm.matrix=Matrix.Translation(arm.head)@row['m'][side+'Arm'].to_quaternion().to_matrix().to_4x4();bpy.context.view_layer.update()
   foot=row['m'][side+'Foot']; target=foot.translation-Vector((0,0,drop));knee=row['m'][side+'Leg'].translation-Vector((0,0,drop))
   solve_leg(side,target,foot.to_quaternion(),knee)
  data.append({'q':{p.name:p.rotation_quaternion.copy() for p in rig.pose.bones},'hip':h.location.copy()})
 # Blend the small original loop mismatch over the final 20%, closing both rotation and root displacement.
 for f,row in enumerate(data):
  t=f/(len(data)-1);blend=max(0,(t-.8)/.2);blend=blend*blend*(3-2*blend)
  for p in rig.pose.bones:
   p.rotation_quaternion=row['q'][p.name].slerp(data[0]['q'][p.name],blend)
   p.keyframe_insert('rotation_quaternion',frame=f)
   if p.name=='Hips':p.location=row['hip'].lerp(data[0]['hip'],blend);p.keyframe_insert('location',frame=f)
 # Resolve residual toe/sole penetration after the loop blend (walk always has a support foot).
 for f in range(len(data)):
  scene.frame_set(f);bpy.context.view_layer.update()
  de=char.evaluated_get(bpy.context.evaluated_depsgraph_get());me=de.to_mesh();floor=min(v.co.z for v in me.vertices);de.to_mesh_clear()
  correction=base_floor-floor if name=='walk' else max(0,base_floor-floor)
  h=rig.pose.bones['Hips'];m=h.matrix.copy();m.translation+=Vector((0,0,correction));h.matrix=m;h.keyframe_insert('location',frame=f)
 # Linear dense quaternion samples prevent per-channel cubic overshoot.
 for layer in action.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for curve in bag.fcurves:
     for key in curve.keyframe_points:key.interpolation='LINEAR'
 report['clips'][name]={'frames':len(rows),'fps':scene.render.fps,'source_floor_min':grounded,'target_floor':base_floor,'clavicle_motion_scale':.22 if name=='walk' else .38}
rig.animation_data.action=None
for p in rig.pose.bones:p.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
# Lower and soften the high pinched collar. Only the suit changes; skin, neck, weights and rest joints stay put.
ids=set(v for p in char.data.polygons if p.material_index==3 for v in p.vertices)
count=0
for i in ids:
 v=char.data.vertices[i];z=v.co.z
 if z>1.485 and abs(v.co.x)<.15:
  w=max(0,min(1,(.15-abs(v.co.x))/.055))
  v.co.z-=max(0,z-1.485)*.50*w;count+=1
char.data.update();report['collar_vertices']=count
# Fabric has no metal response; the retained normal bake is much too strong at skin distance.
mat=char.data.materials[3];nt=mat.node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
for socket,value in [('Metallic',0.0),('Roughness',.84)]:
 for link in list(bs.inputs[socket].links):nt.links.remove(link)
 bs.inputs[socket].default_value=value
for n in nt.nodes:
 if n.type=='NORMAL_MAP':n.inputs['Strength'].default_value=.42
report['suit']={'metallic':0,'roughness':.84,'normal_strength':.42}
exec(compile((OUT/'author_belt.py').read_text(),str(OUT/'author_belt.py'),'exec'))
# Rebuild just the export tracks, pointing at the authored clips. No original action is destroyed.
for track in list(rig.animation_data.nla_tracks):rig.animation_data.nla_tracks.remove(track)
for name in ['idle','walk','run']:
 track=rig.animation_data.nla_tracks.new();track.name=name;track.strips.new(name,0,bpy.data.actions[name]);track.mute=True
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'player_polish.blend'))
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);char.select_set(True);bpy.context.view_layer.objects.active=rig
# NLA_TRACKS includes muted tracks (same export contract as the established source pipeline).
bpy.ops.export_scene.gltf(filepath=str(OUT/'colonist_polish.glb'),use_selection=True,export_format='GLB',export_skins=True,export_animations=True,export_animation_mode='NLA_TRACKS',export_morph=False,export_yup=True,export_image_format='AUTO',export_vertex_color='NAME',export_vertex_color_name='Col',export_all_vertex_colors=False,export_tangents=True)
(OUT/'authoring.json').write_text(json.dumps(report,indent=2))
rig.animation_data.action=bpy.data.actions['walk'];scene.frame_set(10)
print(json.dumps(report))
