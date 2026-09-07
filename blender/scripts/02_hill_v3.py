ACTIVE_LANDMARK='hill_tree'
for obj in list(bpy.context.scene.objects):
    if obj.get('landmark')==ACTIVE_LANDMARK:bpy.data.objects.remove(obj,do_unlink=True)
random.seed(482)
# Low retaining plinth and the accepted three flights of six 25 cm treads.
box('ENV_hill_plinth',(0,.70,0),(14,1.4,14),'stone',.045,True)
box('ENV_hill_surface',(0,1.45,0),(14,.1,14),'grass',.015,True)
for side in ['west','south','north']:
    for i in range(6):
        h=(i+1)*.25;d=10.3-i*.6
        pos=(-d,h/2,0) if side=='west' else (0,h/2,d if side=='south' else -d)
        size=(.6,h,4) if side=='west' else (4,h,.6)
        box('ENV_hill_stair_'+side+'_'+str(i),pos,size,'stone',.016,True)
for x,z,sx,sz in [(-4,0,6,3),(0,4,3,6),(0,-4,3,6)]:box('ENV_hill_path',(x,1.51,z),(sx,.02,sz),'stone',.008)
for edge in [-1,1]:
    for center in [-4.55,4.55]:
        box('ENV_hill_cap',(edge*6.85,1.48,center),(.36,.20,4.5),'stone',.035)
        box('ENV_hill_cap',(center,1.48,edge*6.85),(4.5,.20,.36),'stone',.035)
# Gently irregular central earth, kept inside the verified walking paths.
verts=[(0,2.12,0)];faces=[];segments=28
for ring_i in range(1,4):
    r=ring_i*1.05
    for j in range(segments):
        a=math.tau*j/segments
        verts.append((math.cos(a)*r,1.5+.65*(1-r/3.3)+random.uniform(-.07,.07),math.sin(a)*r))
for j in range(segments):faces.append((0,1+j,1+(j+1)%segments))
for row in range(2):
    for j in range(segments):
        a=1+row*segments+j;b=1+row*segments+(j+1)%segments
        faces.append((a,b,b+segments,a+segments))
mesh('ENV_hill_mound',verts,[tuple(reversed(f)) for f in faces],'grass')
# Authored asymmetric scaffold: lower left shelf, higher swept right crown,
# exposed branch tips, and three unequal trunk forks. No spherical crown mesh.
trunk=[(0,1.5,0),(.18,2.4,.15),(-.3,3.7,.1),(-.48,5.2,-.08),(-.15,6.6,0),(.35,8,.18),(.62,9.2,.25)]
tube('TREE_gnarled_trunk',trunk,[1.6,1.55,1.28,1.17,1.07,.92,.75],segments=18)
collider('tree_core',(0,5.8,0),(2.6,8.6,2.6),'cylinder')
for j in range(11):
    a=j*math.tau/11+.18
    radius=3.0+random.random()*.65
    points=[(.3*math.cos(a),2.7,.3*math.sin(a)),(1.4*math.cos(a+.1),1.95,1.4*math.sin(a+.1)),
      (2.4*math.cos(a),1.58,2.4*math.sin(a)),(radius*math.cos(a-.12),1.52,radius*math.sin(a-.12))]
    tube('TREE_root_%02d'%j,points,[.50,.32,.15,.015],segments=9)
scaffolds=[
 ([(-.2,6.1,0),(-2.6,8.3,.5),(-5.7,8.8,1.1),(-7.1,11.9,1.4),(-9,13,1.8)],[1.15,.82,.58,.29,.045]),
 ([(.2,7.2,.15),(-1.4,10,-.3),(-.4,13.2,-.7),(-2.8,16.4,.1),(-3.4,20.5,-.7)],[1.0,.87,.62,.4,.07]),
 ([(.1,6.3,.1),(2.8,8.2,-.4),(5.8,10,1.5),(6.6,14.6,2),(8,18,2.4)],[1.05,.86,.6,.34,.04]),
 ([(-.3,7.8,-.1),(-2.8,9.9,-2.8),(-5.9,11.8,-4.0),(-6.2,15.8,-5.8)],[.74,.56,.32,.035]),
 ([(.2,8.8,.1),(2.7,11,-3),(2.1,14.6,-5.5),(3.6,18.8,-6.1)],[.74,.55,.31,.03]),
 ([(.1,7.5,.3),(-1.7,9.6,3),(-.9,12.4,5.2),(-2.7,15.1,6.5)],[.78,.58,.29,.025]),
 ([(.2,10.5,.2),(2.4,13,.5),(1.5,17.2,-.9),(3.5,21,-.2)],[.73,.52,.29,.035]),
]
for i,(p,r) in enumerate(scaffolds):
    p=[(x*1.18,y,z*1.18) for x,y,z in p]
    tube('TREE_scaffold_%02d'%i,p,r,segments=12)
