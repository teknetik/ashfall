"""Create editable seamless layered materials through the live Blender MCP.
All physical shading stays in normal/roughness maps; emission bakes contain no lighting.
"""
import bpy,math,json
from pathlib import Path
R=Path('/home/teknetik/code/ao2');O=R/'art/facade_materials_20260909'
assert 'Facade material bake studio' not in bpy.data.scenes,'Preserve the existing studio'
scene=bpy.data.scenes.new('Facade material bake studio');bpy.context.window.scene=scene
scene.unit_settings.system='METRIC';scene.render.engine='CYCLES';scene.cycles.samples=4
scene.cycles.use_denoising=False;scene.render.bake.margin=24
scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0;scene.view_settings.gamma=1
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.image_settings.color_depth='8'
try:
 prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='CUDA';prefs.get_devices()
 for device in prefs.devices:device.use=device.type=='CUDA'
 scene.cycles.device='GPU' if any(d.use for d in prefs.devices)else'CPU'
except Exception:scene.cycles.device='CPU'
me=bpy.data.meshes.new('Four metre material tile');me.from_pydata([(-2,-2,0),(2,-2,0),(2,2,0),(-2,2,0)],[],[(0,1,2,3)]);me.update()
uv=me.uv_layers.new(name='UV0')
for loop,v in zip(me.loops,[(0,0),(1,0),(1,1),(0,1)]):uv.data[loop.index].uv=v
plane=bpy.data.objects.new('Four metre material bake tile',me);scene.collection.objects.link(plane);bpy.context.view_layer.objects.active=plane;plane.select_set(True)

