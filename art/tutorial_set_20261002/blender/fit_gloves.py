"""Tutorial set gloves: fingerless work gloves as a shell over the player's own hands, so they follow every finger.
Stage 'shell': cut hand + finger joints 01-02 + wrist from char1, offset along normals, export an unrigged GLB with the
body's UVs (meshy retexture input, glove design from pieces/glove.png). Stage 'final': same shell, retextured, skinned
from the body, exported as TS_Gloves.glb.
Usage: blender_mpfb.sh fit_gloves.py -- shell|final"""
import sys; sys.path.insert(0, '/home/teknetik/code/ao2/art/tutorial_set_20261002/blender')
import bmesh
from mathutils import Vector
from fitlib import *

STAGE = sys.argv[sys.argv.index('--') + 1]
arm, body = load_final()
KEEP = {'LeftHand', 'RightHand'} | {f'{d}_{j}_{s}' for d in ('index', 'middle', 'ring', 'pinky', 'thumb') for j in ('01', '02') for s in 'lr'}
gname = {g.index: g.name for g in body.vertex_groups}
skin_slot = next(i for i, m in enumerate(body.data.materials) if m and m.name.startswith('PlayerSkin'))
wl = bone_head(arm, 'LeftHand'); wr = bone_head(arm, 'RightHand')
def dom(v):
    if not v.groups: return None
    g = max(v.groups, key=lambda g: g.weight); return gname[g.group]
sel = set()
for v in body.data.vertices:
    d = dom(v)
    w = body.matrix_world @ v.co
    if d in KEEP or (d in ('LeftForeArm', 'RightForeArm') and min((w - wl).length, (w - wr).length) < 0.055): sel.add(v.index)
shell = body.copy(); shell.data = body.data.copy(); shell.name = 'TS_Gloves'; shell.data.name = 'TS_Gloves'
bpy.context.collection.objects.link(shell)
bm = bmesh.new(); bm.from_mesh(shell.data); bm.faces.ensure_lookup_table()
kill = [f for f in bm.faces if f.material_index != skin_slot or not all(v.index in sel for v in f.verts)]
bmesh.ops.delete(bm, geom=kill, context='FACES'); bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
bm.normal_update()
for v in bm.verts: v.co += v.normal * 0.0028      # leather thickness
bm.to_mesh(shell.data); bm.free(); shell.data.update()
print('SHELL verts', len(shell.data.vertices), 'faces', len(shell.data.polygons))
shell.data.materials.clear()
if STAGE == 'shell':
    for m in list(shell.modifiers): shell.modifiers.remove(m)
    shell.parent = None
    bpy.ops.object.select_all(action='DESELECT'); shell.select_set(True); bpy.context.view_layer.objects.active = shell
    bpy.ops.export_scene.gltf(filepath=str(OUT / 'out' / 'gloves_shell.glb'), use_selection=True, export_format='GLB', export_skins=False, export_animations=False)
else:
    G = MESHY / 'glove_retex'
    def img(p, nc=False):
        im = bpy.data.images.load(str(p), check_existing=True)
        if nc: im.colorspace_settings.name = 'Non-Color'
        return im
    m = bpy.data.materials.new('TutorialGloves'); m.use_nodes = True; nt = m.node_tree; bs = nt.nodes['Principled BSDF']
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = img(G / 'tex0_base_color.png'); nt.links.new(t.outputs['Color'], bs.inputs['Base Color'])
    for key, sock in (('roughness', 'Roughness'), ('metallic', 'Metallic')):
        f = G / f'tex0_{key}.png'
        if f.exists():
            tt = nt.nodes.new('ShaderNodeTexImage'); tt.image = img(f, True); nt.links.new(tt.outputs['Color'], bs.inputs[sock])
    f = G / 'tex0_normal.png'
    if f.exists():
        tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = img(f, True); nm = nt.nodes.new('ShaderNodeNormalMap')
        nt.links.new(tn.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], bs.inputs['Normal'])
    shell.data.materials.append(m)
    normalise(shell); print('UNWEIGHTED', ensure_weighted(shell, 'RightHand'))
    export_skinned([shell], arm, OUT / 'out' / 'TS_Gloves.glb', ratio=1.0)   # already light (4k)
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.name not in (shell.name, body.name): o.hide_render = True
    h = bone_head(arm, 'RightHand')
    render_views(str(OUT / 'fit' / 'gloves'), (h.x - 0.05, h.y - 0.03, h.z - 0.05), 0.3, views=('front', 'rside', 'top', 'back'), res=(450, 450))
