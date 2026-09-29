"""Bake the 1.24M-triangle Meshy neon sign to a clean runtime front plate (Blender 5.2, Cycles CPU).

Run: env -i HOME=$HOME PATH=/usr/bin:/bin blender -b --factory-startup -P bake_sign.py -- <outdir>
Source GLB is never modified. Output: basecolor/normal/metalgloss/emission PNGs, sign-mesh.json (glTF axes: X right, Y up, +Z front), bake-report.json.
"""
import bpy, bmesh, json, math, sys, time, os
import numpy as np

out = sys.argv[sys.argv.index('--') + 1]
os.makedirs(out, exist_ok=True)
GLB = '/home/teknetik/code/ao2/meshy/basic-general-sign-20260929/Meshy_AI_Neon_Command_Sign_0929072950_texture.glb'
TW, TH = 4096, 1320
T0 = time.time()
def log(*a): print('[bake %.0fs]' % (time.time() - T0), *a, flush=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
high = [o for o in bpy.context.scene.objects if o.type == 'MESH'][0]
high.name = 'sign_high'
co = np.empty(len(high.data.vertices) * 3, dtype=np.float32); high.data.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
mn, mx = co.min(0), co.max(0)
W, D, H = float(mx[0] - mn[0]), float(mx[1] - mn[1]), float(mx[2] - mn[2])   # Blender axes: X width, Y depth (front = -Y), Z height
log('bounds', mn, mx, 'W', W, 'H', H, 'D', D)

# ---- low-poly front plate (front-most plane, chamfered octagon), UV = orthographic front projection -----------------
CH = 0.05
xs0, xs1, zs0, zs1 = float(mn[0]), float(mx[0]), float(mn[2]), float(mx[2])
yfront = float(mn[1]) - 0.0005
pts = [(xs0 + CH, zs0), (xs1 - CH, zs0), (xs1, zs0 + CH), (xs1, zs1 - CH), (xs1 - CH, zs1), (xs0 + CH, zs1), (xs0, zs1 - CH), (xs0, zs0 + CH)]
def build_front():
    me = bpy.data.meshes.new('sign_low_front'); bm = bmesh.new()
    vs = [bm.verts.new((x, yfront, z)) for x, z in pts]
    f = bm.faces.new(vs[::-1] if False else vs)   # counter-clockwise seen from -Y? fix normal below
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if f.normal.y > 0: f.normal_flip()
    uv = bm.loops.layers.uv.new('UVMap')
    for l in f.loops:
        x, _, z = l.vert.co; l[uv].uv = ((x - xs0) / W, (z - zs0) / H)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    return me
low = bpy.data.objects.new('sign_low', build_front()); bpy.context.collection.objects.link(low)

sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 8; sc.cycles.use_denoising = False
b = sc.render.bake
b.use_selected_to_active = True; b.target = 'IMAGE_TEXTURES'; b.use_clear = True; b.margin = 24; b.margin_type = 'EXTEND'
b.cage_extrusion = 0.004; b.max_ray_distance = 0.14; b.use_cage = False

def new_image(name, srgb, w=TW, h=TH):
    im = bpy.data.images.new(name, w, h, alpha=False, float_buffer=False)
    im.colorspace_settings.name = 'sRGB' if srgb else 'Non-Color'
    return im
def bake(kind, im, **kw):
    mat = bpy.data.materials.new('bake_' + kind); mat.use_nodes = True
    n = mat.node_tree.nodes.new('ShaderNodeTexImage'); n.image = im; mat.node_tree.nodes.active = n
    low.data.materials.clear(); low.data.materials.append(mat)
    bpy.ops.object.select_all(action='DESELECT'); high.select_set(True); low.select_set(True); bpy.context.view_layer.objects.active = low
    t = time.time(); bpy.ops.object.bake(type=kind, **kw); log('baked', kind, '%.0fs' % (time.time() - t))

albedo = new_image('albedo', True); bake('DIFFUSE', albedo, pass_filter={'COLOR'})
normal = new_image('normal', False)
sc.render.bake.normal_space = 'TANGENT'; sc.render.bake.normal_r = 'POS_X'; sc.render.bake.normal_g = 'POS_Y'; sc.render.bake.normal_b = 'POS_Z'
bake('NORMAL', normal)
rough = new_image('rough', False); bake('ROUGHNESS', rough)
# metallic: route the metallic socket into an emission shader and bake EMIT
hm = high.data.materials[0]; nt = hm.node_tree
pb = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'); outn = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
src = pb.inputs['Metallic'].links[0].from_socket if pb.inputs['Metallic'].links else None
em = nt.nodes.new('ShaderNodeEmission')
if src: nt.links.new(src, em.inputs['Color'])
else: em.inputs['Color'].default_value = (pb.inputs['Metallic'].default_value,) * 3 + (1,)
nt.links.new(em.outputs['Emission'], outn.inputs['Surface'])
metal = new_image('metal', False); bake('EMIT', metal)

def px(im): a = np.array(im.pixels[:], dtype=np.float32).reshape(im.size[1], im.size[0], 4); return a
def save(name, arr, srgb, ch=4):
    im = bpy.data.images.new(name, arr.shape[1], arr.shape[0], alpha=(ch == 4), float_buffer=False)
    im.colorspace_settings.name = 'sRGB' if srgb else 'Non-Color'
    a = np.ones((arr.shape[0], arr.shape[1], 4), np.float32); a[..., :arr.shape[2]] = arr[..., :arr.shape[2]]
    im.pixels.foreach_set(a.ravel()); im.filepath_raw = os.path.join(out, name + '.png'); im.file_format = 'PNG'
    im.save()
    log('saved', name, arr.shape)

A, N, R, M = px(albedo), px(normal), px(rough), px(metal)
save('sign_basecolor', A[..., :3], True, 3)
save('sign_normal', N[..., :3], False, 3)
smooth = 1 - R[..., 0]
mg = np.zeros_like(A); mg[..., 0] = M[..., 0]; mg[..., 3] = smooth
save('sign_metalgloss', mg, False, 4)
# emission: glowing colour only (saturated, bright albedo = letters, OPEN plate, cyan traces). Albedo is linear here (float buffer).
rgb = A[..., :3]; v = rgb.max(-1); s = (v - rgb.min(-1)) / np.maximum(v, 1e-4)
mask = np.clip((v - 0.30) / 0.25, 0, 1) * np.clip((s - 0.45) / 0.25, 0, 1)
emis = rgb * mask[..., None]
emis2 = emis.reshape(TH // 2, 2, TW // 2, 2, 3).mean((1, 3))
save('sign_emission', emis2, True, 3)

rep = dict(source=GLB, tris_high=len(high.data.polygons), bounds_min=mn.tolist(), bounds_max=mx.tolist(), width=W, height=H, depth=D, tex=[TW, TH],
           coverage=dict(albedo_nonblack=float((v > 0.01).mean()), emission_frac=float((mask > 0.05).mean()), metal_mean=float(M[..., 0].mean()), rough_mean=float(R[..., 0].mean())),
           seconds=time.time() - T0)
json.dump(rep, open(os.path.join(out, 'bake-report.json'), 'w'), indent=1)

# ---- mesh export (glTF axes: x, y=Blender z, z=-Blender y). Front plate + 8 side quads using an interior flat dark texel patch ----
side_uv = None
nrm = N[..., :3] * 2 - 1
flat = (nrm[..., 2] > 0.995) & (v < 0.10)
# choose the flat-dark texel whose 25x25 neighbourhood is flat; search on coarse grid inside the panel
ys, xs = np.where(flat[::25, ::25]); best = None
for yy, xx in zip(ys, xs):
    y0, x0 = yy * 25, xx * 25
    if 60 < y0 < TH - 60 and 60 < x0 < TW - 60 and flat[y0 - 12:y0 + 13, x0 - 12:x0 + 13].all(): best = (x0 / TW, y0 / TH); break
side_uv = best
rep['side_uv'] = side_uv; json.dump(rep, open(os.path.join(out, 'bake-report.json'), 'w'), indent=1)
log('side patch', side_uv)

def gl(p): return [p[0], p[2], -p[1]]
verts, norms, uvs, tris = [], [], [], []
fm = low.data; fmw = [tuple(v.co) for v in fm.vertices]
def add(vs, n, uv_list, quad):
    base = len(verts)
    G = [gl(p) for p in vs]
    e1 = [G[1][k] - G[0][k] for k in range(3)]; e2 = [G[2][k] - G[0][k] for k in range(3)]
    cr = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]]
    flip = sum(cr[k] * n[k] for k in range(3)) < 0     # right-handed glTF: ccw seen from the normal side
    if flip: vs = vs[::-1]; uv_list = uv_list[::-1]
    for p, u in zip(vs, uv_list): verts.append(gl(p)); norms.append(n); uvs.append(u)
    idx = [0, 1, 2] if not quad else [0, 1, 2, 0, 2, 3]
    tris.extend(base + i for i in idx)
