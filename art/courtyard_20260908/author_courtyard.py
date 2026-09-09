"""Original courtyard assets, executed through the live Blender MCP connection.

Author coordinates are Unity metres. B maps them into Blender's Z-up frame.
The saved blend and FBX preserve authoring geometry; mesh-data.json is an explicit
normal/UV-preserving interchange for Unity, with one editable object per part.
"""
import bpy, math, random, json, pathlib
from mathutils import Vector, noise

ROOT=pathlib.Path('/home/teknetik/code/ao2')
OUT=ROOT/'art/courtyard_20260908'
OUT.mkdir(exist_ok=True)
rng=random.Random(908261)
old=bpy.data.collections.get('Ward courtyard authored')
if old:
    for o in list(old.objects):bpy.data.objects.remove(o,do_unlink=True)
    bpy.data.collections.remove(old)
coll=bpy.data.collections.new('Ward courtyard authored');bpy.context.scene.collection.children.link(coll)
def B(p):return Vector((p[0],-p[2],p[1]))
def U(p):return [round(p[0],6),round(p[2],6),round(-p[1],6)]
def own(o,name,group):
    o.name=name
    for c in list(o.users_collection):c.objects.unlink(o)
    coll.objects.link(o);o['group']=group
    return o
def mat(name,color):
    m=bpy.data.materials.get('CW '+name) or bpy.data.materials.new('CW '+name)
    m.diffuse_color=(*color,1);m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=.9
    return m
M={}
for name,color in {'Stone0':(.54,.43,.30),'Stone1':(.62,.51,.37),'Stone2':(.46,.38,.29),'Stone3':(.58,.49,.38),'Sand':(.65,.50,.30),'Mortar':(.34,.29,.22),'Iron':(.12,.095,.075),'Brass':(.35,.23,.12),'Canvas':(.31,.068,.037),'CanvasPatch':(.46,.16,.08),'Rope':(.30,.25,.16),'Straw0':(.43,.31,.14),'Straw1':(.61,.46,.22),'Straw2':(.29,.25,.13),'Leaf':(.28,.33,.12),'Paper':(.59,.49,.32),'Karaveen':(.63,.42,.12),'Warden':(.43,.075,.043),'Graffiti':(.10,.085,.07),'Drum':(.34,.24,.15)}.items():M[name]=mat(name,color)

def mesh(name,vs,fs,material,group,uvs=None):
    me=bpy.data.meshes.new(name);me.from_pydata([B(v) for v in vs],[],fs);me.update()
    o=bpy.data.objects.new(name,me);coll.objects.link(o);o['group']=group;me.materials.append(M[material])
    if uvs:
        uv=me.uv_layers.new()
        for poly in me.polygons:
            for i in poly.loop_indices:uv.data[i].uv=uvs[me.loops[i].vertex_index]
    else:project_uv(o)
    return o
def project_uv(o,scale=.8):
    me=o.data;uv=me.uv_layers.active or me.uv_layers.new()
    offset=Vector((rng.random()*3,rng.random()*3))
    for p in me.polygons:
        n=p.normal;axis=max(range(3),key=lambda i:abs(n[i]))
        for i in p.loop_indices:
            v=me.vertices[me.loops[i].vertex_index].co
            uv.data[i].uv=Vector(((v.y if axis==0 else v.x)*scale,(v.y if axis==2 else v.z)*scale))+offset

def stone(name,center,size,group='Stonework',severity=1,material=None):
    bpy.ops.mesh.primitive_cube_add(size=1,location=B(center));o=own(bpy.context.object,name,group)
    o.dimensions=(size[0],size[2],size[1]);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    be=o.modifiers.new('Rounded chipped arrises','BEVEL');be.width=min(.033*severity,min(size)*.17);be.segments=3
    bpy.ops.object.modifier_apply(modifier=be.name)
    su=o.modifiers.new('Local erosion geometry','SUBSURF');su.subdivision_type='SIMPLE';su.levels=2
    bpy.ops.object.modifier_apply(modifier=su.name)
    sx,sz,sy=size[0]/2,size[2]/2,size[1]/2
    seed=rng.random()*100
    for v in o.data.vertices:
        q=v.co;near=max(abs(q.x)/sx,abs(q.y)/sz)
        edge=min(1,max(0,(near-.80)*5))
        n=noise.noise_vector(q*17+Vector((seed,seed*.2,seed*.7)))
        # Surface relief is millimetres; larger wear remains concentrated on edges.
        q.x+=n.x*(.002+.009*edge)*severity;q.y+=n.y*(.002+.009*edge)*severity
        q.z+=n.z*.0025*severity
        if q.z>sy*.6:q.z-=max(0,noise.noise(q*9+Vector((seed,0,0)))-.12)*.027*edge*severity
    o.data.update();o.data.materials.append(M[material or ('Stone'+str(rng.randrange(4)))])
    project_uv(o,.65)
    for p in o.data.polygons:p.use_smooth=True
    wn=o.modifiers.new('Face-weighted stone normals','WEIGHTED_NORMAL');wn.keep_sharp=True;wn.weight=40
    bpy.ops.object.modifier_apply(modifier=wn.name)
    return o

