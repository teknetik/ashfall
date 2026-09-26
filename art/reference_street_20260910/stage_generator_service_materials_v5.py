"""STAGED, NOT EXECUTED: source-only generator material v5 after Blender handover.
Requires the saved generator-v3-source-handback scene. Geometry, all original
materials and Meshy maps stay unchanged. Render only the three matched service
views via render_generator_v3_source.py with tag materials-v5 for critic review.
"""
import bpy,json,hashlib,math
from array import array
from pathlib import Path
R=Path('/home/teknetik/code/ao2');O=R/'meshy/ground-detail-20260910/generator-v3-source'
S=bpy.data.scenes.get('Generator v3 side service authoring');assert S,'Load the retained source handback explicitly before this staged material pass'
assert not (O/'service-materials-v5.json').exists() and not (O/'generator-v3-service-materials-v5.blend').exists(),'Preserve the prior material version'
assert hashlib.sha256((O/'service-materials-v4.json').read_bytes()).hexdigest()=='689d94e81808ae6e12332d6e90cf7795bc24224e353512624fe3f7d6a790bb5b','Previous material contract changed'
old_profiles=json.loads((O/'service-materials-v4.json').read_text())['profiles'];C=bpy.data.collections['Generator v3 editable source parts'];core=bpy.data.objects['GENERATOR_V3_RETAINED_CORE']
active=[o for o in C.objects if o.type=='MESH' and not o.hide_render]
for o in active:o.data.calc_loop_triangles()
assert len(active)==135 and sum(len(o.data.loop_triangles)for o in active)==2025574,'Frozen source geometry changed; inspect rather than apply blindly'
def geometry_hash(o):
 co=array('f',[0])* (len(o.data.vertices)*3);o.data.vertices.foreach_get('co',co)
 ix=array('i',[0])*len(o.data.loops);o.data.loops.foreach_get('vertex_index',ix)
 h=hashlib.sha256();h.update(co.tobytes());h.update(ix.tobytes());return h.hexdigest()
geometry_before={o.name:geometry_hash(o)for o in active}
for profile in old_profiles:
 old=bpy.data.materials.get(profile['material']);assert old,'Previous material missing'
 roster=[o.name for o in active if o!=core for slot in o.material_slots if slot.material==old]
 assert sorted(roster)==sorted(profile['objects']),'Previous material roster changed; inspect before mutation'
