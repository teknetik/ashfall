"""Gabion fill and welded-mesh textures for the West Gate bastion rework (Ward life pass, 3 Oct 2026). Blender 5.2.

Carl's open item from the overnight build: "gabion bastions read as tiled boxes". The round-two baskets were a flat
hessian liner behind a 25 cm wire grid. Real Warden gabions are welded-mesh baskets filled with broken stone (and, in
Ward, rubble of the Fall), so the fill has to read through the mesh.

1. Fill (tileable 1.5 m x 1.5 m at 2048 px): ~450 angular stones (8-26 cm; sandstone, pale limestone, grey basalt,
   red-brown ironstone, a few broken dressed blocks) packed against the mesh plane in a front layer with a smaller back
   layer filling the voids, periodic copies across the tile edges so the bake tiles. Rendered orthographically with
   Cycles as emission passes (albedo, world normal, height, ambient occlusion) to EXR, then packed in numpy:
     WL_GabionFill_BaseMap (sRGB, mild cavity darkening only), _Normal (OpenGL, tangent = image axes),
     _Mask (URP: R metal 0, G AO, B 0, A smoothness), _Height (parallax).
2. Welded mesh (tileable 1 m at 1024 px, 100 mm squares, 5 mm wire, front horizontals, weld beads): galvanised wire
   weathered to white rust with red rust patches (WL_GabionWire_*) and a fresh galvanised repair set
   (WL_GabionWireFresh_*); alpha in the base map for alpha clipping.
3. LOD1 fill with the mesh composited in (WL_GabionFillWired_BaseMap/_Normal): no alpha-tested layer beyond ~20 m.

Rock surface detail: Poly Haven worn_rock_natural_01 (CC0, already in art/vanguard_hall_20260930/polyhaven).
Run: $O/blender.sh bake_gabion.py [-- --res 2048 --quick]
"""
import bpy, bmesh, math, random, sys
import numpy as np
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import stones

OUT = ROOT / "unity/AthenHill/Assets/AthenHill/Art/WardLife/Textures"
OUT.mkdir(parents=True, exist_ok=True)
WORK = HERE / "bake"
WORK.mkdir(exist_ok=True)
PH = ROOT / "art/vanguard_hall_20260930/polyhaven/worn_rock_natural_01"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
RES = int(ARGS[ARGS.index("--res") + 1]) if "--res" in ARGS else 2048
QUICK = "--quick" in ARGS
W = 1.5            # fill tile, metres
DEPTH = 0.30       # background plane depth behind the mesh plane


# ------------------------------------------------------------------ helpers
def srgb(lin):
    lin = np.clip(lin, 0, 1)
    return np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(lin, 1 / 2.4) - 0.055)


def save_png(path, arr, colorspace="sRGB"):
    h, w = arr.shape[:2]
    if arr.shape[2] == 3:
        arr = np.concatenate([arr, np.ones((h, w, 1), np.float32)], 2)
    img = bpy.data.images.new(Path(path).stem, w, h, alpha=True)
    img.colorspace_settings.name = colorspace
    img.pixels.foreach_set(np.clip(arr, 0, 1).astype(np.float32).ravel())
    img.filepath_raw = str(path)
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    print("wrote", path, flush=True)


def load_exr(path):
    img = bpy.data.images.load(str(path))
    w, h = img.size
    a = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(a)
    bpy.data.images.remove(img)
    return a.reshape(h, w, 4)


