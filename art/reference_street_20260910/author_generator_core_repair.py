"""STAGED live-Blender source repair. Never launches an application.
Creates a separate source scene; old V3 scene, complete core and PBR stay intact.
The immutable mask is reviewable as an orange source patch. This is a source
AUDITION, not permission to reduce/install. Uses no Boolean on the open Meshy mesh.
"""
import bpy,numpy as np,math,json,hashlib,sys
from pathlib import Path
from mathutils import Vector
R=Path('/home/teknetik/code/ao2');P=R/'art/reference_street_20260910';I=P/'generator-core-repair-inputs';O=R/'meshy/ground-detail-20260910/generator-v4-source'
assert not O.exists(),'Preserve prior source-repair audition'
assert not bpy.data.scenes.get('Generator v4 core repair audition'),'A previous live attempt already created the scene; inspect/resume its saved failure instead of duplicating it'
OLD=bpy.data.scenes.get('Generator v3 side service authoring');assert OLD,'Load approved handback before this script'
H=bpy.data.objects['GENERATOR_V3_RETAINED_CORE'];m=H.data;contract=json.loads((I/'mask-contract.json').read_text());maskfile=I/'proposed-guard-face-mask.npz'
assert hashlib.sha256(maskfile.read_bytes()).hexdigest()==contract['maskFileSha256']
assert hashlib.sha256((R/'meshy/ground-detail-20260910/generator-v2/model.fbx').read_bytes()).hexdigest()==contract['originalFbxSha256']
assert len(m.vertices)==960755 and len(m.polygons)==1927842 and len(m.loops)==5783526
co=np.empty((len(m.vertices),3),np.float32);m.vertices.foreach_get('co',co.ravel());tri=np.empty((len(m.polygons),3),np.int32);m.loops.foreach_get('vertex_index',tri.ravel())
assert hashlib.sha256(tri.tobytes()).hexdigest()==contract['sourceTriangleIndicesInt32Sha256']
mat=np.asarray(H.matrix_world,dtype=np.float64);world=(co@mat[:3,:3].T+mat[:3,3]).astype(np.float32)
assert hashlib.sha256(world.tobytes()).hexdigest()==contract['sourceWorldPositionsFloat32Sha256'],'Original source positions/transform changed'
removed=np.load(maskfile)['removed_face_indices'];assert hashlib.sha256(removed.tobytes()).hexdigest()==contract['removedFaceIndicesSha256']
keep=np.ones(len(tri),bool);keep[removed]=False;retained=np.flatnonzero(keep)
lo,hi=np.asarray(contract['strictAllowedWorldBoundsBlender']);rv=world[tri[removed]];assert ((rv>=lo)&(rv<=hi)).all()
uv=[]
for layer in m.uv_layers:
 a=np.empty((len(m.loops),2),np.float32);layer.data.foreach_get('uv',a.ravel());uv.append((layer.name,a.reshape(-1,3,2)))
