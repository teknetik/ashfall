"""Ranged enemies: rigged gunner inspection (headless Blender 5.2, Cycles CPU).
Usage: blender.sh inspect_rig.py -- <rig folder> <render dir> [clip stem ...]
Rest model: front/side/back/three-quarter renders, head/optic, gun arm, left hand and feet close-ups, bone list, weights.
Each clip: strip of four phases (front three-quarter from the gun side) + foot height, height, edge stretch, bone motion and
the gun-arm aim (right forearm direction: azimuth from +forward, elevation) per sampled frame. Writes <render dir>/rig.json
(or clips-<first stem>.json when clip stems are given)."""
import bpy, sys, json, math
from pathlib import Path
from mathutils import Vector, Matrix
import numpy as np
args = sys.argv[sys.argv.index('--') + 1:]
RIG, OUT = Path(args[0]), Path(args[1]); ONLY = args[2:]
OUT.mkdir(parents=True, exist_ok=True)
report = {}


def reset(res=(560, 700)):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.render.engine = 'CYCLES'; s.cycles.device = 'CPU'; s.cycles.samples = 14; s.cycles.use_denoising = True
    s.view_settings.view_transform = 'AgX'
    s.render.resolution_x, s.render.resolution_y = res
    w = bpy.data.worlds.new('w'); s.world = w; w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[0].default_value = (.55, .58, .62, 1); w.node_tree.nodes['Background'].inputs[1].default_value = .7
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); s.collection.objects.link(sun)
    sun.data.energy = 3.0; sun.rotation_euler = (math.radians(50), 0, math.radians(-35))
    fill = bpy.data.objects.new('fill', bpy.data.lights.new('fill', 'AREA')); s.collection.objects.link(fill)
    fill.data.energy = 300; fill.data.size = 3; fill.location = (3, -3, 2.5); fill.rotation_euler = (math.radians(60), 0, math.radians(45))
    bpy.ops.mesh.primitive_plane_add(size=14, location=(0, 0, 0))
    g = bpy.context.object; m = bpy.data.materials.new('ground'); m.use_nodes = True
    m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.36, .31, .26, 1); g.data.materials.append(m)
    # 1.8 m human scale marker 1.3 m to the gunner's left (+X in Blender: the model faces -Y)
    mk = bpy.data.materials.new('marker'); mk.use_nodes = True
    mk.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.15, .35, .8, 1)
    for kind, loc, sc in [('c', (1.2, .4, .45), (.07, .07, .45)), ('c', (1.4, .4, .45), (.07, .07, .45)), ('c', (1.3, .4, 1.17), (.19, .12, .3)),
                          ('s', (1.3, .4, 1.68), (.11, .11, .12)), ('c', (1.03, .4, 1.12), (.05, .05, .33)), ('c', (1.57, .4, 1.12), (.05, .05, .33))]:
        (bpy.ops.mesh.primitive_cylinder_add if kind == 'c' else bpy.ops.mesh.primitive_uv_sphere_add)(location=loc)
        o = bpy.context.object; o.scale = sc; o.data.materials.append(mk); o.name = 'marker'
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); s.collection.objects.link(cam); s.camera = cam
    return s


def load(glb):
    bpy.ops.import_scene.gltf(filepath=str(glb))
    arm = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
    mesh = next(o for o in bpy.context.scene.objects if o.type == 'MESH' and o.name != 'Plane' and not o.name.startswith('marker'))
    return arm, mesh


def world_verts(mesh):
    dg = bpy.context.evaluated_depsgraph_get(); ev = mesh.evaluated_get(dg); me = ev.to_mesh()
    co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    mw = np.array(ev.matrix_world); co = co @ mw[:3, :3].T + mw[:3, 3]
    ed = np.empty(len(me.edges) * 2, np.int32); me.edges.foreach_get('vertices', ed); ed = ed.reshape(-1, 2)
    ev.to_mesh_clear(); return co, ed


