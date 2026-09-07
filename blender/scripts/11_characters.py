"""Original colonist shared kit. Run only in live Blender through city_core.py.
Author at feet origin, Three +Z facing, metre scale. Two atlas materials, one rig.
"""
from mathutils import Quaternion
ATLAS = ROOT/'public/assets/textures/colonist_atlas.png'
assert ATLAS.exists(), 'Generate the original character atlas before this stage'
for ob in list(bpy.context.scene.objects):
    if ob.get('characterAsset'):bpy.data.objects.remove(ob,do_unlink=True)

image=bpy.data.images.load(str(ATLAS),check_existing=True)
CHAR_MATS={}
for name in ['MAT_body','MAT_cloth']:
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.91
    bs.inputs['Metallic'].default_value=0
    tex=m.node_tree.nodes.get('CHAR_albedo') or m.node_tree.nodes.new('ShaderNodeTexImage')
    tex.name='CHAR_albedo';tex.image=image
    m.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
    CHAR_MATS[name]=m

# Neutral A pose. Shared bone names allow the same gameplay clip contract.
BONES={
 'hips':((0,.90,0),(0,1.04,0),None),
 'spine':((0,1.04,0),(0,1.22,0),'hips'),
 'chest':((0,1.22,0),(0,1.43,0),'spine'),
 'neck':((0,1.43,0),(0,1.54,0),'chest'),
 'head':((0,1.54,0),(0,1.79,0),'neck')}
for side,sign in [('L',1),('R',-1)]:
    BONES.update({
      'shoulder.'+side:((sign*.08,1.43,0),(sign*.24,1.40,0),'chest'),
      'upper_arm.'+side:((sign*.24,1.40,0),(sign*.40,1.13,0),'shoulder.'+side),
      'forearm.'+side:((sign*.40,1.13,0),(sign*.47,.91,.018),'upper_arm.'+side),
      'hand.'+side:((sign*.47,.91,.018),(sign*.49,.80,.03),'forearm.'+side),
      'thigh.'+side:((sign*.11,.92,0),(sign*.13,.51,.012),'hips'),
      'shin.'+side:((sign*.13,.51,.012),(sign*.13,.12,0),'thigh.'+side),
      'foot.'+side:((sign*.13,.12,0),(sign*.13,.06,.18),'shin.'+side)})

PARTS=[]; CURRENT_RIG=None; DETAIL=1

def char_uv(u,v,cell):
    col=cell%2; row=cell//2
    # Insets prevent filtered sampling of an adjacent material swatch.
    return ((col+.03+.94*u)/2,1-(row+.03+.94*v)/4)

def ch_mesh(name,verts,faces,cell,bone,uvs=None,cloth=False,weights=None):
    data=bpy.data.meshes.new(name);data.from_pydata([xyz(v) for v in verts],[],faces);data.update()
    ob=bpy.data.objects.new(name,data);bpy.context.scene.collection.objects.link(ob)
    ob['characterAsset']=True;ob.data.materials.append(CHAR_MATS['MAT_cloth' if cloth else 'MAT_body'])
    uv=data.uv_layers.new(name='UV0')
    for poly in data.polygons:
        poly.use_smooth=True
        for li in poly.loop_indices:
            vi=data.loops[li].vertex_index
            coord=uvs[vi] if uvs else ((verts[vi][0]*3)%1,(verts[vi][1]*3)%1)
            uv.data[li].uv=char_uv(*coord,cell)
    for vi in range(len(verts)):
        blend=weights[vi] if weights else {bone:1}
        for key,value in blend.items():
            group=ob.vertex_groups.get(key) or ob.vertex_groups.new(name=key)
            group.add([vi],value,'REPLACE')
    PARTS.append(ob);return ob

