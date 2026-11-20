"""Bake the jumpsuit's surface data into its own UV layout (4096², rest pose, Cycles CPU), saved as .npy for
make_suit.py: object-space position, object-space normal, ambient occlusion (suit + body), body region weights
(arms / legs / torso from the skin weights) and coverage. Source: the polish blend that the shipped colonist.glb was
exported from (art/character_polish_20261005/player_polish.blend), opened read-only (nothing saved)."""
import bpy, bmesh, numpy as np, os, sys
POLISH = '/home/teknetik/code/ao2/art/character_polish_20261005/player_polish.blend'
OUT = '/home/teknetik/code/ao2/art/colonist_back_20261120/bake/'
RES = int(sys.argv[sys.argv.index('--') + 1]) if '--' in sys.argv else 4096
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=POLISH)
arm = bpy.data.objects['Armature']; char = bpy.data.objects['char1']
if arm.animation_data:
    arm.animation_data.action = None
    for t in arm.animation_data.nla_tracks: t.mute = True
for pb in arm.pose.bones: pb.matrix_basis.identity()
for m in list(char.modifiers):
    if m.type == 'ARMATURE': char.modifiers.remove(m)
bpy.context.view_layer.update()
mats = [m.name for m in char.data.materials]
import json
json.dump({b.name: list(arm.matrix_world @ b.head_local) + list(arm.matrix_world @ b.tail_local) for b in arm.data.bones},
          open(OUT + 'joints.json', 'w'), indent=0)
SUIT = mats.index('PlayerJumpsuit')
# region colour per vertex from the skin weights
groups = {g.index: g.name for g in char.vertex_groups}
def region(name):
    n = name.lower()
    if any(k in n for k in ('arm', 'hand', 'thumb', 'index', 'middle', 'ring', 'pinky')) and 'shoulder' not in n: return 0
    if any(k in n for k in ('upleg', 'leg', 'foot', 'toe')): return 1
    return 2
me = char.data
col = me.color_attributes.new('cb_region', 'FLOAT_COLOR', 'POINT')
for v in me.vertices:
    acc = [0.0, 0.0, 0.0]
    for g in v.groups: acc[region(groups[g.group])] += g.weight
    s = sum(acc) or 1.0
    col.data[v.index].color = (acc[0] / s, acc[1] / s, acc[2] / s, 1.0)
# suit-only copy for the emission bakes; the full char stays for AO occlusion
suit = char.copy(); suit.data = char.data.copy(); suit.name = 'suit_bake'; bpy.context.collection.objects.link(suit)
bm = bmesh.new(); bm.from_mesh(suit.data)
bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index != SUIT], context='FACES')
bm.to_mesh(suit.data); bm.free()
suit.data.materials.clear()
occ = char.copy(); occ.data = char.data.copy(); occ.name = 'occluder'; bpy.context.collection.objects.link(occ)
bm = bmesh.new(); bm.from_mesh(occ.data)
bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index == SUIT], context='FACES')
bm.to_mesh(occ.data); bm.free(); occ.hide_render = True
mat = bpy.data.materials.new('bake'); mat.use_nodes = True; suit.data.materials.append(mat)
nt = mat.node_tree; nt.nodes.clear()
outn = nt.nodes.new('ShaderNodeOutputMaterial'); em = nt.nodes.new('ShaderNodeEmission')
nt.links.new(em.outputs[0], outn.inputs['Surface'])
img = bpy.data.images.new('bake', RES, RES, float_buffer=True, alpha=True)
tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = img; nt.nodes.active = tex
geo = nt.nodes.new('ShaderNodeNewGeometry'); attr = nt.nodes.new('ShaderNodeAttribute'); attr.attribute_name = 'cb_region'
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 1
sc.render.bake.margin = 24; sc.render.bake.margin_type = 'EXTEND'
char.hide_render = True
for o in bpy.data.objects:
    o.select_set(False)
suit.select_set(True); bpy.context.view_layer.objects.active = suit
def grab(name):
    a = np.empty(RES * RES * 4, np.float32); img.pixels.foreach_get(a)
    np.save(OUT + name + '.npy', a.reshape(RES, RES, 4)[::-1].copy()); print('BAKED', name)
def emit(sock, name):
    for l in list(em.inputs['Color'].links): nt.links.remove(l)
    nt.links.new(sock, em.inputs['Color'])
    img.pixels.foreach_set(np.zeros(RES * RES * 4, np.float32))
    bpy.ops.object.bake(type='EMIT'); grab(name)
emit(geo.outputs['Position'], 'position')
vm = nt.nodes.new('ShaderNodeVectorTransform'); vm.vector_type = 'NORMAL'; vm.convert_from = 'WORLD'; vm.convert_to = 'OBJECT'
nt.links.new(geo.outputs['Normal'], vm.inputs[0])
emit(vm.outputs[0], 'normal')
emit(attr.outputs['Color'], 'region')
emit(geo.outputs['Pointiness'], 'pointiness')
# coverage without margin
sc.render.bake.margin = 0
for l in list(em.inputs['Color'].links): nt.links.remove(l)
em.inputs['Color'].default_value = (1, 1, 1, 1)
img.pixels.foreach_set(np.zeros(RES * RES * 4, np.float32)); bpy.ops.object.bake(type='EMIT'); grab('coverage')
sc.render.bake.margin = 24
# AO with the body (skin, hair, belt) as occluder
occ.hide_render = False
sc.cycles.samples = 64
img.pixels.foreach_set(np.zeros(RES * RES * 4, np.float32))
sc.world = sc.world or bpy.data.worlds.new('W')
sc.world.light_settings.distance = 0.25
bpy.ops.object.bake(type='AO'); grab('ao')
print('DONE')
