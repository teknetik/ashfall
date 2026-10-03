"""player_face_20261003: the Meshy retexture input and the concept-paint references.
- meshy_input/skin_head.glb: the MPFB skin mesh (head, neck, hands; A-pose as in suit_m0.25.blend) with its original UVs,
  plus the eyeballs with their UVs packed into an empty part of the skin layout (0.24-0.44, 0.40-0.50) so Meshy sees eyes
  in the sockets without overwriting skin texels. No hair/beard/brow/lash cards: those are separate materials.
- renders/ref_head_{front,side,quarter}.png: the head lit flat (neutral grey skin, no cards) as the shape reference that
  the concept paint-over keeps.
Usage: blender.sh prep_meshy.py"""
import sys; sys.path.insert(0, '/home/teknetik/code/ao2/art/tutorial_set_20261002/blender')
import bpy, json, math
from pathlib import Path
from mathutils import Vector
from fitlib import *

PF = AO2 / 'art/player_face_20261003'
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'mpfb' / 'suit_m0.25.blend'))
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
keep = {'Human', 'Human.high-poly'}
for o in list(bpy.data.objects):
    if o.type == 'MESH' and o.name not in keep: bpy.data.objects.remove(o)
human = bpy.data.objects['Human']; eyes = bpy.data.objects['Human.high-poly']
# eyes: pack the UVs into an empty region of the skin layout
uv = eyes.data.uv_layers.active.data
xs = [d.uv.x for d in uv]; ys = [d.uv.y for d in uv]
x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
for d in uv:
    d.uv.x = 0.24 + (d.uv.x - x0) / (x1 - x0) * 0.20
    d.uv.y = 0.40 + (d.uv.y - y0) / (y1 - y0) * 0.10
# one neutral material on both (Meshy ignores it; the renders use it)
m = bpy.data.materials.new('Neutral'); m.use_nodes = True
bs = m.node_tree.nodes['Principled BSDF']; bs.inputs['Base Color'].default_value = (0.55, 0.45, 0.40, 1); bs.inputs['Roughness'].default_value = 0.6
for o in (human, eyes): o.data.materials.clear(); o.data.materials.append(m)
bpy.context.view_layer.update()
hd = rig.matrix_world @ rig.data.bones['Head'].head_local
rec = {'head_bone': list(hd), 'eye_uv_src': [x0, x1, y0, y1]}
# renders: flat, even light
sc = bpy.context.scene
cam = setup_render((768, 1024)); cam.data.lens = 85
for n in ('key', 'fill'):
    l = bpy.data.objects.get(n)
    if l: l.data.energy = 2.0 if n == 'key' else 1.6
centre = Vector((hd.x, hd.y - 0.02, hd.z + 0.06))
for v, d in (('front', Vector((0, -1, 0))), ('side', Vector((1, 0, 0))), ('quarter', Vector((0.6, -0.8, 0.0)).normalized())):
    cam.location = centre + d * 1.15
    cam.rotation_euler = (centre - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = str(PF / 'renders' / f'ref_head_{v}.png'); bpy.ops.render.render(write_still=True)
# export for Meshy: static mesh (no skin), original UVs
(PF / 'meshy_input').mkdir(exist_ok=True)
bpy.ops.object.select_all(action='DESELECT'); human.select_set(True); eyes.select_set(True); bpy.context.view_layer.objects.active = human
bpy.ops.export_scene.gltf(filepath=str(PF / 'meshy_input' / 'skin_head.glb'), use_selection=True, export_format='GLB',
                          export_skins=False, export_animations=False, export_morph=False, export_yup=True, export_materials='PLACEHOLDER')
rec['glb_bytes'] = (PF / 'meshy_input' / 'skin_head.glb').stat().st_size
(PF / 'blender' / 'prep_meshy.json').write_text(json.dumps(rec, indent=2)); print('REC', rec)
