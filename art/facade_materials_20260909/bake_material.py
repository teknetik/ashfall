"""Execute this file with FAMILY defined through the live Blender MCP."""
import bpy,json,time
from pathlib import Path
O=Path('/home/teknetik/code/ao2/art/facade_materials_20260909');outdir=O/'textures'/FAMILY;outdir.mkdir(parents=True,exist_ok=True)
scene=bpy.data.scenes['Facade material bake studio'];bpy.context.window.scene=scene
plane=scene.objects['Four metre material bake tile'];bpy.context.view_layer.objects.active=plane;plane.select_set(True)
mat=bpy.data.materials['Facade layered '+FAMILY];plane.data.materials[0]=mat;nt=mat.node_tree;out=nt.nodes['Material output'];bs=nt.nodes['Layered physical surface']
record={'family':FAMILY,'tileMetres':4,'blender':bpy.app.version_string,'device':scene.cycles.device,'maps':[]}
for name in ['BaseColor','Normal','Roughness','Metallic']:
 path=outdir/(name+'.png');assert not path.exists(),'Keep prior bake: '+str(path)
 img=bpy.data.images.new(FAMILY+' baked '+name,4096,4096,alpha=False,float_buffer=False);img.colorspace_settings.name='sRGB'if name=='BaseColor'else'Non-Color'
 target=nt.nodes.new('ShaderNodeTexImage');target.name='Bake target '+name;target.image=img;nt.nodes.active=target
 for node in nt.nodes:node.select=node==target
 socket=bs.outputs['BSDF']if name=='Normal'else nt.nodes['Bake '+name].outputs[0];nt.links.new(socket,out.inputs['Surface'])
 start=time.monotonic();bpy.ops.object.bake(type='NORMAL'if name=='Normal'else'EMIT',normal_space='TANGENT',normal_r='POS_X',normal_g='POS_Y',normal_b='POS_Z',use_clear=True,margin=24)
 img.filepath_raw=str(path);img.file_format='PNG';img.save();record['maps'].append({'name':name,'seconds':time.monotonic()-start,'file':str(path),'width':4096,'height':4096})
 nt.nodes.remove(target);bpy.data.images.remove(img)
nt.links.new(bs.outputs['BSDF'],out.inputs['Surface'])
(outdir/'bake.json').write_text(json.dumps(record,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(O/'facade-material-studio-v1.blend'))
print(json.dumps(record))
