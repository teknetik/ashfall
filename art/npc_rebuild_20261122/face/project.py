"""Face repaint -> texture set for one NPC (headless Blender, CPU). The hero base's method
(art/hero_base_20261120/face/face_project.py, build/finish_textures.py) without its character-specific colour keys:

  * figure masks come from the alpha of the rendered views, not a colour key;
  * each repaint is matched to the mean colour of the view it was painted from, so there is no patch edge and the rest
    of the skin needs no regrade;
  * under the repaint the normal map is flattened, roughness kept off mirror values and metal removed (glassy eyes).

blender.sh project.py -- rodin/model.glb face_dir out_dir [normal_flatten=.7]
In: face_dir/cams.json, view_<v>.png (alpha), out_<v>.png. Out: base.png 4096, normal.png 2048, orm.png 1024."""
import bpy, sys, json
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
a = sys.argv[sys.argv.index('--') + 1:]
GLB, F, O = Path(a[0]), Path(a[1]), Path(a[2]); O.mkdir(parents=True, exist_ok=True)
FLAT = float(a[3]) if len(a) > 3 else .7
R = 4096
PRI = {'front': 1., 'left45': .72, 'right45': .72}

bpy.ops.wm.read_factory_settings(use_empty=True)
s = bpy.context.scene; s.render.engine = 'CYCLES'; s.cycles.device = 'CPU'; s.cycles.samples = 1
bpy.ops.import_scene.gltf(filepath=str(GLB))
ob = max((o for o in bpy.data.objects if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
nt = ob.data.materials[0].node_tree; outn = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
def named(word): return next(i for i in bpy.data.images if word in i.name.lower())
B0, N0, M0 = named('diffuse'), named('normal'), named('roughness')

def px(im):
    b = np.empty(im.size[0] * im.size[1] * 4, np.float32); im.pixels.foreach_get(b)
    return b.reshape(im.size[1], im.size[0], 4)
def load(p):
    im = bpy.data.images.load(str(p)); r = px(im).copy(); bpy.data.images.remove(im); return r
def full(im):
    if tuple(im.size) != (R, R):   # the standard tier ships 2K maps
        im.scale(R, R)
    return px(im)[..., :3].copy()
base, nrm, orm = full(B0), full(N0), full(M0)

def bake(sock, add, mul):
    im = bpy.data.images.new('b', R, R, alpha=True, float_buffer=True); im.colorspace_settings.name = 'Non-Color'
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = im
    p = nt.nodes.new('ShaderNodeVectorMath'); p.operation = 'ADD'; p.inputs[1].default_value = (add, add, add)
    q = nt.nodes.new('ShaderNodeVectorMath'); q.operation = 'SCALE'; q.inputs['Scale'].default_value = mul
    e = nt.nodes.new('ShaderNodeEmission'); nt.links.new(sock, p.inputs[0]); nt.links.new(p.outputs[0], q.inputs[0])
    nt.links.new(q.outputs[0], e.inputs[0]); nt.links.new(e.outputs[0], outn.inputs['Surface'])
    for n in nt.nodes: n.select = False
    t.select = True; nt.nodes.active = t; s.render.bake.margin = 0; s.render.bake.use_clear = True
    bpy.ops.object.bake(type='EMIT')
    r = px(im)[..., :3].copy()
    for n in (t, p, q, e): nt.nodes.remove(n)
    bpy.data.images.remove(im); return r

geo = nt.nodes.new('ShaderNodeNewGeometry')
E = bake(geo.outputs['Position'], 10, .05); cover = E.max(2) > .05; P = E * 20 - 10
N = bake(geo.outputs['Normal'], 1, .5) * 2 - 1
cams = json.loads((F / 'cams.json').read_text()); S = cams['ortho_scale']
ys, xs = np.nonzero(cover & (P[..., 2] > cams['head_centre'][2] - S / 2 - .01))
Ps, Ns = P[ys, xs], N[ys, xs]; Ns /= np.maximum(np.linalg.norm(Ns, axis=1, keepdims=True), 1e-6)
bvh = BVHTree.FromPolygons([ob.matrix_world @ v.co for v in ob.data.vertices], [tuple(p.vertices) for p in ob.data.polygons])

def smooth(x, l, h): t = np.clip((x - l) / (h - l), 0, 1); return t * t * (3 - 2 * t)
def lin(c): return np.where(c <= .04045, c / 12.92, ((c + .055) / 1.055) ** 2.4)
def enc(c): return np.where(c <= .0031308, c * 12.92, 1.055 * np.clip(c, 0, None) ** (1 / 2.4) - .055)
def blur(x, r):
    k = 2 * r + 1; c = np.cumsum(np.pad(x, ((r + 1, r), (0, 0))), 0); x = (c[k:] - c[:-k]) / k
    c = np.cumsum(np.pad(x, ((0, 0), (r + 1, r))), 1); return (c[:, k:] - c[:, :-k]) / k
def sample(im, u, v):
    h, w = im.shape[:2]; x = np.clip(u * w - .5, 0, w - 1.001); y = np.clip(v * h - .5, 0, h - 1.001)
    i, j = x.astype(int), y.astype(int); f, g = (x - i)[:, None], (y - j)[:, None]
    return im[j, i] * (1 - f) * (1 - g) + im[j, i + 1] * f * (1 - g) + im[j + 1, i] * (1 - f) * g + im[j + 1, i + 1] * f * g

acc = np.zeros((len(ys), 3), np.float32); tot = np.zeros(len(ys), np.float32); top = np.zeros(len(ys), np.float32); st = {}
for v, rec in cams['views'].items():
    if not (F / f'out_{v}.png').exists():    # left out by the alignment gate
        st[v] = 'no aligned repaint'; continue
    src, was = load(F / f'out_{v}.png')[..., :3], load(F / f'view_{v}.png')
    M = np.array(rec['matrix_world'], np.float32); d = Ps - M[:3, 3]
    u, w_ = d @ M[:3, 0] / S + .5, d @ M[:3, 1] / S + .5
    al = (was[..., 3] > .98).astype(np.float32)
    n = al.shape[0]; inner = (blur(al, max(2, n // 300)) > .999).astype(np.float32); inner = blur(inner, max(2, n // 400))
    core = blur(al, n // 60) > .999; m2 = src.shape[0]
    jj, ii = np.nonzero(core)
    g = lin(was[jj, ii, :3]).mean(0) / lin(src[jj * m2 // n, ii * src.shape[1] // n]).mean(0)
    g = np.clip(g, .72, 1.38)
    edge = np.minimum(np.minimum(u, 1 - u), np.minimum(w_, 1 - w_))
    w = smooth(Ns @ M[:3, 2], .15, .65) * smooth(edge, 0, .09) * smooth(sample(inner[..., None], u, w_)[:, 0], .5, 1)
    c = np.nonzero(w > 1e-3)[0]; to = Vector(M[:3, 2].tolist()); vis = np.zeros(len(ys), np.float32)
    vis[c] = [bvh.ray_cast(Vector(o), to, 3.)[0] is None for o in (Ps[c] + Ns[c] * .0015).tolist()]
    w *= vis * PRI[v]; col = enc(lin(sample(src, u, w_)) * g).astype(np.float32); W = w ** 4
    acc += col * W[:, None]; tot += W; top = np.maximum(top, w / PRI[v]); st[v] = dict(gain=g.tolist(), texels=int(vis.sum()))
m = smooth(top, .08, .55)
base[ys, xs] = base[ys, xs] * (1 - m[:, None]) + (acc / np.maximum(tot, 1e-6)[:, None]) * m[:, None]
mask = np.zeros((R, R), np.float32); mask[ys, xs] = m

filled = cover.copy()
for _ in range(10):
    A = np.zeros_like(base); C = np.zeros((R, R), np.float32)
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        f = np.roll(filled, (dy, dx), (0, 1)); A += np.roll(base, (dy, dx), (0, 1)) * f[..., None]; C += f
        mask = np.where(~filled & f, np.roll(mask, (dy, dx), (0, 1)), mask)
    q = ~filled & (C > 0); base[q] = A[q] / C[q][:, None]; filled |= q

k = (blur(mask, 3) * FLAT)[..., None]; n = (nrm * 2 - 1) * (1 - k) + np.array([0, 0, 1], np.float32) * k
n /= np.maximum(np.linalg.norm(n, axis=2, keepdims=True), 1e-6); nrm = n * .5 + .5
orm[..., 0] = 1
orm[..., 2] *= 1 - mask
orm[..., 1] = np.maximum(orm[..., 1], np.maximum(mask * .5, .58 - .16 * orm[..., 2]))   # no mirror plate or wet leather
orm[..., 2] *= .85                                                                    # worn, dusty metal

GRADE = F / 'grade.json'     # optional: linear gains on the skin alone (Brann came out flushed pink)
if GRADE.exists():
    g = np.array(json.loads(GRADE.read_text())['skin'], np.float32)
    mx, mn = base.max(2), base.min(2); r, gr, b = base[..., 0], base[..., 1], base[..., 2]
    sk = smooth(r - gr, .06, .12) * smooth(mx, .38, .52) * smooth((b - gr) / np.maximum(mx - mn, 1e-4), -.75, -.55)
    base = enc(lin(base) * (1 + blur(sk, 2)[..., None] * (g - 1))).astype(np.float32)

def save(x, p, size, data):
    f = x.shape[0] // size
    if f > 1: x = x.reshape(size, f, size, f, 3).mean((1, 3))
    im = bpy.data.images.new('o', size, size, alpha=False); im.colorspace_settings.name = 'Non-Color' if data else 'sRGB'
    b = np.ones((size, size, 4), np.float32); b[..., :3] = x; im.pixels.foreach_set(np.clip(b, 0, 1).ravel())
    im.filepath_raw = str(p); im.file_format = 'PNG'; im.save(); bpy.data.images.remove(im)
save(base, O / 'base.png', 4096, False); save(nrm, O / 'normal.png', 2048, True); save(orm, O / 'orm.png', 1024, True)
(O / 'stats.json').write_text(json.dumps(st, indent=1)); print('PROJECT OK', st)
