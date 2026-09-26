"""Keep large construction planes flat while smoothly shading their small worn bevels."""
import bpy,ast,json
from pathlib import Path
from mathutils import Vector
R=Path('/home/teknetik/code/ao2');O=R/'art/facade_materials_20260909'
scene=bpy.data.scenes['Refined facade surfaces v1'];bpy.context.window.scene=scene
for node in ast.parse((O/'refine_facade_geometry.py').read_text()).body:
 if isinstance(node,ast.FunctionDef)and node.name in ['B','U','export']:exec(compile(ast.Module(body=[node],type_ignores=[]),'facade export','exec'))
targets={o['source_path']:o for o in scene.objects if o.type=='MESH'and o.get('material_key')in ['Plaster','Stone','Steel']and 'source_path'in o}
for ob in targets.values():
 me=ob.data
 me.normals_split_custom_set([(0,0,0)]*len(me.loops))
 for face in me.polygons:face.use_smooth=max(abs(v)for v in face.normal)<.999
 me.update()
out=[export(path,ob)for path,ob in targets.items()]
(O/'facade-meshes-v2.json').write_text(json.dumps(out,separators=(',',':')))
manifest=json.loads((O/'geometry-manifest-v1.json').read_text());manifest['source']='facade-surfaces-v2.blend';manifest['notes'].append('Large wall planes retain flat normals after Boolean/bevel operations; smooth shading limited to sloped bevel faces.')
(O/'geometry-manifest-v2.json').write_text(json.dumps(manifest,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(O/'facade-surfaces-v2.blend'))
scene.render.filepath=str(O/'source-review-v2.png');bpy.ops.render.render(write_still=True)
print('Saved corrected facade normals, source and review')
