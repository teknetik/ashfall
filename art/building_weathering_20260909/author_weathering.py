"""Execute through live Blender MCP. Weather the two exported Unity sources.
Original source assets and prefab transforms are retained. Metres, explicit axes.
"""
import bpy, bmesh, json, math, random
from pathlib import Path
from mathutils import Vector
R=Path('/home/teknetik/code/ao2'); O=R/'art/building_weathering_20260909'
assert not (O/'weathering-v1.blend').exists(), 'Preserve authored revisions.'
rows=json.loads((O/'unity-source.json').read_text()); rng=random.Random(909114)
scene=bpy.data.scenes.new('Ward Field Supply and Finery weathering v1')
bpy.context.window.scene=scene; scene.unit_settings.system='METRIC'
scene['purpose']='Accepted 9 September building-weathering concept, two existing facades'
M={}; refs={}; changed={}; additions=[]; decals=[]
def B(v):return Vector((v[0],-v[2],v[1]))
def U(v):return [round(v.x,6),round(v.z,6),round(-v.y,6)]
def material(key, desc=None, color=None, texture=None):
 if key in M:return M[key]
 m=bpy.data.materials.new('Wear '+key);m.use_nodes=True;bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.87
 if desc:
  color=desc['color'];texture=desc['baseMap']
 if color:bs.inputs['Base Color'].default_value=(*color,1)
 if texture:
  p=R/'unity/AthenHill'/texture
  if not p.exists():p=R/texture
  node=m.node_tree.nodes.new('ShaderNodeTexImage');node.image=bpy.data.images.load(str(p),check_existing=True)
  m.node_tree.links.new(node.outputs['Color'],bs.inputs['Base Color'])
 if desc and desc['normalMap']:
  n=m.node_tree.nodes.new('ShaderNodeTexImage');n.image=bpy.data.images.load(str(R/'unity/AthenHill'/desc['normalMap']),check_existing=True);n.image.colorspace_settings.name='Non-Color'
  nm=m.node_tree.nodes.new('ShaderNodeNormalMap');m.node_tree.links.new(n.outputs['Color'],nm.inputs['Color']);m.node_tree.links.new(nm.outputs['Normal'],bs.inputs['Normal'])
 m['unity_key']=key;M[key]=m;return m
for row in rows:
 desc=row['materials'][0];material(desc['path'],desc)
 me=bpy.data.meshes.new(row['name']);ii=row['indices'];me.from_pydata([B(v)for v in row['positions']],[],[(ii[i],ii[i+2],ii[i+1])for i in range(0,len(ii),3)]);me.update()
 uv=me.uv_layers.new(name='UV0 retained source')
 for l in me.loops:uv.data[l.index].uv=row['uv'][l.vertex_index]
 ob=bpy.data.objects.new(row['name'],me);scene.collection.objects.link(ob);me.materials.append(M[desc['path']]);ob['source_path']=row['path'];ob['family']=row['family'];refs[row['path']]=ob
 # Retain material tiling in Blender's review; exported source UV stays unchanged.
 ob['source_material_scale']=desc['mapScale'];ob['reference_only']=True
byname={r['name']:r for r in rows}
shared=lambda n:next(r['materials'][0]for r in rows if r['materials'][0]['name']==n)
material('ExposedStone',shared('WardStone'));material('OxideRust',shared('WardWornSteel'))
material('CrackDust',color=(.15,.115,.075));material('DryBlood',color=(.105,.023,.017))
material('Karaveen',texture='refs/courtyard_20260908/karaveen-poster-v1.png')
material('Paper',texture='refs/courtyard_20260908/karaveen-poster-v1.png')
material('Warden',texture='refs/courtyard_20260908/ward-banner-v1.png')
material('Graffiti',texture='unity/AthenHill/Assets/AthenHill/Art/Courtyard/Textures/FactoryGraffiti.png')

def mesh(name,ps,faces,key,uvs=None,family='field_supply',smooth=False):
 me=bpy.data.meshes.new(name);me.from_pydata([B(p)for p in ps],[],faces);me.update()
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 ob=bpy.data.objects.new(name,me);scene.collection.objects.link(ob);me.materials.append(M[key]);ob['family']=family;ob['material_key']=key;ob['reference_only']=False;additions.append(ob)
 uv=me.uv_layers.new(name='UV0 material metres')
 for face in me.polygons:
  axis=max(range(3),key=lambda k:abs(face.normal[k]));face.use_smooth=smooth
  for li in face.loop_indices:
   vi=me.loops[li].vertex_index;p=me.vertices[vi].co
   uv.data[li].uv=uvs[vi] if uvs else ((p.y if axis==0 else p.x)/2,(p.y if axis==2 else p.z)/2)
 return ob