# Platform remains inside the established 7 x 3.5 m collision footprint.
# Irregular slab widths and staggered joints avoid a new checkerboard installation.
for row in range(4):
    cuts=[4.5]+[4.5+j+rng.uniform(-.18,.18) for j in range(1,7)]+[11.5]
    for col in range(7):
        lo,hi=cuts[col:col+2]
        stone(f'Platform paver {row:02d}-{col:02d}',((lo+hi)/2,.117+rng.uniform(-.004,.004),-14.3125+row*.875),(hi-lo-.024,.26,.851),'Platform',1.5)
stone('Platform recessed mortar core',(8,.07,-13),(6.96,.16,3.46),'Platform',.2,'Mortar')
# A light relief sits over the retained flat collider and original paving.
for row in range(15):
    z=-22.5+row
    for col in range(14):
        x=2.5+col+(row%2)*.37
        if 4.0<x<12.0 and -15.2<z<-10.8:continue
        if x>13.1 and ((-21.9<z<-14.0) or z>-12.9):continue
        stone(f'Courtyard paving {row:02d}-{col:02d}',(x,-.022+rng.uniform(-.004,.004),z),(rng.uniform(.942,.977),.104,rng.uniform(.942,.972)),'Paving',.95)
for s in range(6):
    z=-10.3+s*.6;h=(s+1)*.25
    for j in range(4):stone(f'North stair {s}-{j}',(-1.5+j,h/2,z),(.975,h,.595),'North stairs',1.0)
for j in range(5):stone(f'Shop approach tread {j}',(14.1,.123,-19.68+j*.84),(.795,.25,.825),'Shop threshold',1)

# Sand lips are shallow three-dimensional fans with irregular, tapering margins.
def drift(name,center,width,length,height,yaw=0):
    vs=[];fs=[];nx,ny=36,12;angle=math.radians(yaw);seed=rng.random()*99
    for j in range(ny+1):
        v=j/ny
        for i in range(nx+1):
            u=i/nx;along=(u-.5)*length;across=(v-.5)*width
            edge=math.sin(math.pi*u)**1.4*math.sin(math.pi*v)**2.2
            irregular=.76+.24*math.sin(u*17+seed)+.18*math.sin(v*13+u*25)
            cross=across*(.8+.28*math.sin(u*16+seed))+.07*math.sin(u*11+seed)
            x=along*math.cos(angle)-cross*math.sin(angle);z=along*math.sin(angle)+cross*math.cos(angle)
            y=height*edge*irregular+edge*.004*math.sin(along*21+across*34)-.006
            vs.append((center[0]+x,center[1]+y,center[2]+z))
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i;fs.extend([(a,a+nx+1,a+1),(a+1,a+nx+1,a+nx+2)])
    o=mesh(name,vs,fs,'Sand','Sand deposits')
    for p in o.data.polygons:p.use_smooth=True
    return o
for i,(x,length,width,height) in enumerate([(4.95,1.1,.63,.065),(6.15,1.15,.46,.036),(8.95,1.6,.61,.057),(10.85,1.4,.77,.073)]):
    drift('Front sheltered sand fan '+str(i),(x,0,-11.13),width,length,height,rng.uniform(-5,5))
for i,(x,length) in enumerate([(5.1,1.9),(7.5,1.3),(10.55,2.0)]):
    drift('Rear sheltered sand fan '+str(i),(x,0,-14.84),.79,length,.069)
drift('Sand at platform west',(4.40,0,-14.0),.70,1.6,.077,90)
drift('Sand at platform east',(11.63,0,-12.8),.78,1.65,.067,90)
for x in [6,8,10]:
    drift('Terminal sheltered sand '+str(x),(x,.25,-14.35),.58,1.38,.052)
    drift('Terminal joint grit '+str(x),(x+.57,.25,-13.82),.33,.8,.027,90)
for s in range(6):
    for x in [-1.8,1.8]:drift(f'Stair deposit {s} {x}',(x,(s+1)*.25,-10.38+s*.6),.35,.50,.035,90)
