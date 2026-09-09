"""Focused corrections from author/root inspection. Preserve v1 source and images."""
import bpy,json,random,math
from pathlib import Path
from mathutils import Vector
R=Path('/home/teknetik/code/ao2');O=R/'art/quality_20260909/basic-general';scene=bpy.data.scenes['Basic General architectural repair'];bpy.context.window.scene=scene
assert not scene.get('basic_general_v2_complete'), 'v2 already authored; preserve it.'
B=lambda p:Vector((p[0],-p[2],p[1]))
def U(p):return [round(p.x,7),round(p.z,7),round(-p.y,7)]
M={m.get('ward_slot'):m for m in bpy.data.materials if m.name.startswith('General ')and m.get('ward_slot')}
for o in scene.objects:
 if o.name.startswith(('Rear panel fixing','Service lid screw')):o.location+=B((0,0,.30))
 if o.name.startswith('Awning intermediate rib'):o.location+=B((0,-.04,0))
for name in ['Canvas','CanvasPatch']:
 m=M[name];nodes=m.node_tree.nodes;node=nodes.new('ShaderNodeTexImage');node.image=bpy.data.images.load(str(O/'textures'/(name+'_BaseColor.png')),check_existing=True);m.node_tree.links.new(node.outputs['Color'],nodes['Principled BSDF'].inputs['Base Color']);m.diffuse_color=(1,1,1,1)
# Match the warm mineral setting without making global scene material changes.
for node in M['WardConcrete'].node_tree.nodes:
 if node.type=='MIX_RGB':node.inputs[2].default_value=(.73,.62,.45,1)
M['WardConcrete'].diffuse_color=(.73,.62,.45,1)
# Stock is varied modestly, with each bundle seated on its existing shelf.
rng=random.Random(909403)
tins=sorted([o for o in scene.objects if o.name.startswith('Sealed goods tin')],key=lambda o:(round(o.location.x,3),round(o.location.z,3)))
variants=[]
for name,col in [('Tin clay',(.23,.115,.056)),('Tin pale enamel',(.45,.42,.31))]:
 m=M['Bottle'].copy();m.name='General '+name;m['ward_slot']=name;m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*col,1);variants.append(m);M[name]=m
for k,tin in enumerate(tins):
 c=tin.location.copy();base=1.013 if c.z<1.4 else 1.493;newheight=.197+[.014,.042,.003,.032,.052][k%5]
 bundle=[o for o in scene.objects if o.name.startswith(('Tin rolled lid','Tin label','Stock exact label'))and abs(o.location.x-c.x)<.025 and abs(o.location.z-c.z)<.18]
 dx=rng.uniform(-.018,.018);dz=rng.uniform(-.015,.012);dy=base+newheight/2-c.z
 tin.scale.z*=newheight/tin.dimensions.z;tin.location+=Vector((dx,-dz,dy))
 if k%4==1:tin.data.materials[0]=variants[0]
 if k%5==3:tin.data.materials[0]=variants[1]
 for o in bundle:
  o.location+=Vector((dx,-dz,dy))
  if o.name.startswith('Tin rolled lid'):o.location.z=base+newheight+.009
# Tiny actual edge chips are confined to grip/impact areas, not scattered across every panel.
parts=[o for o in scene.objects if o.type=='MESH'and o.get('group')not in[None,'Context']]
def polygon(name,points,mat,uv=None,group='Localized wear'):
 me=bpy.data.meshes.new(name);me.from_pydata([B(p)for p in points],[],[tuple(range(len(points)))]);me.update();layer=me.uv_layers.new(name='UV0')
 for li in range(len(points)):layer.data[li].uv=uv[li]if uv else[(0,0),(1,0),(1,1),(0,1)][li%4]
 me.materials.append(mat);o=bpy.data.objects.new(name,me);scene.collection.objects.link(o);o['group']=group;o['material_slot']=mat['ward_slot'];parts.append(o);return o
