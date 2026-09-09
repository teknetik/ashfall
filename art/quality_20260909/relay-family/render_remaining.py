import bpy,json,math
from pathlib import Path
from mathutils import Vector
R=Path('/home/teknetik/code/ao2/art/quality_20260909/relay-family/revision-01')
scene=bpy.data.scenes['Ward Relay architecture'];assert scene['ward_asset']=='relay-architecture';bpy.context.window.scene=scene
cam=scene.camera
for row in json.loads((R/'review-cameras.json').read_text())[1:]:
 p=row['position'];t=row['target'];cam.location=Vector((p[0],-p[2],p[1]));target=Vector((t[0],-t[2],t[1]));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=row['lens'];scene.render.filepath=str(R/('source-'+row['name']+'.png'));bpy.ops.render.render(write_still=True)
print('Remaining Relay source review views rendered')