drift('Threshold sheltered sand',(13.65,0,-19.8),.65,1.5,.075,90)
drift('Threshold leeward sand',(13.65,0,-16.1),.55,1.1,.055,90)

# Cloth canopy: sagging panel grid, sewn edge, patches and genuinely open tears.
def tube(name,pts,radius,material='Iron',group='Awning hardware',sides=8):
    vs=[];fs=[]
    for j,p in enumerate(pts):
        p=Vector(p);t=Vector(pts[min(j+1,len(pts)-1)])-Vector(pts[max(0,j-1)])
        t.normalize();a=t.cross(Vector((0,1,0)))
        if a.length<.01:a=t.cross(Vector((1,0,0)))
        a.normalize();b=t.cross(a).normalized()
        for i in range(sides):vs.append(p+radius*(math.cos(i*math.tau/sides)*a+math.sin(i*math.tau/sides)*b))
    for j in range(len(pts)-1):
        for i in range(sides):
            a=j*sides+i;b=j*sides+(i+1)%sides;fs.append((a,b,b+sides,a+sides))
    o=mesh(name,vs,fs,material,group)
    for f in o.data.polygons:f.use_smooth=True
    return o
def canopy_y(u,v):return 4.08-.68*u-.25*math.sin(math.pi*v)*math.sin(math.pi*u)+.035*math.sin(v*47)*u
vs=[];fs=[];uv=[];nx,nz=30,48
for j in range(nz+1):
    v=j/nz
    for i in range(nx+1):
        u=i/nx;vs.append((16.82-4.58*u,canopy_y(u,v),-21.42+6.5*v));uv.append((1-u,v))
for j in range(nz):
    for i in range(nx):
        if i>27 and j in [5,6,34]:continue
        a=j*(nx+1)+i;fs.append((a,a+1,a+nx+2,a+nx+1))
cloth=mesh('Ochre red courtyard awning',vs,fs,'Canvas','Canopy',uv)
for f in cloth.data.polygons:f.use_smooth=True
sol=cloth.modifiers.new('Woven cloth thickness','SOLIDIFY');sol.thickness=.005
bpy.context.view_layer.objects.active=cloth;cloth.select_set(True);bpy.ops.object.modifier_apply(modifier=sol.name)
for side in [0,1]:
    z=-21.42+6.5*side
    tube('Canopy side spar '+str(side),[(16.85,4.08,z),(14.5,3.84,z),(12.18,3.41,z)],.035)
    tube('Canopy diagonal brace '+str(side),[(16.82,2.7,z),(14.5,3.84,z)],.026)
    tube('Awning edge rope '+str(side),[(16.82-4.58*i/20,canopy_y(i/20,side)+.012,z) for i in range(21)],.014,'Rope')
tube('Outer canopy crossbar',[(12.23,3.41,-21.45),(12.23,3.41,-14.9)],.04)
for v in [.29,.66]:
    tube('Stitched panel seam '+str(v),[(16.82-4.58*i/20,canopy_y(i/20,v)+.006,-21.42+6.5*v) for i in range(21)],.008,'CanvasPatch','Canopy',5)
for j in range(22):
    z=-21.35+j*.29
    tube('Frayed canvas fibre '+str(j),[(12.24,3.4,z),(12.23+rng.uniform(-.05,.05),3.32-rng.uniform(0,.05),z+.03)],.0027,'Rope','Canopy',4)

