"""Inspection renders and measurements of Carl's delivered Meshy models (2 Oct 2026, next-level enemies).
Headless Blender 5.2 (Cycles CPU, few samples). For each model: front/side/back/three-quarter views beside a 1.8 m
marker, the rest pose and sampled walk/run frames for the rigs; vertex height histogram and loose parts for the
sentinel (to find where a turret head could split from its post). Writes renders/<name>_*.png and inspect.json.
Usage: ~/.local/state/ward-programme/blender.sh inspect_models.py"""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector
HERE = Path(__file__).resolve().parent
INC = HERE.parent / 'incoming-20261002'
OUT = HERE / 'renders'; OUT.mkdir(exist_ok=True)
MODELS = {
    'warden': INC / 'Meshy_AI_Ironclad_Warden_biped/Meshy_AI_Ironclad_Warden_biped_Animation_Walking_withSkin.glb',
    'warden_run': INC / 'Meshy_AI_Ironclad_Warden_biped/Meshy_AI_Ironclad_Warden_biped_Animation_Running_withSkin.glb',
    'reaper': INC / 'Meshy_AI_Scrap_Reaper_biped/Meshy_AI_Scrap_Reaper_biped_Animation_Walking_withSkin.glb',
    'reaper_run': INC / 'Meshy_AI_Scrap_Reaper_biped/Meshy_AI_Scrap_Reaper_biped_Animation_Running_withSkin.glb',
    'sentinel': INC / 'Meshy_AI_Post_Sentinel_1002142607_texture.glb',
}
rec = {}


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 24; sc.cycles.device = 'CPU'; sc.cycles.use_denoising = False
    sc.render.resolution_x = 640; sc.render.resolution_y = 720; sc.render.film_transparent = False
    sc.world = bpy.data.worlds.new('W'); sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes['Background']; bg.inputs[0].default_value = (0.55, 0.6, 0.68, 1); bg.inputs[1].default_value = 1.0
    sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN')); sun.data.energy = 3.5; sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(35)); sc.collection.objects.link(sun)
    # ground
    bpy.ops.mesh.primitive_plane_add(size=12); g = bpy.context.object; g.name = 'Ground'
    m = bpy.data.materials.new('G'); m.diffuse_color = (0.6, 0.5, 0.38, 1); m.use_nodes = True; m.node_tree.nodes['Principled BSDF'].inputs[0].default_value = (0.6, 0.5, 0.38, 1); g.data.materials.append(m)
    # 1.8 m marker: a thin post with rings every 0.5 m
    for z in (0.5, 1.0, 1.5, 1.8):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.06, depth=0.01, location=(1.3, 0, z)); r = bpy.context.object; r.name = f'Ring{z}'
    bpy.ops.mesh.primitive_cylinder_add(radius=0.015, depth=1.8, location=(1.3, 0, 0.9)); p = bpy.context.object; p.name = 'Marker'
    mm = bpy.data.materials.new('M'); mm.use_nodes = True; mm.node_tree.nodes['Principled BSDF'].inputs[0].default_value = (0.9, 0.2, 0.1, 1)
    for o in [p] + [o for o in bpy.data.objects if o.name.startswith('Ring')]: o.data.materials.append(mm)
    cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); cam.data.lens = 50; sc.collection.objects.link(cam); sc.camera = cam
    return sc, cam


def look(cam, target, dist, yaw_deg, pitch_deg=8):
    y = math.radians(yaw_deg); p = math.radians(pitch_deg)
    pos = Vector((target.x + dist * math.cos(p) * math.sin(y), target.y - dist * math.cos(p) * math.cos(y), target.z + dist * math.sin(p)))
    cam.location = pos
    d = target - pos; cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def render(name):
    bpy.context.scene.render.filepath = str(OUT / (name + '.png')); bpy.ops.render.render(write_still=True)


def import_glb(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path), bone_heuristic='BLENDER')
    new = [o for o in bpy.data.objects if o not in before]
    return new


def mesh_bounds(objs):
    lo = Vector((1e9,) * 3); hi = -lo
    dg = bpy.context.evaluated_depsgraph_get()
    for o in objs:
        if o.type != 'MESH': continue
        ev = o.evaluated_get(dg); me = ev.to_mesh()
        for v in me.vertices:
            w = ev.matrix_world @ v.co
            lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
        ev.to_mesh_clear()
    return lo, hi