# front polygons come from the low mesh triangles (front normal glTF +Z)
for poly in fm.polygons:
    ids = list(poly.vertices)
    assert len(ids) == 3
    # ensure ccw seen from glTF +Z (viewer in front, x right, y up): orientation in (x, z_blender) plane
    P = [fmw[i] for i in ids]
    cross = (P[1][0] - P[0][0]) * (P[2][2] - P[0][2]) - (P[1][2] - P[0][2]) * (P[2][0] - P[0][0])
    if cross < 0: P = [P[0], P[2], P[1]]
    add(P, [0, 0, 1], [((p[0] - xs0) / W, (p[2] - zs0) / H) for p in P], False)
if side_uv:
    yb = float(mx[1])   # back plane (Blender +Y = glTF -Z)
    n = len(pts)
    for i in range(n):
        a, c = pts[i], pts[(i + 1) % n]
        A0, A1 = (a[0], yfront, a[1]), (c[0], yfront, c[1]); B0, B1 = (a[0], yb, a[1]), (c[0], yb, c[1])
        ex, ez = c[0] - a[0], c[1] - a[1]; L = math.hypot(ex, ez)
        # outward normal in glTF axes for a ccw (in x,z) ring: (ez, -ex) in (x, y_gltf)
        nn = [ez / L, -ex / L, 0]
        # glTF ring is ccw when seen from +Z; the outward normal for edge (dx, dy) is (dy, -dx)
        cx = [ -1 if False else 1 ]
        quad = [A0, B0, B1, A1]
        # winding: front->back along the edge; keep outward-facing ccw
        u0, v0 = side_uv
        add(quad, nn, [(u0, v0), (u0, v0), (u0, v0), (u0, v0)], True)
json.dump(dict(vertices=verts, normals=norms, uv0=uvs, triangles=tris, width=W, height=H, depth=D, front_rows=len(fm.polygons)), open(os.path.join(out, 'sign-mesh.json'), 'w'))
log('done', len(verts), 'verts', len(tris) // 3, 'tris')
