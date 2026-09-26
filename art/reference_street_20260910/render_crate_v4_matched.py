"""Remove side-by-side lighting ambiguity: exact source/near position and lens."""
import bpy,json
from pathlib import Path
from mathutils import Vector
R=Path('/home/teknetik/code/ao2');O=R/'meshy/ground-detail-20260910/crate-v4-runtime'
S=bpy.context.window.scene
roots={key:next(o for o in S.objects if o.type=='EMPTY' and o.name.startswith(key+' reference')) for key in ['original','candidate']}
for root in roots.values():root.location.x=0
for ob in S.objects:
 if ob.type=='FONT':ob.hide_render=True
S.render.resolution_x=1024;S.render.resolution_y=1024;S.camera.data.ortho_scale=2.8
records=[]
for face,pos in [('rear',(3,-7,3.5)),('handle',(-3,7,3.5))]:
 S.camera.location=pos;S.camera.rotation_euler=(Vector((0,0,1))-S.camera.location).to_track_quat('-Z','Y').to_euler()
 for key in ['original','candidate']:
  for label,root in roots.items():
   for child in root.children:child.hide_render=label!=key
  out=O/('matched-'+face+'-'+('source' if key=='original' else 'runtime')+'.png');assert not out.exists()
  S.render.filepath=str(out);bpy.ops.render.render(write_still=True)
  records.append(dict(view=face,version=key,cameraPosition=list(S.camera.location),cameraRotation=list(S.camera.rotation_euler),orthographicScale=S.camera.data.ortho_scale,rootLocation=list(roots[key].location),runtimeUniformScale=list(roots[key].scale),path=out.name))
bpy.data.libraries.write(str(O/'matched-review.blend'),{S},fake_user=True)
(O/'matched-review.json').write_text(json.dumps(dict(method='Only mesh visibility changes per view; same camera, exposure, lights, position and reference sizing. Each version uses its own correct PBR maps.',renders=records),indent=2));print(json.dumps(records))
