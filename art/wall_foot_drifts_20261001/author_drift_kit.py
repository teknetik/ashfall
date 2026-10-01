"""Wall-foot sand drift kit, Blender 5.2 headless (1 October 2026).

Art-direction review item 6 (30 Sep): where the Ward's buildings meet the paving the junction is knife-clean. This builds
a small kit of low, wind-laid sand drifts that the Unity pass places along building, porch, step and post feet.

Run:  $O/blender.sh author_drift_kit.py          ($O = /home/teknetik/.local/state/ward-programme)

Every piece is a height field authored in Unity metres (X along the wall, Y up, Z out from the wall face; origin on the
wall-foot line), sampled on a regular grid and sunk 8 mm, so the visible edge is the noisy contour where the sand surface
crosses the paving (a "height-blend" edge with a real slope, not a tangent sliver that would z-fight). The back rows run
5 cm into the wall so no gap opens against rough masonry. Faces wholly buried are dropped. LOD0 samples every 4.5 cm,
LOD1 every 10 cm, LOD2 every 20 cm. No vertex colours, one material ("WFD_Sand"), planar UV0 in metres (x, z).

Pieces (local frames):
  Run_L, Run_M, Run_S  straight wall-foot banks (1.6 / 1.1 / 0.7 m long), lobed, a concave fillet against the wall.
  Run_Low              a long, low, broken dusting band (1.5 m) for sheltered stretches between the banks.
  Corner_L, Corner_S   inside-corner banks: walls along +X (face z = 0) and along +Z (face x = 0), origin in the corner.
  Post                 a sand collar round a post footing (half-size up to 0.3 m, hidden inside it) with a lee tail
                       towards +Z (the Unity pass turns +Z downwind).
  Sheet                a thin lobed sand sheet (1.4 x 0.9 m) for alley floors and open lee patches.

Outputs: unity/AthenHill/Assets/AthenHill/Art/WallFootDrifts/Models/WFD_Kit.glb and kit.json (sizes, triangles,
visible footprints) in this folder.
"""
import bpy, bmesh, json, math, sys
from pathlib import Path
from mathutils import Vector, noise

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "unity/AthenHill/Assets/AthenHill/Art/WallFootDrifts/Models"
OUT.mkdir(parents=True, exist_ok=True)

SINK = 0.008          # whole surface lowered by 8 mm: the toe crosses the paving on a real slope
FLOOR = -0.05         # buried vertices are clamped here (the field keeps falling smoothly below the paving until then)
DROP = -0.006         # faces wholly below this are dropped (decks and treads sit ~4 mm under their nominal level)
OUTSIDE = 0.07        # beyond the toe the surface keeps descending (metres per unit of reach), so the contour stays smooth
INTO_WALL = 0.05      # back rows run this far into the wall face
STEPS = {0: 0.045, 1: 0.10, 2: 0.20}
COARSE = {"Corner_L": 1.4, "Corner_S": 1.15, "Post": 1.25, "Sheet": 1.2}   # LOD0 step multiplier for the broad pieces


def n2(x, z, s, seed):
    """Perlin noise in [-1, 1] at frequency s (per metre)."""
    return noise.noise(Vector((x * s + seed * 17.13, z * s - seed * 5.71, seed * 3.3)))


def fbm(x, z, s, seed, octaves=3):
    v, a, f, tot = 0.0, 1.0, 1.0, 0.0
    for o in range(octaves):
        v += a * n2(x, z, s * f, seed + o * 7)
        tot += a
        a *= 0.5
        f *= 2.03
    return v / tot


def bump(t):
    t = abs(t)
    return (1.0 - t * t) ** 2 if t < 1.0 else 0.0


def fillet(t, p=1.7):
    """Cross profile against a wall: 1 at the face, concave down to 0 at the toe (t = 1)."""
    if t <= 0.0:
        return 1.0
    if t >= 1.0:
        return 0.0
    return (1.0 - t) ** p


def smax(a, b, k=0.02):
    """Smooth maximum (polynomial), so merged banks blend without creases. The blend fades out where either input is
    near zero, so two empty fields stay empty (a plain polynomial smax would lift them by k/4 everywhere)."""
    h = max(k - abs(a - b), 0.0) / k
    lo = min(a, b)
    fade = 0.0 if lo <= 0.0 else (1.0 if lo >= k else (lo / k) ** 2 * (3 - 2 * lo / k))
    return max(a, b) + h * h * k * 0.25 * fade


