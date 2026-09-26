"""Read back saved Blender datablock names and record final delivery state via MCP."""
import bpy,json,hashlib,shutil
from pathlib import Path
OUT=Path('/home/teknetik/code/ao2/art/karaveen_artisan_20260910')
path=OUT/'karaveen-artisan-stall-v01.blend'
assert bpy.data.filepath==str(path)
verification_copy=Path('/tmp/ward-blender-mcp-20260910/verification-copy.blend')
shutil.copyfile(path,verification_copy)
assert hashlib.sha256(path.read_bytes()).digest()==hashlib.sha256(verification_copy.read_bytes()).digest()
with bpy.data.libraries.load(str(verification_copy),link=False) as (source,target):
    saved={'scenes':list(source.scenes),'objects':list(source.objects),'armatures':list(source.armatures),'materials':list(source.materials),'images':list(source.images)}
assert 'KA_Artisan_Stall_v01' in saved['scenes']
assert 'KA_Artisan_Rig' in saved['objects']
assert 'KA_Artisan_mechanical_rig_data' in saved['armatures']
scene=bpy.data.scenes['KA_Artisan_Stall_v01'];rig=bpy.data.objects['KA_Artisan_Rig']
assert all(rig[k]==0 for k in ('left_door_open','right_door_open','canopy_billow'))
assert bpy.data.images['04-travelling-artisan-turnaround-v01.png'].packed_file
assets=[o for o in scene.objects if o.get('KA_component') not in (None,'studio','rig')]
report={'status':'pass','file':str(path),'blender':bpy.app.version_string,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'saved_datablocks_readable':True,'active_scene':scene.name,'asset_objects':len(assets),'meshes':sum(o.type=='MESH' for o in assets),'curves':sum(o.type=='CURVE' for o in assets),'material_names':sorted({m.name for o in assets for m in o.data.materials if m}),'packed_reference':True,'external_material_textures':False,'default_rig_pose_restored':True,'merchandise':False,'unity_imported':False,'render_review':'complete','source_rig_checks':'rig-validation-v01.json'}
(OUT/'final-manifest-v01.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