def prism(name,center,u,n,polygon,front,back,key,family):
 c=Vector(center);u=Vector(u);n=Vector(n);v=Vector((0,1,0));k=len(polygon)
 ps=[c+u*x+v*y+n*d for d in [front,back]for x,y in polygon]
 faces=[tuple(range(k)),tuple(range(k,2*k))]+[(i,(i+1)%k,(i+1)%k+k,i+k)for i in range(k)]
 return mesh(name,ps,faces,key,family=family)
def outline(w,h,count=22):
 return [(math.cos(2*math.pi*i/count)*w*.5*rng.uniform(.74,1.08),math.sin(2*math.pi*i/count)*h*.5*rng.uniform(.72,1.07))for i in range(count)]
def damage(name,center,w,h,n=(-1,0,0),u=(0,0,-1)):
 row=byname[name];ob=refs[row['path']];poly=outline(w,h);key=row['materials'][0]['path']
 cut=prism('temporary plaster cutter',center,u,n,poly,.12,-.045,key,row['family'])
 bpy.context.view_layer.objects.active=ob
 mod=ob.modifiers.new('Localized missing plaster depth','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut
 bpy.ops.object.modifier_apply(modifier=mod.name);additions.remove(cut);bpy.data.objects.remove(cut,do_unlink=True)
 changed[row['path']]=ob;ob['reference_only']=False;ob['change']='Shallow irregular plaster spall; structure retained'
 # Rough mineral substrate lies behind a true 45mm cut, slightly inside boundary.
 prism(name+' exposed substrate '+str(len(additions)),center,u,n,[(x*.982,y*.982)for x,y in poly],-.044,-.049,'ExposedStone',row['family'])
 # Small adhered fragments along the broken boundary avoid a smooth cookie edge.
 for j in range(0,len(poly),3):
  x,y=poly[j];p=Vector(center)+Vector(u)*x*.98+Vector((0,1,0))*y*.98
  prism('Clinging plaster flake '+str(len(additions)),p,u,n,outline(.055,.07,6),.006,-.012,key,row['family'])

# Intentionally place damage at joints, thresholds and exposed roof edges.
for name,c,w,h in [
 ('field_supply Front gable',(17.75,5.13,-7.1),1.35,.33),
 ('field_supply Front gable',(17.75,5.21,-10.4),.65,.48),
 ('field_supply Front masonry segment 4 0',(17.87,.83,-12.02),.87,.55),
 ('field_supply Front masonry segment 4 0',(17.87,2.48,-11.73),.72,.40),
 ('field_supply Front masonry segment 4 2',(17.87,4.30,-11.25),.62,.68),
 ('field_supply Front masonry segment 3 2',(17.87,3.41,-9.85),.91,.31),
 ('field_supply Front masonry segment 1 2',(17.87,4.46,-6.22),.46,.58),
 ('Sign fascia',(16.8,4.62,-16.43),.92,.59),
 ('Sign fascia',(16.8,4.30,-20.65),.73,.41),
 ('Lower wall pier 1',(16.8,1.28,-19.43),.52,.41),
 ('Lower wall pier 2',(16.8,2.48,-16.55),.55,.56),
 ('Upper wall pier 1',(16.8,6.31,-19.48),.53,.57),
 ('Upper wall pier 2',(16.8,5.52,-16.72),.52,.39),
 ('Roof parapet end 16.84',(16.715,7.56,-17.3),1.07,.31),
 ('Roof parapet end 16.84',(16.715,7.31,-20.4),.65,.30)]:damage(name,c,w,h)
for name,c,w,h,n,u in [
 ('North wall core',(18.8,5.82,-14.2),1.3,1.1,(0,0,1),(1,0,0)),
 ('North wall core',(20.25,3.23,-14.2),1.1,.86,(0,0,1),(1,0,0)),
 ('North wall core',(17.5,.87,-14.2),1.0,.5,(0,0,1),(1,0,0)),
 ('South wall core',(20.5,1.1,-21.8),1.2,.7,(0,0,-1),(-1,0,0)),
 ('field_supply Full wall return 3.66',(19.2,3.9,-12.8),1.3,.8,(0,0,-1),(-1,0,0)),
 ('field_supply Full wall return 3.66',(22.1,.79,-12.8),1.25,.51,(0,0,-1),(-1,0,0)),
 ('field_supply Full wall return -3.66',(20.7,1.2,-5.2),.95,.8,(0,0,1),(1,0,0))]:damage(name,c,w,h,n,u)

def ribbon(name,points,width,key,n=(-1,0,0),family='field_supply'):
 ps=[];n=Vector(n)
 for i,p in enumerate(points):
  d=Vector(points[min(i+1,len(points)-1)])-Vector(points[max(0,i-1)])
  side=d.cross(n).normalized();w=width*rng.uniform(.4,1)*(1-.60*i/len(points))
  ps.extend([Vector(p)-side*w*.5,Vector(p)+side*w*.5])
 return mesh(name,ps,[(i*2,i*2+1,i*2+3,i*2+2)for i in range(len(points)-1)],key,family=family)

# Fractures branch from the spalls and reveal corners; modest width in metres.
for c,path in [((17.866,0,0),[(-11.9,2.69),(-11.75,2.97),(-11.79,3.12),(-11.52,3.37),(-11.47,3.65)]),
 ((17.746,0,0),[(-10.4,5.32),(-10.13,5.51),(-9.87,5.48)]),
 ((16.796,0,0),[(-19.52,6.53),(-19.61,6.21),(-19.42,6.0),(-19.47,5.66)]),
 ((16.796,0,0),[(-16.6,4.74),(-16.81,4.48),(-16.92,4.32),(-16.88,4.04)]),
 ((16.711,0,0),[(-17.45,7.73),(-17.61,7.53),(-17.78,7.45),(-17.81,7.2)])]:
 family='field_supply'if c[0]>17 else'finery';points=[(c[0],y,z)for z,y in path]
 ribbon('Hairline fracture '+str(len(additions)),points,.018,'CrackDust',family=family)
 p=points[1];ribbon('Fracture branch '+str(len(additions)),[p,(p[0],p[1]+.06,p[2]-.13),(p[0],p[1]+.08,p[2]-.29)],.009,'CrackDust',family=family)
for x,y,z in [(18.7,6.2,-14.195),(20.0,3.8,-14.195),(19.1,4.4,-12.805)]:
 pts=[(x,y,z),(x+.11,y-.22,z),(x+.02,y-.51,z),(x+.26,y-.75,z),(x+.22,y-1.05,z)]
 ribbon('Side wall fracture '+str(len(additions)),pts,.018,'CrackDust',(0,0,1),'finery'if z<-14 else'field_supply')

# Remove small real corner volumes from selected masonry, leaving most courses intact.
stoneRows=[r for r in rows if r['materials'][0]['name'] in ['WardStone','Finery cut stone']and r['bounds']['min'][0]<18.25 and r['bounds']['min'][1]<4]
for i,row in enumerate(stoneRows):
 if i%5!=2:continue
 ob=refs[row['path']];lo=row['bounds']['min'];hi=row['bounds']['max']
 if min(hi[k]-lo[k]for k in range(3))<.1:continue
 c=(lo[0]+.025,lo[1]+.025,lo[2]+.02);bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=1,location=B(c));cut=bpy.context.object
 cut.scale=(rng.uniform(.07,.13),rng.uniform(.07,.15),rng.uniform(.05,.105));bpy.context.view_layer.objects.active=ob
 mod=ob.modifiers.new('Chipped exposed stone corner','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut
 bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cut,do_unlink=True);changed[row['path']]=ob;ob['reference_only']=False