def loft(name,sections,cell,bone,segments=16,cloth=False):
    verts=[];uv=[];faces=[]
    for i,(x,y,z,rx,rz) in enumerate(sections):
        for j in range(segments+1):
            a=math.tau*j/segments
            verts.append((x+rx*math.cos(a),y,z+rz*math.sin(a)));uv.append((j/segments,i/(len(sections)-1)))
    for i in range(len(sections)-1):
        for j in range(segments):
            a=i*(segments+1)+j;b=a+segments+1;faces.append((a,b,b+1,a+1))
    faces.extend([tuple(range(segments)),tuple(reversed([(len(sections)-1)*(segments+1)+j for j in range(segments)]))])
    return ch_mesh(name,verts,faces,cell,bone,uv,cloth)

def limb(name,start,end,r1,r2,cell,bone,segments=14,cloth=False):
    a=Vector(start);b=Vector(end);tangent=(b-a).normalized()
    axis=tangent.cross(Vector((0,0,1))).normalized();second=tangent.cross(axis)
    verts=[];uv=[];faces=[]
    # Curved profile creates fitted cloth joints, not disconnected cylinders.
    for i,(t,scale) in enumerate([(0,.83),(.12,1),(.40,1.02),(.73,.98),(1,.88)]):
        c=a.lerp(b,t);radius=(r1*(1-t)+r2*t)*scale
        for j in range(segments+1):
            angle=math.tau*j/segments;v=c+(axis*math.cos(angle)+second*math.sin(angle))*radius
            verts.append(tuple(v));uv.append((j/segments,t))
    for i in range(4):
        for j in range(segments):
            a=i*(segments+1)+j;b=a+segments+1;faces.append((a,a+1,b+1,b))
    faces.extend([tuple(reversed(range(segments))),tuple(4*(segments+1)+j for j in range(segments))])
    return ch_mesh(name,verts,faces,cell,bone,uv,cloth)

def ellipsoid(name,pos,scale,cell,bone,segments=16,rings=9):
    verts=[];uv=[];faces=[]
    for i in range(rings+1):
        phi=math.pi*i/rings
        for j in range(segments+1):
            theta=math.tau*j/segments
            verts.append((pos[0]+scale[0]*math.sin(phi)*math.cos(theta),pos[1]+scale[1]*math.cos(phi),pos[2]+scale[2]*math.sin(phi)*math.sin(theta)))
            uv.append((j/segments,i/rings))
    for i in range(rings):
        for j in range(segments):
            a=i*(segments+1)+j;b=a+segments+1;faces.append((a,a+1,b+1,b))
    return ch_mesh(name,verts,faces,cell,bone,uv)

def panel(name,pos,size,cell,bone,bevel=.007,cloth=False):
    bpy.ops.mesh.primitive_cube_add(size=1,location=xyz(pos));ob=bpy.context.object;ob.name=name
    ob.scale=(size[0],size[2],size[1]);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel:
        mod=ob.modifiers.new('Tailored_edge','BEVEL');mod.width=bevel;mod.segments=1;bpy.ops.object.modifier_apply(modifier=mod.name)
    ob['characterAsset']=True;ob.data.materials.append(CHAR_MATS['MAT_cloth' if cloth else 'MAT_body'])
    planar_uv(ob,1)
    for uv in ob.data.uv_layers.active.data:uv.uv=char_uv((uv.uv.x+.5)%1,(uv.uv.y+.5)%1,cell)
    group=ob.vertex_groups.new(name=bone);group.add(list(range(len(ob.data.vertices))),1,'REPLACE')
    PARTS.append(ob);return ob


# Deliberate facial cross sections: chin, mandibular corner, cheekbone, socket,
# brow and cranial dome. These replace the uniformly wide cylinder-like head.
HEAD_PROFILE=[
 (1.531,.027,-.030,.057),(1.539,.046,-.046,.072),
 (1.553,.066,-.065,.082),(1.575,.078,-.079,.087),
 (1.601,.080,-.087,.089),(1.627,.085,-.092,.086),
 (1.649,.088,-.094,.083),(1.672,.085,-.093,.081),
 (1.692,.083,-.090,.090),(1.713,.082,-.087,.091),
 (1.735,.077,-.079,.085),(1.753,.065,-.067,.071),
 (1.770,.047,-.050,.048),(1.781,.025,-.032,.026),
 (1.786,.002,-.009,-.005)]


