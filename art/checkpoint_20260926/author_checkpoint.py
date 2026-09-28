"""Checkpoint source: authored in live Blender through MCP, local metre dimensions."""
import bpy,sys,json,math,random
from pathlib import Path
from mathutils import Vector
ROOT=Path('/home/teknetik/code/ao2');OUT=ROOT/'art/checkpoint_20260926'
# Dedicated collection preserves the starting scene.
coll=bpy.data.collections.get('West Gate checkpoint source')
if coll:
 for ob in list(coll.objects):bpy.data.objects.remove(ob,do_unlink=True)
 bpy.data.collections.remove(coll)
# Reuse the project's texture/provenance kit; address nodes by type.
k={};src=(ROOT/'art/ward_retrofit_20260926/kit.py').read_text().replace("nt.nodes['Principled BSDF']","next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')").replace("m.node_tree.nodes['Principled BSDF']","next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')")
exec(compile(src,'ward_kit','exec'),k)
col=k['new_collection']('West Gate checkpoint source');k['CUR']['coll']=col
M=k['M'];box=k['box'];cyl=k['cyl'];span=k['span'];quad=k['quad'];tube=k['tube'];record=k['record'];apply=k['apply_frame'] if 'apply_frame' in k else None
# Local model: Blender (-Unity X,-Unity Z,Unity Y); same glTF/Unity import convention as the district retrofit.
def B(name,size,x,z,y,mat='panel',collide=False):
 o=box(name,size,M[mat],loc=(-x,-z,y),bevel=.02)
 if collide:k['col_box'](name,(-x,-z,y),size)
 return o
# Booth origin intended at (-64,7), flat platform elevation -1.0; front toward -Z.
B('Booth foundation',(3.6,3.9,.18),0,0,.0,'concrete',True)
B('Tread entry step',(3.2,.8,.1),0,-2.05,-.1,'tread',True)
# Structural uprights, roof cantilever, bolted footings
for x in [-1.6,1.6]:
 for z in [-1.75,1.75]:
  B('Upright',( .10,.10,2.6),x,z,1.38,'rust',True)
  B('Bolt footplate',(.26,.26,.04),x,z,.14,'steel')
  for dx,dz in [(-.075,-.075),(.075,.075)]:cyl('Anchor bolt',.018,.045,M['steel'],loc=(-x+dx,-z+dz,.18),sides=10)
B('Armoured rear wall',(3.25,.09,2.42),0,1.75,1.34,'plate_olive',True)
# Side window openings, no glazing to keep believable depth
for x in [-1.6,1.6]:
 B('Side lower armour',(.10,3.45,.85),x,0,.56,'plate_olive',True)
 B('Side upper lintel',(.10,3.45,.42),x,0,2.37,'panel',True)
 for z in [-1.1,1.1]:B('Side mullion',(.12,.10,1.22),x,z,1.58,'rust',True)