# Localised exposed rust along shutter slat edges and lower contact areas.
for row in rows:
 if 'Rolled shutter slat'not in row['name']:continue
 lo=row['bounds']['min'];hi=row['bounds']['max'];y=(lo[1]+hi[1])/2
 for j in range(3 if y<1.2 else 2):
  z=rng.uniform(lo[2]+.15,hi[2]-.15);w=rng.uniform(.12,.43);h=rng.uniform(.016,.045)
  prism('Shutter flaked coating '+str(len(additions)),(lo[0]-.004,y+rng.uniform(-.028,.028),z),(0,0,-1),(-1,0,0),outline(w,h,12),.001,-.001,'OxideRust','field_supply')

def paper(name,c,w,h,key,family,turn=0,seed=0):
 # Mapped paper mesh with ragged perimeter, curled tips and fine undulation.
 rr=random.Random(seed);nx=12;ny=16;ps=[];uvs=[];faces=[];u=Vector((0,0,-1));n=Vector((-1,0,0));c=Vector(c)
 for j in range(ny+1):
  for i in range(nx+1):
   a=i/nx;b=j/ny;x=(a-.5)*w;y=(b-.5)*h
   if i in [0,nx]:x+=rr.uniform(-.023,.023)
   if j in [0,ny]:y+=rr.uniform(-.025,.025)
   if j==0 and i%4==0:y+=rr.uniform(.015,.06)
   edge=max(abs(a-.5)*2,abs(b-.5)*2)
   curl=.002*math.sin(a*16+b*11)+max(0,edge-.80)**2*.8
   if i>nx-2 and j>ny-3:curl+=.045*((i-(nx-2))/2)*((j-(ny-3))/3)
   xx=x*math.cos(turn)-y*math.sin(turn);yy=x*math.sin(turn)+y*math.cos(turn)
   ps.append(c+u*xx+Vector((0,yy,0))+n*curl);uvs.append((a,b if key!='Warden'else .065+b*.935))
 for j in range(ny):
  for i in range(nx):
   if j==0 and i in [1,6,10]:continue
   a=j*(nx+1)+i;faces.append((a,a+1,a+nx+2,a+nx+1))
 return mesh(name,ps,faces,key,uvs,family,smooth=True)
