"""STAGED separate live-Blender panel material audition, after offline map study.
Creates a new scene/material; original source, core repair and all maps persist.
No geometry/UV changes. Protected source pixels remain exact in candidate map.
"""
import bpy,json,hashlib
from pathlib import Path
R=Path('/home/teknetik/code/ao2');D=R/'meshy/ground-detail-20260910/generator-v4-panel-study';report=json.loads((D/'panel-study-manifest.json').read_text())
assert report['outsideAuthoredMaskChangedPixels']==0 and report['protectedBoundaryChangedPixels']==0
assert hashlib.sha256((D/'base_color-authored-paint.png').read_bytes()).hexdigest()==report['candidateBaseColorSha256']
assert hashlib.sha256((D/'authored-paint-mask.png').read_bytes()).hexdigest()==report['authoringMaskSha256']
assert not (D/'generator-v4-panel-material-audition.blend').exists()
assert not bpy.data.scenes.get('Generator v4 protected panel audition'),'Inspect existing audition scene before rerunning'
OLD=bpy.data.scenes.get('Generator v4 core repair audition');assert OLD,'Review the separate core source operation first'
H=bpy.data.objects[OLD['generator_core_repair_core']];original=H.material_slots[0].material
S=bpy.data.scenes.new('Generator v4 protected panel audition');bpy.context.window.scene=S
S.unit_settings.system='METRIC';S.unit_settings.scale_length=1;S.render.engine='CYCLES';S.cycles.device=OLD.cycles.device;S.cycles.samples=24;S.cycles.use_denoising=True
S.world=OLD.world;S.view_settings.view_transform=OLD.view_settings.view_transform;S.view_settings.exposure=OLD.view_settings.exposure;S.render.resolution_x=1400;S.render.resolution_y=1100;S.render.resolution_percentage=100;S.render.image_settings.file_format='PNG';S.render.image_settings.color_mode='RGBA'
cp={}
for o in OLD.objects:
 q=o.copy();S.collection.objects.link(q);q.hide_set(q.hide_render);cp[o]=q
 if o==OLD.camera:q.data=o.data.copy();S.camera=q
for old,q in cp.items():
 if old.parent in cp:q.parent=cp[old.parent];q.matrix_world=old.matrix_world.copy()
core=cp[H];core.name='GENERATOR_V4_PROTECTED_PANEL_CORE';material=original.copy();material.name='Generator v4 authored panel paint candidate'
n=material.node_tree.nodes;k=material.node_tree.links;p=n.get('Principled BSDF')
base=n.new('ShaderNodeTexImage');base.name='Authored protected panel base color';base.image=bpy.data.images.load(str(D/'base_color-authored-paint.png'),check_existing=True);base.image.colorspace_settings.name='sRGB';assert list(base.image.size)==[4096,4096];k.new(base.outputs['Color'],p.inputs['Base Color'])
mask=n.new('ShaderNodeTexImage');mask.name='Protected authored paint interior mask';mask.image=bpy.data.images.load(str(D/'authored-paint-mask.png'),check_existing=True);mask.image.colorspace_settings.name='Non-Color';mask.extension='EXTEND'
g=n.new('ShaderNodeNewGeometry');noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=650;noise.inputs['Detail'].default_value=2;noise.inputs['Roughness'].default_value=.58;k.new(g.outputs['Position'],noise.inputs['Vector'])
def mathnode(op,a,b):
 x=n.new('ShaderNodeMath');x.operation=op
 for value,socket in [(a,x.inputs[0]),(b,x.inputs[1])]:
  if hasattr(value,'is_output'):k.new(value,socket)
  else:socket.default_value=value
 return x.outputs[0]
factor=mask.outputs['Color'];inverse=mathnode('SUBTRACT',1,factor);rough=mathnode('ADD',.53,mathnode('MULTIPLY',noise.outputs['Fac'],.12))
for name,replacement in [('Roughness',rough),('Metallic',0.0)]:
 socket=p.inputs[name];source=socket.links[0].from_socket if socket.links else socket.default_value
 mixed=mathnode('ADD',mathnode('MULTIPLY',source,inverse),mathnode('MULTIPLY',replacement,factor));k.new(mixed,socket)
normal=p.inputs['Normal'].links[0].from_socket if p.inputs['Normal'].links else g.outputs['Normal'];b=n.new('ShaderNodeBump');b.inputs['Strength'].default_value=.20;b.inputs['Distance'].default_value=.000045;k.new(noise.outputs['Fac'],b.inputs['Height'])
mix=n.new('ShaderNodeMixRGB');k.new(factor,mix.inputs[0]);k.new(normal,mix.inputs[1]);k.new(b.outputs['Normal'],mix.inputs[2]);normalize=n.new('ShaderNodeVectorMath');normalize.operation='NORMALIZE';k.new(mix.outputs[0],normalize.inputs[0]);k.new(normalize.outputs[0],p.inputs['Normal'])
core.material_slots[0].link='OBJECT';core.material_slots[0].material=material
assert core.data==H.data and core.matrix_world==H.matrix_world and H.material_slots[0].material==original
S['generator_panel_output']=str(D);S['generator_panel_core']=core.name;S['generator_panel_original_material']=original.name;S['generator_panel_candidate_material']=material.name
record={'scene':S.name,'core':core.name,'originalMaterial':original.name,'candidateMaterial':material.name,'geometryAndUvUnchanged':True,'originalCoreSceneAndMapsUnchanged':True,'candidateStudy':report,'authoringResponse':'Authored paint interiors only: fine 650/m noise normal (45 micrometre bump) and roughness .53..65, metallic0. Original source PBR remains outside the explicit mask.','requiredReview':['Same-geometry before/after PBR close-up','True albedo-emission before/after','Material-mask close-up with preserved glyph/paint edges','Reject residual grid, damaged fine wear/letters, waxy interior or mask response seams'],'sourceAccepted':False,'nativeAccepted':False}
(D/'material-audition-manifest.json').write_text(json.dumps(record,indent=2)+'\n');bpy.data.libraries.write(str(D/'generator-v4-panel-material-audition.blend'),{S},fake_user=True,path_remap='RELATIVE');print(json.dumps({'scene':S.name,'file':str(D/'generator-v4-panel-material-audition.blend'),'sourceAccepted':False}))
