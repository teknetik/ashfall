"""Live Blender: close the daylight gap found at first-person door proximity.
Retain revision 02 and add two solid, overlapping meeting components per door.
"""
import bpy,ast,json,random,re,shutil
from pathlib import Path
from mathutils import Vector
R=Path('/home/teknetik/code/ao2/art/quality_20260909/relay-family')
for file,names in [('author_relay.py',{'B','U','finish','box'}),('author_store_variants.py',{'export'})]:
 for node in ast.parse((R/file).read_text()).body:
  if isinstance(node,ast.FunctionDef)and node.name in names:exec(compile(ast.Module(body=[node],type_ignores=[]),file,'exec'))
manifest=json.loads((R/'store-variants-02/manifest.json').read_text());added=[];merged=[];reports=[]
variants=R/'store-variants-03';assert not variants.exists();variants.mkdir()
for family in ['relay_works']+[a['id']for a in manifest['families']]:
 relay=family=='relay_works';source=R/'revision-02'if relay else R/'store-variants-02'/family
 out=R/'revision-03'if relay else variants/family;assert not out.exists();out.mkdir()
 blend='relay-architecture.blend'if relay else 'source.blend';sn='Ward Relay architecture'if relay else 'Ward '+family+' authored source'
 with bpy.data.libraries.load(str(source/blend),link=False)as(src,dst):dst.scenes=[sn]
 scene=dst.scenes[0];bpy.context.window.scene=scene
 objects=[o for o in scene.objects if o.type=='MESH'and o.get('family')==family]
 M={o['region']:o.data.materials[0]for o in objects};tile={k:.75 for k in M};tile.update(WardGasket=1);rng=random.Random('Door meeting '+family);group='Entrance';proxies=[];original=len(objects)
 pairs=[o for o in objects if re.search(r' leaf 0$',o.name)]
 for left in pairs:
  right=next(o for o in objects if o.name==left.name[:-1]+'1')
  points=[U(o.matrix_world@Vector(v))for o in[left,right]for v in o.bound_box]
  lo=[min(p[i]for p in points)for i in range(3)];hi=[max(p[i]for p in points)for i in range(3)];x=(lo[0]+hi[0])/2;y=(lo[1]+hi[1])/2;height=hi[1]-lo[1]
  prefix=left.name.replace(family+' ','').rsplit(' leaf ',1)[0]
  box(prefix+' continuous meeting seal',(x,y,lo[2]+.02),(.12,height+.025,.07),'WardGasket',.003)
  box(prefix+' overlapping meeting strip',(x-.015,y,hi[2]+.02),(.10,height+.008,.040),'WardPaint',.004)
 bpy.context.view_layer.update();data=export();new=data[original:];added+=new
 name='relay-meshes.json'if relay else 'meshes.json';(out/name).write_text(json.dumps(data,separators=(',',':')))
 shutil.copy2(source/'collider-proxies.json',out/'collider-proxies.json');bpy.data.libraries.write(str(out/blend),{scene},fake_user=True,compress=True)
 if relay:
  shutil.copy2(source/'review-cameras.json',out/'review-cameras.json');shutil.copytree(source/'textures',out/'textures')
 else:merged+=data
 reports.append(dict(id=family,doorPairs=len(pairs),addedParts=len(new),parts=len(data),triangles=sum(len(p['indices'])//3 for p in data),repair='Opaque meeting seal behind both leaves plus overlapping front strip',collision='Existing closed-door proxies unchanged'))
 if relay:
  cam=scene.camera;cam.location=B((.65,1.7,4.55));cam.rotation_euler=(B((0,1.45,2.65))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=38
  scene.render.resolution_x=1200;scene.render.resolution_y=900;scene.cycles.samples=16;scene.render.filepath=str(out/'source-meeting-seal.png');bpy.ops.render.render(write_still=True)
(R/'door-meeting-additions.json').write_text(json.dumps(added,separators=(',',':')))
(R/'door-meeting-revision.json').write_text(json.dumps({'source':'Live Blender correction from first-person native evidence','preserves':'Original source parts, mesh names, UVs, placements and colliders','families':reports},indent=2))
(variants/'store-meshes.json').write_text(json.dumps(merged,separators=(',',':')));shutil.copy2(R/'store-variants-02/collider-proxies.json',variants/'collider-proxies.json');shutil.copy2(R/'store-variants-02/review-cameras.json',variants/'review-cameras.json')
manifest.update(families=[a for a in reports if a['id']!='relay_works'],supersedes='Revision 02 daylight gaps at meeting edges; existing source preserved',sourceOnly=True)
(variants/'manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(reports))