paper('Old paste layer field',(17.861,1.85,-11.59),.87,1.11,'Paper','field_supply',-.055,2)
paper('Karaveen delivery poster field',(17.849,1.86,-11.59),.77,1.027,'Karaveen','field_supply',.014,7)
paper('Warden watch paper',(16.791,1.91,-19.41),.48,1.18,'Warden','finery',-.03,4)
for j,(x,y,z)in enumerate([(17.856,.91,-11.0),(17.853,2.72,-12.10),(16.79,1.35,-16.5)]):paper('Torn old notice '+str(j),(x,y,z),.22,.28,'Paper','field_supply'if x>17 else'finery',rng.uniform(-.25,.25),j+31)

# Graffiti follows separate shutter slats; alpha gaps stay transparent in Unity.
graffiti_rows=[r for r in rows if 'Rolled shutter slat' in r['name']]
for row in graffiti_rows:
 lo=row['bounds']['min'];hi=row['bounds']['max'];a=max(1.42,lo[1]);b=min(2.69,hi[1])
 if b<=a:continue
 z0=-7.66;z1=-10.31;xx=lo[0]-.006
 mesh('Factory graffiti '+row['name'],[(xx,a,z0),(xx,a,z1),(xx,b,z1),(xx,b,z0)],[(0,1,2,3)],'Graffiti',[(0,(a-1.42)/1.27),(1,(a-1.42)/1.27),(1,(b-1.42)/1.27),(0,(b-1.42)/1.27)])

# Restrained old dried blood traces: tiny irregular surface marks, no large pool.
for j in range(15):
 y=rng.uniform(.61,1.22);z=rng.uniform(-18.95,-18.87)
 prism('Old blood wall speck '+str(j),(16.554,y,z),(0,0,-1),(-1,0,0),outline(rng.uniform(.006,.025),rng.uniform(.01,.06),7),.001,0,'DryBlood','finery')
for j in range(17):
 x=rng.uniform(15.6,16.5);z=rng.uniform(-18.92,-18.5);rad=rng.uniform(.007,.023);c=Vector((x,.505,z))
 ps=[c+Vector((math.cos(k*math.tau/9)*rad*rng.uniform(.6,1.2),0,math.sin(k*math.tau/9)*rad*rng.uniform(.7,1.1)))for k in range(9)]
 mesh('Old blood threshold fleck '+str(j),ps,[tuple(range(9))],'DryBlood',family='finery')

# Small fallen chips only at wall toes, below damaged regions.
for family,c in [('field_supply',(17.46,.53,-11.96)),('finery',(16.42,.53,-19.50)),('finery',(18.67,.045,-14.0))]:
 for j in range(8):
  p=Vector(c)+Vector((rng.uniform(-.18,.18),0,rng.uniform(-.30,.30)));bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=1,location=B(p));ob=bpy.context.object
  ob.name='Fallen masonry chip '+str(len(additions));ob.scale=(rng.uniform(.025,.07),rng.uniform(.025,.08),rng.uniform(.012,.035));ob.data.materials.append(M['ExposedStone']);ob['family']=family;ob['material_key']='ExposedStone';ob['reference_only']=False;additions.append(ob)
  uv=ob.data.uv_layers.new(name='UV0 material');
  for l in ob.data.loops:uv.data[l.index].uv=(ob.data.vertices[l.vertex_index].co.x,ob.data.vertices[l.vertex_index].co.y)

