"""Ranged enemies: static inspection of a Meshy GLB (headless Blender 5.2, Cycles CPU).
Usage: blender.sh inspect_static.py -- <model.glb> <render dir> <gunner|lancer> [prefix]
Scales the model uniformly to its intended size (gunner 2.0 m tall, lancer 1.75 m wide; for inspection only), renders
front / side / back / three-quarter views next to a 1.8 m human scale marker, enemy-specific close-ups and a normals
check (back faces red), and writes <prefix>stats.json: triangles, loose parts, open edges, bounds, texture stats."""
import bpy, bmesh, sys, json, math
from pathlib import Path
from mathutils import Vector
import numpy as np
args = sys.argv[sys.argv.index('--') + 1:]
GLB, OUT, KIND = Path(args[0]), Path(args[1]), args[2]
PFX = args[3] if len(args) > 3 else ''
OUT.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
s = bpy.context.scene
s.render.engine = 'CYCLES'; s.cycles.device = 'CPU'; s.cycles.samples = 20; s.cycles.use_denoising = True
s.view_settings.view_transform = 'AgX'
w = bpy.data.worlds.new('w'); s.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs[0].default_value = (.55, .58, .62, 1); w.node_tree.nodes['Background'].inputs[1].default_value = .7
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); s.collection.objects.link(sun)
sun.data.energy = 3.0; sun.rotation_euler = (math.radians(50), 0, math.radians(-35))
fill = bpy.data.objects.new('fill', bpy.data.lights.new('fill', 'AREA')); s.collection.objects.link(fill)
fill.data.energy = 300; fill.data.size = 3; fill.location = (3, -3, 2.5); fill.rotation_euler = (math.radians(60), 0, math.radians(45))
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); s.collection.objects.link(cam); s.camera = cam

bpy.ops.import_scene.gltf(filepath=str(GLB))
meshes = [o for o in s.objects if o.type == 'MESH']
# join into one for stats/scaling (keeps materials)
bpy.ops.object.select_all(action='DESELECT')
for o in meshes: o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
if len(meshes) > 1: bpy.ops.object.join()
obj = bpy.context.view_layer.objects.active
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
me = obj.data
co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
lo, hi = co.min(0), co.max(0); size = hi - lo
src_bounds = dict(min=lo.round(4).tolist(), max=hi.round(4).tolist(), size=size.round(4).tolist())
scale = 2.0 / size[2] if KIND == 'gunner' else 1.75 / max(size[0], size[1])
obj.scale = (scale,) * 3
bpy.ops.object.transform_apply(scale=True)
co *= scale; lo, hi = co.min(0), co.max(0)
# centre on X/Y, feet (gunner) or bottom (lancer) at z = 0 for the gunner; lancer floats with its centre at 1.0 m
off = Vector((-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2] if KIND == 'gunner' else 1.0 - (lo[2] + hi[2]) / 2))
obj.location = off; bpy.ops.object.transform_apply(location=True)
co += np.array(off); lo, hi = co.min(0), co.max(0)

# --- stats
bm = bmesh.new(); bm.from_mesh(me)
split_verts = len(bm.verts)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)  # glTF splits vertices at UV seams; weld for topology stats
bm.verts.ensure_lookup_table(); bm.verts.index_update()
co_w = np.array([v.co[:] for v in bm.verts], np.float32)
tris = sum(len(f.verts) - 2 for f in bm.faces)
open_edges = sum(1 for e in bm.edges if e.is_boundary)
nonmanifold = sum(1 for e in bm.edges if not e.is_manifold and not e.is_boundary)
degenerate = sum(1 for f in bm.faces if f.calc_area() < 1e-10)
# loose parts (vertex-connected components)
parent = list(range(len(bm.verts)))
def find(i):
    while parent[i] != i: parent[i] = parent[parent[i]]; i = parent[i]
    return i
for e in bm.edges:
    a, b = find(e.verts[0].index), find(e.verts[1].index)
    if a != b: parent[a] = b