def head_section(y):
    for a,b in zip(HEAD_PROFILE,HEAD_PROFILE[1:]):
        if y<=b[0]:
            t=max(0,min(1,(y-a[0])/(b[0]-a[0])))
            return tuple(a[k]*(1-t)+b[k]*t for k in (1,2,3))
    return HEAD_PROFILE[-1][1:]


def head_point(y,angle,offset=0):
    rx,back,front=head_section(y);c=math.cos(angle);s=math.sin(angle)
    x=rx*s;center=(front+back)/2;depth=(front-back)/2
    # A flatter facial mask and rounded occiput, with local anatomical relief.
    z=center+depth*(abs(c)**.64)*(1 if c>=0 else -1)
    def g(cx,cy,sx,sy):return math.exp(-((abs(x)-cx)/sx)**2-((y-cy)/sy)**2)
    if c>0:
        relief=(.025*g(0,1.644,.010,.015) + .011*g(0,1.677,.009,.029)
                +.010*g(.048,1.651,.016,.017) -.010*g(.033,1.678,.014,.009)
                +.007*g(.032,1.697,.021,.007) +.005*g(0,1.548,.035,.014)
                -.003*g(.031,1.618,.008,.018))
        z+=relief*c*c
    return (x+s*offset,y,z+c*offset)


def face_depth(x,y):
    rx,_,_=head_section(y)
    return head_point(y,math.asin(max(-.999,min(.999,x/max(rx,.001)))))[2]


def face_ribbon(name,points,width,cell,segments=8):
    """A tapered brow/lid/lip ribbon that lies against the facial surface."""
    verts=[];uv=[];faces=[]
    for j in range(segments+1):
        t=j/segments;f=t*(len(points)-1);i=min(len(points)-2,int(f));local=f-i
        x=points[i][0]*(1-local)+points[i+1][0]*local
        y=points[i][1]*(1-local)+points[i+1][1]*local
        half=width*(.30+.70*math.sin(math.pi*t))
        for k in (-1,1):
            yy=y+k*half
            verts.append((x,yy,face_depth(x,yy)+.0025));uv.append((t,(k+1)/2))
        if j:
            a=(j-1)*2;faces.append((a,a+2,a+3,a+1))
    if points[-1][0]<points[0][0]:faces=[tuple(reversed(f)) for f in faces]
    return ch_mesh(name,verts,faces,cell,'head',uv)