# ---------------------------------------------------------------------- height fields (Unity local metres)
class Run:
    def __init__(self, name, L, W, H, lobes, seed, broken=0.0):
        self.name, self.L, self.W, self.H, self.lobes, self.seed, self.broken = name, L, W, H, lobes, seed, broken
        self.xr = (-L / 2 - 0.05, L / 2 + 0.05)
        self.zr = (-INTO_WALL, W * 1.45)

    def env(self, x):
        e = max(a * bump((x - c) / s) for (c, s, a) in self.lobes)
        if self.broken:
            # gaps where the dusting band breaks up
            e *= max(0.0, min(1.0, 0.55 + 1.6 * fbm(x, 0.0, 1.7, self.seed + 40, 2) + 0.3))
        return e

    def h(self, x, z):
        e = max(self.env(x), 0.0)
        w = self.W * (0.55 + 0.45 * e) * (1.0 + 0.22 * fbm(x, 0.0, 2.2, self.seed))
        hh = self.H * e * (1.0 + 0.2 * fbm(x, 0.0, 3.1, self.seed + 3))
        t = max(z, 0.0) / w
        v = hh * fillet(t)
        # wind scallops along the crest and a soft second lobe further out on the lee half
        v += hh * 0.18 * bump((t - 0.55) / 0.35) * (0.5 + 0.5 * fbm(x, z, 2.6, self.seed + 9))
        v *= 1.0 + 0.12 * fbm(x, z, 7.0, self.seed + 5, 2)
        # keep falling below the paving past the toe and past the ends of the lobes (no plateau, no cliff)
        return v - OUTSIDE * max(0.0, t - 1.0) - 0.05 * max(0.0, 0.08 - e)


class Corner:
    """Inside corner: wall A along +X with its face at z = 0, wall B along +Z with its face at x = 0."""

    def __init__(self, name, R, H, seed):
        self.name, self.R, self.H, self.seed = name, R, H, seed
        self.xr = (-INTO_WALL, R * 1.75)
        self.zr = (-INTO_WALL, R * 1.75)

    def h(self, x, z):
        R, H = self.R, self.H
        xa, za = max(x, 0.0), max(z, 0.0)
        r = math.hypot(xa, za)
        rr = R * (1.0 + 0.18 * fbm(math.atan2(za, xa) * 0.6, 0.0, 2.0, self.seed))
        cone = H * fillet(r / rr, 1.5)
        # banks running out along each wall, tapering away from the corner
        wa = R * 0.55 * (1.0 + 0.2 * fbm(xa, 0.0, 2.4, self.seed + 1))
        bank_a = H * 0.5 * bump(xa / (R * 1.7)) * fillet(za / wa)
        wb = R * 0.5 * (1.0 + 0.2 * fbm(za, 0.0, 2.4, self.seed + 2))
        bank_b = H * 0.45 * bump(za / (R * 1.55)) * fillet(xa / wb)
        v = smax(smax(cone, bank_a, 0.03), bank_b, 0.03)
        v *= 1.0 + 0.14 * fbm(x, z, 6.5, self.seed + 5, 2)
        return v - OUTSIDE * max(0.0, r / (R * 1.2) - 1.0)


class Post:
    """Collar round a footing at the origin (hidden inside it) with a lee tail towards +Z."""

    def __init__(self, name, H, seed):
        self.name, self.H, self.seed = name, H, seed
        self.xr = (-0.7, 0.7)
        self.zr = (-0.65, 1.1)

    def h(self, x, z):
        H = self.H
        r = math.hypot(x, z)
        th = math.atan2(x, z)                       # 0 = downwind (+Z), pi = upwind
        ring_r = 0.36 * (1.0 + 0.12 * fbm(th, 0.0, 1.4, self.seed))
        collar = H * (1.0 - min(1.0, max(0.0, (r - 0.1) / ring_r)) ** 1.6) if r < 0.1 + ring_r else 0.0
        # windward bank a little higher, flanks scoured lower
        collar *= 0.75 + 0.35 * max(0.0, -math.cos(th)) - 0.2 * abs(math.sin(th))
        # lee tail: an elongated tongue with a soft tip
        tail = H * 0.7 * math.exp(-((x / (0.19 + 0.05 * max(z, 0.0))) ** 2) - (max(z - 0.25, 0.0) / 0.42) ** 2) if z > 0.0 else 0.0
        v = smax(max(collar, 0.0), tail, 0.03)
        v *= 1.0 + 0.15 * fbm(x, z, 6.0, self.seed + 5, 2)
        return v - OUTSIDE * 0.5 * max(0.0, r - 0.5)


class Sheet:
    def __init__(self, name, LX, LZ, H, seed):
        self.name, self.LX, self.LZ, self.H, self.seed = name, LX, LZ, H, seed
        self.xr = (-LX / 2 - 0.1, LX / 2 + 0.1)
        self.zr = (-LZ / 2 - 0.1, LZ / 2 + 0.1)
        self.blobs = [(-0.35, -0.08, 0.5, 0.33, 1.0), (0.25, 0.1, 0.48, 0.3, 0.85), (0.05, -0.18, 0.38, 0.25, 0.7),
                      (0.52, -0.12, 0.2, 0.17, 0.6), (-0.6, 0.2, 0.18, 0.14, 0.5)]

    def h(self, x, z):
        v = 0.0
        for (cx, cz, sx, sz, a) in self.blobs:
            d = ((x - cx) / sx) ** 2 + ((z - cz) / sz) ** 2
            v = max(v, a * math.exp(-1.6 * d))
        v *= 1.0 + 0.5 * fbm(x, z, 3.0, self.seed, 3)
        return self.H * (v - 0.12) / 0.88


