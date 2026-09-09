"""Resume missing v2 source review frames through the live Blender MCP.
Preserve saved authoring and existing source-front evidence.
"""
import bpy,json
from pathlib import Path
from mathutils import Vector
root=Path('/home/teknetik/code/ao2/art/quality_20260909/basic-general')
scene=bpy.data.scenes.get('Basic General architectural repair')
if scene is None:
 with bpy.data.libraries.load(str(root/'basic-general-source-v2.blend'),link=False) as (src,dst):
  dst.scenes=['Basic General architectural repair']
 scene=dst.scenes[0]
bpy.context.window.scene=scene
assert scene.get('basic_general_v2_complete')
B=lambda p:Vector((p[0],-p[2],p[1]))
views=json.loads((root/'source-view-plan-v1.json').read_text())
for name,pos,target,lens in views:
 path=root/('source-v2-'+name+'.png')
 if path.exists():continue
 cam=scene.camera;cam.location=B(pos);cam.rotation_euler=(B(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=lens
 scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
print('Source v2 review views complete; saved source unchanged.')