def build(family,base,normal,rough,aggregate=None):
 mat=bpy.data.materials.new('Facade layered '+family);mat.use_nodes=True;nt=mat.node_tree;nt.nodes.clear();nodes=nt.nodes;links=nt.links
 def n(kind,name):a=nodes.new(kind);a.label=name;a.name=name;return a
 def link(value,socket):
  if hasattr(value,'node'):links.new(value,socket)
  else:
   if isinstance(value,(int,float)) and hasattr(socket.default_value,'__len__'):value=tuple([value]*len(socket.default_value))
   socket.default_value=value
 def mathnode(op,a,b=0,name=None):
  q=n('ShaderNodeMath',name or op);q.operation=op;link(a,q.inputs[0]);link(b,q.inputs[1]);return q.outputs[0]
 def mix(a,b,f,name):
  q=n('ShaderNodeMixRGB',name);q.blend_type='MIX';link(f,q.inputs[0]);link(a,q.inputs[1]);link(b,q.inputs[2]);return q.outputs[0]
 def ramp(a,lo,hi,name):
  q=n('ShaderNodeMapRange',name);q.clamp=True;link(a,q.inputs['Value']);q.inputs['From Min'].default_value=lo;q.inputs['From Max'].default_value=hi;return q.outputs['Result']
 tex=n('ShaderNodeTexCoord','Tile UV');sep=n('ShaderNodeSeparateXYZ','UV axes');links.new(tex.outputs['UV'],sep.inputs[0]);turn=[mathnode('MULTIPLY',sep.outputs[k],math.tau)for k in ['X','Y']]
 xyzw=[mathnode('COSINE',turn[0]),mathnode('SINE',turn[0]),mathnode('COSINE',turn[1]),mathnode('SINE',turn[1])]
 vector=n('ShaderNodeCombineXYZ','Periodic four dimensional coordinates')
 for i in range(3):link(xyzw[i],vector.inputs[i])
 def noise(scale,name,detail=3):
  q=n('ShaderNodeTexNoise',name);q.noise_dimensions='4D';link(vector.outputs[0],q.inputs['Vector']);link(xyzw[3],q.inputs['W']);q.inputs['Scale'].default_value=scale;q.inputs['Detail'].default_value=detail;q.inputs['Roughness'].default_value=.68;return q.outputs['Fac']
 def image(path,name,color=True):
  q=n('ShaderNodeTexImage',name);q.image=bpy.data.images.load(str(R/path),check_existing=True);q.image.colorspace_settings.name='sRGB'if color else'Non-Color';q.extension='REPEAT';links.new(tex.outputs['UV'],q.inputs['Vector']);return q.outputs['Color']
 albedo=image(base,'Photographic colour');normal_image=image(normal,'Photographic normal',False);roughness=image(rough,'Photographic roughness',False)
 macro=noise(.65,'Uneven weather exposure',2);meso=noise(4.8,'Repair and flake boundaries');fine=noise(76,'Grain and pores');tiny=noise(225,'Fine mineral pits',2)
 nm=n('ShaderNodeNormalMap','Source material relief');nm.inputs['Strength'].default_value=.8;link(normal_image,nm.inputs['Color']);surface_normal=nm.outputs[0]
 roughness=mathnode('MULTIPLY',roughness,.78)
 # Separate named output values make the bakes repeatable and inspectable.
 metallic=0;crack=0
 if family=='Plaster':
  aggregate_color=image(aggregate,'Exposed mineral aggregate');repair=ramp(mathnode('ADD',meso,mathnode('MULTIPLY',macro,.27)),.685,.735,'Ragged repair edges')
  aged=mix(albedo,(.40,.345,.265,1),ramp(macro,.36,.70,'Faded limewash'),'Sun faded plaster')
  aggregate_color=mix(aggregate_color,(.22,.19,.14,1),.48,'Warm mineral undercoat')
  color=mix(aged,aggregate_color,mathnode('MULTIPLY',repair,.64),'Exposed aggregate and old repairs')
  band=mathnode('ABSOLUTE',mathnode('SUBTRACT',noise(2.4,'Fine branching fracture contours',4),.515))
  crack=mathnode('MULTIPLY',mathnode('SUBTRACT',1,ramp(band,.00035,.0019,'Hairline fracture width')),ramp(macro,.47,.62,'Localized fracture mask'))
  color=mix(color,(.085,.066,.043,1),mathnode('MULTIPLY',crack,.50),'Hairline crack colour')
  height=mathnode('ADD',mathnode('MULTIPLY',fine,.23),mathnode('MULTIPLY',tiny,.14));height=mathnode('SUBTRACT',height,mathnode('MULTIPLY',repair,.40));height=mathnode('SUBTRACT',height,mathnode('MULTIPLY',crack,.45))
  roughness=mathnode('ADD',roughness,.20);distance=.008
 elif family=='Stone':
  salt=ramp(macro,.43,.63,'Mineral weather patches');color=mix(albedo,(.34,.295,.215,1),mathnode('MULTIPLY',salt,.45),'Uneven sandstone mineral tone')
  color=mix(color,(.11,.087,.059,1),mathnode('MULTIPLY',ramp(fine,.62,.73,'Localized stone pores'),.30),'Pitted stone')
  height=mathnode('ADD',mathnode('MULTIPLY',fine,.28),mathnode('MULTIPLY',tiny,.16));roughness=mathnode('ADD',roughness,.18);distance=.006
 else:
  rust=ramp(mathnode('ADD',meso,mathnode('MULTIPLY',macro,.28)),.70,.76,'Irregular paint loss')
  paint=mix((.015,.022,.022,1),(.066,.077,.070,1),ramp(macro,.30,.72,'Paint fading'),'Chalked dark green steel paint')
  rust_color=mix(albedo,(.20,.068,.023,1),.40,'Oxide under old coating');color=mix(paint,rust_color,rust,'Corroded shutter surface')
  height=mathnode('SUBTRACT',mathnode('MULTIPLY',fine,.10),mathnode('MULTIPLY',rust,.48));roughness=mix((.57,.57,.57,1),(.96,.96,.96,1),rust,'Paint and oxide roughness');metallic=mathnode('MULTIPLY',mathnode('SUBTRACT',1,rust),.12);distance=.004
 bump=n('ShaderNodeBump','Baked fine relief in metres');bump.inputs['Distance'].default_value=distance;bump.inputs['Strength'].default_value=1;link(height,bump.inputs['Height']);link(surface_normal,bump.inputs['Normal'])
 bs=n('ShaderNodeBsdfPrincipled','Layered physical surface');link(color,bs.inputs['Base Color']);link(bump.outputs['Normal'],bs.inputs['Normal']);link(roughness,bs.inputs['Roughness']);link(metallic,bs.inputs['Metallic'])
 out=n('ShaderNodeOutputMaterial','Material output');links.new(bs.outputs['BSDF'],out.inputs['Surface'])
 for name,value in [('Bake BaseColor',color),('Bake Roughness',roughness),('Bake Metallic',metallic)]:
  q=n('ShaderNodeEmission',name);link(value,q.inputs['Color'])
 mat['tileMetres']=4.0;mat['normalConvention']='OpenGL tangent +Y';mat['family']=family
 return mat

S='refs/quality_20260909/building-materials/'
materials=[]
for family,src in [('Plaster','beige_wall_001'),('Stone','rock_surface'),('Steel','rusty_metal_sheet')]:
 materials.append(build(family,S+src+'/'+src+'_diff_4k.png',S+src+'/'+src+'_nor_gl_4k.png',S+src+'/'+src+'_rough_4k.png',S+'rough_concrete/rough_concrete_diff_4k.png'))
plane.data.materials.append(materials[0])
bpy.ops.wm.save_as_mainfile(filepath=str(O/'facade-material-studio-v1.blend'))
print(json.dumps({'materials':[m.name for m in materials],'device':scene.cycles.device,'tileMetres':4,'bakeResolution':4096}))
