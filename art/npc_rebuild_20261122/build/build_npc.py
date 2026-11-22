"""Runtime file for one NPC from its Meshy rig and finished textures (headless Blender).
Keeps the installers' contract: armature `Armature`, meshes `char1` (LOD0) and `char1_lod1`, the Meshy bone names
(finger bones included, which ArmPoseFingerPass relaxes), one material, no animation in the file.
blender.sh build_npc.py -- rigged.glb tex_dir out.glb TITLE [lod0=36000] [lod1=7000]"""
import bpy, sys, json, bmesh
from pathlib import Path
a = sys.argv[sys.argv.index('--') + 1:]
RIG, TEX, OUT, TITLE = a[0], Path(a[1]), a[2], a[3]
T0 = int(a[4]) if len(a) > 4 else 36000; T1 = int(a[5]) if len(a) > 5 else 7000
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=RIG, merge_vertices=True, bone_heuristic='BLENDER')
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
ch = max((o for o in bpy.data.objects if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
for o in list(bpy.data.objects):
    if o not in (arm, ch): bpy.data.objects.remove(o)
arm.animation_data_clear()
for x in list(bpy.data.actions): bpy.data.actions.remove(x)
for pb in arm.pose.bones: pb.matrix_basis.identity()
arm.name = arm.data.name = 'Armature'; ch.name = ch.data.name = 'char1'
bpy.ops.object.select_all(action='DESELECT'); ch.select_set(True); bpy.context.view_layer.objects.active = ch
try: bpy.ops.mesh.customdata_custom_splitnormals_clear()
except Exception: pass
bm = bmesh.new(); bm.from_mesh(ch.data); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5); bm.to_mesh(ch.data); bm.free()

m = bpy.data.materials.new(TITLE); m.use_nodes = True; n = m.node_tree; p = next(x for x in n.nodes if x.type == 'BSDF_PRINCIPLED')
def tex(f, data):
    t = n.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(str(TEX / f))
    t.image.colorspace_settings.name = 'Non-Color' if data else 'sRGB'; return t
n.links.new(tex('base.png', False).outputs[0], p.inputs['Base Color'])
nm = n.nodes.new('ShaderNodeNormalMap'); n.links.new(tex('normal.png', True).outputs[0], nm.inputs['Color'])
n.links.new(nm.outputs[0], p.inputs['Normal'])
sep = n.nodes.new('ShaderNodeSeparateColor'); n.links.new(tex('orm.png', True).outputs[0], sep.inputs[0])
n.links.new(sep.outputs[1], p.inputs['Roughness']); n.links.new(sep.outputs[2], p.inputs['Metallic'])
ch.data.materials.clear(); ch.data.materials.append(m)

names = {g.index: g.name for g in ch.vertex_groups}
def guard(name):
    if name in ('Head', 'head_end', 'headfront') or name.startswith('Bone_0'): return 1.
    return .6 if 'Hand' in name else .35 if name == 'neck' else 0.
def tris(o): return sum(len(f.vertices) - 2 for f in o.data.polygons)
lod1 = ch.copy(); lod1.data = ch.data.copy(); lod1.name = lod1.data.name = 'char1_lod1'; bpy.context.collection.objects.link(lod1)
rec = {}
for o, target, factor in ((ch, T0, 6.), (lod1, T1, .25)):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    g = o.vertex_groups.new(name='protect')
    for v in o.data.vertices:
        w = sum(x.weight * guard(names.get(x.group, '')) for x in v.groups)
        if w > .04: g.add([v.index], min(1., w), 'REPLACE')
    d = o.modifiers.new('d', 'DECIMATE'); d.ratio = target / tris(o); d.use_collapse_triangulate = True
    d.vertex_group = 'protect'; d.vertex_group_factor = factor; d.invert_vertex_group = True
    while o.modifiers[0].name != 'd': bpy.ops.object.modifier_move_up(modifier='d')
    bpy.ops.object.modifier_apply(modifier='d'); o.vertex_groups.remove(o.vertex_groups['protect'])
    for f in o.data.polygons: f.use_smooth = True
    rec[o.name] = tris(o)
bpy.ops.object.select_all(action='DESELECT')
for o in (arm, ch, lod1): o.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.gltf(filepath=OUT, use_selection=True, export_format='GLB', export_skins=True, export_animations=False,
                          export_morph=False, export_yup=True, export_tangents=True, export_influence_nb=4)
rec['bones'] = len(arm.data.bones); print('BUILD OK', json.dumps(rec))
