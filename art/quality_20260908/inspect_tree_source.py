import bpy
import json
import pathlib

ROOT = pathlib.Path('/home/teknetik/code/ao2')
SOURCE = ROOT / 'refs/quality_20260908/tree/jacaranda_tree/jacaranda_tree_4k.blend'
OUT = ROOT / 'art/quality_20260908/tree'
OUT.mkdir(parents=True, exist_ok=True)
bpy.context.preferences.filepaths.use_scripts_auto_execute = False
bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False, use_scripts=False)
rows = []
for obj in bpy.data.objects:
    row = {'name': obj.name, 'type': obj.type, 'location': list(obj.location), 'dimensions': list(obj.dimensions), 'hideRender': obj.hide_render, 'hideViewport': obj.hide_viewport, 'collections': [c.name for c in obj.users_collection], 'modifiers': [{'name': m.name, 'type': m.type, 'viewport': m.show_viewport, 'render': m.show_render, 'properties': {k: str(v) for k, v in m.items()}} for m in obj.modifiers]}
    if obj.type == 'MESH':
        obj.data.calc_loop_triangles()
        row.update(vertices=len(obj.data.vertices), triangles=len(obj.data.loop_triangles), materials=[m.name if m else None for m in obj.data.materials])
    rows.append(row)
images = [{'name': i.name, 'filepath': i.filepath, 'size': list(i.size), 'colorspace': i.colorspace_settings.name} for i in bpy.data.images]
report = {'objects': rows, 'images': images, 'scene': bpy.context.scene.name, 'renderEngine': bpy.context.scene.render.engine}
(OUT / 'source-inspection.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({'objects': len(rows), 'meshes': [r for r in rows if r['type'] == 'MESH'], 'imageCount': len(images)}, indent=2))
