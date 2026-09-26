"""Live Blender source audit; retained FBX and unreduced GLB remain untouched.

Invoke with GROUND_FAMILY='trash'/'scrap'/'crate'. Writes a source comparison,
not native-game acceptance. Camera/model scale is matched between each pair.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Vector
R=Path('/home/teknetik/code/ao2')
F=globals().get('GROUND_FAMILY','trash')
O=Path(globals().get('GROUND_OUTPUT',str(R/'meshy/ground-detail-20260910'/F)))
assert not (O/'source-review.blend').exists(), 'Preserve previous source review'
S=bpy.data.scenes.new('Ground source comparison '+F)
bpy.context.window.scene=S
S.render.engine='CYCLES';S.cycles.samples=24;S.cycles.use_denoising=True
try:
 p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='CUDA';p.get_devices()
 for d in p.devices:d.use=d.type=='CUDA'
 S.cycles.device='GPU'
except Exception:pass
S.render.resolution_x=1600;S.render.resolution_y=900;S.render.resolution_percentage=100
S.view_settings.view_transform='AgX'
S.world=bpy.data.worlds.new('Neutral inspection world '+F);S.world.use_nodes=True
S.world.node_tree.nodes['Background'].inputs[0].default_value=(.38,.43,.5,1)
S.world.node_tree.nodes['Background'].inputs[1].default_value=.55

def own(ob):
 for c in list(ob.users_collection):c.objects.unlink(ob)
 S.collection.objects.link(ob)
 return ob
def material(label,folder):
 m=bpy.data.materials.new(label);m.use_nodes=True;nt=m.node_tree;bs=nt.nodes.get('Principled BSDF')
 files={'base_color':('Base Color',False),'normal':('Normal',True),'roughness':('Roughness',True),'metallic':('Metallic',True)}
 for f,(s,linear) in files.items():
  paths=list(folder.rglob(f+'.png'))
  if not paths:continue
  t=nt.nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(paths[0]),check_existing=True)
  if linear:t.image.colorspace_settings.name='Non-Color'
  if s=='Normal':
   n=nt.nodes.new('ShaderNodeNormalMap');nt.links.new(t.outputs['Color'],n.inputs['Color']);nt.links.new(n.outputs['Normal'],bs.inputs['Normal'])
  else:nt.links.new(t.outputs['Color'],bs.inputs[s])
 return m
report=[]
original_path=Path(globals().get('GROUND_ORIGINAL',str(R/'meshy/salvage-20260908'/F/(F+'.fbx'))))
for label,path,x in [('original',original_path,-1.45),('candidate',O/'model.fbx',1.45)]:
 before=set(S.objects);bpy.ops.import_scene.fbx(filepath=str(path))
 obs=[o for o in S.objects if o not in before and o.type=='MESH']
 verts=[o.matrix_world@Vector(c) for o in obs for c in o.bound_box]
 lo=Vector(tuple(min(v[k] for v in verts) for k in range(3)));hi=Vector(tuple(max(v[k] for v in verts) for k in range(3)))
 # Normalize uniformly to a 2 m longest extent. Z-up Blender axes retained.
 scale=2/max(hi-lo);center=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
 root=bpy.data.objects.new(label+' reference 2m normalized',None);S.collection.objects.link(root)
 for ob in obs:
  old=ob.matrix_world.copy();ob.parent=root;ob.matrix_world=old
 root.scale=(scale,)*3;root.location=Vector((x,0,0))-center*scale
 if label=='candidate' or 'GROUND_ORIGINAL' in globals():
  mat=material(label+' full original PBR '+F,(O if label=='candidate' else original_path.parent)/'model_textures')
  for ob in obs:ob.data.materials.clear();ob.data.materials.append(mat)
 for ob in obs:
  ob.data.calc_loop_triangles()
 report.append(dict(version=label,source=str(path.relative_to(R)),objects=len(obs),triangles=sum(len(o.data.loop_triangles) for o in obs),vertices=sum(len(o.data.vertices) for o in obs),sourceBounds=[list(lo),list(hi)],uniformReviewScale=scale,uvLayers=[len(o.data.uv_layers) for o in obs],normal='Imported source normals',sourceUnmodified=True))
 # Label is explicit review annotation, not game content.
 cu=bpy.data.curves.new(label,'FONT');cu.body=('FULL SOURCE' if label=='original' else 'RUNTIME') if 'GROUND_ORIGINAL' in globals() else label.upper();cu.align_x='CENTER';cu.size=.17
 tx=bpy.data.objects.new(label+' label',cu);S.collection.objects.link(tx);tx.location=(x,-.1,2.3);tx.rotation_euler=(math.pi/2,0,0)
bpy.ops.mesh.primitive_plane_add(size=200);floor=own(bpy.context.object);floor.location.z=-.015
fm=bpy.data.materials.new('Neutral floor');fm.diffuse_color=(.20,.21,.22,1);floor.data.materials.append(fm)
for name,pos,energy,size in [('Key',(-3,-4,6),1100,4),('Fill',(4,-2,4),600,5),('Rim',(1,4,5),800,3)]:
 ld=bpy.data.lights.new(name,'AREA');ld.energy=energy;ld.shape='DISK';ld.size=size
 ob=bpy.data.objects.new(name,ld);S.collection.objects.link(ob);ob.location=pos;ob.rotation_euler=(Vector((0,0,.7))-ob.location).to_track_quat('-Z','Y').to_euler()
cd=bpy.data.cameras.new('Source comparison camera');cam=bpy.data.objects.new('Source comparison camera',cd);S.collection.objects.link(cam)
cam.location=(4,-9,4.0);target=Vector((0,0,1.0));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cd.type='ORTHO';cd.ortho_scale=6.2;S.camera=cam
(O/'source-geometry-review.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(O/'source-review.blend'))
S.render.filepath=str(O/'source-review-front.png');bpy.ops.render.render(write_still=True)
cam.location=(-4,8,3.2);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
S.render.filepath=str(O/'source-review-back.png');bpy.ops.render.render(write_still=True)
print(json.dumps(report))