def anatomical_head(kind):
    player=kind=='player';n=48 if player else 24
    # Denser player rows resolve nose/cheek/socket relief; NPCs retain the same
    # actual profile landmarks rather than adding invisible tessellation.
    rows=[1.531+(1.786-1.531)*i/30 for i in range(31)] if player else [p[0] for p in HEAD_PROFILE]
    verts=[];uv=[];faces=[]
    for i,y in enumerate(rows):
        for j in range(n+1):
            angle=-math.pi+math.tau*j/n
            verts.append(head_point(y,angle));uv.append((j/n,i/(len(rows)-1)))
    for i in range(len(rows)-1):
        for j in range(n):
            a=i*(n+1)+j;b=a+n+1;faces.append((a,a+1,b+1,b))
    faces.extend([tuple(reversed(range(n))),tuple((len(rows)-1)*(n+1)+j for j in range(n))])
    ch_mesh('CHR_anatomical_head',verts,faces,1,'head',uv)
    for sign in (-1,1):
        # Folded auricle: concha depression, antihelix and outer helix. The ear
        # is a small side feature, rather than a separate 5 cm spherical bulb.
        en=20 if player else 10
        ear_layers=[(.24,.089),(.48,.091),(.70,.099),(.86,.100),(1,.091)] if player else [(.35,.09),(.77,.099),(1,.091)]
        ev=[(sign*.088,1.650,-.007)];eu=[(.5,.5)];ef=[]
        for scale,ex in ear_layers:
            for j in range(en):
                a=math.tau*j/en
                ev.append((sign*ex,1.651+math.sin(a)*.030*scale,
                           -.005+math.cos(a)*.017*scale))
                eu.append((.5+math.cos(a)*scale*.48,.5+math.sin(a)*scale*.48))
        for j in range(en):ef.append((0,1+(j+1)%en,1+j))
        for row in range(len(ear_layers)-1):
            for j in range(en):
                a=1+row*en+j;b=1+row*en+(j+1)%en
                ef.append((a,b,b+en,a+en))
        if sign<0:ef=[tuple(reversed(f)) for f in ef]
        ch_mesh('CHR_ear_helix',ev,ef,1,'head',eu)
        ellipsoid('CHR_ear_tragus',(sign*.090,1.646,.010),(.005,.010,.005),1,'head',12 if player else 6,6 if player else 4)
        # Small almond-shaped visible sclera; the eyelid rim obscures a globe.
        ex=sign*.033;ey=1.679;es=20 if player else 12
        ev=[];eu=[];ef=[]
        for scale in (1,.52):
            for j in range(es):
                a=math.tau*j/es;x=ex+math.cos(a)*.0135*scale
                dy=math.copysign(abs(math.sin(a))**1.30,math.sin(a))*.0045*scale
                y=ey+dy;z=face_depth(x,y)+.0015+(1-scale)*.007
                ev.append((x,y,z));eu.append((.5+math.cos(a)*.48,.5+math.sin(a)*.48))
        ev.append((ex,ey,face_depth(ex,ey)+.006));eu.append((.5,.5))
        for j in range(es):
            k=(j+1)%es;ef.extend([(j,k,k+es,j+es),(2*es,es+j,es+k)])
        ch_mesh('CHR_inset_eye',ev,ef,7,'head',eu)
        ellipsoid('CHR_iris',(ex,ey,face_depth(ex,ey)+.0066),(.0049,.0049,.0012),6,'head',12 if player else 8,5 if player else 3)
        face_ribbon('CHR_upper_lid',[(ex-.014,ey),(ex,ey+.0059),(ex+.014,ey+.0002)],.0017,1,12 if player else 6)
        face_ribbon('CHR_lower_lid',[(ex-.013,ey-.0003),(ex,ey-.0048),(ex+.013,ey-.0003)],.0010,1,10 if player else 5)
        face_ribbon('CHR_natural_brow',[(sign*.014,1.697),(sign*.033,1.704),(sign*.056,1.697)],.0032,6,12 if player else 6)
        # Alar wings integrate the nose into the cheek instead of a pyramidal
        # protruding block; their lower seam supplies the nostril definition.
        ellipsoid('CHR_nose_alar',(sign*.0105,1.638,.108),(.006,.0045,.005),1,'head',12 if player else 6,6 if player else 3)
    face_ribbon('CHR_mouth_crease',[(-.021,1.607),(0,1.6055),(.021,1.607)],.0008,6,12 if player else 6)
    face_ribbon('CHR_lower_lip',[(-.019,1.603),(0,1.601),(.019,1.603)],.0017,1,12 if player else 6)


