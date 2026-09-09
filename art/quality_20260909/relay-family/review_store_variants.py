"""Live Blender source inspection of every separate store, with resumable frames."""
import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path('/home/teknetik/code/ao2/art/quality_20260909/relay-family/store-variants-01')
B=lambda p:Vector((p[0],-p[2],p[1]))
views=[('front',(10,7,16),(0,3.5,-.5),43),('door',(1.5,1.7,7),(0,1.45,2.6),34),('left',(-10,3.7,5),(-2,3,-.7),36),('right',(10,3.7,5),(2,3,-.7),36),('rear',(8,4,-15),(0,3,-2),40),('roof',(9,14,12),(0,5,-.8),42)]
(O/'review-cameras.json').write_text(json.dumps([dict(name=n,position=p,target=t,lens=l)for n,p,t,l in views],indent=2))
for row in json.loads((O/'manifest.json').read_text())['families']:
 folder=O/row['id'];sn='Ward '+row['id']+' authored source';scene=bpy.data.scenes.get(sn)
 if scene is None:
  with bpy.data.libraries.load(str(folder/'source.blend'),link=False)as(src,dst):dst.scenes=[sn]
  scene=dst.scenes[0]
 bpy.context.window.scene=scene;scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
 scene.render.resolution_x=1200;scene.render.resolution_y=900
 for name,p,t,l in views:
  path=folder/('source-'+name+'.png')
  if path.exists():continue
  cam=scene.camera;cam.location=B(p);cam.rotation_euler=(B(t)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=l
  scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
 print(row['id']+' six source views complete',flush=True)
print('All six source variants individually captured; no native acceptance.')