def rig_report(name, path, frames):
    sc, cam = reset(); objs = import_glb(path)
    arm = next(o for o in objs if o.type == 'ARMATURE'); meshes = [o for o in objs if o.type == 'MESH']
    r = dict(file=path.name, armature_scale=list(arm.matrix_world.to_scale()), bones=len(arm.data.bones))
    # rest pose: disable the action
    act = arm.animation_data.action if arm.animation_data else None
    if arm.animation_data: arm.animation_data.action = None
    bpy.context.view_layer.update(); lo, hi = mesh_bounds(meshes)
    r['rest_bounds'] = dict(min=list(lo), max=list(hi), height=hi.z - lo.z)
    def bone_world(n):
        b = arm.pose.bones.get(n); return (arm.matrix_world @ b.head) if b else None
    hf = bone_world('headfront'); hd = bone_world('head')
    r['head'] = list(hd) if hd else None; r['headfront_dir'] = list((hf - hd).normalized()) if hf and hd else None
    r['feet'] = {k: list(bone_world(k)) for k in ('foot_l', 'foot_r', 'ball_l', 'ball_r') if bone_world(k)}
    r['hands'] = {k: list(bone_world(k)) for k in ('hand_l', 'hand_r', 'lowerarm_l', 'lowerarm_r', 'upperarm_l', 'upperarm_r') if bone_world(k)}
    centre = Vector((0, 0, (hi.z - lo.z) / 2))
    for yaw, tag in ((0, 'front'), (90, 'side'), (180, 'back'), (40, 'quarter')):
        look(cam, centre + Vector((0.4, 0, 0)), 4.2, yaw); render(f'{name}_rest_{tag}')
    look(cam, Vector((0.2, 0, (hi.z - lo.z) * 0.8)), 1.6, 30, 5); render(f'{name}_rest_head')
    look(cam, Vector((0.0, 0, 0.35)), 1.6, 30, -5); render(f'{name}_rest_feet')
    # animated frames
    if act:
        arm.animation_data.action = act
        fr = act.frame_range; r['action'] = dict(name=act.name, frames=list(fr), fps=sc.render.fps)
        sc.frame_start, sc.frame_end = int(fr[0]), int(fr[1])
        soles = []
        for k, f in enumerate(frames):
            sc.frame_set(int(fr[0] + (fr[1] - fr[0]) * f)); bpy.context.view_layer.update()
            lo2, hi2 = mesh_bounds(meshes); soles.append(dict(f=f, low=lo2.z, high=hi2.z, pelvis=list(bone_world('pelvis')) if bone_world('pelvis') else None))
            look(cam, centre + Vector((0.4, 0, 0)), 4.2, 60); render(f'{name}_anim{k}_quarter')
            if k == 0: look(cam, centre + Vector((0.4, 0, 0)), 4.2, 90); render(f'{name}_anim{k}_side')
        r['anim_samples'] = soles
    rec[name] = r


def static_report(name, path):
    sc, cam = reset(); objs = import_glb(path); meshes = [o for o in objs if o.type == 'MESH']
    lo, hi = mesh_bounds(meshes); r = dict(file=path.name, bounds=dict(min=list(lo), max=list(hi), size=list(hi - lo)))
    me = meshes[0].data; r['verts'] = len(me.vertices); r['faces'] = len(me.polygons)
    zs = [ (meshes[0].matrix_world @ v.co).z for v in me.vertices]
    import collections
    hist = collections.Counter(round((z - lo.z) / (hi.z - lo.z) * 20) for z in zs); r['height_histogram_20bins'] = [hist.get(i, 0) for i in range(21)]
    # radial extent per height band (to find the post vs head)
    bands = []
    for i in range(20):
        z0 = lo.z + (hi.z - lo.z) * i / 20; z1 = z0 + (hi.z - lo.z) / 20
        rad = [math.hypot((meshes[0].matrix_world @ v.co).x, (meshes[0].matrix_world @ v.co).y) for v in me.vertices if z0 <= (meshes[0].matrix_world @ v.co).z < z1]
        bands.append(dict(z=[round(z0 - lo.z, 3), round(z1 - lo.z, 3)], n=len(rad), max_radius=round(max(rad), 3) if rad else 0))
    r['bands'] = bands
    # loose parts
    bpy.context.view_layer.objects.active = meshes[0]; bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.separate(type='LOOSE'); bpy.ops.object.mode_set(mode='OBJECT')
    parts = [o for o in bpy.data.objects if o.type == 'MESH' and o.name != 'Ground']
    pr = []
    for o in parts:
        l2, h2 = mesh_bounds([o]); pr.append(dict(name=o.name, verts=len(o.data.vertices), min=[round(x, 3) for x in l2], max=[round(x, 3) for x in h2]))
    pr.sort(key=lambda p: -p['verts']); r['loose_parts'] = pr[:25]; r['loose_count'] = len(parts)
    # put the model on the ground for the views
    for o in parts: o.location.z -= lo.z
    centre = Vector((0, 0, (hi.z - lo.z) / 2))
    for yaw, tag in ((0, 'front'), (90, 'side'), (180, 'back'), (40, 'quarter'), (220, 'quarter_back')):
        look(cam, centre + Vector((0.4, 0, 0)), 4.6, yaw); render(f'{name}_{tag}')
    look(cam, Vector((0, 0, (hi.z - lo.z) * 0.85)), 1.8, 30, 10); render(f'{name}_head')
    look(cam, Vector((0, 0, 0.3)), 1.8, 30, -5); render(f'{name}_base')
    rec[name] = r


if __name__ == '__main__':
    rig_report("warden", MODELS['warden'], [0.0, 0.25, 0.5, 0.75])
    rig_report('warden_run', MODELS['warden_run'], [0.0, 0.5])
    rig_report('reaper', MODELS['reaper'], [0.0, 0.25, 0.5, 0.75])
    rig_report('reaper_run', MODELS['reaper_run'], [0.0, 0.5])
    static_report('sentinel', MODELS['sentinel'])
    (HERE / 'inspect.json').write_text(json.dumps(rec, indent=1, default=str))
    print('INSPECT DONE')