# Branch envelopes are deliberately nonuniform and leave skyline gaps.
clusters=[(-8,13.0,1.8,2.4,1.1,2.0),(-5.7,14.5,2.4,2.5,1.1,2.0),(-6.2,16.0,-5.8,2.7,1.2,2.3),
 (-3.5,20,-.7,2.0,1.4,1.8),(-2.2,17.2,-1,2.4,1.1,1.8),(0.1,19,-2.5,2.5,1.1,2.4),
 (3.5,21,-.3,2.8,1.2,2.2),(6.2,19,1.2,2.9,1.3,2.3),(8,17.4,2.4,2.6,1.2,2.4),
 (3.6,18.5,-6,2.7,1.2,2.4),(5,16,-4,2.7,1.4,2.1),(-2.7,15.1,6.5,2.7,1.0,2.0),(2.3,15.6,5,2.5,1.2,2.4),
 (-6.4,11.4,2.6,2.7,1.0,2.0),(5.5,12.5,2.9,2.8,1.0,2.1),(-1.1,12.4,5.0,2.2,1,1.8)]
clusters=[(x*1.18,y,z*1.18,rx*1.15,ry,rz*1.15) for x,y,z,rx,ry,rz in clusters]
for i,(cx,cy,cz,rx,ry,rz) in enumerate(clusters):
    # Twig sprays, including several clean dead forks visible beyond foliage.
    for j in range(9):
        a=random.random()*math.tau
        end=(cx+math.cos(a)*rx*.95,cy+random.uniform(.2,1.1),cz+math.sin(a)*rz*.95)
        base=(cx,cy-1.7,cz)
        mid=((base[0]+end[0])*.5,cy-.2,(base[2]+end[2])*.5)
        tube('TREE_twig_%02d_%02d'%(i,j),[base,mid,end],[.1,.06,.008],segments=5)
        fork=(end[0]+math.cos(a+.9)*.5,end[1]+.55,end[2]+math.sin(a+.9)*.5)
        tube('TREE_tip_%02d_%02d'%(i,j),[mid,end,fork],[.05,.024,.003],segments=4)
# Original leaf geometry gives a working opaque canopy until the generated
# alpha spray texture is assigned. 4-point lanceolate leaves, not blob crowns.
verts=[];faces=[];uvs=[]
for cx,cy,cz,rx,ry,rz in clusters:
    for j in range(210):
        a=random.random()*math.tau; r=math.sqrt(random.random())
        center=Vector((cx+math.cos(a)*rx*r,cy+random.uniform(-ry,ry)*.65,cz+math.sin(a)*rz*r))
        normal=Vector((random.uniform(-1,1),random.uniform(.3,1),random.uniform(-1,1))).normalized()
        axis=normal.cross(Vector((0,0,1))).normalized();second=normal.cross(axis)
        length=random.uniform(.65,1.25);width=length*.65
        quad=[center-axis*length,center+second*width,center+axis*length,center-second*width]
        start=len(verts);verts.extend(tuple(p) for p in quad);faces.append(tuple(start+k for k in range(4)))
        uvs.extend([(0,.5),(.5,0),(1,.5),(.5,1)])
leaf=mesh('TREE_leaf_sprays',verts,faces,'leaf',uvs)
leaf['foliage']=True
MATS['leaf'].use_backface_culling=False
if ACTIVE_LANDMARK not in AUTHORED:AUTHORED.append(ACTIVE_LANDMARK)
save('02_hill_tree.blend');export_world()
