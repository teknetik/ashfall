"""Run through Blender MCP after authoring; attach cloth details and verify rig."""
import bpy, math, json
from pathlib import Path
from mathutils import Vector
OUT=Path('/home/teknetik/code/ao2/art/karaveen_artisan_20260910')
scene=bpy.data.scenes['KA_Artisan_Stall_v01'];bpy.context.window.scene=scene
rig=bpy.data.objects['KA_Artisan_Rig']
roof=bpy.data.objects['KA_Tensioned_sand_canvas']
prefixes=('KA_Stitched_roof_repair_','KA_Patch_seam_','KA_Reinforced_canopy_seams','KA_Double_rows_of_stitching')
attached=[]
for obj in scene.objects:
    if obj.name.startswith(prefixes) and obj.type in ('MESH','CURVE'):
        if not obj.data.shape_keys:obj.shape_key_add(name='Basis')
        key=obj.data.shape_keys.key_blocks.get('Soft billow') or obj.shape_key_add(name='Soft billow')
        basis=obj.data.shape_keys.key_blocks['Basis']
        inv=obj.matrix_world.inverted().to_3x3()
        for src,dst in zip(basis.data,key.data):
            co=obj.matrix_world@src.co
            u=max(0,min(1,(co.x+1.65)/3.3));v=max(0,min(1,(co.y+1.35)/2.7))
            dz=.035*math.sin(math.pi*u)**2*math.sin(math.pi*v)**2*math.sin(3*math.pi*u+v)
            dst.co=src.co+inv@Vector((0,0,dz))
        try:key.driver_remove('value')
        except Exception:pass
        d=key.driver_add('value').driver;d.type='SCRIPTED'
        var=d.variables.new();var.name='billow';var.type='SINGLE_PROP';var.targets[0].id=rig;var.targets[0].data_path='["canopy_billow"]';d.expression='billow'
        attached.append(obj.name)

def update():
    rig.update_tag(refresh={'OBJECT'});scene.frame_set(1);bpy.context.view_layer.update()

rig['left_door_open']=0.;rig['right_door_open']=0.;rig['canopy_billow']=0.;update()
closed={s:list(bpy.data.objects['KA_Cupboard_door_'+s].matrix_world.translation) for s in ('L','R')}
rig['left_door_open']=90.;rig['right_door_open']=90.;update()
opened={s:list(bpy.data.objects['KA_Cupboard_door_'+s].matrix_world.translation) for s in ('L','R')}
for s in ('L','R'):
    assert opened[s][1] < closed[s][1]-.4, ('Door failed outward swing',s,closed[s],opened[s])
rig['left_door_open']=0.;rig['right_door_open']=0.;rig['canopy_billow']=1.;update()
for name in ['KA_Tensioned_sand_canvas']+attached:
    assert abs(bpy.data.objects[name].data.shape_keys.key_blocks['Soft billow'].value-1)<1e-5,('Cloth driver failed',name)
key=roof.data.shape_keys.key_blocks['Soft billow'];basis=roof.data.shape_keys.key_blocks['Basis']
max_billow=max((a.co-b.co).length for a,b in zip(key.data,basis.data))
assert .02 < max_billow < .04
for a,b in zip(key.data,basis.data):
    if abs(abs(b.co.x)-1.65)<1e-5 or abs(abs(b.co.y)-1.35)<1e-5:
        assert (a.co-b.co).length<1e-5,'Canopy edge detached'
rig['canopy_billow']=0.;update()
root=rig.pose.bones['ROOT'];root.location=(.4,.2,.1);update()
root_displacement=list(bpy.data.objects['KA_Cupboard_door_L'].matrix_world.translation-Vector(closed['L']))
assert Vector(root_displacement).length > .4
root.location=(0,0,0);update()
assets=[o for o in scene.objects if o.get('KA_component') not in (None,'studio','rig')]
assert all(o.parent==rig for o in assets)
assert all(all(abs(v-1)<1e-6 for v in o.scale) for o in assets),'Unexpected scale'
bounds=[]
for o in assets:
    e=o.evaluated_get(bpy.context.evaluated_depsgraph_get())
    if o.type=='CURVE':
        # Blender's shape-key curve bounds include control radii; measure rendered geometry.
        mesh=e.to_mesh()
        bounds += [e.matrix_world@v.co for v in mesh.vertices]
        e.to_mesh_clear()
    else:
        bounds += [e.matrix_world@Vector(c) for c in e.bound_box]
mins=[min(v[i] for v in bounds) for i in range(3)];maxs=[max(v[i] for v in bounds) for i in range(3)]
assert -0.015<mins[2]<.015,('Ground contact',mins)
assert 2.64<maxs[2]<2.70,('Roof height',maxs)
assert not any(any(word in o.name.lower() for word in ('pottery','merchandise','rug_','plant_')) for o in assets)
bad_uv=[o.name for o in assets if o.type=='MESH' and not o.data.uv_layers]
assert not bad_uv,bad_uv
report={'status':'pass','scope':'Blender source geometry and mechanical rig; no Unity work','asset_objects':len(assets),'bounds_min':mins,'bounds_max':maxs,'closed_door_centres':closed,'open_90_degree_centres':opened,'root_displacement':root_displacement,'cloth_details_following_billow':attached,'max_billow_m':max_billow,'canopy_edges_pinned':True,'mesh_uvs_present':True,'merchandise_present':False,'door_restored_degrees':[rig['left_door_open'],rig['right_door_open']],'billow_restored':rig['canopy_billow']}
(OUT/'rig-validation-v01.json').write_text(json.dumps(report,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'karaveen-artisan-stall-v01.blend'))
print(json.dumps(report))
