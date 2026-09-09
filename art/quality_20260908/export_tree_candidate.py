"""Preserve complete source LODs, export an editable FBX audition through Blender MCP."""
import bpy, pathlib, json
from mathutils import Vector
ROOT = pathlib.Path('/home/teknetik/code/ao2')
OUT = ROOT / 'art/quality_20260908/tree'
scene = bpy.context.scene
scene.render.film_transparent = False
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .8
fill_data = bpy.data.lights.new('Inspection fill', 'AREA')
fill_data.energy = 1800
fill_data.shape = 'DISK'
fill_data.size = 8
fill = bpy.data.objects.new('Inspection fill', fill_data)
scene.collection.objects.link(fill)
fill.location = (3,-7,8)
fill.rotation_euler = (Vector((0,0,4))-fill.location).to_track_quat('-Z','Y').to_euler()
scene.view_settings.exposure = .4
camera = scene.camera
for name, position, target in [('source-trunk-lit',(5,-7,3),(0,0,3.7)),('source-roots-lit',(3.5,-4.5,1.8),(0,0,.8))]:
    camera.location = position
    camera.rotation_euler = (Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath = str(OUT/(name+'.png'))
    bpy.ops.render.render(write_still=True)
exports = []
for lod in (0,1):
    original = bpy.data.objects['jacaranda_tree_LOD'+str(lod)]
    bpy.ops.object.select_all(action='DESELECT')
    obj = original.copy()
    obj.data = original.data.copy()
    obj.name = 'WardTree_LOD'+str(lod)
    scene.collection.objects.link(obj)
    obj.hide_render = False
    obj.hide_viewport = False
    obj.hide_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.separate(type='MATERIAL')
    bpy.ops.object.mode_set(mode='OBJECT')
    objects = list(bpy.context.selected_objects)
    rows = []
    for part in objects:
        mat = part.data.materials[0]
        part.name = 'WardTree_LOD%d_%s' % (lod,mat.name.replace('jacaranda_tree_',''))
        part.data.calc_loop_triangles()
        rows.append({'name':part.name,'vertices':len(part.data.vertices),'triangles':len(part.data.loop_triangles),'material':mat.name,'uvLayers':[x.name for x in part.data.uv_layers]})
    destination = OUT / ('WardTree_LOD%d.fbx' % lod)
    bpy.ops.export_scene.fbx(filepath=str(destination), use_selection=True, object_types={'MESH'}, use_mesh_modifiers=True, mesh_smooth_type='OFF', use_tspace=True, add_leaf_bones=False, bake_anim=False, axis_forward='-Z', axis_up='Y', path_mode='STRIP', embed_textures=False)
    exports.append({'lod':lod,'path':str(destination),'objects':rows,'triangles':sum(r['triangles'] for r in rows),'bytes':destination.stat().st_size})
    for part in objects:
        part.hide_render = True
        part.hide_set(True)
(OUT/'export-manifest.json').write_text(json.dumps({'source':'Poly Haven Jacaranda tree CC0','uniformRuntimeScale':.78,'exports':exports},indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'tree-runtime-authoring.blend'))
print(json.dumps(exports,indent=2))