PIECES = [
    Run("Run_L", 1.6, 0.55, 0.13, [(-0.45, 0.42, 1.0), (0.22, 0.45, 0.82), (0.55, 0.22, 0.6)], 11),
    Run("Run_M", 1.1, 0.45, 0.10, [(-0.18, 0.36, 1.0), (0.26, 0.26, 0.7)], 23),
    Run("Run_S", 0.7, 0.35, 0.07, [(0.0, 0.33, 1.0)], 37),
    Run("Run_Low", 1.5, 0.3, 0.035, [(-0.38, 0.4, 1.0), (0.32, 0.42, 0.9)], 41, broken=1.0),
    Corner("Corner_L", 0.85, 0.19, 53),
    Corner("Corner_S", 0.5, 0.1, 61),
    Post("Post", 0.085, 71),
    Sheet("Sheet", 1.4, 0.9, 0.026, 83),
]


# ---------------------------------------------------------------------- meshing
def heightfield(piece, step):
    x0, x1 = piece.xr
    z0, z1 = piece.zr
    nx = max(2, int(round((x1 - x0) / step)))
    nz = max(2, int(round((z1 - z0) / step)))
    xs = [x0 + (x1 - x0) * i / nx for i in range(nx + 1)]
    zs = [z0 + (z1 - z0) * k / nz for k in range(nz + 1)]
    Y = [[max(FLOOR, piece.h(x, z) - SINK) for x in xs] for z in zs]
    return xs, zs, Y


def build(piece, lod):
    xs, zs, Y = heightfield(piece, STEPS[lod] * (COARSE.get(piece.name, 1.0) if lod == 0 else 1.0))
    verts, faces, idx = [], [], {}

    def vid(i, k):
        if (i, k) not in idx:
            idx[(i, k)] = len(verts)
            verts.append((xs[i], Y[k][i], zs[k]))
        return idx[(i, k)]

    for k in range(len(zs) - 1):
        for i in range(len(xs) - 1):
            ys = (Y[k][i], Y[k][i + 1], Y[k + 1][i + 1], Y[k + 1][i])
            if max(ys) <= DROP:
                continue                                     # wholly under the paving
            # split along the diagonal that follows the surface best (keeps the toe contour smooth)
            a, b, c, d = vid(i, k), vid(i + 1, k), vid(i + 1, k + 1), vid(i, k + 1)
            if abs(ys[0] - ys[2]) <= abs(ys[1] - ys[3]):
                faces += [(a, b, c), (a, c, d)]
            else:
                faces += [(a, b, d), (b, c, d)]
    # footprint of the visible sand (y > 0), for layout validation
    vis = [v for v in verts if v[1] > 0.0]
    fp = [min(v[0] for v in vis), max(v[0] for v in vis), min(v[2] for v in vis), max(v[2] for v in vis)] if vis else [0, 0, 0, 0]
    top = max(v[1] for v in verts) if verts else 0.0
    return verts, faces, fp, top


def to_blender(v):
    x, y, z = v
    return (-x, -z, y)                                       # Unity (x, y, z) -> Blender; glTF/glTFast map it back


def make_object(name, verts, faces, mat):
    me = bpy.data.meshes.new(name)
    me.from_pydata([to_blender(v) for v in verts], [], faces)
    me.update()
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()
    for f in bm.faces:
        if f.normal.z < 0.0:
            f.normal_flip()
    uv = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for l in f.loops:
            co = l.vert.co
            l[uv].uv = (-co.x, -co.y)                       # Unity (x, z) in metres
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mat = bpy.data.materials.new("WFD_Sand")
    mat.diffuse_color = (0.78, 0.66, 0.5, 1.0)
    objs, rec = [], {"source": "art/wall_foot_drifts_20261001/author_drift_kit.py", "date": "2026-10-01",
                     "units": "Unity metres, piece-local (x along the wall, y up, z out of the wall face)",
                     "sink": SINK, "intoWall": INTO_WALL, "pieces": {}}
    for p in PIECES:
        pr = {"lods": {}}
        for lod in (0, 1, 2):
            verts, faces, fp, top = build(p, lod)
            ob = make_object(f"WFD_{p.name}_LOD{lod}", verts, faces, mat)
            objs.append(ob)
            pr["lods"][f"LOD{lod}"] = len(faces)
            if lod == 0:
                pr["footprint"] = [round(v, 3) for v in fp]          # visible x0, x1, z0, z1
                pr["height"] = round(top, 3)
        rec["pieces"][p.name] = pr
        print(p.name, pr)
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    path = OUT / "WFD_Kit.glb"
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True, export_yup=True,
                              export_image_format="NONE", export_tangents=True, export_normals=True, export_apply=True,
                              export_extras=False, export_materials="EXPORT")
    (HERE / "kit.json").write_text(json.dumps(rec, indent=1))
    if "--blend" in sys.argv:
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE / "drift-kit.blend"))
    print("wrote", path)


main()