def vnoise(n, cells, seed, octaves=4):
    """Tileable fractal value noise on an n x n grid, base period `cells` per tile, values ~0..1."""
    rs = np.random.RandomState(seed)
    out = np.zeros((n, n), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        c = cells * (2 ** o)
        g = rs.rand(c, c).astype(np.float32)
        t = (np.arange(n) + 0.5) / n * c
        i0 = np.floor(t).astype(int)
        f = t - i0
        f = f * f * (3 - 2 * f)
        i0 %= c
        i1 = (i0 + 1) % c
        a = g[i0][:, i0] * (1 - f)[None, :] + g[i0][:, i1] * f[None, :]
        b = g[i1][:, i0] * (1 - f)[None, :] + g[i1][:, i1] * f[None, :]
        out += amp * (a * (1 - f)[:, None] + b * f[:, None])
        tot += amp
        amp *= 0.5
    return out / tot


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------ fill scene
def pack_stones(rng):
    """Front layer by dart throwing (largest first), then a back layer in the voids. Returns [(x, y, z, size, kind, seed)]."""
    front = []
    def ok(x, y, r, lst, k=0.74):
        for (x2, y2, _, s2, _, _) in lst:
            dx = abs(x - x2); dx = min(dx, W - dx)
            dy = abs(y - y2); dy = min(dy, W - dy)
            if dx * dx + dy * dy < ((r + s2 * 0.45) * k) ** 2:
                return False
        return True
    bands = [(0.20, 0.26, 400), (0.15, 0.20, 1500), (0.11, 0.15, 4000), (0.07, 0.11, 6000)]
    for (lo, hi, tries) in bands:
        for _ in range(tries if not QUICK else tries // 4):
            s = rng.uniform(lo, hi)
            x, y = rng.uniform(0, W), rng.uniform(0, W)
            if ok(x, y, s * 0.45, front):
                kind = "block" if rng.random() < 0.07 else "rock"
                front.append((x, y, -s * 0.22 - rng.uniform(0.0, 0.025), s, kind, rng.randrange(1 << 30)))
    back = []
    for _ in range(2500 if not QUICK else 600):
        s = rng.uniform(0.10, 0.20)
        x, y = rng.uniform(0, W), rng.uniform(0, W)
        if ok(x, y, s * 0.45, back, 0.85):
            back.append((x, y, -s * 0.42 - rng.uniform(0.03, 0.07), s, "rock", rng.randrange(1 << 30)))
    return front, back


def build_fill():
    rng = random.Random(20261003)
    front, back = pack_stones(rng)
    bm = bmesh.new()
    lr = bm.verts.layers.float.new("srand")
    lk = bm.verts.layers.float.new("skind")
    n = 0
    for (x, y, z, s, kind, seed) in front + back:
        r0 = random.Random(seed)
        tint = r0.random()
        kval = 1.0 if kind == "block" else 0.0
        for ox in (-W, 0.0, W):
            for oy in (-W, 0.0, W):
                cx, cy = x + ox, y + oy
                if cx < -s or cx > W + s or cy < -s or cy > W + s:
                    continue
                faces = stones.add_stone(bm, (cx, cy, z), s, random.Random(seed), subdiv=3 if s > 0.12 else 2, kind=kind)
                for v in {v for f in faces for v in f.verts}:
                    v[lr] = tint
                    v[lk] = kval
                    if v.co.z > -0.004:                       # pressed flat against the mesh
                        v.co.z = -0.004 - (v.co.z + 0.004) * 0.15
                n += 1
    me = bpy.data.meshes.new("Fill")
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new("Fill", me)
    bpy.context.scene.collection.objects.link(ob)
    # backing: dusty shadowed earth behind the stones
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=24, y_subdivisions=24, size=W * 3, location=(W / 2, W / 2, -DEPTH))
    plane = bpy.context.active_object
    print(f"fill: {len(front)} front + {len(back)} back stones, {n} instances incl. tile copies, {len(me.polygons)} faces", flush=True)
    return ob, plane


def node(nt, kind, loc=(0, 0), **props):
    nd = nt.nodes.new(kind)
    nd.location = loc
    for k, v in props.items():
        setattr(nd, k, v)
    return nd


def vmath(nt, op, a, b=None, c=None):
    nd = nt.nodes.new("ShaderNodeVectorMath")
    nd.operation = op
    for i, x in enumerate((a, b, c)):
        if x is None:
            continue
        if isinstance(x, (tuple, list)):
            nd.inputs[i].default_value = x
        else:
            nt.links.new(x, nd.inputs[i])
    return nd.outputs[0]


def stone_material(mode):
    m = bpy.data.materials.new("Stone_" + mode)
    nt = m.node_tree
    nt.nodes.clear()
    out = node(nt, "ShaderNodeOutputMaterial")
    em = node(nt, "ShaderNodeEmission")
    em.inputs["Strength"].default_value = 1.0
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    tc = node(nt, "ShaderNodeTexCoord")
    geo = node(nt, "ShaderNodeNewGeometry")
    ar = node(nt, "ShaderNodeAttribute", attribute_name="srand")
    ak = node(nt, "ShaderNodeAttribute", attribute_name="skind")
    # per-stone texture offset so neighbours never share the same patch of rock
    off = vmath(nt, "MULTIPLY", ar.outputs["Fac"], (13.7, 7.1, 5.3))
    co = vmath(nt, "MULTIPLY_ADD", tc.outputs["Object"], (1.6, 1.6, 1.6), off)
    def img(name, cs):
        t = node(nt, "ShaderNodeTexImage")
        t.image = bpy.data.images.load(str(PH / name), check_existing=True)
        t.image.colorspace_settings.name = cs
        t.projection = "BOX"
        t.projection_blend = 0.35
        nt.links.new(co, t.inputs["Vector"])
        return t
    if mode == "albedo":
        tex = img("worn_rock_natural_01_diff_4k.jpg", "sRGB")
        # stone families: sandstone (most), pale limestone, grey basalt, red-brown ironstone
        ramp = node(nt, "ShaderNodeValToRGB")
        ramp.color_ramp.interpolation = "CONSTANT"
        els = ramp.color_ramp.elements
        els[0].position, els[0].color = 0.0, (1.18, 0.95, 0.72, 1)
        els[1].position, els[1].color = 0.45, (1.32, 1.24, 1.08, 1)
        for pos, col in ((0.68, (0.62, 0.6, 0.58, 1)), (0.80, (1.12, 0.74, 0.55, 1)), (0.88, (1.2, 1.05, 0.88, 1))):
            e = els.new(pos)
            e.color = col
        nt.links.new(ar.outputs["Fac"], ramp.inputs["Fac"])
        # broken dressed blocks take the Ward ashlar colour
        col = vmath(nt, "MULTIPLY", tex.outputs["Color"], ramp.outputs["Color"])
        # value jitter per stone (second hash of srand)
        jit = node(nt, "ShaderNodeMath", operation="FRACT")
        mul = node(nt, "ShaderNodeMath", operation="MULTIPLY")
        nt.links.new(ar.outputs["Fac"], mul.inputs[0]); mul.inputs[1].default_value = 37.31
        nt.links.new(mul.outputs[0], jit.inputs[0])
        jv = node(nt, "ShaderNodeMapRange")
        nt.links.new(jit.outputs[0], jv.inputs["Value"])
        jv.inputs["To Min"].default_value, jv.inputs["To Max"].default_value = 0.78, 1.12
        col = vmath(nt, "SCALE", col, None, None)
        sc = col.node
        nt.links.new(jv.outputs["Result"], sc.inputs["Scale"])
        ash = vmath(nt, "MULTIPLY", tex.outputs["Color"], (1.25, 1.08, 0.86))
        bl = vmath(nt, "SUBTRACT", ash, col)
        col = vmath(nt, "MULTIPLY_ADD", bl, ak.outputs["Fac"], col)
        # settled dust on the upward faces of the stones
        up = node(nt, "ShaderNodeSeparateXYZ")
        nt.links.new(geo.outputs["Normal"], up.inputs[0])
        dmask = node(nt, "ShaderNodeMapRange")
        nt.links.new(up.outputs["Y"], dmask.inputs["Value"])
        dmask.inputs["From Min"].default_value, dmask.inputs["From Max"].default_value = 0.25, 0.85
        dmask.inputs["To Min"].default_value, dmask.inputs["To Max"].default_value = 0.0, 0.42
        dust = vmath(nt, "SUBTRACT", (0.56, 0.46, 0.33), col)
        col = vmath(nt, "MULTIPLY_ADD", dust, dmask.outputs["Result"], col)
        nt.links.new(col, em.inputs["Color"])
    elif mode == "normal":
        tex = img("worn_rock_natural_01_disp_4k.jpg", "Non-Color")
        bump = node(nt, "ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.55
        bump.inputs["Distance"].default_value = 0.004
        nt.links.new(tex.outputs["Color"], bump.inputs["Height"])
        n = vmath(nt, "MULTIPLY_ADD", bump.outputs["Normal"], (0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
        nt.links.new(n, em.inputs["Color"])
    elif mode == "height":
        sep = node(nt, "ShaderNodeSeparateXYZ")
        nt.links.new(geo.outputs["Position"], sep.inputs[0])
        mr = node(nt, "ShaderNodeMapRange")
        nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
        mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = -DEPTH, 0.0
        nt.links.new(mr.outputs["Result"], em.inputs["Color"])
    elif mode == "ao":
        ao = node(nt, "ShaderNodeAmbientOcclusion")
        ao.samples = 16
        ao.inputs["Distance"].default_value = 0.12
        nt.links.new(ao.outputs["AO"], em.inputs["Color"])
    return m


def back_material(mode):
    m = bpy.data.materials.new("Back_" + mode)
    nt = m.node_tree
    nt.nodes.clear()
    out = node(nt, "ShaderNodeOutputMaterial")
    em = node(nt, "ShaderNodeEmission")
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    col = {"albedo": (0.06, 0.05, 0.04, 1), "normal": (0.5, 0.5, 1.0, 1), "height": (0, 0, 0, 1)}.get(mode)
    if mode == "ao":
        ao = node(nt, "ShaderNodeAmbientOcclusion")
        ao.inputs["Distance"].default_value = 0.12
        nt.links.new(ao.outputs["AO"], em.inputs["Color"])
    else:
        em.inputs["Color"].default_value = col
    return m


def render_passes(fill, plane):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.use_denoising = False
    sc.cycles.filter_width = 1.0
    sc.render.resolution_x = sc.render.resolution_y = RES
    sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = "Standard"
    sc.render.image_settings.file_format = "OPEN_EXR"
    sc.render.image_settings.color_depth = "32"
    w = bpy.data.worlds.new("black")
    w.color = (0, 0, 0)
    sc.world = w
    cam_d = bpy.data.cameras.new("cam")
    cam_d.type = "ORTHO"
    cam_d.ortho_scale = W
    cam_d.clip_start, cam_d.clip_end = 0.1, 5.0
    cam = bpy.data.objects.new("cam", cam_d)
    sc.collection.objects.link(cam)
    cam.location = (W / 2, W / 2, 2.0)
    sc.camera = cam
    paths = {}
    for mode, spp in (("albedo", 16), ("normal", 16), ("height", 8), ("ao", 12)):
        fill.data.materials.clear(); fill.data.materials.append(stone_material(mode))
        plane.data.materials.clear(); plane.data.materials.append(back_material(mode))
        sc.cycles.samples = spp if not QUICK else max(2, spp // 8)
        p = WORK / f"fill_{mode}.exr"
        sc.render.filepath = str(p)
        bpy.ops.render.render(write_still=True)
        paths[mode] = p
        print("rendered", mode, flush=True)
    return paths


def wire_tiles(n=1024, fresh=False, seed=7):
    """Welded mesh, 1 m tile, 100 mm pitch, 5 mm wire. Returns (base RGBA sRGB, normal, mask, alpha)."""
    px = n / 1.0
    t = (np.arange(n) + 0.5) / px
    x = t[None, :].repeat(n, 0)
    y = t[:, None].repeat(n, 1)
    pitch, r, rw = 0.1, 0.0025, 0.0042
    dx = (x + pitch / 2) % pitch - pitch / 2
    dy = (y + pitch / 2) % pitch - pitch / 2
    av = np.clip((r - np.abs(dx)) * px + 0.5, 0, 1)
    ah = np.clip((r - np.abs(dy)) * px + 0.5, 0, 1)
    dd = np.sqrt(dx * dx + dy * dy)
    aw = np.clip((rw - dd) * px + 0.5, 0, 1)
    alpha = np.maximum(np.maximum(av, ah), aw)
    nx = np.zeros((n, n), np.float32); ny = np.zeros((n, n), np.float32)
    vx = np.clip(dx / r, -0.95, 0.95); hy = np.clip(dy / r, -0.95, 0.95)
    nx = np.where(av > 0, vx, nx)
    ny = np.where(ah > 0, hy, ny); nx = np.where(ah > 0, 0, nx)          # horizontals in front
    wx, wy = np.clip(dx / rw, -0.95, 0.95), np.clip(dy / rw, -0.95, 0.95)
    nx = np.where(aw > 0.5, wx, nx); ny = np.where(aw > 0.5, wy, ny)
    nz = np.sqrt(np.clip(1 - nx * nx - ny * ny, 0.05, 1))
    normal = np.stack([nx * 0.5 + 0.5, ny * 0.5 + 0.5, nz * 0.5 + 0.5], 2)
    f1 = vnoise(n, 6, seed, 4)
    f2 = vnoise(n, 24, seed + 1, 3)
    f3 = vnoise(n, 3, seed + 2, 3)
    if fresh:
        zinc = np.array([0.70, 0.72, 0.73]); white = np.array([0.80, 0.80, 0.78])
        rust = smoothstep(0.86, 0.95, f1 * 0.6 + f2 * 0.4) * 0.5 * (aw > 0.3)
        wr = smoothstep(0.55, 0.8, f2) * 0.25
    else:
        zinc = np.array([0.55, 0.555, 0.54]); white = np.array([0.73, 0.71, 0.66])
        rust = smoothstep(0.5, 0.72, f1 * 0.55 + f2 * 0.3 + f3 * 0.15)
        rust = np.maximum(rust, 0.85 * (aw > 0.3) * smoothstep(0.35, 0.6, f2))       # welds rust first
        wr = smoothstep(0.45, 0.75, f2) * 0.6
    rcol = np.array([0.44, 0.25, 0.13]) * (0.75 + 0.35 * f2[..., None])
    col = zinc[None, None, :] * (0.85 + 0.25 * f2[..., None])
    col = col + (white - zinc)[None, None, :] * wr[..., None]
    col = col + (rcol - col) * rust[..., None]
    dust = smoothstep(0.3, 0.8, ny)[..., None] * 0.45
    col = col + (np.array([0.74, 0.64, 0.5]) - col) * dust
    # crossing shadow: verticals darker where the horizontal sits in front
    occl = np.where((av > 0) & (ah <= 0) & (np.abs(dy) < r * 2.2), 0.72, 1.0)
    col = col * occl[..., None]
    base = np.concatenate([col, alpha[..., None]], 2).astype(np.float32)
    metal = (0.85 if fresh else 0.6) * (1 - rust)
    smooth = (0.55 if fresh else 0.38) * (1 - rust) + 0.12 * rust
    mask = np.stack([metal, occl, np.zeros_like(metal), smooth], 2).astype(np.float32)
    return base, normal.astype(np.float32), mask, alpha


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    wb, wn, wm, wa = wire_tiles(1024, False, 7)
    save_png(OUT / "WL_GabionWire_BaseMap.png", wb)
    save_png(OUT / "WL_GabionWire_Normal.png", wn, "Non-Color")
    save_png(OUT / "WL_GabionWire_Mask.png", wm, "Non-Color")
    fb, fn, fm, _ = wire_tiles(1024, True, 11)
    save_png(OUT / "WL_GabionWireFresh_BaseMap.png", fb)
    save_png(OUT / "WL_GabionWireFresh_Mask.png", fm, "Non-Color")

    fill, plane = build_fill()
    paths = render_passes(fill, plane)
    alb = load_exr(paths["albedo"])[..., :3]
    nrm = load_exr(paths["normal"])[..., :3]
    hgt = load_exr(paths["height"])[..., 0]
    ao = np.clip(load_exr(paths["ao"])[..., 0], 0, 1)
    # albedo: only a mild cavity darkening (the AO lives in the mask for the indirect light)
    alb = alb * (0.55 + 0.45 * ao[..., None] ** 0.7)
    lum = (alb * np.array([0.2126, 0.7152, 0.0722])).sum(2, keepdims=True)
    alb = lum + (alb - lum) * 0.75                              # Ward's sun-bleached stone, less orange than the scan
    n3 = nrm * 2 - 1
    n3 /= np.maximum(np.linalg.norm(n3, axis=2, keepdims=True), 1e-4)
    nrm8 = n3 * 0.5 + 0.5
    rough_n = vnoise(RES, 12, 5, 4)
    smooth = np.clip(0.14 + 0.12 * rough_n + 0.06 * hgt, 0, 1) * (0.4 + 0.6 * ao)
    mask = np.stack([np.zeros_like(ao), ao, np.zeros_like(ao), smooth], 2)
    save_png(OUT / "WL_GabionFill_BaseMap.png", srgb(alb))
    save_png(OUT / "WL_GabionFill_Normal.png", nrm8, "Non-Color")
    save_png(OUT / "WL_GabionFill_Mask.png", mask, "Non-Color")
    save_png(OUT / "WL_GabionFill_Height.png", np.repeat(hgt[..., None], 3, 2), "Non-Color")

    # LOD1: the weathered mesh composited over the fill (tile 1.5 m holds 15 mesh cells exactly)
    pxm = RES / W
    t = (np.arange(RES) + 0.5) / pxm
    ii = ((t % 1.0) * 1024).astype(int) % 1024
    wbt = wb[ii][:, ii]; wnt = wn[ii][:, ii]
    a = wbt[..., 3:4]
    sh = np.roll(np.roll(a, -3, 0), 3, 1)                     # wire shadow on the stones (light from above-left)
    base_lin = alb * (1 - 0.35 * sh)
    wire_lin = np.power(np.clip(wbt[..., :3], 0, 1), 2.2)
    comp = base_lin * (1 - a) + wire_lin * a
    save_png(OUT / "WL_GabionFillWired_BaseMap.png", srgb(comp))
    save_png(OUT / "WL_GabionFillWired_Normal.png", nrm8 * (1 - a) + wnt * a, "Non-Color")
    print("done", flush=True)


main()
