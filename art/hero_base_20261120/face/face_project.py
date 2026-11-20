"""Hero face pass, step 2 (headless Blender 5.2, CPU): project the repainted head views back onto the body texture.
Usage: blender.sh face_project.py -- <model.glb> <views dir with cams.json and out_<view>_<tag>.png> <out dir> [tag]

1. Bakes world position and normal of every texel of the model's UV layout (4096 x 4096, float).
2. For every head texel and every view: orthographic projection through the stored camera, a ray cast towards the
   camera for visibility, a facing weight and a frame-edge feather. The views are blended with sharpened weights so one
   view owns each area (the front view owns the face).
3. Grades the rest of the skin and the rest of the hair towards the repainted tones, so the repaint does not sit in the
   old texture as a patch.
4. Fills the padding round the UV charts from the new texels (16 px), so mip-mapping does not pull the old colours in.
Writes diffuse_<tag>.png (8-bit sRGB, same layout as the Rodin colour map), mask_<tag>.png and stats_<tag>.json."""
import bpy, sys, json, time
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
args = sys.argv[sys.argv.index('--') + 1:]
GLB = Path(args[0]); VIEWS = Path(args[1]); OUT = Path(args[2]); OUT.mkdir(parents=True, exist_ok=True)
TAG = args[3] if len(args) > 3 else 'v1'
RES = 4096
PRIORITY = {'front': 1.0, 'left45': 0.8, 'right45': 0.8}
t0 = time.time()


def log(*a): print('PROJECT', round(time.time() - t0, 1), *a, flush=True)


bpy.ops.wm.read_factory_settings(use_empty=True)
s = bpy.context.scene
s.render.engine = 'CYCLES'; s.cycles.device = 'CPU'; s.cycles.samples = 1
bpy.ops.import_scene.gltf(filepath=str(GLB))
mesh = max((o for o in bpy.data.objects if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
bpy.ops.object.select_all(action='DESELECT'); mesh.select_set(True); bpy.context.view_layer.objects.active = mesh
mat = mesh.data.materials[0]; nt = mat.node_tree
bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'); outn = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
base_img = bsdf.inputs['Base Color'].links[0].from_node.image


def pixels(img):
    a = np.empty(img.size[0] * img.size[1] * 4, np.float32); img.pixels.foreach_get(a)
    return a.reshape(img.size[1], img.size[0], 4)


def bake(vector_socket, name):
    """Bake an arbitrary vector as emission into a float image on the mesh's UV layout."""
    img = bpy.data.images.new(name, RES, RES, alpha=True, float_buffer=True); img.colorspace_settings.name = 'Non-Color'
    tgt = nt.nodes.new('ShaderNodeTexImage'); tgt.image = img
    for n in nt.nodes: n.select = False
    tgt.select = True; nt.nodes.active = tgt
    em = nt.nodes.new('ShaderNodeEmission'); nt.links.new(vector_socket, em.inputs['Color']); nt.links.new(em.outputs[0], outn.inputs['Surface'])
    s.render.bake.margin = 0; s.render.bake.use_clear = True
    bpy.ops.object.bake(type='EMIT')
    a = pixels(img).copy(); nt.nodes.remove(tgt); nt.nodes.remove(em); bpy.data.images.remove(img)
    return a


geo = nt.nodes.new('ShaderNodeNewGeometry')
add = nt.nodes.new('ShaderNodeVectorMath'); add.operation = 'ADD'; add.inputs[1].default_value = (10, 10, 10)
scl = nt.nodes.new('ShaderNodeVectorMath'); scl.operation = 'SCALE'; scl.inputs['Scale'].default_value = 0.05
nt.links.new(geo.outputs['Position'], add.inputs[0]); nt.links.new(add.outputs[0], scl.inputs[0])
pos_enc = bake(scl.outputs[0], 'pos'); log('baked position')
addn = nt.nodes.new('ShaderNodeVectorMath'); addn.operation = 'ADD'; addn.inputs[1].default_value = (1, 1, 1)
scn = nt.nodes.new('ShaderNodeVectorMath'); scn.operation = 'SCALE'; scn.inputs['Scale'].default_value = 0.5
nt.links.new(geo.outputs['Normal'], addn.inputs[0]); nt.links.new(addn.outputs[0], scn.inputs[0])
nrm_enc = bake(scn.outputs[0], 'nrm'); log('baked normal')
cover = pos_enc[..., :3].max(axis=2) > 0.05
P = pos_enc[..., :3] * 20.0 - 10.0
N = nrm_enc[..., :3] * 2.0 - 1.0
orig = pixels(base_img)[..., :3].copy()          # sRGB-encoded 0..1, bottom row first
assert orig.shape[0] == RES, orig.shape

# world-space BVH for the visibility rays
dg = bpy.context.evaluated_depsgraph_get(); ev = mesh.evaluated_get(dg); me = ev.to_mesh()
vw = [mesh.matrix_world @ v.co for v in me.vertices]
bvh = BVHTree.FromPolygons(vw, [tuple(p.vertices) for p in me.polygons]); ev.to_mesh_clear()

cams = json.loads((VIEWS / 'cams.json').read_text()); ORTHO = cams['ortho_scale']
hc = np.array(cams['head_centre'], np.float32)
zmin = float(hc[2] - ORTHO / 2 - 0.01)
sel = cover & (P[..., 2] > zmin)
ys, xs = np.nonzero(sel); Ps = P[ys, xs]; Ns = N[ys, xs]
Ns /= np.maximum(np.linalg.norm(Ns, axis=1, keepdims=True), 1e-6)
log('head texels', len(ys))


def smooth(a, lo, hi):
    t = np.clip((a - lo) / (hi - lo), 0, 1); return t * t * (3 - 2 * t)


def bilinear(img, u, v):
    h, w = img.shape[:2]
    x = np.clip(u * w - .5, 0, w - 1.001); y = np.clip(v * h - .5, 0, h - 1.001)
    x0 = x.astype(np.int32); y0 = y.astype(np.int32); fx = (x - x0)[:, None]; fy = (y - y0)[:, None]
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy) + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)


