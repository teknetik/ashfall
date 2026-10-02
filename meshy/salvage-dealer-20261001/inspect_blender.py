"""Brann inspection (headless Blender, Cycles CPU). Usage: blender.sh inspect_blender.py -- <record folder>
Renders the rigged model (front/side/three-quarter/back full body, face, hands) and a mid frame of each clip, and writes
inspect.json: triangles, bones, bounds, textures, metallic statistics, per-clip foot height, bone motion and skin stretch."""
import bpy, sys, json, math
from pathlib import Path
from mathutils import Vector, Matrix
import numpy as np
HERE = Path(sys.argv[sys.argv.index('--') + 1])
OUT = HERE / 'renders'; OUT.mkdir(exist_ok=True)
report = {}


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.render.engine = 'CYCLES'; s.cycles.device = 'CPU'; s.cycles.samples = 24; s.cycles.use_denoising = True
    s.render.resolution_x, s.render.resolution_y = 640, 960; s.render.film_transparent = False
    w = bpy.data.worlds.new('w'); s.world = w; w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[0].default_value = (.55, .58, .62, 1); w.node_tree.nodes['Background'].inputs[1].default_value = .6
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); s.collection.objects.link(sun)
    sun.data.energy = 3.2; sun.rotation_euler = (math.radians(50), 0, math.radians(-35))
    fill = bpy.data.objects.new('fill', bpy.data.lights.new('fill', 'AREA')); s.collection.objects.link(fill)
    fill.data.energy = 250; fill.data.size = 3; fill.location = (3, -3, 2); fill.rotation_euler = (math.radians(60), 0, math.radians(45))
    bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, 0))
    g = bpy.context.object; m = bpy.data.materials.new('ground'); m.use_nodes = True
    m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.35, .3, .25, 1); g.data.materials.append(m)
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); s.collection.objects.link(cam); s.camera = cam
    return s


def load(glb):
    bpy.ops.import_scene.gltf(filepath=str(glb))
    arm = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
    mesh = next(o for o in bpy.context.scene.objects if o.type == 'MESH' and o.name != 'Plane')
    return arm, mesh


def world_verts(mesh):
    dg = bpy.context.evaluated_depsgraph_get(); ev = mesh.evaluated_get(dg); me = ev.to_mesh()
    co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    mw = np.array(ev.matrix_world); co = co @ mw[:3, :3].T + mw[:3, 3]
    ed = np.empty(len(me.edges) * 2, np.int32); me.edges.foreach_get('vertices', ed); ed = ed.reshape(-1, 2)
    ev.to_mesh_clear(); return co, ed


def shoot(name, target, dist, yaw_deg, height, lens=50, res=(640, 960)):
    s = bpy.context.scene; cam = s.camera; cam.data.lens = lens
    s.render.resolution_x, s.render.resolution_y = res
    yaw = math.radians(yaw_deg)  # 0 = front (model faces -Y in Blender after glTF import)
    cam.location = Vector(target) + Vector((math.sin(yaw) * dist, -math.cos(yaw) * dist, height - target[2]))
    d = Vector(target) - cam.location; cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    s.render.filepath = str(OUT / f'{name}.png'); bpy.ops.render.render(write_still=True)
    return str((OUT / f'{name}.png').relative_to(HERE))


# 1. Rigged model at rest.
s = reset(); arm, mesh = load(HERE / 'rigged.glb')
for o in s.objects:
    if o.animation_data: o.animation_data.action = None
for pb in arm.pose.bones: pb.matrix_basis = Matrix()
bpy.context.view_layer.update()
co, ed = world_verts(mesh)
lo, hi = co.min(0), co.max(0)
tris = sum(len(p.vertices) - 2 for p in mesh.data.polygons)
imgs = []
for im in bpy.data.images:
    if im.size[0] == 0: continue
    px = np.empty(im.size[0] * im.size[1] * im.channels, np.float32); im.pixels.foreach_get(px)
    px = px.reshape(-1, im.channels)
    imgs.append(dict(name=im.name, size=list(im.size), colorspace=im.colorspace_settings.name,
                     mean=[round(float(x), 3) for x in px.mean(0)], p95=[round(float(x), 3) for x in np.percentile(px, 95, axis=0)]))
mat = mesh.data.materials[0]
links = {l.to_socket.name: (l.from_node.type, getattr(l.from_node, 'image', None) and l.from_node.image.name, l.from_socket.name)
         for l in mat.node_tree.links if l.to_node.type == 'BSDF_PRINCIPLED'}
report['model'] = dict(triangles=tris, vertices=len(mesh.data.vertices), bones=[b.name for b in arm.data.bones],
                       bone_count=len(arm.data.bones), bounds_min=lo.round(4).tolist(), bounds_max=hi.round(4).tolist(),
                       height=round(float(hi[2] - lo[2]), 4), armature_scale=list(arm.scale), images=imgs,
                       material=mat.name, bsdf_links={k: list(v) for k, v in links.items()})
