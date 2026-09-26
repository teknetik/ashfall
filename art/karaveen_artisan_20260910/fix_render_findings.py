"""Focused corrections from native Blender image review, executed via MCP."""
import bpy,math,json,sys
from pathlib import Path
from mathutils import Vector
OUT=Path('/home/teknetik/code/ao2/art/karaveen_artisan_20260910')
scene=bpy.data.scenes['KA_Artisan_Stall_v01'];bpy.context.window.scene=scene
rig=bpy.data.objects['KA_Artisan_Rig'];bpy.context.view_layer.update()
corrected=[]
for o in scene.objects:
    if o.name.startswith('KA_Sloping_roof_rail_') and not o.get('KA_sag_clearance_fixed'):
        if not any(o.name.endswith(s) for s in ('_-1.5','_1.5')):
            world=o.matrix_world.copy();world.translation.z-=.070;o.matrix_world=world
            o['KA_sag_clearance_fixed']=True;corrected.append(o.name)
    if o.name.startswith('KA_Shelf_upright_') and not o.get('KA_ground_contact_fixed'):
        # Extend the existing support down to 5 mm above ground; attach a rubber cap below.
        for v in o.data.vertices:
            if v.co.z < 0:v.co.z-=.035
        o.data.update();o['KA_ground_contact_fixed']=True;corrected.append(o.name)

# Add small rubber feet without merging or moving the separate display rack.
col=bpy.data.collections['KA_04 Empty display fixtures']
mat=bpy.data.materials['KA_Rubber_Feet']
for dx in (-.34,.34):
    for dy in (-.19,.19):
        name='KA_Shelf_rubber_cap_'+str(dx)+'_'+str(dy)
        if bpy.data.objects.get(name):continue
        verts=[(x,y,z) for z in (-.0125,.0125) for y in (-.034,.034) for x in (-.034,.034)]
        faces=[(0,2,3,1),(0,1,5,4),(1,3,7,5),(3,2,6,7),(2,0,4,6),(4,5,7,6)]
        me=bpy.data.meshes.new(name+'_mesh');me.from_pydata(verts,[],faces);me.update();me.uv_layers.new(name='UVMap')
        o=bpy.data.objects.new(name,me);col.objects.link(o);o.location=(.94+dx,.945+dy,.0125);o.data.materials.append(mat)
        b=o.modifiers.new('Rounded rubber edges','BEVEL');b.width=.006;b.segments=3
        o['KA_component']='shelf';bpy.context.view_layer.update();world=o.matrix_world.copy();o.parent=rig;o.parent_type='BONE';o.parent_bone='ROOT';o.matrix_world=world;corrected.append(name)

# Slightly more readable natural cloth folds, anchored along the upper valance seam.
o=bpy.data.objects['KA_Front_sewn_valance']
if not o.get('KA_valance_refined'):
    for p in o.data.vertices:
        u=(p.co.x+1.65)/3.3
        v=max(0,min(1,(2.30-p.co.z)/(.21+.018*math.sin(math.pi*u))))
        p.co.y-=.018*math.sin(12*math.pi*u+.2)*v**1.5
        p.co.z-=.012*(.5-.5*math.cos(10*math.pi*u))*v
    o.data.update();o['KA_valance_refined']=True;corrected.append(o.name)

bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'karaveen-artisan-stall-v01.blend'))
print(json.dumps({'corrections':corrected,'scope':'rafter/cloth clearance, shelf ground contact, sewn valance folds'}))
