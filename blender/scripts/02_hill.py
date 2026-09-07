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
 ([(-.2,6.1,0),(-2.5,8,-.5),(-5,9.5,.2),(-7.3,10.2,.8),(-10,12,1.1)],[1.1,.78,.43,.18,.02]),
 ([(.1,7.6,.1),(-1.3,10.2,-.1),(-3.6,12.6,-.7),(-5.8,14.2,-.7),(-8.8,15.4,.5)],[.9,.72,.41,.17,.018]),
 ([(.2,8.4,.1),(.9,11,-1),(0,14,-.9),(-1.1,17,-1),(-2,20,-.9)],[.81,.61,.38,.15,.012]),
 ([(.2,6.8,.1),(2.6,9.2,.3),(4.1,12.3,.4),(6.7,15.1,1),(8.7,17.6,1.6)],[1.0,.77,.46,.21,.018]),
 ([(.2,8.4,.1),(.9,11,-1),(2.1,13.7,-1.8),(3.5,17,-1.6),(5,21,-1.4)],[.78,.6,.39,.16,.012]),
 ([(-.2,7.5,0),(-1.5,10,-2.8),(-3.8,12.2,-5.4),(-5,15,-7)],[.72,.49,.24,.018]),
 ([(.1,8,.2),(1.4,10.5,3.1),(.6,13.2,5.5),(-1.8,16.3,6.8)],[.70,.47,.22,.018]),
]
# Every twig spray descends from a real primary or secondary fork. Unequal
# fork lengths follow the low left shelf and higher right crown in ref01.
clusters=[]
for i,(p,r) in enumerate(scaffolds):
    p=[Vector((x*1.12,y,z*1.12)) for x,y,z in p]
    tube('TREE_scaffold_%02d'%i,[tuple(v) for v in p],r,segments=12)
    for k in range(1,len(p)-1):
        base=p[k].lerp(p[k+1],.35)
        radial=Vector((base.x,0,base.z))
        if radial.length<.1:radial=Vector((1,0,0))
        radial.normalize()
        tangent=Vector((-radial.z,0,radial.x))
        for side in [-1,1]:
            reach=random.uniform(1.5,3.1)
            end=base+radial*random.uniform(.65,1.4)+tangent*reach*side+Vector((0,random.uniform(1.5,2.9),0))
            middle=base.lerp(end,.55)+Vector((0,-.28,0))
            radius=r[k]*.38
            tube('TREE_secondary_%02d_%02d_%d'%(i,k,side),[tuple(base),tuple(middle),tuple(end)],[radius,radius*.48,.011],segments=9)
            clusters.append((end,Vector((random.uniform(1.1,1.7),random.uniform(.8,1.4),random.uniform(1.1,1.7))),middle))
    clusters.append((p[-1],Vector((1.6,1.15,1.6)),p[-2].lerp(p[-1],.65)))
for i,(center,radius,branch_base) in enumerate(clusters):
    for j in range(4):
        a=random.random()*math.tau
        end=center+Vector((math.cos(a)*radius.x,random.uniform(.2,1.1),math.sin(a)*radius.z))
        mid=branch_base.lerp(end,.63)
        tube('TREE_twig_%02d_%02d'%(i,j),[tuple(branch_base),tuple(mid),tuple(end)],[.06,.031,.005],segments=5)
        if j==0:
            fork=end+Vector((.4,.6,-.3))
            tube('TREE_dead_tip_%02d'%i,[tuple(mid),tuple(end),tuple(fork)],[.03,.014,.002],segments=4)
# Scattered leaf sprays with local gaps. Cards lean in all directions and
# clusters vary in density instead of forming identical horizontal pads.
verts=[];faces=[];uvs=[]
for i,(cluster,radius,branch_base) in enumerate(clusters):
    for j in range(random.randint(62,98)):
        a=random.random()*math.tau;r=math.sqrt(random.random())
        if i%5==0 and math.sin(a*2)>.3:continue
        center=cluster+Vector((math.cos(a)*radius.x*r,random.uniform(-radius.y,radius.y),math.sin(a)*radius.z*r))
        normal=Vector((random.uniform(-1,1),random.uniform(-.7,1),random.uniform(-1,1))).normalized()
        axis=normal.cross(Vector((0,0,1))).normalized();second=normal.cross(axis)
        length=random.uniform(.42,.85);width=length*.70
        quad=[center-axis*length,center+second*width,center+axis*length,center-second*width]
        start=len(verts);verts.extend(tuple(p) for p in quad);faces.append(tuple(start+k for k in range(4)))
        uvs.extend([(0,.5),(.5,0),(1,.5),(.5,1)])
leaf=mesh('TREE_leaf_sprays',verts,faces,'leaf',uvs)
leaf['foliage']=True
MATS['leaf'].use_backface_culling=False
if ACTIVE_LANDMARK not in AUTHORED:AUTHORED.append(ACTIVE_LANDMARK)
save('02_hill_tree.blend');export_world()
