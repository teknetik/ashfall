"""Read the saved source tree through the live Blender MCP connection."""
import bpy, json
from pathlib import Path

ROOT = Path('/home/teknetik/code/ao2')
OUT = ROOT / 'art/phase1_20260908'
OUT.mkdir(exist_ok=True)
# The inspected live session is the empty startup scene, with no user file open.
assert not bpy.data.filepath, 'Inspect an empty Blender session before importing.'
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT / 'unity/AthenHill/Assets/AthenHill/Art/Imported/world.glb'))
for obj in list(bpy.data.objects):
    if not obj.name.startswith('TREE_'):
        bpy.data.objects.remove(obj, do_unlink=True)
report = []
for obj in bpy.data.objects:
    if obj.type != 'MESH':
        continue
    obj.data.calc_loop_triangles()
    report.append(dict(name=obj.name, vertices=len(obj.data.vertices),
                       triangles=len(obj.data.loop_triangles),
                       dimensions=list(obj.dimensions),
                       location=list(obj.location),
                       materials=[m.name for m in obj.data.materials if m]))
(OUT / 'tree-source-inventory.json').write_text(json.dumps(report, indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'tree-audition.blend'))
print(json.dumps(dict(objects=len(report), triangles=sum(r['triangles'] for r in report))))