before=[(o.name,o.data.as_pointer(),tuple(tuple(row)for row in o.matrix_world),o.hide_render,tuple(slot.material for slot in o.material_slots))for o in active]
bpy.context.window.scene=S;profiles=[]
clamps=[{'y':-.225,'z':.612,'width':.014,'weight':.50},{'y':.225,'z':.612,'width':.019,'weight':.10},{'y':-.225,'z':.527,'width':.010,'weight':0.0},{'y':.225,'z':.527,'width':.012,'weight':.28},{'y':-.225,'z':.442,'width':.021,'weight':.06},{'y':.225,'z':.442,'width':.015,'weight':.37},{'y':-.225,'z':.357,'width':.017,'weight':.13},{'y':.225,'z':.357,'width':.010,'weight':0.0}]
for profile in old_profiles:
 kind=profile['kind'];old=bpy.data.materials.get(profile['material']);assert old
 m=old.copy();m.name={'tank':'Generator service v5 ochre paint','steel':'Generator service v5 painted frame','copper':'Generator service v5 copper','hardware':'Generator service v5 steel hardware'}[kind]
 n=m.node_tree.nodes;k=m.node_tree.links;p=n.get('Principled BSDF');g=n.new('ShaderNodeNewGeometry');g.label='Metric positions; no directional light in base color'
 def setinput(value,socket):
  if hasattr(value,'is_output'):k.new(value,socket)
  else:socket.default_value=value
 def mathnode(op,a,b=0):
  q=n.new('ShaderNodeMath');q.operation=op;setinput(a,q.inputs[0]);setinput(b,q.inputs[1]);return q.outputs[0]
 def noise(scale,offset=None):
  q=n.new('ShaderNodeTexNoise');q.inputs['Scale'].default_value=scale;q.inputs['Detail'].default_value=2;q.inputs['Roughness'].default_value=.58
  if offset:
   add=n.new('ShaderNodeVectorMath');add.operation='ADD';k.new(g.outputs['Position'],add.inputs[0]);add.inputs[1].default_value=offset;k.new(add.outputs[0],q.inputs['Vector'])
  else:k.new(g.outputs['Position'],q.inputs['Vector'])
  return q.outputs['Fac']
 def unlink(socket):
  for link in list(socket.links):k.remove(link)
 def final_mix():
  assert len(p.inputs['Base Color'].links)==1
  q=p.inputs['Base Color'].links[0].from_node;assert q.bl_idname=='ShaderNodeMixRGB';return q
 # All new variation is below a few millimetres, with bounded roughness amplitude.
 scale={'tank':650,'steel':550,'copper':720,'hardware':780}[kind]
 grain=noise(scale);rough0={'tank':.50,'steel':.50,'copper':.34,'hardware':.36}[kind];roughAmp={'tank':.14,'steel':.15,'copper':.09,'hardware':.13}[kind]
 rough=mathnode('ADD',rough0,mathnode('MULTIPLY',grain,roughAmp))
 # Remove broad color-noise modulation; retain sparse v4 paint-loss masks.
 if kind in ('tank','steel'):
  mix=final_mix();unlink(mix.inputs[1]);mix.inputs[1].default_value=(*({'tank':(.285,.140,.034),'steel':(.044,.053,.050)}[kind]),1)
 elif kind=='hardware':
  unlink(p.inputs['Base Color']);p.inputs['Base Color'].default_value=(.150,.161,.148,1)
 else:
  sep=n.new('ShaderNodeSeparateXYZ');k.new(g.outputs['Position'],sep.inputs[0]);Y=sep.outputs['Y'];Z=sep.outputs['Z'];mask=0.0
  for i,c in enumerate(clamps):
   if c['weight']==0:continue
   dy=mathnode('DIVIDE',mathnode('SUBTRACT',Y,c['y']),c['width']);dz=mathnode('DIVIDE',mathnode('SUBTRACT',Z,c['z']),.019)
   radius=mathnode('SQRT',mathnode('ADD',mathnode('MULTIPLY',dy,dy),mathnode('MULTIPLY',dz,dz)))
   envelope=mathnode('MAXIMUM',0,mathnode('SUBTRACT',1,radius));irregular=noise(125,(i*.179,i*.227,-i*.131));local=mathnode('MULTIPLY',envelope,mathnode('MULTIPLY',irregular,c['weight']))
   mask=mathnode('MAXIMUM',mask,local)
  # Low-saturation contact oxidation, unequal extent/intensity, two contacts unoxidized.
  mix=n.new('ShaderNodeMixRGB');setinput(mask,mix.inputs[0]);mix.inputs[1].default_value=(.41,.170,.068,1);mix.inputs[2].default_value=(.048,.063,.042,1);unlink(p.inputs['Base Color']);k.new(mix.outputs[0],p.inputs['Base Color'])
  unlink(p.inputs['Metallic']);k.new(mathnode('SUBTRACT',.97,mathnode('MULTIPLY',mask,.82)),p.inputs['Metallic']);rough=mathnode('ADD',rough,mathnode('MULTIPLY',mask,.17))
 unlink(p.inputs['Roughness']);k.new(rough,p.inputs['Roughness']);unlink(p.inputs['Normal'])
 bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.22;bump.inputs['Distance'].default_value={'tank':.000055,'steel':.000045,'copper':.000018,'hardware':.000024}[kind];k.new(grain,bump.inputs['Height']);k.new(bump.outputs['Normal'],p.inputs['Normal'])
 objects=[]
 for o in active:
  if o==core:continue
  for slot in o.material_slots:
   if slot.material==old:slot.link='OBJECT';slot.material=m;objects.append(o.name)
 assert sorted(objects)==sorted(profile['objects']),'Unexpected previous-material roster'
 profiles.append({'kind':kind,'material':m.name,'previousMaterial':old.name,'objects':objects,'metricGrainNoiseScale':scale,'roughnessBase':rough0,'roughnessAmplitude':roughAmp,'normalBumpDistanceMetres':bump.inputs['Distance'].default_value})
for name,mesh,matrix,visible,materials in before:
 o=bpy.data.objects[name];assert o.data.as_pointer()==mesh and tuple(tuple(row)for row in o.matrix_world)==matrix and o.hide_render==visible
assert all(geometry_hash(o)==geometry_before[o.name]for o in active),'Frozen vertex/index data changed'
assert core.material_slots[0].material==next(row[4][0]for row in before if row[0]==core.name)
record={'revision':'generator-v3-source service-materials-v5','status':'Source material audition; no native approval','sourceGeometryFrozenAtConstruction4Of5':True,'geometryHashesBeforeAndAfter':geometry_before,'originalCoreMaterialsUnchanged':True,'previousMaterialsRetained':True,'broadColorNoiseRemoved':True,'clampOxidation':clamps,'profiles':profiles,'requiredMatchedViews':['front_oblique-materials-v5','right-materials-v5','connection_close-materials-v5'],'sourceAccepted':False,'nativeAccepted':False}
(O/'service-materials-v5.json').write_text(json.dumps(record,indent=2)+'\n');bpy.data.libraries.write(str(O/'generator-v3-service-materials-v5.blend'),{S},fake_user=True,path_remap='RELATIVE');print(json.dumps({'saved':str(O/'generator-v3-service-materials-v5.blend'),'materials':len(profiles),'geometryChanged':False,'requiredViews':record['requiredMatchedViews']}))
