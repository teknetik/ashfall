# kit/calibrate_rig.py: what a white diffuse card (albedo 0.8) reads in scene-linear under review.studio(), per rig,
# per light and for three ways the card can face. SEAM.md section 8: the card must read about 0.9 where it faces the
# key, so nothing diffuse clips under AgX. Writes kit/rig_calibration.json and prints it.
#   SH/blender.sh kit/calibrate_rig.py
import sys, os, json, math
KIT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KIT)
import bpy
import numpy as np
from mathutils import Vector
import review as RV

OUT = os.path.join(KIT, 'rig_calibration.json')
TMP = os.path.join(KIT, 'example', 'export', '_cal.exr')
res = {}


def card_scene(warm, normal):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = RV.studio(samples=24, res=(24, 24), warm=warm)
    sc.cycles.use_denoising = False
    sc.cycles.use_adaptive_sampling = False
    n = Vector(normal).normalized()
    bpy.ops.mesh.primitive_plane_add(size=0.3, location=(0, 0, 0))
    card = bpy.context.active_object
    card.rotation_euler = n.to_track_quat('Z', 'Y').to_euler()
    m = bpy.data.materials.new('card'); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new('ShaderNodeOutputMaterial'); d = nt.nodes.new('ShaderNodeBsdfDiffuse')
    d.inputs['Color'].default_value = (0.8, 0.8, 0.8, 1); nt.links.new(d.outputs[0], o.inputs[0])
    card.data.materials.append(m)
    cam = RV.look_cam('cal', (0, 0, 0), n * 0.5, ortho=0.1)
    sc.camera = cam
    sc.render.image_settings.file_format = 'OPEN_EXR'
    sc.render.image_settings.color_depth = '32'
    return sc


def read():
    sc = bpy.context.scene
    sc.render.filepath = TMP
    bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(TMP, check_existing=False)
    px = np.array(im.pixels[:], dtype=np.float64).reshape(-1, 4)
    bpy.data.images.remove(im)
    return [round(float(x), 4) for x in px[:, :3].mean(0)]


def measure(warm):
    out = {}
    key_dir = None
    for label in ('key', 'up', 'bench_camera'):
        if label == 'key':
            bpy.ops.wm.read_factory_settings(use_empty=True)
            RV.studio(samples=4, res=(8, 8), warm=warm)
            key_dir = tuple(bpy.data.objects['light_key'].location)
        n = {'key': key_dir, 'up': (0, 0, 1), 'bench_camera': (0, -math.cos(math.radians(40)), math.sin(math.radians(40)))}[label]
        sc = card_scene(warm, n)
        lights = {o.name: o.data.energy for o in bpy.data.objects if o.type == 'LIGHT'}
        bg = [x for x in sc.world.node_tree.nodes if x.type == 'MATH'][0]
        sky = bg.inputs[1].default_value
        row = {'all': read()}
        for which in list(lights) + ['sky']:
            for nm, e in lights.items():
                bpy.data.objects[nm].data.energy = e if nm == which else 0.0
            bg.inputs[1].default_value = sky if which == 'sky' else 0.0
            row[which] = read()
        for nm, e in lights.items():
            bpy.data.objects[nm].data.energy = e
        bg.inputs[1].default_value = sky
        row['energies'] = dict(lights, sky=sky)
        out['card_facing_' + label] = row
    return out


res['neutral'] = measure(False)
res['warm'] = measure(True)
res['target'] = 'a white diffuse card of albedo 0.8 facing the key reads about 0.9 (largest channel) in both rigs'
json.dump(res, open(OUT, 'w'), indent=1)
try:
    os.remove(TMP)
except OSError:
    pass
for rig in ('neutral', 'warm'):
    for k, v in res[rig].items():
        print('CAL', rig, k, json.dumps(v), flush=True)
