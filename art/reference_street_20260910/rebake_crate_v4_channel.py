"""Live Blender one-channel projection bake from full retained crate source."""
import bpy,json,time
from pathlib import Path
R=Path('/home/teknetik/code/ao2');O=R/'meshy/ground-detail-20260910/crate-v4-runtime'
C=globals().get('BAKE_CHANNEL','base_color');assert C in ['base_color','metallic','roughness','normal']
assert not (O/'model_textures'/(C+'.png')).exists(),'Immutable baked channel exists'
S=bpy.data.scenes['Crate v4 source to near PBR bake'];bpy.context.window.scene=S
H=bpy.data.objects['CRATE_V4_HIGH'];L=bpy.data.objects['CRATE_V4_LOW']
HM=H.data.materials[0];LM=L.data.materials[0];N=HM.node_tree.nodes;K=HM.node_tree.links;OUT=N.get('Material Output')
for link in list(OUT.inputs['Surface'].links):K.remove(link)
if C=='normal':K.new(N.get('Principled BSDF').outputs['BSDF'],OUT.inputs['Surface'])
else:
 E=N.get('BAKE_EMISSION') or N.new('ShaderNodeEmission');E.name='BAKE_EMISSION';E.inputs['Strength'].default_value=1
 for link in list(E.inputs['Color'].links):K.remove(link)
 K.new(N['SOURCE_'+C].outputs['Color'],E.inputs['Color']);K.new(E.outputs[0],OUT.inputs['Surface'])
I=bpy.data.images.new('CRATE_V4_BAKED_'+C,width=4096,height=4096,alpha=False,float_buffer=False)
I.colorspace_settings.name='sRGB' if C=='base_color' else 'Non-Color';I.filepath_raw=str(O/'model_textures'/(C+'.png'));I.file_format='PNG'
T=LM.node_tree.nodes.new('ShaderNodeTexImage');T.name='BAKED_'+C;T.image=I
for node in LM.node_tree.nodes:node.select=False
T.select=True;LM.node_tree.nodes.active=T
for ob in S.objects:ob.select_set(False)
H.hide_render=False;H.hide_set(False);L.hide_set(False);H.select_set(True);L.select_set(True);bpy.context.view_layer.objects.active=L
start=time.time();bpy.ops.object.bake(type='NORMAL' if C=='normal' else 'EMIT');I.save()
record=dict(channel=C,seconds=time.time()-start,dimensions=[I.size[0],I.size[1]],path=str(I.filepath_raw),method='source normal including source normal texture to target tangent basis' if C=='normal' else 'emission projection without scene lighting',colorspace=I.colorspace_settings.name)
(O/('bake-'+C+'.json')).write_text(json.dumps(record,indent=2));print(json.dumps(record))