def groom_hair(kind):
    player=kind=='player';n=36 if player else 18;rows=12 if player else 6
    verts=[];uv=[];faces=[]
    for i in range(rows+1):
        t=i/rows
        for j in range(n+1):
            a=-math.pi+math.tau*j/n;c=math.cos(a)
            edge=1.680+.037*max(0,c)-.035*max(0,-c)+.006*math.sin(a)*max(0,c)
            y=edge*(1-t)+1.795*t
            p=head_point(min(y,1.786),a,.004*(1-t)+.003)
            # Keep the cap outside the anatomical scalp; inward shrinkage exposes skin.
            verts.append((p[0],y,p[2]))
            uv.append((j/n,t))
    for i in range(rows):
        for j in range(n):
            a=i*(n+1)+j;b=a+n+1;faces.append((a,a+1,b+1,b))
    faces.append(tuple(rows*(n+1)+j for j in range(n)))
    ch_mesh('CHR_tapered_hairline',verts,faces,6,'head',uv)
    # Low raised swept locks follow the cap and preserve the 1.795 m crown.
    for lock in range(6 if player else 2):
        x=-.050+lock*(.018 if player else .071)
        centers=[(x,1.724,.073),(x*.90+.006,1.756,.065),
                 (x*.62+.009,1.785,.023),(x*.62+.009,1.780,-.029),
                 (x*.70,1.753,-.064)]
        vs=[];us=[];fs=[];ns=8 if player else 5
        for row,p in enumerate(centers):
            radius=(.005,.008,.006,.006,.002)[row]
            tangent=Vector(centers[min(row+1,4)])-Vector(centers[max(0,row-1)])
            tangent.normalize();axis=tangent.cross(Vector((1,0,0))).normalized();other=tangent.cross(axis)
            for j in range(ns+1):
                a=math.tau*j/ns;q=Vector(p)+(axis*math.cos(a)+other*math.sin(a))*radius
                vs.append((q.x,min(q.y,1.795),q.z));us.append((j/ns,row/4))
        for row in range(4):
            for j in range(ns):
                a=row*(ns+1)+j;b=a+ns+1;fs.append((a,a+1,b+1,b))
        fs.extend([tuple(reversed(range(ns))),tuple(4*(ns+1)+j for j in range(ns))])
        ch_mesh('CHR_swept_hair_lock',vs,fs,6,'head',us)
    if not player:return
    # Short continuous beard shell over the chin and front cheeks, open at
    # the mouth and nape. It follows the head; no closed jaw cylinder remains.
    n=40;rows=6;verts=[];uv=[];faces=[]
    for row in range(rows+1):
        t=row/rows
        for j in range(n+1):
            a=math.radians(-105+210*j/n);q=abs(a)/math.radians(105)
            bottom=1.529+.080*q**1.35
            top=1.594+.084*q**1.25
            y=bottom*(1-t)+top*t+.0014*math.sin(j*2.3)*(1-t)
            thickness=.003+.006*(1-t)*max(0,math.cos(a))
            p=head_point(y,a,thickness)
            verts.append(p);uv.append((j/n,t))
    for row in range(rows):
        for j in range(n):
            a=row*(n+1)+j;b=a+n+1;faces.append((a,a+1,b+1,b))
    ch_mesh('CHR_connected_short_beard',verts,faces,6,'head',uv)
    for sign in (-1,1):
        face_ribbon('CHR_moustache',[(sign*.002,1.624),(sign*.015,1.621),(sign*.027,1.614)],.0026,6,12)