def blur(a, r=2):
    k = 2 * r + 1; c = np.cumsum(np.pad(a, ((r + 1, r), (0, 0))), axis=0); a = (c[k:] - c[:-k]) / k
    c = np.cumsum(np.pad(a, ((0, 0), (r + 1, r))), axis=1); return (c[:, k:] - c[:, :-k]) / k


def hsv(c):
    mx = c.max(axis=-1); mn = c.min(axis=-1); df = mx - mn + 1e-6
    r, g, b = c[..., 0], c[..., 1], c[..., 2]
    h = np.where(mx == r, ((g - b) / df) % 6, np.where(mx == g, (b - r) / df + 2, (r - g) / df + 4)) / 6.0
    return h, df / (mx + 1e-6), mx


# texels that were shirt in the Rodin map take no repaint (the collar keeps its own cloth)
oc = orig[ys, xs]
h, sa, va = hsv(oc)
shirt = (h > .085) & (h < .17) & (sa > .12) & (sa < .5) & (va > .3) & (va < .8)
acc = np.zeros((len(ys), 3), np.float32); wsum = np.zeros(len(ys), np.float32); wmax = np.zeros(len(ys), np.float32)
stats = {'views': {}}
for name, rec in cams['views'].items():
    f = VIEWS / f'out_{name}_{TAG}.png'
    if not f.exists(): log('no image for', name); continue
    im = bpy.data.images.load(str(f)); src = pixels(im)[..., :3].copy()
    M = np.array(rec['matrix_world'], np.float32)
    right, up, back, C = M[:3, 0], M[:3, 1], M[:3, 2], M[:3, 3]
    d = Ps - C
    u = d @ right / ORTHO + .5; v = d @ up / ORTHO + .5
    facing = Ns @ back                                   # the camera looks down its -Z, so +Z points at the viewer
    edge = np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v))
    bg = src[:8, :8].reshape(-1, 3).mean(0)
    isbg = (np.abs(src - bg).max(axis=2) < .07).astype(np.float32)
    core = (blur(isbg, 8) > .999).astype(np.float32)             # large background areas only (no specks in the beard)
    fg = 1.0 - (blur(core, 13) > .0005).astype(np.float32)       # ... grown 5 px into the figure
    fgw = bilinear(fg[..., None], u, v)[:, 0]
    w = smooth(facing, .12, .6) * smooth(edge, 0.0, .07) * smooth(fgw, .5, 1.0) * (~shirt)
    cand = np.nonzero(w > 1e-3)[0]
    tocam = Vector(back.tolist())
    vis = np.zeros(len(ys), np.float32)
    org = Ps[cand] + Ns[cand] * 0.0015
    hit = [bvh.ray_cast(Vector(o), tocam, 3.0)[0] is None for o in org.tolist()]
    vis[cand] = np.array(hit, np.float32)
    w *= vis * PRIORITY.get(name, .8)
    col = bilinear(src, u, v)
    W = w ** 3
    acc += col * W[:, None]; wsum += W; wmax = np.maximum(wmax, w / PRIORITY.get(name, .8) * (1.0 if name == 'front' else .95))
    stats['views'][name] = {'candidates': int(len(cand)), 'visible': int(vis.sum())}
    log('view', name, stats['views'][name])

