"""Feral gunner build inspection (headless Blender 5.2, Cycles CPU).
Usage: blender.sh inspect_gunner.py -- <build dir> <render dir> [clip ...]
For each clip GLB in <build dir>/clips (merged rig + strapped forearm gun): four phases from the gun side and from the
front-left, and per sampled frame: sole height, top, the gun's clearance from the rest of the body (gun vertices within
1.5 cm of a body vertex that is not driven by the right forearm/hand), and the barrel direction. Fire/aim clips also get
game-distance views (25 m and 35 m, 60 deg vertical FOV at 1080p, cropped) to judge how the shot reads at range.
Writes <render dir>/gunner_inspect.json."""
import bpy, sys, json, math
from pathlib import Path
from mathutils import Vector, Matrix, kdtree
import numpy as np
args = sys.argv[sys.argv.index('--') + 1:]
BUILD, OUT = Path(args[0]), Path(args[1]); ONLY = args[2:]
OUT.mkdir(parents=True, exist_ok=True)
report = {}


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.render.engine = 'CYCLES'; s.cycles.device = 'CPU'; s.cycles.samples = 14; s.cycles.use_denoising = True
    s.view_settings.view_transform = 'AgX'; s.render.fps = 30
    w = bpy.data.worlds.new('w'); s.world = w; w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[0].default_value = (.62, .6, .56, 1); w.node_tree.nodes['Background'].inputs[1].default_value = .8
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); s.collection.objects.link(sun)
    sun.data.energy = 3.2; sun.rotation_euler = (math.radians(50), 0, math.radians(-35))
    bpy.ops.mesh.primitive_plane_add(size=120, location=(0, 0, 0))
    g = bpy.context.object; m = bpy.data.materials.new('ground'); m.use_nodes = True
    m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.5, .42, .32, 1); g.data.materials.append(m)
    mk = bpy.data.materials.new('marker'); mk.use_nodes = True
    mk.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.15, .35, .8, 1)
    for kind, loc, sc in [('c', (1.2, .6, .45), (.07, .07, .45)), ('c', (1.4, .6, .45), (.07, .07, .45)), ('c', (1.3, .6, 1.17), (.19, .12, .3)),
                          ('s', (1.3, .6, 1.68), (.11, .11, .12)), ('c', (1.03, .6, 1.12), (.05, .05, .33)), ('c', (1.57, .6, 1.12), (.05, .05, .33))]:
        (bpy.ops.mesh.primitive_cylinder_add if kind == 'c' else bpy.ops.mesh.primitive_uv_sphere_add)(location=loc)
        o = bpy.context.object; o.scale = sc; o.data.materials.append(mk); o.name = 'marker'
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); s.collection.objects.link(cam); s.camera = cam
    return s


def load(glb):
    bpy.ops.import_scene.gltf(filepath=str(glb))
    sc = bpy.context.scene
    arm = next(o for o in sc.objects if o.type == 'ARMATURE')
    body = max((o for o in sc.objects if o.type == 'MESH' and any(m.type == 'ARMATURE' for m in o.modifiers)), key=lambda o: len(o.data.vertices))
    gun = next(o for o in sc.objects if o.type == 'MESH' and o.name.startswith('ForearmGun'))
    muz = next(o for o in sc.objects if o.name.startswith('Muzzle'))
    gun.parent = None   # placed per frame from <clip>.gun.json (see make_gunner.py)
    return arm, body, gun, muz


C = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))   # glTF (Y up) -> Blender (Z up)
def place_gun(gun, mats, k):
    m = Matrix(mats[max(0, min(k, len(mats) - 1))])
    gun.matrix_world = C @ m @ C.inverted()
    bpy.context.view_layer.update()


def verts(o):
    dg = bpy.context.evaluated_depsgraph_get(); ev = o.evaluated_get(dg); me = ev.to_mesh()
    co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    mw = np.array(ev.matrix_world); co = co @ mw[:3, :3].T + mw[:3, 3]; ev.to_mesh_clear(); return co


def shoot(name, target, dist, yaw, height, lens=50, res=(560, 700)):
    s = bpy.context.scene; cam = s.camera; cam.data.lens = lens; cam.data.sensor_fit = 'VERTICAL'; cam.data.sensor_height = 24
    s.render.resolution_x, s.render.resolution_y = res
    y = math.radians(yaw)   # 0 = in front of the robot (it faces -Y in Blender)
    cam.location = Vector(target) + Vector((math.sin(y) * dist, -math.cos(y) * dist, height - target[2]))
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    s.render.filepath = str(OUT / f'{name}.png'); bpy.ops.render.render(write_still=True)
    return f'{name}.png'