H = float(hi[2]); cx, cy = float((lo[0] + hi[0]) / 2), float((lo[1] + hi[1]) / 2)
head = arm.matrix_world @ arm.data.bones['Head'].head_local
lh = arm.matrix_world @ arm.data.bones['LeftHand'].head_local; rh = arm.matrix_world @ arm.data.bones['RightHand'].head_local
r = report['renders'] = {}
r['rest_front'] = shoot('rest_front', (cx, cy, H * .5), 4.6, 0, H * .55)
r['rest_side'] = shoot('rest_side', (cx, cy, H * .5), 4.6, 90, H * .55)
r['rest_threequarter'] = shoot('rest_threequarter', (cx, cy, H * .5), 4.6, 35, H * .55)
r['rest_back'] = shoot('rest_back', (cx, cy, H * .5), 4.6, 180, H * .55)
face = (head.x, head.y, head.z + .08)
r['face'] = shoot('face', face, .9, 15, face[2] + .02, lens=85, res=(768, 768))
r['hand_left'] = shoot('hand_left', tuple(lh), .7, 30, lh.z + .1, lens=85, res=(768, 768))
r['hand_right'] = shoot('hand_right', tuple(rh), .7, -30, rh.z + .1, lens=85, res=(768, 768))
r['feet'] = shoot('feet', (cx, cy, .12), 1.6, 20, .5, lens=50, res=(960, 640))
rest_edges = np.linalg.norm(co[ed[:, 0]] - co[ed[:, 1]], axis=1) + 1e-6

# 2. Clips.
report['clips'] = {}
for glb in sorted(HERE.glob('*.glb')):
    if glb.stem in ('rigged',): continue
    s = reset(); arm, mesh = load(glb)
    act = arm.animation_data.action if arm.animation_data else None
    f0, f1 = (int(act.frame_range[0]), int(act.frame_range[1])) if act else (1, 1)
    arm.animation_data.action = None
    for pb in arm.pose.bones: pb.matrix_basis = Matrix()
    bpy.context.view_layer.update(); c0, e0 = world_verts(mesh)
    clip_rest = np.linalg.norm(c0[e0[:, 0]] - c0[e0[:, 1]], axis=1) + 1e-6
    arm.animation_data.action = act
    rest_rot = {}
    s.frame_set(f0); bpy.context.view_layer.update()
    for pb in arm.pose.bones: rest_rot[pb.name] = (arm.matrix_world @ pb.matrix).to_quaternion()
    feet, top, maxang, stretch, worst = [], [], {}, 0.0, 0
    frames = list(range(f0, f1 + 1, max(1, (f1 - f0) // 24)))
    for f in frames:
        s.frame_set(f); bpy.context.view_layer.update()
        c, e = world_verts(mesh)
        feet.append(float(c[:, 2].min())); top.append(float(c[:, 2].max()))
        L = np.linalg.norm(c[e[:, 0]] - c[e[:, 1]], axis=1); ratio = L / clip_rest
        stretch = max(stretch, float(ratio.max())); worst = max(worst, int((ratio > 1.8).sum()))
        for pb in arm.pose.bones:
            q = (arm.matrix_world @ pb.matrix).to_quaternion()
            maxang[pb.name] = max(maxang.get(pb.name, 0), math.degrees(rest_rot[pb.name].rotation_difference(q).angle))
    mid = (f0 + f1) // 2; s.frame_set(mid); bpy.context.view_layer.update()
    c, _ = world_verts(mesh); lo2, hi2 = c.min(0), c.max(0); H2 = float(hi2[2])
    cx2, cy2 = float((lo2[0] + hi2[0]) / 2), float((lo2[1] + hi2[1]) / 2)
    rr = {'mid_front': shoot(f'{glb.stem}_mid_front', (cx2, cy2, H2 * .5), 4.4, 0, H2 * .55),
          'mid_threequarter': shoot(f'{glb.stem}_mid_threequarter', (cx2, cy2, H2 * .55), 3.2, 40, H2 * .6)}
    if glb.stem.startswith('talk'):
        q = (f0 + 3 * f1) // 4; s.frame_set(q); bpy.context.view_layer.update()
        rr['q3_front'] = shoot(f'{glb.stem}_q3_front', (cx2, cy2, H2 * .55), 3.2, 10, H2 * .6)
    top_moving = sorted(maxang.items(), key=lambda kv: -kv[1])[:6]
    report['clips'][glb.stem] = dict(action=act.name if act else None, frames=[f0, f1], fps=s.render.fps,
        seconds=round((f1 - f0) / 30, 2), min_vertex_z=[round(min(feet), 4), round(max(feet), 4)],
        max_vertex_z=[round(min(top), 4), round(max(top), 4)], max_edge_stretch=round(stretch, 3),
        edges_stretched_over_1_8x=worst, bone_motion_deg=[(k, round(v, 1)) for k, v in top_moving],
        hips_motion_deg=round(maxang.get('Hips', 0), 1), head_motion_deg=round(maxang.get('Head', 0), 1), renders=rr)
(HERE / 'inspect.json').write_text(json.dumps(report, indent=2)); print('INSPECT DONE')