def tailored_jacket_details(kind):
    # An inset undershirt and thin shaped lapels replace the horizontal collar
    # blocks. All vertices stay attached to the existing chest bone.
    ch_mesh('CHR_undershirt_insert',[(-.048,1.437,.091),(.048,1.437,.091),
             (.014,1.310,.142),(-.014,1.310,.142)],[(0,3,2,1)],3,'chest')
    for sign in (-1,1):
        points=[(sign*.015,1.317,.144),(sign*.029,1.427,.107),
                (sign*.060,1.475,.036),(sign*.098,1.450,.052),
                (sign*.106,1.390,.124),(sign*.057,1.341,.146)]
        face=tuple(range(6)) if sign<0 else tuple(reversed(range(6)))
        ch_mesh('CHR_shaped_lapel',points,[face],0,'chest',cloth=True)
        # Fabric pocket surfaces curve back to the torso at their outer edges.
        for flap in (False,True):
            vs=[];us=[];fs=[]
            for row in range(3):
                v=row/2;y=(1.313+v*.025) if flap else (1.235+v*.094)
                for col in range(5):
                    u=col/4;x=sign*(.066+u*.091)
                    rz=.131;rx=.205
                    z=rz*math.sqrt(max(.01,1-(x/rx)**2))+.006
                    z+=.004*math.sin(math.pi*u)+(0.006*(1-v) if flap else 0)
                    vs.append((x,y,z));us.append((u,v))
            for row in range(2):
                for col in range(4):
                    a=row*5+col;b=a+5
                    f=(a,a+1,b+1,b);fs.append(f if sign>0 else tuple(reversed(f)))
            ch_mesh('CHR_tailored_pocket_flap' if flap else 'CHR_tailored_pocket',vs,fs,0,'chest',us,True)
        if kind=='player':
            # Thin sewn seam strips add construction detail with real placement.
            panel('CHR_jacket_seam',(sign*.181,1.105,.019),(.008,.13,.018),0,'spine',.001,True)
    # A faceted asymmetric shoulder shell with a beveled rim, replacing the
    # complete ellipsoid. The outer edge follows the descending upper arm.
    outline=[(-.151,1.420,-.068),(-.196,1.468,-.101),(-.290,1.464,-.110),
             (-.369,1.383,-.087),(-.381,1.362,.058),(-.337,1.412,.109),
             (-.235,1.469,.116),(-.160,1.441,.076)]
    vs=outline+[(-.254,1.475,.006)]+[(x,y-.010,z) for x,y,z in outline]
    fs=[]
    for j in range(8):
        k=(j+1)%8;fs.extend([(8,j,k),(j,j+9,k+9,k)])
    fs.append(tuple(reversed(range(9,17))))
    shell=ch_mesh('CHR_faceted_shoulder_shell',vs,fs,4,'upper_arm.R')
    for p in shell.data.polygons:p.use_smooth=False
    activate(shell);mod=shell.modifiers.new('Salvaged_plate_edge','BEVEL');mod.width=.004;mod.segments=1
    bpy.ops.object.modifier_apply(modifier=mod.name)

def rig_create(name):
    data=bpy.data.armatures.new(name);rig=bpy.data.objects.new(name,data);bpy.context.scene.collection.objects.link(rig)
    rig['characterAsset']=True;activate(rig);bpy.ops.object.mode_set(mode='EDIT')
    for name,(start,end,parent) in BONES.items():
        b=data.edit_bones.new(name);b.head=xyz(start);b.tail=xyz(end)
        if parent:b.parent=data.edit_bones[parent]
    bpy.ops.object.mode_set(mode='OBJECT');return rig