roots = np.array([find(i) for i in range(len(bm.verts))])
uniq, counts = np.unique(roots, return_counts=True)
parts = []
for r_, c in sorted(zip(uniq, counts), key=lambda x: -x[1]):
    p = co_w[roots == r_]; plo, phi = p.min(0), p.max(0)
    parts.append(dict(verts=int(c), min=plo.round(3).tolist(), max=phi.round(3).tolist()))
bm.free()
imgs = []
for im in bpy.data.images:
    if im.size[0] == 0: continue
    px = np.empty(im.size[0] * im.size[1] * im.channels, np.float32); im.pixels.foreach_get(px); px = px.reshape(-1, im.channels)
    imgs.append(dict(name=im.name, size=list(im.size), colorspace=im.colorspace_settings.name,
                     mean=[round(float(x), 3) for x in px.mean(0)], p95=[round(float(x), 3) for x in np.percentile(px, 95, axis=0)]))
mats = []
for m in me.materials:
    links = {l.to_socket.name: (l.from_node.type, getattr(l.from_node, 'image', None) and l.from_node.image.name, l.from_socket.name)
             for l in m.node_tree.links if l.to_node.type == 'BSDF_PRINCIPLED'} if m and m.use_nodes else {}
    mats.append(dict(name=m.name if m else None, links={k: list(v) for k, v in links.items()}))
stats = dict(glb=str(GLB), kind=KIND, source_bounds=src_bounds, inspection_scale=round(float(scale), 5),
             triangles=tris, polygons=len(me.polygons), vertices=len(me.vertices), welded_vertices=len(co_w),
             open_edges=open_edges, nonmanifold_edges=nonmanifold, degenerate_faces=degenerate,
             loose_parts=len(parts), largest_parts=parts[:12], small_parts_under_50_verts=sum(1 for p in parts if p['verts'] < 50),
             scaled_bounds=dict(min=lo.round(3).tolist(), max=hi.round(3).tolist(), size=(hi - lo).round(3).tolist()),
             materials=mats, images=imgs)

# --- scale marker: 1.8 m mannequin of primitives, beside the model
def marker(x):
    mat = bpy.data.materials.new('marker'); mat.use_nodes = True
    mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.15, .35, .8, 1)
    z0 = 0 if KIND == 'gunner' else 0
    parts_ = [('cyl', (x - .1, 0, .45), (.07, .07, .45)), ('cyl', (x + .1, 0, .45), (.07, .07, .45)),
              ('cyl', (x, 0, 1.17), (.19, .12, .3)), ('sph', (x, 0, 1.68), (.11, .11, .12)),
              ('cyl', (x - .27, 0, 1.12), (.05, .05, .33)), ('cyl', (x + .27, 0, 1.12), (.05, .05, .33))]
    for kind, loc, sc in parts_:
        if kind == 'cyl': bpy.ops.mesh.primitive_cylinder_add(vertices=16, location=(loc[0], loc[1], loc[2] + z0))
        else: bpy.ops.mesh.primitive_uv_sphere_add(location=(loc[0], loc[1], loc[2] + z0))
        o = bpy.context.object; o.scale = sc; o.data.materials.append(mat)
mx = float(hi[0]) + .55
marker(mx)
bpy.ops.mesh.primitive_plane_add(size=12, location=(0, 0, 0))
g = bpy.context.object; gm = bpy.data.materials.new('ground'); gm.use_nodes = True
gm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.36, .31, .26, 1); g.data.materials.append(gm)

def shoot(name, target, dist, yaw_deg, height, lens=50, res=(900, 900)):
    cam.data.lens = lens; s.render.resolution_x, s.render.resolution_y = res
    yaw = math.radians(yaw_deg)  # 0 = front: the glTF model faces +Z in glTF = -Y in Blender
    cam.location = Vector(target) + Vector((math.sin(yaw) * dist, -math.cos(yaw) * dist, height - target[2]))
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    s.render.filepath = str(OUT / f'{PFX}{name}.png'); bpy.ops.render.render(write_still=True)
    return f'{PFX}{name}.png'

