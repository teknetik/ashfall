"""Resume source views from the preserved Hall correction, via live Blender."""
import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path('/home/teknetik/code/ao2/art/quality_20260909/vanguard-hall/revision-02')
with bpy.data.libraries.load(str(O/'hall-repaired.blend'),link=False)as(src,dst):dst.scenes=['Ward Vanguard Hall repair']
scene=dst.scenes[0];bpy.context.window.scene=scene
B=lambda p:Vector((p[0],-p[2],p[1]))
scene.render.resolution_x=1600;scene.render.resolution_y=1200;scene.cycles.samples=24
for row in json.loads((O/'review-cameras.json').read_text()):
 path=O/('source-'+row['name']+'.png')
 if path.exists():continue
 cam=scene.camera;cam.location=B(row['position']);cam.rotation_euler=(B(row['target'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=row['lens']
 scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
print('Hall correction source views complete; no Unity installation.')