def create_body(kind):
    global PARTS,DETAIL
    PARTS=[];DETAIL=1 if kind=='player' else .65
    n=22 if kind=='player' else 12
    # Pelvis, sculpted torso and overlapping tailored coat edge.
    loft('CHR_pelvis',[ (0,.84,0,.16,.105),(0,.91,0,.175,.12),(0,1.0,0,.16,.12)],2,'hips',n)
    loft('CHR_jacket',[ (0,.965,0,.177,.124),(0,1.02,0,.18,.127),(0,1.12,0,.155,.113),(0,1.24,0,.193,.128),(0,1.34,0,.221,.135),(0,1.405,0,.21,.115),(0,1.44,0,.12,.085)],0,'chest',n,True)
    # Blend coat vertex weights down the spine to keep hip motion connected.
    coat=PARTS[-1]
    for v in coat.data.vertices:
        height=v.co.z
        chest=max(0,min(1,(height-1.14)/.18));hips=max(0,min(1,(1.10-height)/.12));spine=1-chest-hips
        for bone,w in [('chest',chest),('hips',hips),('spine',spine)]:
            g=coat.vertex_groups.get(bone) or coat.vertex_groups.new(name=bone);g.add([v.index],max(0,w),'REPLACE')
    limb('CHR_neck',(0,1.405,0),(0,1.565,0),.061,.063,1,'neck',n)
    anatomical_head(kind)
    groom_hair(kind)
    for side,sign in [('L',1),('R',-1)]:
        upper='upper_arm.'+side;lower='forearm.'+side;hand='hand.'+side
        thigh='thigh.'+side;shin='shin.'+side;foot='foot.'+side
        limb('CHR_sleeve_upper_'+side,(sign*.20,1.405,0),(sign*.408,1.105,0),.092,.065,0,upper,n,True)
        limb('CHR_sleeve_lower_'+side,(sign*.392,1.16,0),(sign*.478,.898,.018),.068,.05,0,lower,n,True)
        limb('CHR_cuff_'+side,(sign*.46,.95,.014),(sign*.48,.89,.021),.055,.05,3,lower,n)
        ellipsoid('CHR_hand_'+side,(sign*.486,.853,.025),(.044,.064,.027),1,hand,n,8)
        for f in range(4):
            x=sign*(.462+f*.015)
            limb('CHR_finger_'+side+str(f),(x,.827,.023),(x+sign*.005,.775+abs(f-1.5)*.008,.035),.009,.006,1,hand,8 if kind=='player' else 5)
        limb('CHR_thumb_'+side,(sign*.45,.871,.035),(sign*.435,.821,.055),.013,.008,1,hand,9 if kind=='player' else 5)
        limb('CHR_cargo_upper_'+side,(sign*.105,.94,0),(sign*.13,.48,.012),.10,.073,2,thigh,n)
        limb('CHR_cargo_lower_'+side,(sign*.13,.53,.012),(sign*.13,.12,0),.078,.057,2,shin,n)
        panel('CHR_cargo_pocket_'+side,(sign*.202,.729,.015),(.046,.16,.105),2,thigh,.013)
        panel('CHR_knee_patch_'+side,(sign*.13,.515,.074),(.105,.125,.02),3,shin,.012)
        ellipsoid('CHR_boot_'+side,(sign*.13,.089,.075),(.079,.09,.159),3,foot,n,10 if kind=='player' else 6)
        panel('CHR_boot_sole_'+side,(sign*.13,.021,.073),(.153,.042,.298),3,foot,.013)
        for k in range(3):panel('CHR_boot_lace_'+side,(sign*.13,.126-k*.017,.175),(.077,.011,.015),7,foot,.002)
    # Jacket closures, utilitarian pockets, one original salvaged shoulder pad.
    panel('CHR_zip',(0,1.20,.135),(.015,.35,.016),4,'chest',.003)
    tailored_jacket_details(kind)
    panel('CHR_belt',(0,.995,.128),(.305,.045,.035),3,'hips',.004)
    panel('CHR_buckle',(0,.998,.15),(.053,.053,.013),4,'hips',.004)
    panel('CHR_shoulder_badge',(-.31,1.39,.105),(.081,.05,.016),5,'upper_arm.R',.005)
    panel('CHR_wrist_terminal',(.468,.976,.059),(.093,.085,.035),4,'forearm.L',.008)
    panel('CHR_wrist_face',(.468,.981,.081),(.065,.045,.01),3,'forearm.L',.004)
    for sign in [-1,1]:panel('CHR_back_seam',(sign*.10,1.22,-.132),(.009,.26,.008),7,'chest',.002)
    return PARTS


