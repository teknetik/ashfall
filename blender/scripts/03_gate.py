ACTIVE_LANDMARK='west_gate'
for obj in list(bpy.context.scene.objects):
    if obj.get('landmark')==ACTIVE_LANDMARK:bpy.data.objects.remove(obj,do_unlink=True)

for a,b in [(-45,-3.7),(3.7,8.3),(15.7,45)]:
    box('BLD_west_wall',(-48,3.7,(a+b)/2),(3,7.4,b-a),'stone',.045,True)
    box('BLD_west_wall_coping',(-48,7.5,(a+b)/2),(3.4,.3,b-a),'metal',.045)
    for z in [a+1.3+i*5 for i in range(int((b-a)/5))]:
        box('BLD_wall_buttress',(-46.25,3.8,z),(.6,7.6,.65),'stone',.05)
        box('BLD_wall_inset',(-46.58,6.8,z+1.8),(.035,.4,2.4),'metal',.015)
        box('BLD_wall_signal',(-46.53,6.82,z+1.8),(.025,.065,1.6),'cyan',.005)

for z in [0,12]:
    for sign in [-1,1]:
        box('BLD_gate_pier',(-48,1.5,z+sign*3.25),(3,3,.9),'stone',.045,True)
        box('BLD_gate_plinth',(-46.25,.25,z+sign*3.35),(.75,.5,1.15),'stone',.035)
    # Individually authored wedge voussoirs, with narrow mortar joints.
    for j in range(18):
        start=math.pi*j/18+.003;end=math.pi*(j+1)/18-.003
        verts=[]
        for x in [-49.5,-46.5]:
            for a,r in [(start,3.68),(start,2.8),(end,2.8),(end,3.68)]:
                verts.append((x,3+math.sin(a)*r,z+math.cos(a)*r))
        obj=mesh('BLD_gate_arch_wedge',verts,[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],'stone')
        activate(obj);bev=obj.modifiers.new('wedge_edge_bevel','BEVEL');bev.width=.025;bev.segments=1
        bpy.ops.object.modifier_apply(modifier=bev.name);planar_uv(obj,8)
    # Structural spandrel blocks above curve; never an invisible wall across arch.
    for j in range(14):
        local_z=-3.68+(j+.5)*(7.36/14)
        lower=3+math.sqrt(max(0,3.68**2-local_z**2))
        h=7.4-lower
        box('BLD_gate_spandrel',(-48,lower+h/2,z+local_z),(2.9,h,7.36/14+.006),'stone',.008)
    # Collision keeps the accepted broad route and headroom.
    collider('gate_tunnel_roof',(-48,6.6,z),(3,1.6,5.6))
    for s in [-1,1]:collider('gate_arch_shoulder',(-48,4.8,z+s*2.7),(3,2.4,.85))
    box('BLD_gate_top_rail',(-48,7.5,z),(3.4,.3,7.5),'metal',.04)

for i,z in enumerate([-6,6,18]):
    box('BLD_gate_banner_pier',(-46.15,4.4,z),(.6,8.8,1.6),'stone',.05)
    box('PROP_banner_rod',(-45.77,6.6,z),(.12,.12,1.6),'metal',.02)
    verts=[];faces=[];uvs=[]
    for row in range(9):
        for col in range(5):
            u=col/4;v=row/8
            verts.append((-45.75+math.sin(v*6+u*4)*.085,6.45-v*3.4,z+(u-.5)*1.3))
            uvs.append((u,1-v))
    for row in range(8):
        for col in range(4):
            a=row*5+col;faces.append((a,a+1,a+6,a+5))
    mesh('PROP_free_column_gate_banner',verts,faces,'red',uvs)
box('PROP_gate_console',(-44.1,.7,-5),(.8,1.4,.65),'metal',.055,True)
box('PROP_gate_console_screen',(-43.68,1.13,-5),(.035,.40,.51),'cyan',.005)
if ACTIVE_LANDMARK not in AUTHORED:AUTHORED.append(ACTIVE_LANDMARK)
save('03_west_gate.blend');export_world()
