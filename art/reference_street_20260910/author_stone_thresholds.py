"""Live Blender authoring: individually settled mineral threshold stones.

Preserves the four existing platform/step renderer identities and collider
envelopes. Original source is retained; this is geometry, not a runtime builder.
"""
import bpy,bmesh,json,math,random
from pathlib import Path
from mathutils import Vector,noise
R=Path('/home/teknetik/code/ao2');O=R/'art/reference_street_20260910'
assert not (O/'stone-thresholds-v1.blend').exists(),'Preserve earlier source'
S=bpy.data.scenes.new('Individually settled street thresholds v1');bpy.context.window.scene=S
S.unit_settings.system='METRIC';rng=random.Random(910826)
rows=json.loads((R/'art/reference_street_20260909/threshold-source.json').read_text())
parts=[];sources=[]
def B(p):return Vector((p[0],-p[2],p[1]))
def U(p):return [round(p.x,6),round(p.z,6),round(-p.y,6)]
def own(ob):
 for c in list(ob.users_collection):c.objects.unlink(ob)
 S.collection.objects.link(ob);return ob
def active(ob):
 for p in bpy.context.selected_objects:p.select_set(False)
 ob.select_set(True);bpy.context.view_layer.objects.active=ob
def mat(name,color):
 m=bpy.data.materials.new(name);m.use_nodes=True;bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=.9
 return m
M={n:mat(n,c) for n,c in [('ThresholdStone',(.44,.37,.29)),('ThresholdMortar',(.27,.23,.18)),('ThresholdGrit',(.39,.32,.24))]}
def box(name,lo,hi,material,detail=True,seed=0):
 center=(Vector(lo)+Vector(hi))*.5;size=Vector(hi)-Vector(lo)
 bpy.ops.mesh.primitive_cube_add(size=1,location=B(center));ob=own(bpy.context.object);ob.name=name
 ob.dimensions=(size.x,size.z,size.y);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 if detail:
  be=ob.modifiers.new('Small varied mineral arris','BEVEL');be.width=.011+rng.random()*.010;be.segments=3
  bpy.ops.object.modifier_apply(modifier=be.name)
  su=ob.modifiers.new('Surface sampling for physical abrasion','SUBSURF');su.subdivision_type='SIMPLE';su.levels=2
  bpy.ops.object.modifier_apply(modifier=su.name)
  # Coherent minute surface relief plus distinctly greater erosion at exposed arrises.
  hx,hy,hz=size.x/2,size.z/2,size.y/2
  for v in ob.data.vertices:
   q=v.co;nx=abs(q.x)/hx;ny=abs(q.y)/hy;nz=abs(q.z)/hz
   edge=max(0,min(nx,ny)-.82)/.18
   a=noise.noise_vector(q*14+Vector((seed,seed*.7,seed*.3)))
   q.x+=a.x*(.0015+.006*max(edge,max(0,nz-.9)*5))
   q.y+=a.y*(.0015+.006*max(edge,max(0,nz-.9)*5))
   if q.z>0:q.z+=a.z*.0025-max(0,noise.noise(q*11+Vector((seed,0,0))))*.025*edge
  ob.data.update()
 ob.data.materials.append(M[material]);ob['material_key']=material
 return ob
def chip(ob,c,size,seed):
 bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2,radius=1,location=B(c));cut=own(bpy.context.object)
 for v in cut.data.vertices:
  q=v.co;q*=1+.17*math.sin(q.x*7+q.z*4+seed)+.08*math.sin(q.y*17+q.z*8)
 cut.scale=(size[0],size[2],size[1]);active(ob)
 mod=ob.modifiers.new('Open fracture across exposed arris','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut
 bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cut,do_unlink=True)
def uv_shade(ob):
 me=ob.data;bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000005);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();me.update()
 uv=me.uv_layers.new(name='UV0 two metre mineral scale');offset=Vector((rng.random()*2,rng.random()*2))
 for f in me.polygons:
  # Planes retain face definition; curved fractured borders get shared normals.
  n=f.normal;axis=max(range(3),key=lambda k:abs(n[k]));f.use_smooth=max(abs(n[k]) for k in range(3))<.98
  for li in f.loop_indices:
   q=ob.matrix_world@me.vertices[me.loops[li].vertex_index].co
   a,b=(q.y,q.z) if axis==0 else ((q.x,q.z) if axis==1 else (q.x,q.y))
   uv.data[li].uv=(a/2+offset.x,b/2+offset.y)