proj = acc / np.maximum(wsum, 1e-6)[:, None]
m = smooth(wmax, .08, .55)                               # how much of the repaint a texel takes


def lin(c): return np.where(c <= .04045, c / 12.92, ((c + .055) / 1.055) ** 2.4)
def enc(c): return np.where(c <= .0031308, c * 12.92, 1.055 * np.clip(c, 0, None) ** (1 / 2.4) - .055)


# ---- tone match: grade the old skin and the old head hair towards the repaint
strong = m > .9
skin_h = (h < .085) & (sa > .12) & (sa < .6) & (va > .55)
hair_h = va < .42
gain = {}
for key, cls in (('skin', skin_h), ('hair', hair_h)):
    k = strong & cls
    if k.sum() < 2000: gain[key] = [1, 1, 1]; continue
    g = lin(proj[k]).mean(0) / np.maximum(lin(oc[k]).mean(0), 1e-4)
    gain[key] = [float(x) for x in g]
stats['gain'] = gain; log('gains', gain)
out = orig.copy()
H, S, V = hsv(orig)
skin_all = (cover & (H < .085) & (S > .12) & (S < .6) & (V > .55)).astype(np.float32)
hair_head = (cover & (V < .42) & (P[..., 2] > zmin + .02)).astype(np.float32)


covf = blur(cover.astype(np.float32))                 # blur over covered texels only, so chart borders keep the full grade
skin_all = np.clip(blur(skin_all) / np.maximum(covf, 1e-3), 0, 1) * cover
hair_head = np.clip(blur(hair_head) / np.maximum(covf, 1e-3), 0, 1) * cover
lo = lin(out)
for key, msk in (('skin', skin_all), ('hair', hair_head)):
    g = np.array(gain[key], np.float32)
    lo = lo * (1 + msk[..., None] * (g - 1))
out = enc(lo).astype(np.float32)
# ---- lay the repaint in
cur = out[ys, xs]
out[ys, xs] = cur * (1 - m[:, None]) + proj * m[:, None]
mask = np.zeros((RES, RES), np.float32); mask[ys, xs] = m

# ---- fill the chart padding from the new texels
filled = cover.copy(); res = out.copy()
for it in range(16):
    acc2 = np.zeros_like(res); cnt = np.zeros((RES, RES), np.float32)
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
        f = np.roll(filled, (dy, dx), (0, 1)); acc2 += np.roll(res, (dy, dx), (0, 1)) * f[..., None]; cnt += f
    new = (~filled) & (cnt > 0)
    res[new] = acc2[new] / cnt[new][:, None]; filled |= new
out = res


def save(arr, path, non_color=False):
    h, w = arr.shape[:2]
    img = bpy.data.images.new('o', w, h, alpha=False); img.colorspace_settings.name = 'Non-Color' if non_color else 'sRGB'
    a = np.ones((h, w, 4), np.float32); a[..., :3] = arr if arr.ndim == 3 else arr[..., None]
    img.pixels.foreach_set(np.clip(a, 0, 1).ravel()); img.filepath_raw = str(path); img.file_format = 'PNG'; img.save(); bpy.data.images.remove(img)


save(out, OUT / f'diffuse_{TAG}.png'); save(mask, OUT / f'mask_{TAG}.png', True)
stats['head_texels'] = int(len(ys)); stats['repainted_over_half'] = int((m > .5).sum())
(OUT / f'stats_{TAG}.json').write_text(json.dumps(stats, indent=1))
log('done', stats['repainted_over_half'])