R = stats['renders'] = {}
H = float(hi[2]); cz = (lo[2] + hi[2]) / 2
c = ((float(lo[0]) + mx) / 2, 0, float(cz))
span = max(float(hi[0]) - float(lo[0]) + 1.0, H)
d = span * 1.9
for nm, yaw in (('front', 0), ('side_right', -90), ('back', 180), ('threequarter', 35)):
    R[nm] = shoot(nm, c if nm != 'threequarter' else (0, 0, float(cz)), d, yaw, float(cz) + (.15 if KIND == 'gunner' else .9), res=(900, 900))
R['top'] = shoot('top', (0, 0, float(cz)), d * .8, 0.01, float(cz) + d * .8 - .01 if False else float(cz) + 2.6) if KIND == 'lancer' else None
# close-ups: densest geometry regions picked from bounds
if KIND == 'gunner':
    top = co[co[:, 2] > H - .35]
    hc = top.mean(0)
    R['head'] = shoot('head', tuple(hc), .9, 20, hc[2] + .05, lens=85)
    # the robot's right side is +X in glTF = -X in Blender after import (model faces -Y), so right arm at x < 0
    arm_r = co[(co[:, 0] < lo[0] + .45) & (co[:, 2] > .6)]
    if len(arm_r): ac = arm_r.mean(0); R['gun_arm'] = shoot('gun_arm', tuple(ac), 1.5, -60, ac[2] + .25, lens=60)
    arm_l = co[(co[:, 0] > hi[0] - .35) & (co[:, 2] > .6)]
    if len(arm_l): al = arm_l.mean(0); R['left_hand'] = shoot('left_hand', tuple(al), .9, 50, al[2] + .1, lens=70)
    R['feet'] = shoot('feet', (0, 0, .15), 1.7, 20, .55, lens=50, res=(1100, 700))
else:
    R['front_close'] = shoot('front_close', (0, -.2, float(cz)), 1.6, 0, float(cz) + .15, lens=60)
    R['under'] = shoot('under', (0, 0, float(cz)), 2.6, 25, float(cz) - 1.6, lens=50)
    R['rotor_close'] = shoot('rotor_close', (float(lo[0]) + .3, float(hi[1]) - .3, float(hi[2]) - .05), 1.2, -40, float(hi[2]) + .7, lens=60)

# normals check: back faces red, front faces grey (material override)
nm = bpy.data.materials.new('normcheck'); nm.use_nodes = True; nt = nm.node_tree
for n in list(nt.nodes): nt.nodes.remove(n)
geo = nt.nodes.new('ShaderNodeNewGeometry'); mix = nt.nodes.new('ShaderNodeMixRGB'); dif = nt.nodes.new('ShaderNodeBsdfDiffuse'); out = nt.nodes.new('ShaderNodeOutputMaterial')
mix.inputs[1].default_value = (.7, .7, .7, 1); mix.inputs[2].default_value = (1, 0, 0, 1)
nt.links.new(geo.outputs['Backfacing'], mix.inputs[0]); nt.links.new(mix.outputs[0], dif.inputs[0]); nt.links.new(dif.outputs[0], out.inputs[0])
saved = [sl.material for sl in obj.material_slots]
for sl in obj.material_slots: sl.material = nm
R['normals_front'] = shoot('normals_front', (0, 0, float(cz)), d * .8, 25, float(cz) + .8)
R['normals_back'] = shoot('normals_back', (0, 0, float(cz)), d * .8, 205, float(cz) + .8)
for sl, m in zip(obj.material_slots, saved): sl.material = m
(OUT / f'{PFX}stats.json').write_text(json.dumps(stats, indent=2)); print('STATIC INSPECT DONE', tris, len(parts))
