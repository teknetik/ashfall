"""Headless Blender: frame sheets of the player's rifle library clips, and a rough fit of the Meshy plate carrier on the
rigged colonist. Workbench renders only. Usage: blender.sh preview.py"""
import bpy, math, sys, json
from pathlib import Path
from mathutils import Vector
ROOT = Path('/home/teknetik/code/ao2')
CLIPS = ROOT / 'meshy/character-feel-20260927/player-rifle'
OUT_CLIPS = CLIPS / 'previews'; OUT_CLIPS.mkdir(exist_ok=True)
CARRIER = ROOT / 'meshy/plate-carrier-20261002'
OUT_FIT = CARRIER / 'fit'
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'; sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'MATERIAL'
sc.render.resolution_x = 360; sc.render.resolution_y = 480; sc.render.film_transparent = False
sc.world = bpy.data.worlds.new('w') if not sc.world else sc.world
def clear():
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    for c in (bpy.data.meshes, bpy.data.armatures, bpy.data.materials, bpy.data.images, bpy.data.actions): 
        for b in list(c):
            if b.users == 0: c.remove(b)
def camera(target, dist, yaw_deg, pitch_deg=10, lens=50):
    cam = bpy.data.cameras.new('cam'); co = bpy.data.objects.new('cam', cam); sc.collection.objects.link(co); sc.camera = co
    cam.lens = lens
    yaw = math.radians(yaw_deg); pitch = math.radians(pitch_deg)
    pos = Vector((math.sin(yaw) * dist * math.cos(pitch), -math.cos(yaw) * dist * math.cos(pitch), target.z + dist * math.sin(pitch)))
    co.location = pos
    d = Vector(target) - pos; co.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return co
def render(path):
    sc.render.filepath = str(path); bpy.ops.render.render(write_still=True)
def bbox(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs if o.type == 'MESH' for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))); hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi
report = {}
# 1. clip frame sheets
for name in ['lower_334', 'aim_95', 'rifleturn_573', 'runshoot_98', 'charge_511']:
    clear()
    bpy.ops.import_scene.gltf(filepath=str(CLIPS / f'{name}.glb'))
    objs = list(bpy.context.scene.objects)
    arm = next((o for o in objs if o.type == 'ARMATURE'), None)
    act = arm.animation_data.action if arm and arm.animation_data else None
    f0, f1 = (int(act.frame_range[0]), int(act.frame_range[1])) if act else (0, 0)
    lo, hi = bbox(objs); centre = (lo + hi) / 2
    report[name] = {'frames': [f0, f1], 'fps': sc.render.fps, 'height_m': round(hi.z - lo.z, 3)}
    cam = camera(centre, 4.2, 35, 8, 50)
    for i, frac in enumerate([0, .2, .4, .6, .8, 1.0]):
        sc.frame_set(int(round(f0 + (f1 - f0) * frac)))
        render(OUT_CLIPS / f'{name}_{i}.png')
    bpy.data.objects.remove(cam)
# 2. plate carrier fit on the rigged colonist (rest pose)
clear()
bpy.ops.import_scene.gltf(filepath=str(CLIPS / 'rigged.glb'))
body = [o for o in bpy.context.scene.objects if o.type == 'MESH']
blo, bhi = bbox(body)
# chest width: body vertices between 1.25 and 1.45 m (shoulders) in world space
xs = []; ys = []
for o in body:
    mw = o.matrix_world
    dep = bpy.context.evaluated_depsgraph_get(); ev = o.evaluated_get(dep)
    for v in ev.data.vertices:
        p = mw @ v.co
        if 1.2 < p.z < 1.45: xs.append(p.x); ys.append(p.y)
chest_w = max(xs) - min(xs); chest_d = max(ys) - min(ys); chest_cx = (max(xs) + min(xs)) / 2; chest_cy = (max(ys) + min(ys)) / 2
report['colonist'] = {'height': round(bhi.z - blo.z, 3), 'chest_width_1.2-1.45': round(chest_w, 3), 'chest_depth': round(chest_d, 3), 'chest_centre': [round(chest_cx, 3), round(chest_cy, 3)]}
before = set(bpy.context.scene.objects)
bpy.ops.import_scene.gltf(filepath=str(CARRIER / 'refine.glb'))
vest = [o for o in bpy.context.scene.objects if o not in before and o.type == 'MESH']
vroot = [o for o in bpy.context.scene.objects if o not in before and o.parent is None]
vlo, vhi = bbox(vest)
report['vest_raw'] = {'size': [round(vhi.x - vlo.x, 3), round(vhi.y - vlo.y, 3), round(vhi.z - vlo.z, 3)]}
# scale so the vest is ~0.46 m wide at the chest (slightly over the body), centre it on the chest
target_w = chest_w + .06
s = target_w / (vhi.x - vlo.x)
for r in vroot: r.scale = r.scale * s
bpy.context.view_layer.update(); vlo, vhi = bbox(vest)
vc = (vlo + vhi) / 2
shift = Vector((chest_cx - vc.x, chest_cy - vc.y, 1.33 - vc.z))
for r in vroot: r.location = r.location + shift
bpy.context.view_layer.update(); vlo, vhi = bbox(vest)
report['vest_fit'] = {'scale': round(s, 4), 'size': [round(vhi.x - vlo.x, 3), round(vhi.y - vlo.y, 3), round(vhi.z - vlo.z, 3)], 'z_range': [round(vlo.z, 3), round(vhi.z, 3)], 'centre_xy': [round((vlo.x + vhi.x) / 2, 3), round((vlo.y + vhi.y) / 2, 3)]}
sc.render.resolution_x = 480; sc.render.resolution_y = 640
centre = Vector((chest_cx, chest_cy, 1.1))
for label, yaw in [('front', 0), ('side', 90), ('quarter', 40), ('back', 180)]:
    cam = camera(centre, 3.2, yaw, 5, 60); render(OUT_FIT / f'fit_{label}.png'); bpy.data.objects.remove(cam)
# which way does the colonist face? vertex mean of the head region vs nose: report the y of the face-most vertices
(OUT_FIT / 'fit.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
