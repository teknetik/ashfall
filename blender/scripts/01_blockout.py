exec(compile((ROOT/'blender/scripts/city_core.py').read_text(),'city_core.py','exec'))
# Preserve the previous probe .blend on disk, create a fresh authoring scene.
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.context.scene.name='AthenHill_AuthoredWorld'
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
ACTIVE_LANDMARK='blockout'
box('BLOCK_pavement',(0,-.3,0),(120,.6,90),'stone',0)
box('BLOCK_hill',(0,.75,0),(14,1.5,14),'grass',0)
box('BLOCK_tree',(0,11,0),(2.4,22,2.4),'bark',0)
box('BLOCK_west_wall',(-48,3.7,0),(3,7.4,90),'stone',0)
for side in [-1,1]:
    for i,z in enumerate([-18,-9,9,18]):box('BLOCK_shop_%s_%s'%(side,i),(side*22,5,z),(8,10,7),'metal',0)
box('BLOCK_hall',(10,6,-32.5),(13,12,10),'metal',0)
box('BLOCK_grid',(0,1,-38),(6,2,6),'cyan',0)
box('BLOCK_ring',(0,2,36),(12,4,6),'stone',0)
cameras_and_light();save('01_blockout.blend')
for obj in list(bpy.context.scene.objects):
    if obj.get('landmark')=='blockout':bpy.data.objects.remove(obj,do_unlink=True)
print('Blockout saved; clean authored scene ready')