def shoot(name, target, dist, yaw_deg, height, lens=50, res=None):
    s = bpy.context.scene; cam = s.camera; cam.data.lens = lens
    if res: s.render.resolution_x, s.render.resolution_y = res
    yaw = math.radians(yaw_deg)  # 0 = front (glTF +Z forward = Blender -Y)
    cam.location = Vector(target) + Vector((math.sin(yaw) * dist, -math.cos(yaw) * dist, height - target[2]))
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    s.render.filepath = str(OUT / f'{name}.png'); bpy.ops.render.render(write_still=True)
    return f'{name}.png'


def bone_world(arm, name):
    pb = arm.pose.bones[name]; m = arm.matrix_world
    return m @ pb.head, m @ pb.tail


def aim(arm):
    """Right forearm direction: azimuth (deg, 0 = straight ahead -Y, + = toward the robot's left/+X) and elevation."""
    h, t = bone_world(arm, 'RightForeArm'); d = (t - h).normalized()
    return round(math.degrees(math.atan2(d.x, -d.y)), 1), round(math.degrees(math.asin(max(-1, min(1, d.z)))), 1)


rigged = RIG / 'rigged.glb'
if not ONLY:
    s = reset(); arm, mesh = load(rigged)
    for o in s.objects:
        if o.animation_data: o.animation_data.action = None
    for pb in arm.pose.bones: pb.matrix_basis = Matrix()
    bpy.context.view_layer.update()
    co, ed = world_verts(mesh); lo, hi = co.min(0), co.max(0)
    vg = {g.index: g.name for g in mesh.vertex_groups}
    infl = [sum(1 for g in v.groups if g.weight > .01) for v in mesh.data.vertices]
    imgs = [dict(name=im.name, size=list(im.size), colorspace=im.colorspace_settings.name) for im in bpy.data.images if im.size[0]]
    mat = mesh.data.materials[0]
    links = {l.to_socket.name: (l.from_node.type, getattr(l.from_node, 'image', None) and l.from_node.image.name)
             for l in mat.node_tree.links if l.to_node.type == 'BSDF_PRINCIPLED'}
    report['model'] = dict(triangles=sum(len(p.vertices) - 2 for p in mesh.data.polygons), vertices=len(mesh.data.vertices),
        bones=[(b.name, b.parent.name if b.parent else None) for b in arm.data.bones], bounds_min=lo.round(4).tolist(),
        bounds_max=hi.round(4).tolist(), height=round(float(hi[2] - lo[2]), 4), max_influences=max(infl), images=imgs,
        material=mat.name, bsdf_links={k: list(v) for k, v in links.items()}, rest_aim=aim(arm))
    H = float(hi[2]); r = report['renders'] = {}
    for nm, yaw in (('front', 0), ('side_right', -90), ('back', 180), ('threequarter', -35)):
        r['rest_' + nm] = shoot('rest_' + nm, (.35, 0, H * .5), 5.2, yaw, H * .55, res=(900, 900))
    hd = bone_world(arm, 'Head')[0]
    r['head'] = shoot('rest_head', (hd.x, hd.y, hd.z + .08), .9, 15, hd.z + .12, lens=85, res=(700, 700))
    fh, ft = bone_world(arm, 'RightForeArm'); rh = bone_world(arm, 'RightHand')[0]
    gc = (fh + rh) / 2 + (rh - fh) * .4
    r['gun_arm'] = shoot('rest_gun_arm', tuple(gc), 1.4, -60, gc.z + .3, lens=55, res=(800, 700))
    r['gun_arm_under'] = shoot('rest_gun_arm_under', tuple(gc), 1.2, 30, gc.z - .5, lens=55, res=(800, 700))
    lh = bone_world(arm, 'LeftHand')[0]
    r['left_hand'] = shoot('rest_left_hand', tuple(lh), .8, 40, lh.z + .15, lens=70, res=(700, 700))
    r['feet'] = shoot('rest_feet', (0, 0, .12), 1.7, 20, .55, res=(1000, 600))
    # weights of the gun arm: which bones hold the vertices beyond the right wrist
    d = (rh - fh).normalized(); proj = (co - np.array(rh)) @ np.array(d)
    beyond = np.flatnonzero(proj > .02)
    lat = np.linalg.norm((co[beyond] - np.array(rh)) - np.outer(proj[beyond], np.array(d)), axis=1)
    beyond = beyond[lat < .25]
    from collections import Counter
    cnt = Counter()
    for i in beyond:
        gs = sorted(mesh.data.vertices[int(i)].groups, key=lambda g: -g.weight)
        if gs: cnt[vg[gs[0].group]] += 1
    report['gun_tip_region'] = dict(vertices=len(beyond), dominant_bone=dict(cnt), max_projection_past_wrist=round(float(proj.max()), 4))