def decal(name,p,size,tile,opacity,n,depth=.09):decals.append(dict(name=name,position=p,size=size,tile=tile,opacity=opacity,direction=n,depth=depth))
for x,y,z,w,h in [(17.83,4.52,-6.0,.70,1.0),(17.83,4.29,-10.90,.49,1.3),(17.72,5.0,-7.1,.46,.6),(16.69,7.25,-17.4,.67,1.0),(16.69,7.27,-20.4,.54,.95),(16.77,4.51,-16.58,.65,.7),(16.57,5.42,-19.2,.40,.9)]:decal('Roof and sill runoff '+str(len(decals)),[x,y,z],[w,h],3,.63,[1,0,0],.30)
for x,z,w in [(17.85,-11.75,1.65),(17.84,-6.6,.65),(16.72,-19.40,.75),(16.73,-16.60,.65)]:decal('Foundation grime '+str(len(decals)),[x,.76,z],[w,.52],1,.62,[1,0,0],.32)
for x,z in [(17.46,-11.92),(16.2,-19.30),(18.7,-14.02)]:decal('Sheltered sand '+str(len(decals)),[x,.53 if x<18 else .04,z],[.9,.45],0,.65,[0,-1,0],.075)
for x,y,z,w,h in [(18.9,5.9,-14.16,1.2,1.7),(20.7,2.0,-14.16,.7,2.6),(21.8,2.2,-12.83,.9,3.1)]:decal('Side drainage '+str(len(decals)),[x,y,z],[w,h],3,.56,[0,0,-1]if z<-14 else[0,0,1],.15)

def export(ob,source=None):
 deps=bpy.context.evaluated_depsgraph_get();ev=ob.evaluated_get(deps);me=ev.to_mesh();me.calc_loop_triangles();uv=me.uv_layers.active
 pos=[];ns=[];us=[];indices=[];normalmatrix=ob.matrix_world.to_3x3().inverted().transposed()
 for tri in me.loop_triangles:
  base=len(pos)
  for li in tri.loops:
   l=me.loops[li];pos.append(U(ob.matrix_world@me.vertices[l.vertex_index].co));ns.append(U((normalmatrix@me.corner_normals[li].vector).normalized()));us.append(list(uv.data[li].uv)if uv else[0,0])
  indices.extend([base,base+2,base+1])
 ev.to_mesh_clear()
 return dict(name=ob.name,family=ob.get('family'),sourcePath=source,material=ob.get('material_key',''),positions=pos,normals=ns,uv=us,indices=indices,castsShadow=ob.get('material_key')not in ['Graffiti','DryBlood','OxideRust','CrackDust'])
output=[export(ob,path)for path,ob in changed.items()]+[export(ob)for ob in additions]
(O/'weathering-meshes-v1.json').write_text(json.dumps(output,separators=(',',':')))
(O/'weathering-decals-v1.json').write_text(json.dumps(decals,indent=2))
(O/'manifest-v1.json').write_text(json.dumps(dict(blender=bpy.app.version_string,replacements=len(changed),additions=len(additions),triangles=sum(len(o['indices'])//3 for o in output),decals=len(decals),coordinates='Unity world -> Blender (x,-z,y); reverse triangle winding at import and export',materials={k:v.get('unity_key')for k,v in M.items()},originalMeshesRetained=True,concept='refs/building_weathering_20260909/weathering-concept-v1.png'),indent=2))
scene.render.engine='BLENDER_EEVEE_NEXT';scene.render.resolution_x=1600;scene.render.resolution_y=1000;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
scene.world=bpy.data.worlds.new('Ward review sky');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.32,.40,.5,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.6
ld=bpy.data.lights.new('Review sunlight','SUN');ld.energy=2.5;ld.angle=.04;light=bpy.data.objects.new('Review sunlight',ld);scene.collection.objects.link(light);light.rotation_euler=(.5,-.6,-.7)
cd=bpy.data.cameras.new('Weathering source review');cam=bpy.data.objects.new('Weathering source review',cd);scene.collection.objects.link(cam);scene.camera=cam;cd.lens=46
cam.location=B((4.0,7.0,-4.0));cam.rotation_euler=(B((18.5,3.6,-13.0))-cam.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.wm.save_as_mainfile(filepath=str(O/'weathering-v1.blend'))
scene.render.filepath=str(O/'source-review-v1.png');bpy.ops.render.render(write_still=True)
print(json.dumps(dict(changed=len(changed),new=len(additions),triangles=sum(len(o['indices'])//3 for o in output),decals=len(decals))))
