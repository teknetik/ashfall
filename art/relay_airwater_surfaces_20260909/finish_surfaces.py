"""Finish wrapped service UVs and retain useful whole-building source review cameras."""
import bpy,ast,json,math,hashlib
from pathlib import Path
from mathutils import Vector
R=Path('/home/teknetik/code/ao2');O=R/'art/relay_airwater_surfaces_20260909'
scene=bpy.data.scenes['Relay and Air + Water surface revision'];bpy.context.window.scene=scene
for node in ast.parse((R/'art/facade_materials_20260909/refine_facade_geometry.py').read_text()).body:
 if isinstance(node,ast.FunctionDef)and node.name in ['B','U','export']:exec(compile(ast.Module(body=[node],type_ignores=[]),'surface export','exec'))
out=[]
for ob in scene.objects:
 if ob.type!='MESH'or'material_key'not in ob:continue
 if any(k in ob.name for k in ['Filter canister','Riveted water vessel']):
  phase=int(hashlib.sha256(ob.name.encode()).hexdigest()[:8],16)/4294967296
  for uv in ob.data.uv_layers.active.data:uv.uv.x+=phase;uv.uv.y+=phase*.713
 part=export(ob.get('source_path'),ob);out.append(part)
(O/'facade-meshes-v2.json').write_text(json.dumps(out,separators=(',',':')))
manifest=json.loads((O/'geometry-manifest-v1.json').read_text());manifest['source']='relay-airwater-surfaces-v2.blend';manifest['notes']=['Continuous cylindrical wraps for tanks/filter canisters, with distinct offsets','Large unmodified surface normals retained; Boolean planes are flat with smooth small bevels','Source-camera lettering appears mirrored under the orientation-preserving Unity-to-Blender axis convention; original letter geometry is reference only and never exported in this pass. Native Unity cameras remain the review authority.']
(O/'geometry-manifest-v2.json').write_text(json.dumps(manifest,indent=2))
for family,z in [('relay_works',-18),('air_water',-9)]:
 camera=bpy.data.cameras.new(family+' full source camera');cam=bpy.data.objects.new(family+' full source camera',camera);scene.collection.objects.link(cam);cam.location=B((-6.0,5.8,z+1.8));target=B((-20.2,4.5,z));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();camera.lens=38;scene.camera=cam
 scene.render.filepath=str(O/(family+'-source-whole.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'relay-airwater-surfaces-v2.blend'))
print('Final source, varied service wraps and complete review cameras saved')
