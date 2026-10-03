"""player_face_20261003: face renders under the SAME light and framing as the NPC inspection renders
(meshy/ward-npcs-20261003/inspect_npc.py: Cycles CPU 20 spp, AgX, sun 3.0 at 50/-35 deg, area fill, 85 mm at 0.9 m,
front and 40-deg three-quarter), so the player can be judged side by side with Torr/Vex.
Usage:
  blender.sh face_lookdev.py -- glb PATH.glb NAME          # a finished player GLB (e.g. out/colonist_mpfb.glb)
  blender.sh face_lookdev.py -- cand MESHY_DIR NAME [cards] # suit_m0.25.blend skin + a Meshy retexture candidate
Writes art/player_face_20261003/renders/<NAME>_{face,face_q,face_side,shade}.png"""
import sys, math
import bpy
from pathlib import Path
from mathutils import Vector
sys.path.insert(0, '/home/teknetik/code/ao2/art/tutorial_set_20261002/blender')
args = sys.argv[sys.argv.index('--') + 1:]
MODE, SRC, NAME = args[0], args[1], args[2]
CARDS = 'cards' in args[3:]
PF = Path('/home/teknetik/code/ao2/art/player_face_20261003'); OUTD = PF / 'renders'


def setup():
    s = bpy.context.scene
    s.render.engine = 'CYCLES'; s.cycles.device = 'CPU'; s.cycles.samples = 20; s.cycles.use_denoising = True
    s.render.film_transparent = False; s.view_settings.view_transform = 'AgX'
    w = bpy.data.worlds.new('w'); s.world = w; w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[0].default_value = (.55, .58, .62, 1); w.node_tree.nodes['Background'].inputs[1].default_value = .7
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); s.collection.objects.link(sun)
    sun.data.energy = 3.0; sun.rotation_euler = (math.radians(50), 0, math.radians(-35))
    fill = bpy.data.objects.new('fill', bpy.data.lights.new('fill', 'AREA')); s.collection.objects.link(fill)
    fill.data.energy = 220; fill.data.size = 3; fill.location = (3, -3, 2); fill.rotation_euler = (math.radians(60), 0, math.radians(45))
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); s.collection.objects.link(cam); s.camera = cam
    return s, sun


def shoot(name, target, dist, yaw_deg, height, lens=85, res=(640, 640)):
    s = bpy.context.scene; cam = s.camera; cam.data.lens = lens
    s.render.resolution_x, s.render.resolution_y = res
    yaw = math.radians(yaw_deg)
    cam.location = Vector(target) + Vector((math.sin(yaw) * dist, -math.cos(yaw) * dist, height - target[2]))
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    s.render.filepath = str(OUTD / f'{NAME}_{name}.png'); bpy.ops.render.render(write_still=True)


def tex_node(nt, path, non_color=False):
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(str(path), check_existing=True)
    if non_color: t.image.colorspace_settings.name = 'Non-Color'
    return t


if MODE == 'glb':
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s, sun = setup()
    before = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=str(SRC))
    new = [o for o in bpy.data.objects if o not in before]
    arm = next(o for o in new if o.type == 'ARMATURE')
    head = arm.matrix_world @ arm.data.bones['Head'].head_local
else:
    bpy.ops.wm.open_mainfile(filepath='/home/teknetik/code/ao2/art/tutorial_set_20261002/blender/mpfb/suit_m0.25.blend')
    for o in list(bpy.data.objects):
        if o.type == 'LIGHT' or o.type == 'CAMERA': bpy.data.objects.remove(o)
    s, sun = setup()
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    head = arm.matrix_world @ arm.data.bones['Head'].head_local
    human = bpy.data.objects['Human']
    if not CARDS:
        for o in bpy.data.objects:
            if o.type == 'MESH' and any(k in o.name for k in ('short02', 'beard', 'eyebrow')): o.hide_render = True
    d = Path(SRC)
    if (d / 'skin_base.png').exists():   # our processed set (make_tex.py): same loader, other names
        import shutil
        for a, b in (('skin_base', 'tex0_base_color'), ('skin_normal', 'tex0_normal'), ('skin_rough', 'tex0_roughness')):
            pass
        names = {'tex0_base_color.png': 'skin_base.png', 'tex0_normal.png': 'skin_normal.png', 'tex0_roughness.png': 'skin_rough.png'}
    else: names = {}
    _p = lambda n: d / names.get(n, n)
    m = bpy.data.materials.new('Cand'); m.use_nodes = True; nt = m.node_tree; bs = nt.nodes['Principled BSDF']
    nt.links.new(tex_node(nt, _p('tex0_base_color.png')).outputs['Color'], bs.inputs['Base Color'])
    if _p('tex0_roughness.png').exists(): nt.links.new(tex_node(nt, _p('tex0_roughness.png'), True).outputs['Color'], bs.inputs['Roughness'])
    if _p('tex0_normal.png').exists():
        nm = nt.nodes.new('ShaderNodeNormalMap'); nt.links.new(tex_node(nt, _p('tex0_normal.png'), True).outputs['Color'], nm.inputs['Color'])
        nt.links.new(nm.outputs['Normal'], bs.inputs['Normal'])
    human.data.materials.clear(); human.data.materials.append(m)
    if 'shells' in args[3:]:
        sys.path.insert(0, str(PF / 'blender')); import shells
        sh, info = shells.build_shells(human, arm); print('SHELLS', info)
cx, cy, hz = head.x, head.y, head.z + 0.06
shoot('face', (cx, cy, hz), .9, 0, hz)
shoot('face_q', (cx, cy, hz), .9, 40, hz)
shoot('face_side', (cx, cy, hz), .9, 90, hz)
# shade: sun behind the head, only sky + fill (the 'in shade' check)
sun.rotation_euler = (math.radians(50), 0, math.radians(160)); sun.data.energy = 3.0
shoot('shade', (cx, cy, hz), .9, 25, hz)
# hands (the right hand from the back of the hand and the palm side)
if 'hands' in args[3:]:
    sun.rotation_euler = (math.radians(50), 0, math.radians(-35))
    hb = arm.matrix_world @ arm.data.bones['RightHand'].head_local
    ht = arm.matrix_world @ arm.data.bones['RightHand'].tail_local
    c = (hb + ht) / 2
    shoot('hand_out', c, .55, -90, c.z + .1)
    shoot('hand_front', c, .55, 0, c.z + .05)