# Branching stems, curved leaves and seed heads; full geometry rather than triangles standing upright.
def plant(name,center,kind,seed,scale=1):
    pr=random.Random(seed);vs=[];fs=[];mi=[]
    mats=['Straw0','Straw1','Straw2','Leaf']
    def ribbon(path,width,m):
        a0=len(vs);ang=pr.random()*math.tau;side=Vector((math.cos(ang),0,math.sin(ang)))
        for j,p in enumerate(path):
            w=width*max(0,math.sin(math.pi*j/(len(path)-1)))**.6*(1-.65*j/(len(path)-1))
            vs.extend([Vector(p)-side*w,Vector(p)+Vector((0,w*.24,0)),Vector(p)+side*w])
        for j in range(len(path)-1):
            for k in range(2):fs.append((a0+j*3+k,a0+j*3+k+1,a0+(j+1)*3+k+1,a0+(j+1)*3+k));mi.append(m)
    count=75 if kind=='grass' else 38
    for k in range(count):
        ang=pr.random()*math.tau;r=pr.random()*.15;h=pr.uniform(.17,.52) if kind=='grass' else pr.uniform(.20,.63)
        bend=pr.uniform(.09,.34);base=Vector((math.cos(ang)*r,0,math.sin(ang)*r));dr=Vector((math.cos(ang),0,math.sin(ang)))
        path=[base+dr*bend*(t/6)**1.7+Vector((0,h*(t/6)-h*.25*(t/6)**3,0)) for t in range(7)]
        ribbon(path,.008 if kind=='grass' else .006,pr.randrange(3))
        if kind!='grass':
            for j in [2,3,4,5]:
                for sign in [-1,1]:
                    p=path[j];a=ang+sign*pr.uniform(.6,1.9);d=Vector((math.cos(a),.25,math.sin(a)))
                    ribbon([p+d*.025,p+d*.08+Vector((0,.012,0)),p+d*.13],.015,3 if kind=='green' else pr.choice([0,1,2]))
        elif k%4==0:
            top=path[-1]
            for j in range(5):
                a=ang+j*2.4;d=Vector((math.cos(a)*.028,.015*j,math.sin(a)*.028))
                ribbon([top+Vector((0,j*.014,0)),top+d,top+d+Vector((0,.034,0))],.005,1)
    vs=[Vector(center)+v*scale for v in vs]
    o=mesh(name,vs,fs,'Straw0','Vegetation');o.data.materials.clear()
    for m in mats:o.data.materials.append(M[m])
    for i,p in enumerate(o.data.polygons):p.material_index=mi[i];p.use_smooth=True
    return o
placements=[(4.25,0,-14.6),(4.28,0,-12.1),(11.69,0,-14.4),(11.72,0,-11.45),(6.7,0,-10.98),(9.9,0,-10.98),(7.8,0,-15.1),(5.1,0,-15.0),(10.1,0,-15.0),(5.45,.25,-14.4),(8.48,.25,-14.37),(10.53,.25,-14.38),(1.82,.25,-10.31),(-1.84,.5,-9.7),(1.83,.75,-9.0),(13.34,0,-20.15),(13.44,0,-16.0),(15.4,.5,-21.45),(15.3,.5,-14.3),(16.15,.5,-20.9)]
for i,p in enumerate(placements):plant('Dry joint growth '+str(i),p,'grass' if i%3 else 'scrub',300+i,.85 if p[1]>.0 else 1.12)
for i,p in enumerate([(46.1,0,-7.28),(46.19,0,-7.65)]):plant('Aquifer green growth '+str(i),p,'green',100+i,.7)
for i,p in enumerate([(46.12,0,-12.2),(46.1,0,-9.7),(46.08,0,-14.3)]):plant('Service wall scrub '+str(i),p,'scrub',110+i,.9)

# Masonry repair panels and water/conduit fittings on the courtyard-facing shop side.
for row in range(5):
    for j in range(5):
        stone(f'Shop side repair block {row}-{j}',(16.9+j*.72,.78+row*.53,-14.16),(.705,.514,.18),'Facade',.8,'Stone1')
for x in [16.43,20.10]:
    tube('Facade conduit '+str(x),[(x,.55,-14.02),(x,3.60,-14.02),(x,3.82,-14.24)],.037,'Iron','Facade')
    for y in [.68,1.8,3.3]:tube(f'Pipe fixing {x} {y}',[(x-.09,y,-14.0),(x+.09,y,-14.0)],.018,'Brass','Facade')

# Paper has a few lifted/torn corners and a real back surface. Text is a separate texture.
def paper(name,center,w,h,material,yaw=0,curl=.035):
    vs=[];fs=[];uv=[];nx,ny=16,24;ang=math.radians(yaw)
    for j in range(ny+1):
        v=j/ny
        for i in range(nx+1):
            u=i/nx;x=(u-.5)*w;y=(v-.5)*h
            if material=='Warden':y+=.045*(1-v)**10*(math.sin(u*41)+.5*math.sin(u*79))
            edge=(abs(u-.5)*2)**12;lift=curl*edge*(.4+.6*(1-v)**4)+.001*math.sin(u*30+v*39)
            if (i==nx or i==0):x+=.009*math.sin(v*87)
            vs.append((center[0]+x*math.cos(ang)+lift*math.sin(ang),center[1]+y,center[2]-x*math.sin(ang)+lift*math.cos(ang)));uv.append((1-u,v))
    for j in range(ny):
        for i in range(nx):
            if i>14 and j<2:continue
            a=j*(nx+1)+i;fs.append((a,a+1,a+nx+2,a+nx+1))
    o=mesh(name,vs,fs,material,'Wall graphics',uv)
    for f in o.data.polygons:f.use_smooth=True
    return o
