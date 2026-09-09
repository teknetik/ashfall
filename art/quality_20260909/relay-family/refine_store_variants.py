"""Live Blender correction of inspected connections; preserve revision 01."""
import bpy,bmesh,ast,json,math,random
from pathlib import Path
from mathutils import Vector
R=Path('/home/teknetik/code/ao2');base=R/'art/quality_20260909/relay-family';O=base/'store-variants-02'
assert not O.exists();O.mkdir()
for file,names in [('author_relay.py',{'B','U','finish','box','cyl','tube','pipe','ring','plate','bolt','proxy'}),('author_store_variants.py',{'export'})]:
 for node in ast.parse((base/file).read_text()).body:
  if isinstance(node,ast.FunctionDef)and node.name in names:exec(compile(ast.Module(body=[node],type_ignores=[]),file,'exec'))
manifest=json.loads((base/'store-variants-01/manifest.json').read_text());allparts=[];allproxies=[];reports=[]
for row in manifest['families']:
 family=row['id'];scene=bpy.data.scenes['Ward '+family+' authored source'];bpy.context.window.scene=scene
 objects=[o for o in scene.objects if o.type=='MESH' and o.get('family')==family];M={o['region']:o.data.materials[0]for o in objects};tile={k:.75 for k in M};tile.update(WardPlaster=3,WardStone=2,WardConcrete=1.23,WardWornSteel=2,WardLetter=1,WardGasket=1,WardGlass=1)
 for k in M:
  if k.startswith('WardCloth'):tile[k]=.4
 rng=random.Random('Ward fittings '+family);proxies=json.loads((base/'store-variants-01'/family/'collider-proxies.json').read_text());changes=[]
 if family!='field_supply':
  width,offset={'air_water':(3.45,-1.35),'repairs':(4,-.7),'salvage':(4.45,-.7),'thread_hide':(6,0),'tool_exchange':(3.9,1)}[family]
  group='Awning'
  for x in [offset-width/2,offset+width/2]:plate('Lower awning wall anchor '+str(x),(x,2.15,2.735),(.19,.24,.13),'WardPaint')
  changes.append('Lower awning arms fastened to wall plates')
 group='Stone ground transition'
 # Base courses are segmented stone on the existing slab, not an extra raised step.
 for x in [-3.64,3.64]:
  for i in range(7):box('Side damp course '+str((x,i)),(x,.13,-3.72+i*1.0),(.39,.26,.982),'WardStone',.014)
 for i in range(7):box('Rear damp course '+str(i),(-3.12+i*1.04,.13,-4.28),(1.022,.26,.34),'WardStone',.014)
 changes.append('Stone damp courses connect side and rear walls to retained foundations')
 if family=='air_water':
  group='Water storage and filtration'
  for ob in objects:
   if 'Tank saddle' in ob.name:ob.scale.z*=.36/.28;ob.location.z+=.04
  pipe('Twin vessel cross feed',(-1.7,7.08,.80),(1.7,7.08,.80),.085,'WardBrass')
  tube('Roof to filter downfeed',[(1.7,7.08,.80),(1.7,7.08,3.03),(3.18,7.08,3.03),(3.18,2.1,3.03),(2.85,2.1,2.98)],.055,'WardBrass')
  for y in [2.4,3.9,5.8]:
   plate('Feed masonry anchor '+str(y),(3.18,y,2.77),(.18,.17,.15),'WardPaint')
   box('Feed stand-off '+str(y),(3.18,y,2.94),(.075,.075,.22),'WardSteel',.004)
   ring('Feed retaining clamp '+str(y),(3.18,y,3.03),.061,.011,'WardSteel',axis=(0,1,0))
  for x in [.9,1.7,2.5]:pipe('Filter manifold inlet '+str(x),(x,1.94,2.98),(x,2.10,2.98),.048,'WardBrass')
  changes.append('Vessels seated on saddles; cross feed, downfeed and filter inlets connected')
 if family=='field_supply':
  group='Loading canopy structure'
  for x in [-3.3,3.3]:
   proxy('Loading canopy post '+str(x),(x,1.48,4.12),(.18,2.96,.18))
   plate('Canopy masonry attachment '+str(x),(x,3.02,2.76),(.24,.30,.13),'WardPaint')
  changes.append('Loading posts receive matching collision and rear attachment plates')
 if family=='salvage':
  group='Loft lifting bracket';ring('Suspended lifting eye',(2.65,4.75,4.13),.080,.018,'WardSteel',axis=(1,0,0))
  changes.append('Lifting cable ends in attached eye')
 if family=='thread_hide':
  for ob in objects:
   if 'Hanging cloth length' not in ob.name:continue
   me=ob.data;bm=bmesh.new();bm.from_mesh(me);bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=16,use_grid_fill=True)
   for v in bm.verts:
    t=max(0,min(1,(7.78-v.co.z)/.96));v.co.y+=.045*math.sin(v.co.x*16)*t;v.co.z-=.018*math.sin(v.co.x*12)**2*t
   bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
  changes.append('Drying cloth receives folds that remain pinned to its rail')
 bpy.context.view_layer.update();data=export();allparts+=data;allproxies+=proxies;folder=O/family;folder.mkdir()
 (folder/'meshes.json').write_text(json.dumps(data,separators=(',',':')));(folder/'collider-proxies.json').write_text(json.dumps(proxies,indent=2))
 bpy.data.libraries.write(str(folder/'source.blend'),{scene},fake_user=True,compress=True)
 reports.append(dict(id=family,parts=len(data),triangles=sum(len(p['indices'])//3 for p in data),changes=changes,status='Revised source; no scene installation or acceptance'))
(O/'store-meshes.json').write_text(json.dumps(allparts,separators=(',',':')));(O/'collider-proxies.json').write_text(json.dumps(allproxies,indent=2))
manifest.update(families=reports,supersedes='store-variants-01 connections and footing; source revision 01 retained',sourceOnly=True)
(O/'manifest.json').write_text(json.dumps(manifest,indent=2));(O/'review-cameras.json').write_text((base/'store-variants-01/review-cameras.json').read_text())
print(json.dumps(reports))