for i,x in enumerate([-.63,-.48,-.31,.17,.33,.71]):
 w=[.034,.07,.025,.046,.024,.035][i];y=.941;z=-.9041
 polygon('Counter grip paint loss '+str(i),[(x-w,y-.005,z),(x-w*.35,y-.009,z),(x+w,y-.005,z),(x+w*.63,y+.005,z),(x-w*.45,y+.007,z)],M['Steel'])
for i,(x,y)in enumerate([(-2.48,2.13),(2.46,2.48),(-2.44,2.47)]):
 polygon('Sign plate corner contact wear '+str(i),[(x-.012,y-.011,1.7665),(x+.026,y-.009,1.7665),(x+.013,y+.009,1.7665),(x-.008,y+.018,1.7665)],M['Steel'])
# Existing original atlas supplies a handful of collected deposits, with soft alpha edges.
dirt=bpy.data.materials.new('General Collected sand');dirt.use_nodes=True;dirt['ward_slot']='Collected sand';dirt['tile_metres']=1
p=dirt.node_tree.nodes['Principled BSDF'];p.inputs['Roughness'].default_value=.96;tex=dirt.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(R/'unity/AthenHill/Assets/AthenHill/Art/Weathering/WeatheringAtlas.png'),check_existing=True);dirt.node_tree.links.new(tex.outputs['Color'],p.inputs['Base Color']);dirt.node_tree.links.new(tex.outputs['Alpha'],p.inputs['Alpha']);M['Collected sand']=dirt
for i,(x,z,w,d)in enumerate([(-2.02,-.76,.43,.94),(1.97,-.66,.44,1.1),(-1.32,-.77,.72,.33),(1.17,-.72,.58,.36)]):
 polygon('Collected sheltered floor sand '+str(i),[(x-w/2,.002,z-d/2),(x-w/2,.002,z+d/2),(x+w/2,.002,z+d/2),(x+w/2,.002,z-d/2)],dirt,[(.02,.53),(.02,.985),(.49,.985),(.49,.53)])
# Threshold visuals reproduce the existing slab and step without changing their colliders.
for name in ['Existing porch context','Existing step context']:
 o=scene.objects[name];o['group']='Threshold';o['material_slot']='WardConcrete';parts.append(o)
scene['basic_general_v2_complete']=True
source=O/'basic-general-source-v2.blend';bpy.data.libraries.write(str(source),{scene},fake_user=True,compress=True)
# Reuse the explicit exporter, now retaining triangle winding as verified against Unity's built-in mesh.
code=(O/'author_basic_general.py').read_text();code=code[code.index('# Explicit Unity mesh interchange'):]
code=code.replace("    # Unity's clockwise front faces use the opposite winding from the right-handed authored B-space.\n    for at in range(0,len(indices),3):indices[at+1],indices[at+2]=indices[at+2],indices[at+1]\n",'')
code=code.replace('v1.json','v2.json')
materials=json.loads((O/'material-bindings-v1.json').read_text())
for m in materials:
 if m['slot']in['Canvas','CanvasPatch']:m['base']=str(O/'textures'/(m['slot']+'_BaseColor.png'));m['tint']=[1,1,1]
 if m['slot']=='WardConcrete':m['tint']=[.73,.62,.45]
materials += [{'slot':m['ward_slot'],'tint':list(m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value[:3]),'roughness':.3,'metal':.1,'tileMetres':1}for m in variants]
materials += [{'slot':'Collected sand','base':str(R/'unity/AthenHill/Assets/AthenHill/Art/Weathering/WeatheringAtlas.png'),'alpha':True,'roughness':.96,'tint':[1,1,1],'tileMetres':1}]
exec(compile(code,'export corrected Basic General','exec'))
# Review the final source under the same cameras. Preserve v1 evidence.
views=json.loads((O/'source-view-plan-v1.json').read_text());cam=scene.camera
for name,pos,target,lens in views:
 cam.location=B(pos);cam.rotation_euler=(B(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=lens;scene.render.filepath=str(O/('source-v2-'+name+'.png'));bpy.ops.render.render(write_still=True)
print('BASIC_GENERAL_V2_SOURCE_COMPLETE')