clips = sorted(p for p in RIG.glob('*.glb') if p.stem != 'rigged' and not p.stem.startswith('basic_'))
clips += sorted(RIG.glob('basic_*.glb'))
if ONLY: clips = [RIG / f'{c}.glb' for c in ONLY]
report['clips'] = {}
for glb in clips:
    s = reset(); arm, mesh = load(glb)
    act = arm.animation_data.action if arm.animation_data else None
    f0, f1 = (int(act.frame_range[0]), int(act.frame_range[1])) if act else (1, 1)
    arm.animation_data.action = None
    for pb in arm.pose.bones: pb.matrix_basis = Matrix()
    bpy.context.view_layer.update(); c0, e0 = world_verts(mesh)
    rest_len = np.linalg.norm(c0[e0[:, 0]] - c0[e0[:, 1]], axis=1) + 1e-6
    arm.animation_data.action = act
    s.frame_set(f0); bpy.context.view_layer.update()
    rest_rot = {pb.name: (arm.matrix_world @ pb.matrix).to_quaternion() for pb in arm.pose.bones}
    feet, top, maxang, stretch, aims, root = [], [], {}, 0.0, [], []
    step = max(1, (f1 - f0) // 30)
    for f in range(f0, f1 + 1, step):
        s.frame_set(f); bpy.context.view_layer.update()
        c, e = world_verts(mesh)
        feet.append(float(c[:, 2].min())); top.append(float(c[:, 2].max()))
        L = np.linalg.norm(c[e[:, 0]] - c[e[:, 1]], axis=1); stretch = max(stretch, float((L / rest_len).max()))
        for pb in arm.pose.bones:
            q = (arm.matrix_world @ pb.matrix).to_quaternion()
            a_ = math.degrees(rest_rot[pb.name].rotation_difference(q).angle); a_ = min(a_, 360 - a_)
            maxang[pb.name] = max(maxang.get(pb.name, 0), a_)
        aims.append((f, *aim(arm)))
        hp = bone_world(arm, 'Hips')[0]; root.append((round(hp.x, 3), round(hp.y, 3)))
    strip = []
    for k, ph in enumerate((.12, .37, .62, .87)):
        f = int(round(f0 + ph * (f1 - f0))); s.frame_set(f); bpy.context.view_layer.update()
        hp = bone_world(arm, 'Hips')[0]
        strip.append(shoot(f'{glb.stem}_p{k}', (hp.x + .3, hp.y, 1.0), 5.0, -30, 1.3, res=(560, 700)))
    report['clips'][glb.stem] = dict(action=act.name if act else None, frames=[f0, f1], seconds=round((f1 - f0) / 30, 2),
        sole_z=[round(min(feet), 3), round(max(feet), 3)], top_z=[round(min(top), 3), round(max(top), 3)],
        max_edge_stretch=round(stretch, 3), hips_xy_start_end=[root[0], root[-1]],
        bone_motion_deg=[(k, round(v, 1)) for k, v in sorted(maxang.items(), key=lambda kv: -kv[1])[:8]],
        right_forearm_aim_az_el=aims, strip=strip)
name = 'rig.json' if not ONLY else f'clips-{ONLY[0]}.json'
(OUT / name).write_text(json.dumps(report, indent=1)); print('RIG INSPECT DONE')