def game_view(name, dist, yaw):
    """60 deg vertical FOV at 1920x1080, rendered as a 480x480 crop around the robot (1:1 game pixels)."""
    s = bpy.context.scene; cam = s.camera
    fov = math.radians(60); full_h = 1080
    # crop: 480 px of a 1080 px frame -> the same angular size per pixel with a narrower camera
    crop = 480; cam.data.sensor_fit = 'VERTICAL'; cam.data.sensor_height = 24
    cam.data.lens = 12 / math.tan(fov / 2) * full_h / crop
    s.render.resolution_x = s.render.resolution_y = crop
    y = math.radians(yaw); tgt = Vector((0, 0, 1.2))
    cam.location = tgt + Vector((math.sin(y) * dist, -math.cos(y) * dist, .5))
    cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()
    s.render.filepath = str(OUT / f'{name}.png'); bpy.ops.render.render(write_still=True)
    return f'{name}.png'


clips = sorted((BUILD / 'clips').glob('*.glb'))
if ONLY: clips = [BUILD / 'clips' / f'{c}.glb' for c in ONLY]
for glb in clips:
    s = reset(); arm, body, gun, muz = load(glb)
    # mark the lens of the muzzle for the renders: a small bright sphere 2 cm ahead of the muzzle (not exported)
    act = arm.animation_data.action
    f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
    mats = json.loads((BUILD / 'clips' / f'{glb.stem}.gun.json').read_text())
    def goto(f): s.frame_set(f); bpy.context.view_layer.update(); place_gun(gun, mats, f - f0)
    # vertices driven by the right forearm/hand (excluded from the clearance test)
    vg = {g.index: g.name for g in body.vertex_groups}
    own = np.array([max(v.groups, key=lambda g: g.weight).group if v.groups else -1 for v in body.data.vertices])
    own_names = np.array([vg.get(int(i), '') for i in own])
    keep = ~np.isin(own_names, ['RightForeArm', 'RightHand'])
    rows = []
    for f in range(f0, f1 + 1, max(1, (f1 - f0) // 20)):
        goto(f)
        b = verts(body); g = verts(gun)
        kd = kdtree.KDTree(int(keep.sum()))
        for i, p in enumerate(b[keep]): kd.insert(p, i)
        kd.balance()
        close = sum(1 for p in g[::4] if kd.find(p)[2] < .015) * 4
        md = muz.matrix_world; d = md.to_3x3() @ Vector((0, -1, 0))   # glTF +Z of the muzzle empty = Blender local -Y (Y-up to Z-up conversion)
        rows.append(dict(frame=f, sole=round(float(b[:, 2].min()), 3), top=round(float(max(b[:, 2].max(), g[:, 2].max())), 3),
                         gun_lowest=round(float(g[:, 2].min()), 3), gun_verts_within_1_5cm_of_body=close,
                         muzzle=[round(x, 3) for x in md.translation], muzzle_axis=[round(x, 3) for x in d.normalized()]))
    strip = []
    for k, ph in enumerate((.1, .35, .6, .85)):
        f = int(round(f0 + ph * (f1 - f0))); goto(f)
        hp = arm.matrix_world @ arm.pose.bones['Hips'].head
        strip.append(shoot(f'{glb.stem}_p{k}_gunside', (hp.x - .2, hp.y, 1.0), 5.2, -40, 1.4))
        strip.append(shoot(f'{glb.stem}_p{k}_front', (hp.x, hp.y, 1.0), 5.2, 25, 1.3))
    extra = {}
    if glb.stem in ('fire', 'fire_raise', 'aim'):
        shot = {'fire_raise': .55, 'fire': .05, 'aim': 0}[glb.stem]
        for lab, dt in (('hold', -.1), ('shot', .03), ('recoil', .1), ('settle', .35)):
            f = int(round(f0 + (shot + dt) * 30))
            if f < f0 or f > f1: continue
            goto(f)
            extra[lab] = [shoot(f'{glb.stem}_{lab}_front', (0, 0, 1.2), 6, 15, 1.5), game_view(f'{glb.stem}_{lab}_game25m', 25, 20),
                          game_view(f'{glb.stem}_{lab}_game35m_side', 35, -70)]
            if glb.stem == 'aim': break
    report[glb.stem] = dict(frames=[f0, f1], gun_matrices=len(mats), samples=rows, strip=strip, fire_views=extra,
                            max_gun_body_contact=max(r['gun_verts_within_1_5cm_of_body'] for r in rows),
                            sole_range=[min(r['sole'] for r in rows), max(r['sole'] for r in rows)])
    print('CLIP', glb.stem, report[glb.stem]['max_gun_body_contact'], flush=True)
name = 'gunner_inspect.json' if not ONLY else f'gunner_inspect_{ONLY[0]}.json'
(OUT / name).write_text(json.dumps(report, indent=1)); print('GUNNER INSPECT DONE')
