import bpy,math,json
from pathlib import Path
from mathutils import Vector
ROOT=Path('/home/teknetik/code/ao2')
scene=bpy.context.scene
assert scene.name.startswith('AthenHill_DesertTerrain'), 'Open the final terrain source scene first.'
bpy.context.window.scene=scene
# Present the final mesh in the original city context for source-art inspection.
bpy.ops.import_scene.gltf(filepath=str(ROOT/'unity/AthenHill/Assets/AthenHill/Art/Imported/world.glb'))
for obj in list(scene.objects):
 if obj.name.startswith(('COL_','ENV_sandstone_mesa_','ENV_mesa_buttress_')):obj.hide_render=True
for obj in scene.objects:
 if obj.name.startswith('DesertBasin_'):
  mat=obj.data.materials[0];mat.use_nodes=True
  nodes=mat.node_tree.nodes;links=mat.node_tree.links;bs=nodes.get('Principled BSDF')
  tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(ROOT/'unity/AthenHill/Assets/AthenHill/Art/Terrain/SandstoneAlbedo.png'),check_existing=True);tex.projection='BOX';tex.projection_blend=.25
  coord=nodes.new('ShaderNodeTexCoord');mapping=nodes.new('ShaderNodeVectorMath');mapping.operation='SCALE';mapping.inputs[3].default_value=.073
  links.new(coord.outputs['Object'],mapping.inputs[0]);links.new(mapping.outputs[0],tex.inputs[0]);links.new(tex.outputs['Color'],bs.inputs['Base Color']);bs.inputs['Roughness'].default_value=.95
  break
scene.render.engine='CYCLES';scene.cycles.samples=8
scene.render.resolution_x=1280;scene.render.resolution_y=720
cameras=[('cam_gate',(-32,9,18),(-48,3.4,5)),('cam_avenue',(-12,7,34),(0,9,-5)),('cam_hill',(23,14,27),(0,9,0)),('cam_grid',(-10,6,-28),(0,2,-38)),('cam_whompah',(13,6.5,26),(0,3,36)),('cam_hero',(-5,3.4,9),(0,9,0))]
output=ROOT/'blender/previews/terrain-20260908';output.mkdir(exist_ok=True)
for name,p,t in cameras:
 data=bpy.data.cameras.new(name);obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj)
 data.type='PERSP';data.lens=38.6;data.clip_end=650
 obj.location=Vector((p[0],-p[2],p[1]));target=Vector((t[0],-t[2],t[1]));obj.rotation_euler=(target-obj.location).to_track_quat('-Z','Y').to_euler()
 scene.camera=obj;scene.render.filepath=str(output/(name+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/scenes/20_terrain_city_review.blend'))
print('Six source-geometry cameras rendered. Unity remains the final material and atmosphere authority.')
