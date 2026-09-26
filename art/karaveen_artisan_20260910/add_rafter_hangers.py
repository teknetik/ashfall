"""Connect the lowered roof rails to the perimeter frame; run through MCP."""
import bpy,math,json
from pathlib import Path
from mathutils import Vector
OUT=Path('/home/teknetik/code/ao2/art/karaveen_artisan_20260910')
scene=bpy.data.scenes['KA_Artisan_Stall_v01'];bpy.context.window.scene=scene
rig=bpy.data.objects['KA_Artisan_Rig'];col=bpy.data.collections['KA_01 Frame and fixings'];material=bpy.data.materials['KA_Charcoal_Frame_Steel']
added=[]
def small_box(name,loc,dims):
    if bpy.data.objects.get(name):return
    a,b,c=[v*.5 for v in dims]
    vs=[(x,y,z) for z in (-c,c) for y in (-b,b) for x in (-a,a)]
    fs=[(0,2,3,1),(0,1,5,4),(1,3,7,5),(3,2,6,7),(2,0,4,6),(4,5,7,6)]
    mesh=bpy.data.meshes.new(name+'_mesh');mesh.from_pydata(vs,[],fs);mesh.update();mesh.uv_layers.new(name='UVMap')
    ob=bpy.data.objects.new(name,mesh);col.objects.link(ob);ob.location=loc;mesh.materials.append(material)
    mod=ob.modifiers.new('Pressed bracket corners','BEVEL');mod.width=.002;mod.segments=3
    ob['KA_component']='frame';bpy.context.view_layer.update();world=ob.matrix_world.copy();ob.parent=rig;ob.parent_type='BONE';ob.parent_bone='ROOT';ob.matrix_world=world;added.append(name)
for x in (-.75,0,.75):
    rail=bpy.data.objects['KA_Sloping_roof_rail_'+str(x)]
    length=max(v.co.z for v in rail.data.vertices)-min(v.co.z for v in rail.data.vertices)
    for sign in (-1,1):
        end=rail.matrix_world@Vector((0,0,sign*length*.5))
        y=-1.2 if end.y<0 else 1.2
        upper=bpy.data.objects['KA_Width_top_rail_'+str(y)].matrix_world.translation.z
        mid=(upper+end.z)*.5
        small_box('KA_Rafter_drop_bracket_'+str(x)+'_'+str(y),(x,y,mid),(.056,.038,upper-end.z+.030))
        small_box('KA_Rafter_cradle_'+str(x)+'_'+str(y),(x,y,end.z-.012),(.070,.075,.022))
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'karaveen-artisan-stall-v01.blend'))
print(json.dumps({'added_rafter_supports':added}))