paper('Karaveen illustrated poster',(18.3,2.0,-14.047),1.13,1.51,'Karaveen',0,.035)
paper('Older paper backing',(18.38,1.99,-14.066),1.35,1.63,'Paper',0,.016)
paper('Ward watch banner',(16.95,1.78,-14.028),.61,1.83,'Warden',0,.02)
paper('Factory hand-painted lettering',(20.10,2.13,-14.043),1.04,1.05,'Graffiti',0,.001)
paper('Service bay illustrated notice',(46.465,1.75,-10.85),1.05,1.40,'Karaveen',-90,.04)
for i in range(10):
    paper('Torn notice fragment '+str(i),(17.1+rng.random()*3.2,.88+rng.random()*2.3,-14.032-rng.random()*.008),rng.uniform(.12,.37),rng.uniform(.12,.36),'Paper',0,.015)

# Repaired steel drum with rim, ribs and an inset dusty interior. Clear of the shop doorway.
# A revolved authored shell, with no solid top pretending to be an opening.
profile=[(.275,0),(.304,.05),(.310,.14),(.319,.40),(.304,.71),(.306,.78),(.285,.78),(.281,.72),(.274,.13)]
vs=[];fs=[]
for ri,(r,y) in enumerate(profile):
    for j in range(40):
        a=j/40*math.tau;dent=1-.018*math.sin(a*5)*math.sin(math.pi*y/.8)
        vs.append((15.18+math.cos(a)*r*dent,.5+y,-14.38+math.sin(a)*r*dent))
for ri in range(len(profile)-1):
    for j in range(40):
        a=ri*40+j;b=ri*40+(j+1)%40;fs.append((b,a,a+40,b+40))
barrel=mesh('Salvaged drum planter',vs,fs,'Drum','Courtyard props')
for p in barrel.data.polygons:p.use_smooth=True
for y in [.56,.74,1.09,1.26]:
    tube('Drum welded hoop '+str(y),[(15.18+.316*math.cos(j/40*math.tau),y,-14.38+.316*math.sin(j/40*math.tau)) for j in range(41)],.017,'Brass','Courtyard props')
drift('Planter dry earth',(15.18,1.08,-14.38),.48,.48,.02)
plant('Drum drought shrub',(15.18,1.08,-14.38),'scrub',919,.94)

# Loose chipped stone and gravel accumulate in the sand, with working lanes clear.
for i in range(45):
    x=rng.uniform(4,12);z=rng.choice([-15.08,-10.96])+rng.uniform(-.18,.18)
    stone('Loose stone chip '+str(i),(x,.023,z),(rng.uniform(.025,.10),rng.uniform(.02,.055),rng.uniform(.03,.12)),'Gravel',.8,'Stone2')

# Export full per-corner normals and UV0; no source downsampling or destructive atlas.
objects=[]
for o in list(coll.objects):
    if o.type!='MESH':continue
    me=o.data;me.calc_loop_triangles();uv=me.uv_layers.active
    positions=[];normals=[];tex=[];indices=[];sub=[];unique={}
    for t in me.loop_triangles:
        # The explicit interchange rotates coordinates without reflecting an axis.
        for li in t.loops:
            l=me.loops[li];pos=U(o.matrix_world@me.vertices[l.vertex_index].co)
            nor=U(o.matrix_world.to_3x3()@me.corner_normals[li].vector)
            tx=[round(float(v),6) for v in uv.data[li].uv];key=tuple(pos+nor+tx)
            if key not in unique:
                unique[key]=len(positions);positions.append(pos);normals.append(nor);tex.append(tx)
            indices.append(unique[key])
        sub.append(t.material_index)
    objects.append({'name':o.name,'group':o['group'],'positions':positions,'normals':normals,'uv':tex,'indices':indices,'triangleMaterials':sub,'materials':[m.name[3:] for m in me.materials]})
(OUT/'mesh-data.json').write_text(json.dumps(objects,separators=(',',':')))
bpy.ops.object.select_all(action='DESELECT')
for o in coll.objects:o.select_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'courtyard-source.blend'))
bpy.ops.export_scene.fbx(filepath=str(OUT/'courtyard-source.fbx'),use_selection=True,axis_forward='-Z',axis_up='Y',add_leaf_bones=False,bake_anim=False)
(OUT/'geometry-report.json').write_text(json.dumps({'objects':len(objects),'triangles':sum(len(o['indices'])//3 for o in objects),'source':'Live Blender MCP authoring; original geometry','groups':sorted(set(o['group'] for o in objects))},indent=2))
print((OUT/'geometry-report.json').read_text())
