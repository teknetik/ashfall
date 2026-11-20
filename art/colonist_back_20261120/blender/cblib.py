"""Colonist back pass (20 Nov 2026): shared Blender helpers. Loads the shipped colonist.glb plus worn armour GLBs onto
one armature in the idle pose, sets up the conversation-camera and follow-camera views and three light rigs
(sun, shade, night 20:30), and renders review frames. Blender 5.2 headless via P2/blender.sh.
Coordinates after glTF import: Z up, the colonist faces -Y, his right hand is -X."""
import bpy, math, os
from mathutils import Vector

AO2 = '/home/teknetik/code/ao2'
ART = AO2 + '/unity/AthenHill/Assets/AthenHill/Art'
COLONIST = ART + '/Imported/Meshy/colonist.glb'
TS = ART + '/Armour/TutorialSet/'
PIECES = {'vest': TS + 'TS_FieldVest.glb', 'boots': TS + 'TS_Boots.glb', 'helmet': TS + 'TS_Helmet.glb',
          'carrier': TS + 'TS_WardenCarrier.glb', 'arms': TS + 'TS_ArmGuards.glb', 'gloves': TS + 'TS_Gloves.glb',
          'legs': TS + 'TS_LegArmour.glb'}
HERE = AO2 + '/art/colonist_back_20261120'

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def import_glb(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    return [o for o in bpy.data.objects if o not in before]

def load(pieces=(), colonist=COLONIST, piece_paths=None, frame=12, action='idle'):
    objs = import_glb(colonist)
    arm = next(o for o in objs if o.type == 'ARMATURE')
    body = next(o for o in objs if o.type == 'MESH')
    act = next((a for a in bpy.data.actions if a.name.lower().startswith(action)), None)
    if act:
        ad = arm.animation_data or arm.animation_data_create()
        ad.action = act
        try:
            if act.slots: ad.action_slot = act.slots[0]
        except Exception: pass
    got = {}
    for k in pieces:
        p = (piece_paths or {}).get(k, PIECES[k])
        po = import_glb(p)
        for o in po:
            if o.type == 'MESH':
                for m in o.modifiers:
                    if m.type == 'ARMATURE': m.object = arm
                mw = o.matrix_world.copy(); o.parent = arm; o.matrix_world = mw
                got[k] = o
        for o in po:
            if o.type == 'ARMATURE': bpy.data.objects.remove(o)
    for o in list(bpy.data.objects):
        if o.type == 'MESH' and o.name.startswith('Icosphere'): bpy.data.objects.remove(o)
    bpy.context.scene.frame_set(frame)
    return arm, body, got

def head_pos(arm):
    return arm.matrix_world @ arm.pose.bones['Head'].head

def setup(res=(1920, 1080), light='sun'):
    sc = bpy.context.scene
    # Cycles on the CPU, 8 threads, low samples + denoise: no GPU use while Carl plays (fix round, 19 Nov evening).
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = int(os.environ.get('CB_SAMPLES', '24'))
    sc.cycles.use_denoising = True; sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    sc.render.threads_mode = 'FIXED'; sc.render.threads = 8
    sc.cycles.max_bounces = 4
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.image_settings.file_format = 'PNG'
    sc.view_settings.view_transform = 'AgX'
    w = bpy.data.worlds.get('W') or bpy.data.worlds.new('W'); sc.world = w
    w.use_nodes = True; bg = w.node_tree.nodes['Background']
    for n in [o for o in bpy.data.objects if o.type == 'LIGHT']: bpy.data.objects.remove(n)
    def sun(rot, e, col=(1, 1, 1)):
        l = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); l.data.energy = e; l.data.color = col
        l.data.angle = math.radians(1.5)
        l.rotation_euler = [math.radians(a) for a in rot]; sc.collection.objects.link(l); return l
    if light == 'sun':      # late-morning sun from the player's front-left (NPC lit, his back in partial light)
        bg.inputs[0].default_value = (0.55, 0.62, 0.75, 1); bg.inputs[1].default_value = 0.8
        sun((48, 0, 150), 4.5, (1.0, 0.93, 0.82))
    elif light == 'backsun':  # sun behind the camera: his back fully lit (the worst case for speckle)
        bg.inputs[0].default_value = (0.55, 0.62, 0.75, 1); bg.inputs[1].default_value = 0.8
        sun((55, 0, 20), 4.5, (1.0, 0.93, 0.82))
    elif light == 'shade':
        bg.inputs[0].default_value = (0.55, 0.62, 0.75, 1); bg.inputs[1].default_value = 1.1
    elif light == 'night':  # 20:30: dim cool sky, warm wall lamp up and to the right
        bg.inputs[0].default_value = (0.10, 0.13, 0.22, 1); bg.inputs[1].default_value = 0.35
        l = bpy.data.objects.new('lamp', bpy.data.lights.new('lamp', 'POINT')); l.data.energy = 120
        l.data.color = (1.0, 0.72, 0.45); l.location = (-1.6, 0.6, 3.0); sc.collection.objects.link(l)
    # ground
    if not bpy.data.objects.get('ground'):
        bpy.ops.mesh.primitive_plane_add(size=20); g = bpy.context.active_object; g.name = 'ground'
        m = bpy.data.materials.new('groundmat'); m.use_nodes = True
        m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.42, 0.33, 0.24, 1)
        g.data.materials.append(m)
    cam = bpy.data.objects.get('cam') or bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    if cam.name not in sc.collection.objects: sc.collection.objects.link(cam)
    sc.camera = cam
    return cam

def aim(cam, pos, target, vfov_deg=40):
    cam.location = Vector(pos)
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.sensor_fit = 'VERTICAL'; cam.data.angle = math.radians(vfov_deg)

def views(arm):
    """Named camera poses (position, target, vertical fov). conv = ConversationFraming.Shot.Default (40°, 1.25 m back,
    +0.05 m, shoulder ~0.6 m to his right, NPC head 1.9 m ahead); follow = FollowCamera-like 3.2 m back, 0.5 m up."""
    h = head_pos(arm)
    fwd = Vector((0, -1, 0)); right = Vector((-1, 0, 0)); up = Vector((0, 0, 1))
    npc = h + fwd * 1.9 + right * -0.15
    v = {}
    v['conv'] = (h + up * 0.05 - fwd * 1.25 + right * 0.6, npc + right * 0.55, 40)
    v['follow'] = (h + up * 0.45 - fwd * 3.2 + right * 0.35, h + fwd * 2.0 + up * -0.1, 50)
    v['back15'] = (h + up * -0.05 - fwd * 1.5, h + up * -0.35, 40)
    v['quarter'] = (h + up * -0.05 - fwd * 1.2 + right * 0.9, h + up * -0.35, 40)
    v['helmet'] = (h + up * 0.12 - fwd * 0.62 + right * 0.32, h + up * 0.05, 40)
    v['vest'] = (h + up * -0.25 - fwd * 0.85 + right * 0.25, h + up * -0.40, 40)
    return v

def render(path, cam, pos, target, fov, res=None):
    aim(cam, pos, target, fov)
    sc = bpy.context.scene
    if res: sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path