def animate(rig):
    scene=bpy.context.scene;scene.render.fps=24
    for clip,duration in [('idle',48),('walk',24),('run',18),('talk',48)]:
        rig.animation_data_create();action=bpy.data.actions.new(clip);rig.animation_data.action=action
        for frame in range(1,duration+2,3):
            # Include the exact last frame to make cyclic endpoints coincide.
            t=(frame-1)/duration;phase=t*math.tau
            for p in rig.pose.bones:p.rotation_mode='QUATERNION';p.rotation_quaternion=Quaternion();p.location=(0,0,0)
            def rot(name,axis,angle):
                local=rig.data.bones[name].matrix_local.to_quaternion().inverted()@xyz(axis)
                rig.pose.bones[name].rotation_quaternion=Quaternion(local,angle)
            bounce=(.008 if clip=='idle' else .015)*math.sin(phase*2)
            # Pose location is bone-local: convert world-up into the hips rest
            # basis so bobbing never introduces horizontal root translation.
            rig.pose.bones['hips'].location=rig.data.bones['hips'].matrix_local.to_quaternion().inverted()@xyz((0,bounce,0))
            if clip in ['walk','run']:
                swing=.53 if clip=='walk' else .80
                for side,offset in [('L',0),('R',math.pi)]:
                    s=math.sin(phase+offset)
                    rot('thigh.'+side,(1,0,0),s*swing)
                    rot('shin.'+side,(1,0,0),-max(0,-s)*(.67 if clip=='walk' else 1.1))
                    rot('foot.'+side,(1,0,0),s*-.12)
                    rot('upper_arm.'+side,(1,0,0),-s*(.32 if clip=='walk' else .56))
                    rot('forearm.'+side,(1,0,0),.16 if clip=='walk' else .6)
                rot('chest',(0,1,0),math.sin(phase)*.04)
            elif clip=='talk':
                gesture=.5-.5*math.cos(phase)
                rot('upper_arm.R',(1,0,0),-.8*gesture)
                rot('forearm.R',(1,0,0),-.5*gesture)
                rot('head',(0,1,0),.10*math.sin(phase))
            else:
                rot('chest',(1,0,0),.012*math.sin(phase));rot('head',(0,1,0),.025*math.sin(phase))
            for p in rig.pose.bones:
                p.keyframe_insert(data_path='rotation_quaternion',frame=frame)
                if p.name=='hips':p.keyframe_insert(data_path='location',frame=frame)
        track=rig.animation_data.nla_tracks.new();track.name=clip
        strip=track.strips.new(clip,1,action);strip.action_frame_start=1;strip.action_frame_end=duration+1
        track.mute=True
    rig.animation_data.action=None
    for p in rig.pose.bones:p.rotation_quaternion=Quaternion();p.location=(0,0,0)
    scene.frame_set(1)


for kind in ['player','npc']:
    rig=rig_create('RIG_'+kind);parts=create_body(kind)
    # Join by material family: two skinned render meshes, one shared atlas.
    joined=[]
    families={name:[o for o in parts if o.data.materials[0].name==name] for name in ['MAT_body','MAT_cloth']}
    for matname,chosen in families.items():
        bpy.ops.object.select_all(action='DESELECT')
        for o in chosen:o.select_set(True)
        bpy.context.view_layer.objects.active=chosen[0];bpy.ops.object.join()
        ob=bpy.context.object;ob.name='CHR_'+kind+'_'+matname[4:]
        # All authored coordinates become mesh-local at the same ground origin.
        bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
        ob.parent=rig;modifier=ob.modifiers.new('Humanoid_skin','ARMATURE');modifier.object=rig
        joined.append(ob)
    animate(rig)
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
    for o in joined:o.select_set(True)
    triangles=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in joined)
    assert triangles<=(18000 if kind=='player' else 6000), kind+' character triangle budget exceeded: '+str(triangles)
    # Export NLA tracks by their original animation names, with cyclic clips.
    filename='player.glb' if kind=='player' else 'npcs.glb'
    bpy.ops.export_scene.gltf(filepath=str(ROOT/'public/assets'/filename),export_format='GLB',use_selection=True,use_active_scene=True,
      export_yup=True,export_apply=False,export_extras=True,export_animations=True,export_animation_mode='NLA_TRACKS',
      export_nla_strips=True,export_force_sampling=True,export_cameras=False,export_lights=False)
    print(json.dumps({'kind':kind,'triangles':triangles,'bones':len(rig.data.bones),'clips':['idle','walk','run','talk']}))
    rig.location=xyz((-38 if kind=='player' else -33,0,0))
# Leave the authored world visible, with the two workshop actors at the west.
save('11_characters.blend')