normals=np.empty((len(m.loops),3),np.float32);m.corner_normals.foreach_get('vector',normals.ravel());normals=normals.reshape(-1,3,3);assert np.isfinite(normals).all()
smooth=np.empty(len(m.polygons),bool);m.polygons.foreach_get('use_smooth',smooth);mi=np.empty(len(m.polygons),np.int32);m.polygons.foreach_get('material_index',mi)
oldNormalHash=hashlib.sha256(normals.tobytes()).hexdigest()
oldmeshHash=hashlib.sha256(co.tobytes()+tri.tobytes()).hexdigest();oldUvHashes={n:hashlib.sha256(a.tobytes()).hexdigest()for n,a in uv}
# Only after every immutable guard passes do we create the separate audition scene.
try:
 S=bpy.data.scenes.new('Generator v4 core repair audition');bpy.context.window.scene=S
 S.unit_settings.system='METRIC';S.unit_settings.scale_length=1;S.render.engine='CYCLES';S.cycles.device=OLD.cycles.device;S.cycles.samples=24;S.cycles.use_denoising=True
 S.world=OLD.world;S.view_settings.view_transform=OLD.view_settings.view_transform;S.view_settings.exposure=OLD.view_settings.exposure
 S.render.resolution_x=1400;S.render.resolution_y=1100;S.render.resolution_percentage=100;S.render.image_settings.file_format='PNG';S.render.image_settings.color_mode='RGBA'
 C=bpy.data.collections.new('Generator v4 source parts');S.collection.children.link(C)
 A=bpy.data.collections.new('Generator v4 authored grille guard');S.collection.children.link(A)
 Q=bpy.data.collections.new('Generator v4 source recovery and mask');S.collection.children.link(Q)
 copyMap={};service=[]
 for o in OLD.objects:
  if o==H:continue
  q=o.copy();C.objects.link(q);q.hide_set(q.hide_render);copyMap[o]=q
  if o==OLD.camera:q.data=o.data.copy();S.camera=q
  if o.type=='MESH' and 'review ground' not in o.name.lower():service.append({'sourceName':o.name,'copyName':q.name,'sharedMesh':o.data.name,'worldMatrix':[list(row)for row in o.matrix_world],'active':not o.hide_render})
 for old,q in copyMap.items():
  if old.parent in copyMap:q.parent=copyMap[old.parent];q.matrix_world=old.matrix_world.copy()
 original=H.copy();original.name='GENERATOR_V4_ORIGINAL_CORE_RECOVERY';Q.objects.link(original);original.hide_render=True;original.hide_set(True)
 subsetProof=[]
 def subset(name,faceids,collection):
  mesh=bpy.data.meshes.new(name+' mesh');mesh.vertices.add(len(co));mesh.vertices.foreach_set('co',co.ravel());mesh.loops.add(len(faceids)*3);mesh.loops.foreach_set('vertex_index',tri[faceids].ravel());mesh.polygons.add(len(faceids))
  mesh.polygons.foreach_set('loop_start',np.arange(len(faceids),dtype=np.int32)*3);mesh.polygons.foreach_set('loop_total',np.full(len(faceids),3,np.int32));mesh.polygons.foreach_set('use_smooth',smooth[faceids]);mesh.polygons.foreach_set('material_index',mi[faceids]);mesh.update()
  assert not mesh.validate(clean_customdata=False),'Unexpected malformed retained source polygons'
  for nameuv,a in uv:
   layer=mesh.uv_layers.new(name=nameuv);layer.data.foreach_set('uv',np.ascontiguousarray(a[faceids]).ravel())
  for slot in H.material_slots:mesh.materials.append(slot.material)
  expected=np.ascontiguousarray(normals[faceids].reshape(-1,3));normalApi='NumPy sequence'
  try:mesh.normals_split_custom_set(expected)
  except TypeError:
   normalApi='Python sequence fallback';mesh.normals_split_custom_set(expected.tolist())
  q=bpy.data.objects.new(name,mesh);collection.objects.link(q);q.matrix_world=H.matrix_world.copy()
  checkco=np.empty_like(co);mesh.vertices.foreach_get('co',checkco.ravel());checktri=np.empty((len(faceids),3),np.int32);mesh.loops.foreach_get('vertex_index',checktri.ravel());assert np.array_equal(checkco,co) and np.array_equal(checktri,tri[faceids])
  uvProof=[]
  for layer,(nameuv,a) in zip(mesh.uv_layers,uv):
   actual=np.empty((len(faceids)*3,2),np.float32);layer.data.foreach_get('uv',actual.ravel());assert np.array_equal(actual,a[faceids].reshape(-1,2));uvProof.append({'layer':nameuv,'retainedValuesExactlyEqual':True,'sha256':hashlib.sha256(actual.tobytes()).hexdigest()})
  actualnorm=np.empty_like(expected);mesh.corner_normals.foreach_get('vector',actualnorm.ravel());error=float(np.abs(actualnorm-expected).max());dots=np.einsum('ij,ij->i',actualnorm,expected);mindot=float(dots.min())
  assert mindot>.99999 and error<.003,'Custom corner normals changed beyond quantized round-trip tolerance; inspect source before continuing'
  subsetProof.append({'object':q.name,'faces':len(faceids),'vertexValuesExactlyEqual':True,'triangleIndicesExactlyEqual':True,'uv':uvProof,'customNormalMinDot':mindot,'customNormalMaxComponentDelta':error,'customNormalsRestored':True,'normalSetterInput':normalApi})
  return q
 core=subset('GENERATOR_V4_REPAIRED_CORE',retained,C);selected=subset('GENERATOR_V4_REMOVED_GUARD_MASK',removed,Q);selected.hide_render=True;selected.hide_set(True)
 def material(name,color,metal,rough,grain=.000025):
  ma=bpy.data.materials.new(name);ma.use_nodes=True;n=ma.node_tree.nodes;k=ma.node_tree.links;p=n.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
  g=n.new('ShaderNodeNewGeometry');noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=650;noise.inputs['Detail'].default_value=2;k.new(g.outputs['Position'],noise.inputs['Vector']);b=n.new('ShaderNodeBump');b.inputs['Strength'].default_value=.20;b.inputs['Distance'].default_value=grain;k.new(noise.outputs['Fac'],b.inputs['Height']);k.new(b.outputs['Normal'],p.inputs['Normal']);return ma
 paint=material('Generator repaired grille dark steel paint',(.037,.044,.039),.12,.56,.000040);steel=material('Generator repaired guard exposed steel',(.12,.14,.125),.84,.46,.000025);rubber=material('Generator guard isolating washers',(.014,.017,.014),0,.76,.00002)
 maskmat=bpy.data.materials.new('Diagnostic removed source faces orange');maskmat.use_nodes=True;nn=maskmat.node_tree.nodes;ll=maskmat.node_tree.links;e=nn.new('ShaderNodeEmission');e.inputs['Color'].default_value=(1,.13,.015,1);e.inputs['Strength'].default_value=.8;ll.new(e.outputs[0],nn.get('Material Output').inputs['Surface'])
 for slot in selected.material_slots:slot.link='OBJECT';slot.material=maskmat
 parts=[]
 def own(o,name,ma):
  o.name=name
  for c in list(o.users_collection):c.objects.unlink(o)
  A.objects.link(o);o.data.materials.clear();o.data.materials.append(ma);parts.append(o);return o

 def activate(o):
  for x in S.objects:x.select_set(False)
  o.select_set(True);bpy.context.view_layer.objects.active=o

 def box(name,center,size,ma=paint,r=.0012):
  bpy.ops.mesh.primitive_cube_add(size=1,location=center);o=own(bpy.context.object,name,ma);o.scale=size;activate(o);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
  b=o.modifiers.new('Rolled machined edge radius','BEVEL');b.width=r;b.segments=3;b.harden_normals=True;bpy.ops.object.modifier_apply(modifier=b.name)
  for p in o.data.polygons:p.use_smooth=True
  w=o.modifiers.new('Weighted section normals','WEIGHTED_NORMAL');w.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=w.name);return o

 def cylinder(name,a,b,r,ma=steel,sides=32):
  a,b=Vector(a),Vector(b);d=b-a;bpy.ops.mesh.primitive_cylinder_add(vertices=sides,radius=r,depth=d.length,location=(a+b)*.5);o=own(bpy.context.object,name,ma);o.rotation_euler=d.to_track_quat('Z','Y').to_euler()
  for p in o.data.polygons:p.use_smooth=True
  return o

 def wire(name,points,r=.0011,cyclic=False,ma=steel):
  cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.resolution_u=1;cu.bevel_depth=r;cu.bevel_resolution=2;cu.use_fill_caps=not cyclic;sp=cu.splines.new('POLY');sp.points.add(len(points)-1)
  for p,v in zip(sp.points,points):p.co=(*v,1)
  sp.use_cyclic_u=cyclic;o=bpy.data.objects.new(name,cu);S.collection.objects.link(o);own(o,name,ma);activate(o);bpy.ops.object.convert(target='MESH')
  for p in o.data.polygons:p.use_smooth=True
  return o
 # Continuous independent rails seat into retained aperture edges; no stepped stubs.
 rows=[.292,.340,.391,.443,.495,.542,.585,.637]
 for i,z in enumerate(rows):box('Continuous front grille rail '+str(i),(-.1045,-.211,z),(.703,.015,.010),paint,.0011)
 for x in (-.310,.085):
  box('Grille welded vertical spine '+str(x),(x,-.198,.463),(.012,.014,.440),paint,.001)
  for z in (.252,.674):
   box('Spine mounting shoe '+str((x,z)),(x,-.196,z),(.028,.017,.026),paint,.001)
   cylinder('Spine fixing washer '+str((x,z)),(x,-.206,z),(x,-.204,z),.0085,steel,32)
   cylinder('Spine fixing M6 hex '+str((x,z)),(x,-.210,z),(x,-.2055,z),.006,steel,6)
   cylinder('Spine fixing M6 shaft '+str((x,z)),(x,-.207,z),(x,-.190,z),.003,steel,24)
 # A regular welded diamond-wire guard: open cells, clipped to a supported dish.
 cx=-.138;cz=.465;radius=.211
 # At the centre the guard is 38 mm behind the front rails; the edge is dished rearward.
 def surface(x,z):return -.173+.023*((x-cx)**2+(z-cz)**2)/(radius*radius)
 for family,angle in enumerate((math.pi/4,-math.pi/4)):
  u=np.array([math.cos(angle),math.sin(angle)]);v2=np.array([-u[1],u[0]])
  for index,offset in enumerate(np.arange(-.196,.1961,.014)):
   half=math.sqrt(radius*radius-offset*offset);length=2*half;segments=max(12,math.ceil(length/.006));points=[]
   for t in np.linspace(-half,half,segments+1):
    x,z=np.array([cx,cz])+v2*offset+u*t;points.append((float(x),surface(x,z),float(z)))
   wire('Regular guard mesh '+str(family)+' '+str(index),points,.0011)
 # Rolled perimeter conceals the original cut interface while maintaining open fan area.
 for rr,wire_r in ((.213,.0045),(.218,.0035)):
  wire('Rolled fan guard rim '+str(rr),[(cx+rr*math.cos(a),-.149,cz+rr*math.sin(a))for a in np.linspace(0,math.tau,192,endpoint=False)],wire_r,True,paint)
 # Four real guard supports to the rigid grille spines; electrical/fan parts stay behind.
 for side,xspine in ((-1,-.310),(1,.085)):
  for sign in (-1,1):
   gx=cx+side*.145;gz=cz+sign*.145
   box('Guard bracket to spine '+str((side,sign)),((gx+xspine)/2,-.188,gz),(abs(gx-xspine)+.019,.016,.018),paint,.001)
   cylinder('Guard standoff '+str((side,sign)),(gx,-.199,gz),(gx,surface(gx,gz)+.002,gz),.007,steel,32)
   cylinder('Guard isolation washer '+str((side,sign)),(gx,-.201,gz),(gx,-.198,gz),.009,rubber,32)
   cylinder('Guard M5 fixing '+str((side,sign)),(gx,-.205,gz),(gx,-.200,gz),.0055,steel,6)
 # Small supported central guard pad replaces the malformed fused original guard cap.
 cylinder('Fan guard centre weld pad',(cx,-.178,cz),(cx,-.170,cz),.029,paint,64)
 # Axial overlaps at the critic-identified interfaces, in metres. These meet on
 # their broad central faces, away from the small edge bevels.
 def overlap(a,b):return min(a[1],b[1])-max(a[0],b[0])
 jointProof={'railToSpine':overlap((-.2185,-.2035),(-.205,-.191)),
  'spineWasherToShoe':overlap((-.206,-.204),(-.2045,-.1875)),
  'spineHexToWasher':overlap((-.210,-.2055),(-.206,-.204)),
  'spineShaftToShoe':overlap((-.207,-.190),(-.2045,-.1875)),
  'guardWasherToStandoff':overlap((-.201,-.198),(-.199,-.149)),
  'guardHexToWasher':overlap((-.205,-.200),(-.201,-.198))}
 assert min(jointProof.values())>.00049,jointProof
 # Geometry audits: every old service mesh remains shared and at the same transform.
 bpy.context.view_layer.update()
 for row in service:
  q=bpy.data.objects[row['copyName']];assert q.data.name==row['sharedMesh'] and max(abs(q.matrix_world[i][j]-row['worldMatrix'][i][j])for i in range(4)for j in range(4))<1e-8
 checkco=np.empty_like(co);m.vertices.foreach_get('co',checkco.ravel());checktri=np.empty_like(tri);m.loops.foreach_get('vertex_index',checktri.ravel());assert hashlib.sha256(checkco.tobytes()+checktri.tobytes()).hexdigest()==oldmeshHash
 sourceNormalCheck=np.empty_like(normals);m.corner_normals.foreach_get('vector',sourceNormalCheck.ravel());assert hashlib.sha256(sourceNormalCheck.tobytes()).hexdigest()==oldNormalHash
 for layer,(name,a) in zip(m.uv_layers,uv):
  check=np.empty((len(m.loops),2),np.float32);layer.data.foreach_get('uv',check.ravel());assert hashlib.sha256(check.tobytes()).hexdigest()==oldUvHashes[name]
 for o in parts:o.data.calc_loop_triangles()
 O.mkdir();S['generator_core_repair_output']=str(O);S['generator_core_repair_original']=original.name;S['generator_core_repair_core']=core.name;S['generator_core_repair_mask']=selected.name;S['generator_core_repair_authored_collection']=A.name
 record={'revision':'generator-v4-source core repair audition','maskContract':contract,'originalCoreRecoveryObject':original.name,'removedMaskObject':selected.name,'retainedCoreObject':core.name,'subsets':subsetProof,'sourceOriginalGeometryAndUvUntouched':True,'outsideSelectedFaceIndicesUnchanged':True,'serviceGeometryFrozen':True,'serviceCopies':service,'authoredGuardObjects':[{'name':o.name,'triangles':len(o.data.loop_triangles)}for o in parts],'authoredGuardTriangles':sum(len(o.data.loop_triangles)for o in parts),'guard':{'centerXZ':[cx,cz],'openWireRadiusMetres':radius,'wireRadiusMetres':.0011,'diamondSpacingMetres':.014,'railRowsMetres':rows},'sourceAccepted':False,'nativeAccepted':False,'remaining':['Review original/selected/after front and guard oblique; inspect rear retained fragments and open fan clearance','Judge PBR/material matching; core panel grid is deliberately unchanged','Separate protected semantic panel operation','Source acceptance before near preparation'],'vertexStorageCaveat':'Subset meshes retain the original vertex array to preserve exact index/UV/corner correspondence; unused vertices are source recovery data and must be compacted on a separately audited runtime derivative.'}
 record['positiveJointOverlapsMetres']=jointProof
 (O/'core-repair-manifest.json').write_text(json.dumps(record,indent=2)+'\n');np.savez_compressed(O/'source-face-correspondence.npz',retainedSourceFaces=retained.astype(np.int32),removedSourceFaces=removed);bpy.data.libraries.write(str(O/'generator-v4-core-repair.blend'),{S},fake_user=True,path_remap='RELATIVE');print(json.dumps({'scene':S.name,'output':str(O),'retainedFaces':len(retained),'removedFaces':len(removed),'newGuardTriangles':record['authoredGuardTriangles'],'normalProof':subsetProof,'sourceAccepted':False}))
except Exception as error:
 import traceback
 O.mkdir(exist_ok=True)
 failure={'error':str(error),'traceback':traceback.format_exc(),'originalSourcePreserved':True,'action':'Inspect this failed source audition and resume narrowly; do not rerun over it.'}
 try:
  if globals().get('S'):bpy.data.libraries.write(str(O/'failed-core-repair-recovery.blend'),{S},fake_user=True,path_remap='RELATIVE')
 except Exception as saveError:failure['recoverySaveError']=str(saveError)
 (O/'failed-authoring.json').write_text(json.dumps(failure,indent=2)+'\n')
 raise