B('Layered insulated roof',(3.8,4.6,.16),0,-.2,2.65,'corrugated',True)
for x in [-1.9,1.9]:B('Roof edge trim',(.08,4.6,.16),x,-.2,2.69,'rust')
for z in [-2.45,2.05]:B('Roof end trim',(3.8,.1,.16),0,z,2.69,'rust')
for x in [-1.2,0,1.2]:B('Roof stiffener',(.08,4.1,.10),x,-.15,2.50,'steel')
# Open front with service counter on the east side, walk-in gap to west
B('Service counter',(1.15,.6,.08),.94,-1.45,1.03,'tread',True)
B('Counter armour',(1.15,.12,.83),.94,-1.7,.58,'plate_teal',True)
B('Desk radio',(.27,.22,.13),.98,-1.42,1.17,'dark')
B('Desk receiver',(.09,.1,.06),.72,-1.42,1.24,'rubber')
cyl('Radio antenna',.014,.28,M['steel'],loc=(-1.08,1.42,1.38),sides=10)
B('Bench seat',(1.3,.4,.09),.65,1.1,.55,'plate_bone',True)
for x in [.13,1.13]:B('Bench support',(.08,.32,.4),x,1.1,.30,'rust')
# Canopy support cables and rolled canvas shade at front
for x in [-1.55,1.55]:span('Canopy diagonal',(-x,1.70,2.42),(-x,2.4,2.63),.035,.04,M['steel'])
B('Weathered canvas fascia',(3.3,.07,.27),0,-2.35,2.38,'tarp_rust')
B('Warden banner',(.60,.015,1.32),-1.24,1.68,1.65,'banner')
# Practical warm task light, cyan strip local to locker
B('Task lamp casing',(.8,.16,.09),.4,-.3,2.43,'dark')
B('Task lamp diffuser',(.68,.13,.02),.4,-.3,2.37,'interior');k['light_marker']('Booth task light',(-.4,.3,2.25),'amber')
# Utility wiring at rear, antenna, small solar panel
for x in [-1.05,-.97]:tube('Rear electrical conduit',[(-x,-1.69,.2),(-x,-1.69,2.2),(-.6,-1.69,2.2)],.025,M['rubber'],sides=10)
B('Electrical switchboard',(.38,.13,.48),-1.05,1.68,.93,'panel_rust')
cyl('Antenna mast',.035,1.35,M['steel'],loc=(1.3,-1.4,3.25),sides=12)
B('Solar panel',(1.1,1.5,.055),.65,.4,2.8,'solar')
# Cabinet authored separately, preserving gameplay locker root in Unity.
booth=list(col.objects)
for o in booth:o.select_set(False)
# Export only booth collection
bpy.ops.object.select_all(action='DESELECT')
for o in booth:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(ROOT/'unity/AthenHill/Assets/AthenHill/Art/Checkpoint/WardenBooth.glb'),export_format='GLB',use_selection=True,export_yup=True)
# cabinet local at origin, front -Z
start=set(col.objects)
B('Locker carcass',(1.12,.56,1.68),0,0,.86,'panel',True)
for x in [-.29,.29]:
 B('Locker recessed door',(.51,.025,1.45),x,-.295,.9,'plate_teal')
 B('Locker door frame',(.53,.02,.055),x,-.32,.19,'hazard')
 B('Locker handle',(.035,.06,.22),x+.16,-.35,.95,'steel')
 for y in [1.37,1.43,1.49]:B('Locker ventilation slit',(.32,.01,.022),x,-.312,y,'dark')
B('Cyan locker beacon',(1.04,.04,.055),0,-.3,1.66,'cyan_dim')
B('Locker plinth',(1.22,.66,.09),0,0,.04,'rust')
bpy.ops.object.select_all(action='DESELECT')
for o in set(col.objects)-start:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(ROOT/'unity/AthenHill/Assets/AthenHill/Art/Checkpoint/ArmsLocker.glb'),export_format='GLB',use_selection=True,export_yup=True)
# Separate jersey barrier with skinned metal traffic rails and hazard cap.
start=set(col.objects)
# tapered concrete mesh, extruded profile rather than a cube
import bmesh
bm=bmesh.new();profile=[(-.36,0),(.36,0),(.36,.20),(.17,.55),(.13,.94),(-.13,.94),(-.17,.55),(-.36,.20)]
vs=[]
for xx in [-1.2,1.2]:vs.append([bm.verts.new((xx,zz,yy)) for zz,yy in profile])
bm.faces.new(list(reversed(vs[0])));bm.faces.new(vs[1])
for i in range(8):j=(i+1)%8;bm.faces.new((vs[0][i],vs[0][j],vs[1][j],vs[1][i]))
o=k['mesh_obj']('Jersey barrier',bm,M['concrete_cracked']);k['box_uv'](o,.8)
B('Hazard steel cap',(2.42,.28,.055),0,0,.96,'hazard')
for x in [-.8,.8]:B('Barrier reflector',(.13,.012,.08),x,-.185,.58,'amber');B('Barrier lifting eye',(.10,.055,.1),x,0,1.03,'steel')
k['col_box']('Barrier',(0,0,.47),(2.4,.70,.94))
bpy.ops.object.select_all(action='DESELECT')
for o in set(col.objects)-start:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(ROOT/'unity/AthenHill/Assets/AthenHill/Art/Checkpoint/CheckpointBarrier.glb'),export_format='GLB',use_selection=True,export_yup=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'checkpoint-source.blend'))
json.dump({'booth_dimensions_m':[3.8,2.9,4.6],'locker_dimensions_m':[1.22,1.70,.66],'source_textures':'Existing CC0 Ward retrofit kit; original checkpoint geometry','booth_triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in booth if o.type=='MESH')},open(OUT/'geometry.json','w'),indent=2)
print('Authored checkpoint booth, cabinet and barriers')
