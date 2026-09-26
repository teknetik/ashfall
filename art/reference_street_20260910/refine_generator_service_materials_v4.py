"""Live Blender: localized, lighting-independent service-material source revision.
Keeps original Meshy PBR and all previous authored materials unchanged.
"""
import bpy,json,math
from pathlib import Path
R=Path('/home/teknetik/code/ao2');O=R/'meshy/ground-detail-20260910/generator-v3-source'
assert not (O/'generator-v3-service-materials-v4.blend').exists()
S=bpy.data.scenes['Generator v3 side service authoring'];bpy.context.window.scene=S
C=bpy.data.collections['Generator v3 editable source parts'];profiles=[]
def create(oldname,kind):
 old=bpy.data.materials[oldname];m=old.copy();m.name=oldname+' localized source v4';n=m.node_tree.nodes;k=m.node_tree.links;p=n.get('Principled BSDF')
 for socket in ['Base Color','Metallic','Roughness','Normal']:
  for link in list(p.inputs[socket].links):k.remove(link)
 g=n.new('ShaderNodeNewGeometry');sep=n.new('ShaderNodeSeparateXYZ');k.new(g.outputs['Position'],sep.inputs[0])
 def value(v,s):
  if hasattr(v,'is_output'):k.new(v,s)
  else:s.default_value=v
 def mathnode(op,a,b=0):
  x=n.new('ShaderNodeMath');x.operation=op;value(a,x.inputs[0]);value(b,x.inputs[1]);return x.outputs[0]
 def add(a,b):return mathnode('ADD',a,b)
 def mul(a,b):return mathnode('MULTIPLY',a,b)
 def sub(a,b):return mathnode('SUBTRACT',a,b)
 def ab(a):return mathnode('ABSOLUTE',a)
 def lt(a,b):return mathnode('LESS_THAN',a,b)
 def gt(a,b):return mathnode('GREATER_THAN',a,b)
 def maximum(a,b):return mathnode('MAXIMUM',a,b)
 def noise(scale,detail=2):
  x=n.new('ShaderNodeTexNoise');x.inputs['Scale'].default_value=scale;x.inputs['Detail'].default_value=detail;x.inputs['Roughness'].default_value=.62;k.new(g.outputs['Position'],x.inputs['Vector']);return x.outputs['Fac']
 def mix(mask,a,b):
  x=n.new('ShaderNodeMixRGB');x.blend_type='MIX';value(mask,x.inputs[0]);x.inputs[1].default_value=(*a,1);x.inputs[2].default_value=(*b,1);return x.outputs[0]
 y=sep.outputs['Y'];z=sep.outputs['Z'];fine=noise(155,2);broad=noise(7.3,3);chips=noise(62,2);ay=ab(y)
 if kind=='tank':
  bands=lt(ab(sub(ay,.225)),.034);ends=gt(ay,.295);bottom=lt(z,.722);zone=maximum(maximum(bands,ends),bottom)
  wear=mul(zone,gt(chips,.670));wear=maximum(wear,mul(gt(fine,.760),.40))
  paint=mix(broad,(.23,.109,.025),(.34,.173,.044));base=n.new('ShaderNodeMixRGB');k.new(wear,base.inputs[0]);k.new(paint,base.inputs[1]);base.inputs[2].default_value=(.10,.085,.051,1);k.new(base.outputs[0],p.inputs['Base Color'])
  k.new(mul(wear,.71),p.inputs['Metallic']);k.new(add(.51,mul(broad,.17)),p.inputs['Roughness']);bd=.00012
  explanation='Ochre paint mottling; rub-through localized at two strap bands, rolled ends and lower handling edge; sparse smaller chips elsewhere.'
 elif kind=='steel':
  convex=mul(lt(ab(sub(ay,.414)),.027),maximum(lt(ab(sub(z,.974)),.030),lt(ab(sub(z,.092)),.028)));lower=lt(z,.15);jointZ=maximum(lt(ab(sub(z,.655)),.040),lt(ab(sub(z,.16)),.040));joint=mul(jointZ,gt(ay,.335));zone=maximum(convex,maximum(lower,joint))
  wear=mul(zone,gt(chips,.665));color=mix(broad,(.033,.041,.039),(.059,.068,.062));base=n.new('ShaderNodeMixRGB');k.new(wear,base.inputs[0]);k.new(color,base.inputs[1]);base.inputs[2].default_value=(.135,.140,.128,1);k.new(base.outputs[0],p.inputs['Base Color']);k.new(add(.025,mul(wear,.70)),p.inputs['Metallic']);k.new(add(.52,mul(broad,.16)),p.inputs['Roughness']);bd=.00011
  explanation='Dark painted steel, restrained paint loss on convex edges, base contact region and actual outrigger joint heights; no directional color lighting.'
 elif kind=='copper':
  contact=lt(ab(sub(ay,.225)),.026);patina=mul(contact,gt(chips,.49));base=mix(broad,(.32,.111,.040),(.48,.208,.085));mx=n.new('ShaderNodeMixRGB');k.new(patina,mx.inputs[0]);k.new(base,mx.inputs[1]);mx.inputs[2].default_value=(.035,.065,.049,1);k.new(mx.outputs[0],p.inputs['Base Color']);k.new(sub(.97,mul(patina,.80)),p.inputs['Metallic']);k.new(add(.32,add(mul(broad,.10),mul(patina,.18))),p.inputs['Roughness']);bd=.000035
  explanation='Copper color variation with localized dull oxidation at restraint contacts; copper remains metallic elsewhere.'
 else:
  k.new(mix(broad,(.105,.113,.106),(.185,.193,.173)),p.inputs['Base Color']);p.inputs['Metallic'].default_value=.78;k.new(add(.37,mul(broad,.17)),p.inputs['Roughness']);bd=.000045
  explanation='Fastener/strap exposed steel with subtle non-directional roughness variation.'
 bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.17;bump.inputs['Distance'].default_value=bd;k.new(fine,bump.inputs['Height']);k.new(bump.outputs['Normal'],p.inputs['Normal'])
 changed=[]
 for o in C.objects:
  if o.type!='MESH' or o.hide_render or o.name=='GENERATOR_V3_RETAINED_CORE':continue
  for slot in o.material_slots:
   if slot.material==old:slot.link='OBJECT';slot.material=m;changed.append(o.name)
 profiles.append({'material':m.name,'retainedPrevious':old.name,'kind':kind,'description':explanation,'objects':changed,'normalBumpDistanceMetres':bd})
 return m
create('Service tank ochre paint localized source v3','tank');create('Service cradle dark painted steel localized source v3','steel');create('Service cooling tube copper localized source v3','copper');create('Service hardware exposed steel localized source v3','hardware')
record={'revision':'generator-v3-source service-materials-v4','method':'Live Blender procedural source materials, to be baked to explicit PBR maps after source acceptance','sourceMeshyTexturesUnchanged':True,'lightingIndependentBaseColor':True,'profiles':profiles,'sourceAccepted':False,'nativeAccepted':False}
(O/'service-materials-v4.json').write_text(json.dumps(record,indent=2)+'\n');bpy.data.libraries.write(str(O/'generator-v3-service-materials-v4.blend'),{S},fake_user=True,path_remap='RELATIVE');print(json.dumps({'materials':len(profiles),'assignedObjects':sum(len(p['objects'])for p in profiles),'saved':str(O/'generator-v3-service-materials-v4.blend')}))