def export(ob,path=None,name=None):
 uv_shade(ob);me=ob.data;me.calc_loop_triangles();p=[];n=[];u=[];ii=[]
 for t in me.loop_triangles:
  for li in t.loops:
   p.append(U(ob.matrix_world@me.vertices[me.loops[li].vertex_index].co));n.append(U(ob.matrix_world.to_3x3()@me.corner_normals[li].vector));u.append(list(me.uv_layers.active.data[li].uv));ii.append(len(ii))
 parts.append(dict(name=name or ob.name,sourcePath=path,material=ob['material_key'],positions=p,normals=n,uv=u,indices=ii,castsShadow=True))
def join(obs,name):
 for ob in bpy.context.selected_objects:ob.select_set(False)
 for ob in obs:ob.select_set(True)
 bpy.context.view_layer.objects.active=obs[0];bpy.ops.object.join();ob=obs[0];ob.name=name;return ob
for row in rows:
 name=row['name'];lo=Vector([min(p[k] for p in row['positions']) for k in range(3)]);hi=Vector([max(p[k] for p in row['positions']) for k in range(3)])
 path=row.get('sourcePath',row['path']);porch='porch' in name;field='w_02' in name
 faceEnd=(17.91 if field else 16.48) if porch else hi.x
 bands=[lo.x]
 count=3 if porch and field else (2 if porch else 1)
 for k in range(1,count):bands.append(lo.x+(faceEnd-lo.x)*k/count+rng.uniform(-.07,.07))
 bands.append(faceEnd);stones=[]
 for band in range(count):
  cuts=[lo.z];z=lo.z
  while z<hi.z-.55:
   z=min(hi.z,z+rng.uniform(.75,1.18))
   if hi.z-z<.46:z=hi.z
   cuts.append(z)
  if cuts[-1]<hi.z:cuts.append(hi.z)
  for j,(za,zb) in enumerate(zip(cuts,cuts[1:])):
   xl=bands[band]+(.008 if band else 0);xh=bands[band+1]-.008
   ytop=hi.y+rng.uniform(-.004,.002);a=(xl,lo.y,za+.009);b=(xh,ytop,zb-.009)
   ob=box(name+' stone %02d-%02d'%(band,j),a,b,'ThresholdStone',True,rng.random()*99)
   if band==0:
    # Irregular losses connect top/riser at selected corners and old impact sites.
    for q in range(1+(j%3==1)):
     cz=(za+.018 if q==0 and j%2==0 else rng.uniform(za+.10,zb-.10))
     chip(ob,(lo.x+.012,ytop+.012,cz),(.045+rng.random()*.04,.026+rng.random()*.045,.055+rng.random()*.095),j*13+q)
   stones.append(ob)
 if porch:
  # The remainder stays beneath the unchanged building shell; no new obstacles.
  stones.append(box(name+' retained covered platform core',(faceEnd+.003,lo.y,lo.z),(hi.x,hi.y,hi.z),'ThresholdStone',False))
 ob=join(stones,name+' individually laid stone');export(ob,path,name)
 bed=box(name+' recessed joint mortar',(lo.x+.009,lo.y+.005,lo.z+.005),(hi.x-.005,hi.y-.021,hi.z-.005),'ThresholdMortar',False);export(bed)
 sources.append(dict(path=path,originalMesh='Retained in before-scene.unity and threshold-source.json',bounds=[list(lo),list(hi)],stones=len(stones),topDeviationMetres=[-.006,.004],colliderChanges=False))
 # Fracture chips collect below risers and at seam ends, kept out of tread centres.
 for j in range(10 if porch else 4):
  z=rng.uniform(lo.z+.1,hi.z-.1);x=lo.x-rng.uniform(.03,.20)
  floor=0.0
  # First step occupies the middle front of each porch; use its top for contact.
  if porch and ((-11.1<z<-6.9) if field else (-20.1<z<-15.9)):floor=.25
  size=(rng.uniform(.035,.10),rng.uniform(.012,.035),rng.uniform(.04,.12))
  ob=box(name+' settled mineral chip '+str(j),(x-size[0]/2,floor-.003,z-size[2]/2),(x+size[0]/2,floor+size[1],z+size[2]/2),'ThresholdGrit',True,j+10)
  export(ob)
(O/'stone-threshold-meshes-v1.json').write_text(json.dumps(parts,separators=(',',':')))
(O/'stone-threshold-manifest-v1.json').write_text(json.dumps(dict(replacements=sources,parts=len(parts),triangles=sum(len(p['indices'])//3 for p in parts),sourceBlend='stone-thresholds-v1.blend',uvMetres=2,materialSource='retained 4k sandstone_cracks or rock_surface with linear normal/smoothness packing',oldGritToRetire='Previous ReferenceStreet 36 low-detail grit pieces; exact paths checked at installation',preserveColliders=True),indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(O/'stone-thresholds-v1.blend'))
print(json.dumps(dict(parts=len(parts),triangles=sum(len(p['indices'])//3 for p in parts))))
