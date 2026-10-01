"""Ward perimeter walls: modular stone wall kit, Blender 5.2 headless (1 October 2026).

Carl (30 Sep 2026): "walls look too clean, maybe some parts of the wall have fallen." The Ward's perimeter walls were
flat 44-triangle boxes with a tiled ashlar texture. This builds them as old, battle-scarred, repaired stone defences on
the shared Ward masonry kit (art/ward_masonry_kit: dressed ashlar with eroded arrises, chips, ray-traced occlusion,
runoff/rust channels, old battle damage for Athen Hill/Masonry Lit), the same stone as Vanguard Hall, the shops, the hill
and the tree beds.

Three wall kinds (pw_layout.KINDS) and their variants, each module built once at LOD0/LOD1/LOD2:
* NS: north/south curtain walls: rough footing, dressed courses, drip string course, crenellated parapet (through-stone
  merlons with saddle caps), piers every 7 m on both faces with pyramid caps.
* EX: the +X rampart by the District gate: 3 m thick, stepped buttresses with sloped weatherings on the city face, shallow
  pilasters outside, wall walk between a plain inner parapet and a crenellated outer parapet, stone spouts.
* BW: the low Outer Berms walls and the strip wall: saddleback coping, pilasters both faces, a foundation course showing
  where the Berms ground falls away.
Variants: intact (3 seeds), repair (pale replacement stones, bolted straps), merlons/coping (parapet partly broken),
impact (shell craters with the rubble core exposed), siege (impact + broken merlons, the gate flanks), collapse (upper
wall fallen, rubble cones, field repair), breach (wall down to the footing, closed with HESCO, sandbags and welded sheet).
Sheltered sand at the wall feet and on the rubble, dry weeds (Poly Haven CC0) in the sand pockets.

Run:  blender -b --factory-startup --python-exit-code 1 -P author_perimeter_walls.py -- [--kinds NS,EX,BW] [--only substr]
Outputs: unity/AthenHill/Assets/AthenHill/Art/PerimeterWalls/Models/PW_<kind>_LOD<n>.glb, perimeter-walls-<kind>.json.
Module convention: see pw_layout.py (local +X along the wall from 0 to L, city face +Z at z = +T/2, y = 0 paving).
"""
import bpy, bmesh, json, math, random, sys, time, zlib
from pathlib import Path
from mathutils import Vector, Matrix

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "art/ward_masonry_kit"))
sys.path.insert(0, str(HERE))
import ward_masonry as WM
from ward_masonry import (Part, Frame, ashlar_block, eroded_bevel, split_edge, finalize_parts, AOBaker, DripSet, ScarSet,
                          lerp, smoothstep, drng, tri_count, MORTAR_FRONT, nz, block_wear)
import pw_layout as PL

OUT = ROOT / "unity/AthenHill/Assets/AthenHill/Art/PerimeterWalls/Models"
PH = ROOT / "art/hill_20260930/polyhaven/models"
J = 0.009          # joint
FD = 0.062         # kit block face depth in front of the frame plane
SH_IN = 0.09       # shadow mesh inset behind every lit face (URP depth/normal bias alone left the faces in shadow)

# LOD2: no bevels at all (the kit already drops to one segment at LOD1)
_orig_bevel = WM.Part.bevel_edges


def _bevel(self, edges, offset, segs):
    if WM.S.LOD >= 2:
        return
    return _orig_bevel(self, edges, offset, segs)


WM.Part.bevel_edges = _bevel

# vertical schedules (Unity metres above the paving)
SCHED = {
    "NS": dict(courses=[0.0, 0.52, 0.98, 1.43, 1.90, 2.34, 2.79, 3.25, 3.69, 4.12], string=(4.12, 4.30), parapet=(4.30, 4.72),
               sill=(4.72, 4.90), merlon=(4.90, 5.40), cap=(5.40, 5.53), pier_w=1.1, pier_proj=0.25, pier_top=5.56, pier_cap=0.2,
               crenel=0.74, merlon_w=1.45),
    "EX": dict(courses=[0.0, 0.55, 1.02, 1.48, 1.95, 2.41, 2.88, 3.34, 3.80, 4.26, 4.72, 5.18, 5.64, 6.10, 6.50],
               string=(6.50, 6.68), in_par=(6.68, 7.12), in_cope=(7.12, 7.36), in_par_t=0.55, out_par=(6.68, 7.06),
               sill=(7.06, 7.22), merlon=(7.22, 7.78), cap=(7.78, 7.9), out_par_t=0.7, walk=6.68, buttress_w=0.8,
               merlon_w=1.05, period=5.0 / 3.0),
    "BW": dict(courses=[0.0, 0.55, 1.05, 1.54, 2.03, 2.50], cope=(2.50, 2.97), found=-1.2, pil_w=0.9, pil_proj=0.2, pil_top=2.36),
}


def crc(*key):
    return zlib.crc32(repr(key).encode())


def stint(rr, rough=False, pale=0.0):
    """stone_tint() with its own RNG (so LOD-only work never shifts the shared layout RNG)."""
    v = max(0.76, min(1.22, rr.gauss(1.0, 0.125)))
    warm = rr.gauss(0, 0.035)
    t = [v * (1 + warm), v, v * (1 - warm * 1.6)]
    roll = rr.random()
    if roll < 0.06:
        t = [c * f for c, f in zip(t, (1.12, 1.11, 1.12))]
    elif roll < 0.11:
        t = [c * f for c, f in zip(t, (0.82, 0.78, 0.74))]
    elif roll < 0.15:
        t = [c * f for c, f in zip(t, (1.035, 0.96, 0.9))]
    if rough:
        t = [c * 0.95 for c in t]
    if pale:
        t = [c * (1 + 0.14 * pale) for c in (t[0] * 0.99, t[1], t[2] * 1.02)]
    return tuple(min(0.66, 0.5 * c) for c in t)


def interp(pts, x):
    if x <= pts[0][0]:
        return pts[0][1]
    for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
        if x <= xb:
            return lerp(ya, yb, (x - xa) / max(1e-6, xb - xa))
    return pts[-1][1]


def rot_y(deg):
    return Matrix.Rotation(math.radians(deg), 3, "Y")


# ====================================================================== module builder
class Module:
    def __init__(self, spec, lod):
        self.spec = spec
        self.id = spec["id"]
        self.kind = spec["kind"]
        self.var = spec["variant"]
        self.base = self.var.split("_")[0]
        self.L = spec["length"]
        self.T = PL.KINDS[self.kind]["T"]
        self.S = SCHED[self.kind]
        self.lod = lod
        self.start, self.end = spec["start"], spec["end"]
        WM.set_state(lod, random.Random(crc(self.id, "layout")), self.id)
        WM.WEAR["ground_y"] = 0.0
        WM.WEAR["wear_scale"] = 1.15
        self.P = random.Random(crc(self.id, "plan"))          # plan decisions: identical at every LOD
        self.mas = Part(f"{self.id}_Stone_LOD{lod}")
        self.kit = Part(f"{self.id}_Kit_LOD{lod}", wear=False)
        self.drips = DripSet(base=0.0)
        self.scars = ScarSet(base=0.13)
        self.weeds = []            # (x, y, z, species, scale, yaw)
        self.cones = []            # rubble cone collider specs
        self.rec = dict(notes=[])
        T = self.T
        self.Fin = Frame((0.0, 0.0, T / 2 - FD), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0))
        self.Fout = Frame((0.0, 0.0, -T / 2 + FD), (-1.0, 0.0, 0.0), (0.0, 0.0, -1.0))
        self.plan()

    # ------------------------------------------------------------------ helpers
    def F(self, side):
        return self.Fin if side == "in" else self.Fout

    def u_of(self, side, x):
        return x if side == "in" else -x

    def zface(self, side):
        return self.T / 2 if side == "in" else -self.T / 2

    def sgn(self, side):
        return 1.0 if side == "in" else -1.0

    def stone(self, lo, hi, mat="VH_Ashlar", key=None, bev=(0.012, 0.022), rot=None, tops=None, chip=0.25, pale=0.0,
              rough=None, skip=(), part=None, erode=None, seg=0.18):
        """A solid (through) stone from lo to hi (local), optionally rotated (degrees about x, y, z) about its centre and
        with its four top corners offset (tops: dy for corners (x0z0, x1z0, x1z1, x0z1))."""
        part = part or self.mas
        rr = drng("st", self.id, key if key is not None else (round(lo[0], 3), round(lo[1], 3), round(lo[2], 3)))
        rough = mat.endswith("Rough") if rough is None else rough
        x0, y0, z0 = lo
        x1, y1, z1 = hi
        if self.lod >= 3:
            k = min(SH_IN, 0.25 * min(x1 - x0, y1 - y0, z1 - z0))
            x0, z0, x1, y1, z1 = x0 + k, z0 + k, x1 - k, y1 - k, z1 - k
        wl = block_wear(y0)
        er = (0.004 + 0.009 * wl) * (1.35 if rough else 1.0) if erode is None else erode
        bid = part.new_block(tint=stint(rr, rough, pale), erode=er)
        t = tops or (0, 0, 0, 0)
        c = [Vector((x0, y0, z0)), Vector((x1, y0, z0)), Vector((x1, y0, z1)), Vector((x0, y0, z1)),
             Vector((x0, y1 + t[0], z0)), Vector((x1, y1 + t[1], z0)), Vector((x1, y1 + t[2], z1)), Vector((x0, y1 + t[3], z1))]
        if self.lod == 0 and chip > 0 and rr.random() < chip:
            i = rr.choice((4, 5, 6, 7) if rr.random() < 0.7 else (0, 1, 2, 3))
            ctr = sum(c, Vector()) / 8
            d = (ctr - c[i]).normalized()
            c[i] = c[i] + d * rr.uniform(0.02, 0.06)
        if rot is not None:
            ctr = sum(c, Vector()) / 8
            R = (Matrix.Rotation(math.radians(rot[1]), 3, "Y") @ Matrix.Rotation(math.radians(rot[0]), 3, "X")
                 @ Matrix.Rotation(math.radians(rot[2]), 3, "Z"))
            c = [ctr + R @ (p - ctr) for p in c]
        vs, made = part.hexa(c, mat, bid, skip=skip)
        b = rr.uniform(*bev)
        edges = list({e for f in made.values() for e in f.edges})
        eroded_bevel(part, edges, b, 2, seg_len=seg if self.lod == 0 else 0)
        return made

    def core_box(self, lo, hi):
        """Mortar core behind stacked through-stones (piers, buttresses, quoins, merlons): the 9 mm joints show mortar
        instead of daylight or the hollow wall interior. Not built for the shadow mesh."""
        if self.lod >= 3 or hi[0] - lo[0] < 0.02 or hi[1] - lo[1] < 0.02 or hi[2] - lo[2] < 0.02:
            return
        self.mas.box(lo, hi, "VH_Mortar")

    def slab_runs(self, segs, y0, y1, z0, z1):
        """Mortar slab inside each run of touching through-stones (string courses, sills, copings)."""
        segs = sorted(segs)
        runs = []
        for a, b in segs:
            if runs and a - runs[-1][1] < 2.5 * J:
                runs[-1][1] = max(runs[-1][1], b)
            else:
                runs.append([a, b])
        for a, b in runs:
            if b - a > 0.3:
                self.core_box((a + 0.02, y0, z0), (b - 0.02, y1, z1))

    def block_face(self, side, u0, u1, y0, y1, mat, key, depth=FD, back=0.035, tint=None, chip=0.10, wear=None, top=False,
                   bottom=False, bevel=(0.010, 0.022)):
        return ashlar_block(self.mas, self.F(side), u0, u1, y0, y1, mat=mat, key=key, depth=depth, back=back, tint=tint,
                            chip=chip, wear=wear, top=top, bottom=bottom, bevel=bevel)

    # ------------------------------------------------------------------ plan (all decisions, LOD independent)
    def plan(self):
        r, S, L, T, k, b = self.P, self.S, self.L, self.T, self.kind, self.base
        self.craters = []          # (side, x, y, rx, ry, depth)
        self.profile = None        # [(x, y)] broken top (city face); outer face 0.15 lower
        self.patch = None          # (side, x0, x1, ci0, ci1)
        self.plates = []           # (side, x, y0, y1, w, horizontal)
        self.stitches = []         # (side, x, y0, y1): a crack stitched with steel staples
        self.pattress = []         # (x, y): tie-rod pattress plates on both faces
        self.fallen = []           # (x, z, size (sx, sy, sz), rot, mat)
        self.merlon_state = {}     # index -> "gone" | "sheared" | "pale"
        self.cope_state = {}       # index -> "gone" | "shift" | "pale"
        self.screen = None
        self.hesco = None
        self.bagrows = []          # (x0, x1, z, y0, rows)
        self.pale_blocks = set()
        self.holes = {}            # crater index -> [(x0, x1, y0, y1)] blocks knocked out (module x)
        self.laid_tops = {}        # side -> [(x0, x1, top)] face blocks laid (module x): the stepped broken top
        self.face_spans = {}       # side -> u spans of the blocks laid in the latest course (support at breaks)
        self.core_fn = None        # x -> rubble core surface height (collapse / breach), for sandbags
        self.foot_boxes = []       # footprint records for the layout check: (kind, x0, x1, z0, z1, y0, y1)
        # body extent on the faces
        if k == "NS":
            pw = S["pier_w"] / 2
            self.wx0 = pw if self.start == "pier" else 0.0
            self.wx1 = L if self.end == "end" else L - pw
        else:
            self.wx0, self.wx1 = 0.0, L
        top = S["courses"][-1]
        if b == "intact":
            if self.var.endswith("b"):
                self.craters.append(("in", L * 0.62, top * 0.66, 0.26, 0.22, 0.12))
            if self.var.endswith("c"):
                self.pale_blocks = {("in", ci, r.randrange(3)) for ci in (2, 3, 5)}
        elif b == "repair":
            ci0 = 2 if k != "EX" else 5
            self.patch = ("in", L * 0.28, L * 0.55, ci0, ci0 + (3 if k != "BW" else 2))
            self.stitches.append(("in", L * 0.76, top * 0.24, top * 0.72))
            self.pattress.append((L * (0.16 if k != "EX" else 0.2) + (0.1 if k == "NS" else 0.0), top * 0.6))
            if k == "NS":
                self.merlon_state[1] = "pale"
            if k == "BW":
                self.cope_state[2] = "pale"
        elif b in ("merlons", "coping"):
            pass   # merlon/coping states are chosen once the merlons are laid out
        elif b in ("impact", "siege"):
            if k == "NS":
                self.craters += [("in", L * 0.33, 2.9, 0.62, 0.5, 0.26), ("in", L * 0.7, 1.35, 0.42, 0.36, 0.18),
                                 ("out", L * 0.5, 3.3, 0.5, 0.45, 0.2)]
            elif k == "EX":
                if b == "siege":
                    self.craters += [("in", L * 0.56, 5.55, 0.78, 0.6, 0.32), ("in", L * 0.24, 2.95, 0.45, 0.4, 0.2),
                                     ("out", L * 0.45, 4.4, 0.62, 0.5, 0.22)]
                    self.stitches.append(("in", L * 0.8, 1.7, 3.9))
                else:
                    self.craters += [("in", L * 0.32, 4.9, 0.7, 0.55, 0.3), ("in", L * 0.72, 2.2, 0.5, 0.45, 0.2),
                                     ("out", L * 0.5, 5.5, 0.6, 0.5, 0.22)]
            else:
                self.craters += [("in", L * 0.34, 1.5, 0.46, 0.4, 0.2), ("out", L * 0.64, 1.25, 0.56, 0.45, 0.24),
                                 ("out", L * 0.26, 2.05, 0.34, 0.3, 0.14)]
        elif b == "collapse":
            if k == "NS" and self.var == "collapse_n":
                # north wall (Quantum Tube pylons 1.3 m off the city face): rubble mostly fell outwards
                self.profile = [(0.0, 9), (1.55, 9), (1.8, 3.7), (2.35, 3.0), (3.1, 2.5), (4.3, 2.6), (4.95, 3.25), (5.3, 4.05),
                                (5.5, 9), (L, 9)]
                self.screen = dict(x0=1.8, x1=5.35, z=-0.27, y0=2.3, y1=4.6)
                self.cones += [dict(side="in", x=3.6, out=0.95, ru=2.0, h=0.55), dict(side="out", x=3.4, out=3.2, ru=3.1, h=1.6)]
            elif k == "NS":
                self.profile = [(0.0, 9), (1.25, 9), (1.45, 3.95), (1.9, 3.35), (2.5, 2.6), (3.4, 2.3), (4.3, 2.42), (4.95, 3.05),
                                (5.45, 3.8), (5.75, 9), (L, 9)]
                self.screen = dict(x0=1.5, x1=5.6, z=-0.27, y0=2.1, y1=4.55)
                self.cones += [dict(side="in", x=3.4, out=2.2, ru=2.6, h=1.05), dict(side="out", x=3.2, out=2.9, ru=3.0, h=1.45)]
            else:
                self.profile = [(0.0, 9), (0.75, 9), (0.95, 2.2), (1.3, 1.75), (1.9, 1.55), (3.0, 1.5), (3.7, 1.6), (4.05, 2.05),
                                (4.4, 9), (L, 9)]
                self.screen = dict(x0=0.85, x1=4.2, z=-0.72, y0=1.35, y1=2.95)
                self.bagrows.append((1.6, 3.7, 0.05, None, 2))
                self.cones += [dict(side="in", x=2.2, out=1.4, ru=1.9, h=0.6), dict(side="out", x=3.75, out=1.8, ru=1.7, h=0.8)]
        elif b == "breach":
            # the wall is down to its footing over ~2 m; the Wardens cleared the floor and rammed HESCO into the gap
            self.profile = [(0.0, 9), (0.55, 9), (0.72, 2.5), (0.95, 1.55), (1.2, 0.8), (1.5, 0.48), (3.5, 0.42), (3.8, 0.75),
                            (4.05, 1.6), (4.28, 2.5), (4.45, 9), (L, 9)]
            self.hesco = dict(x0=1.0, x1=4.0, y0=0.3)
            self.screen = dict(x0=0.62, x1=4.38, z=-T / 2 - 0.12, y0=0.75, y1=3.0)   # bolted over the outer face
            self.cones += [dict(side="in", x=0.85, out=1.1, ru=1.0, h=0.55), dict(side="in", x=4.15, out=1.0, ru=0.9, h=0.45),
                           dict(side="out", x=2.5, out=2.7, ru=2.9, h=1.1)]
        # fallen stones for the damage variants (on the cones and at the feet)
        nf = {"collapse": 7, "breach": 7, "merlons": 3, "coping": 2, "siege": 4, "impact": 3}.get(b, 0)
        for i in range(nf):
            side = "in" if (i % 2 == 0 or b in ("merlons",)) and not (b == "siege" and i % 3 == 2) else "out"
            if self.cones:
                c = r.choice([c for c in self.cones if c["side"] == side] or self.cones)
                side = c["side"]
                x = c["x"] + r.uniform(-c["ru"], c["ru"]) * 0.8
                d = r.uniform(0.3, c["out"] * 1.05) if c["out"] > 1.5 else r.uniform(0.25, max(0.3, c["out"] * 0.7))
            elif b == "siege":
                # gate flanks: the District gate arch pier covers the module's end (south) or start (north); the
                # aquifer seep pipe stands on the south flank's foot
                x = r.uniform(1.7, L - 1.4) if self.start == "pier" else r.uniform(1.7, L - 0.6)
                d = r.uniform(0.22, 0.42) if side == "in" else r.uniform(0.3, 1.1)
            else:
                # parapet stones land at the foot: close in on the city side (things stand ~0.7 m off the walls)
                x = r.uniform(0.6, L - 0.6)
                if k == "BW" and self.start == "none":
                    side = "in"          # the portal flank: the West Gate sentry nest stands against the outer face
                d = r.uniform(0.22, 0.42) if side == "in" else (r.uniform(0.25, 0.5) if k == "BW" else r.uniform(0.3, 1.3))
            sx, sy, sz = r.uniform(0.55, 1.05), r.uniform(0.3, 0.46), r.uniform(0.28, 0.5)
            if r.random() < 0.35:
                sx *= 0.55
            z = self.sgn(side) * (T / 2 + d)
            yaw = r.uniform(0, 360)
            if side == "in" and not self.cones:
                yaw = r.uniform(-25, 25) + (180 if r.random() < 0.5 else 0)     # lying along the foot, not across it
            self.fallen.append((x, z, (sx, sy, sz), (r.uniform(-14, 14), yaw, r.uniform(-18, 18)), "VH_Ashlar"))

    # ------------------------------------------------------------------ geometry passes
    def top_at(self, side, x):
        if not self.profile:
            return 99.0
        y = interp(self.profile, x)
        return y - (0.15 if side == "out" else 0.0)

    def top_min(self, side, xa, xb):
        """Lowest broken-top height over [xa, xb] (a stone stays only where the whole stone is under the break, so
        nothing overhangs the gap)."""
        if not self.profile:
            return 99.0
        xa, xb = min(xa, xb), max(xa, xb)
        xs = [lerp(xa, xb, t / 6) for t in range(7)] + [p[0] for p in self.profile if xa < p[0] < xb]
        return min(self.top_at(side, x) for x in xs)

    def top_both(self, xa, xb):
        return min(self.top_min("in", xa, xb), self.top_min("out", xa, xb))

    def crater_hit(self, side, x, y):
        """(index, normalised distance) of the nearest crater ellipse on this face (< 1 inside, rim up to ~1.7)."""
        best, idx = 9.0, None
        for i, (s, cx, cy, rx, ry, dp) in enumerate(self.craters):
            if s != side:
                continue
            d = math.hypot((x - cx) / rx, (y - cy) / ry)
            if d < best:
                best, idx = d, i
        return idx, best

    def crater_w(self, side, x, y):
        return self.crater_hit(side, x, y)[1]

    def courses_face(self, side, xa, xb, courses, key, rough_first=True, ulimit=None, allow_patch=True, fdepth=None):
        """Dressed courses on one face between local x xa..xb; skips blocks inside craters / above the broken top; blocks
        at crater rims and at the break get deep returns and heavy chipping. Returns the laid blocks."""
        F = self.F(side)
        Lr = WM.S.LAYOUT
        laid = []
        for ci, (y0, y1) in enumerate(zip(courses, courses[1:])):
            rough = rough_first and y1 <= 0.6
            mat = "VH_AshlarRough" if rough else "VH_Ashlar"
            depth = (0.1 if rough else FD) if fdepth is None else fdepth
            a, b = (xa, xb) if ulimit is None else ulimit(ci, y0, y1)
            if b - a < 0.05:
                continue
            ua, ub = sorted((self.u_of(side, a), self.u_of(side, b)))
            # patch replaced with small pale stones
            prow = None
            if allow_patch and self.patch and self.patch[0] == side and self.patch[3] <= ci < self.patch[4]:
                pa, pb = sorted((self.u_of(side, self.patch[1]), self.u_of(side, self.patch[2])))
                prow = (pa, pb)
            u = ua
            first = True
            run = []            # contiguous mortar runs
            cur = None
            bi = 0
            prev_spans = self.face_spans.get(side, [])   # blocks laid in the course below (this face, u coords)
            course_spans = []
            while u < ub - 1e-4:
                ln = Lr.uniform(0.62, 1.28)
                if first:
                    ln *= (0.45 + 0.35 * Lr.random()) if ci % 2 else 1.0
                    first = False
                if ub - (u + ln) < 0.31:
                    ln = ub - u
                if prow and u < prow[1] and u + ln > prow[0]:
                    # cut the regular block at the patch edge, fill the patch with small pale stones
                    if u < prow[0] - 0.15:
                        ln = prow[0] - u
                    else:
                        self.patch_course(side, u, prow[1], y0, y1, (key, ci))
                        if cur is None:
                            cur = [u, prow[1]]
                        else:
                            cur[1] = prow[1]
                        u = prow[1]
                        prow = None
                        bi += 1
                        continue
                ba, bb = u + J / 2, u + ln - J / 2
                xm = (self.u_of(side, (ba + bb) / 2))
                ym = (y0 + y1) / 2
                hit, cw = self.crater_hit(side, xm, ym)
                topy = self.top_min(side, self.u_of(side, ba), self.u_of(side, bb))
                skip = cw < 1.0 or ym > topy - 0.02
                if not skip and self.profile is not None and topy < 8.5 and y0 > 0.6:
                    # at a break a block stays only where the course below still carries most of it: the break steps
                    # back like real masonry (no stone hanging over a gap, no daylight windows under surviving stones)
                    carried = sum(max(0.0, min(bb, b_) - max(ba, a_)) for a_, b_ in prev_spans)
                    skip = carried < 0.6 * (bb - ba)
                if cw < 1.0 and hit is not None:
                    xa_, xb_ = sorted((self.u_of(side, ba), self.u_of(side, bb)))
                    self.holes.setdefault(hit, []).append((xa_ - J, xb_ + J, y0, y1))
                if not skip:
                    near_break = self.profile is not None and y1 > topy - 0.55
                    rim = cw < 1.7
                    back = -0.22 if (rim or near_break) else 0.035
                    chip = 0.9 if (rim or near_break) else (0.1 if not rough else 0.3)
                    wear = 1.0 if (rim or near_break) else None
                    tint = None
                    if (side, ci, bi % 3) in self.pale_blocks:
                        tint = stint(drng("pale", self.id, side, ci, bi), False, 1.0)
                    d = depth
                    if rim and cw < 1.35:
                        d = depth - 0.02
                    # rim blocks broken off on the crater side: the hole's outline steps irregularly instead of
                    # following whole blocks (the removed part joins the hole, so the bowl covers it)
                    ma, mb = u, u + ln              # this block's mortar span
                    rcut = drng("rimcut", self.id, key, side, ci, round(u, 3))
                    if hit is not None and 1.0 <= cw < 1.6 and rcut.random() < 0.85 and bb - ba > 0.4:
                        f = rcut.uniform(0.25, 0.5)
                        ucx = self.u_of(side, self.craters[hit][1])
                        if ucx < (ba + bb) / 2:
                            cut = (ba, ba + f * (bb - ba))
                            ba = cut[1] + J / 2
                            ma = ba - J / 2
                        else:
                            cut = (bb - f * (bb - ba), bb)
                            bb = cut[0] - J / 2
                            mb = bb + J / 2
                        xa_, xb_ = sorted((self.u_of(side, cut[0]), self.u_of(side, cut[1])))
                        self.holes.setdefault(hit, []).append((xa_ - J, xb_ + J, y0, y1))
                        if ma > u + 1e-6 and cur is not None:
                            run.append(cur)
                            cur = None
                    self.block_face(side, ba, bb, y0 + J / 2, y1 - J / 2, mat, (key, side, ci, round(u, 3)), depth=d, back=back,
                                    chip=chip, wear=wear, tint=tint, top=ym > topy - 0.6 and self.profile is not None)
                    if near_break and self.lod < 3:
                        # the block's back shows where the rubble core behind it has gone: close it with a rough bed
                        F.box(self.mas, ba, bb, y0 + J / 2, y1 - J / 2, back - 0.01, back, "VH_AshlarRough",
                              skip=("s1", "s2", "s3", "top", "bottom"))
                    laid.append((xm, y0, y1))
                    xa_, xb_ = sorted((self.u_of(side, ba), self.u_of(side, bb)))
                    self.laid_tops.setdefault(side, []).append((xa_ - J, xb_ + J, y1))
                    course_spans.append((ba - J, bb + J))
                    if cur is None:
                        cur = [ma, mb]
                    else:
                        cur[1] = mb
                    if mb < u + ln - 1e-6:
                        run.append(cur)
                        cur = None
                else:
                    # skipped at every LOD alike, so the layout RNG stays in step between LODs
                    if cur is not None:
                        run.append(cur)
                        cur = None
                u += ln
                bi += 1
            if cur is not None:
                run.append(cur)
            self.face_spans[side] = course_spans
            for sa, sb in run:
                F.box(self.mas, sa, sb, y0, y1, 0.02, MORTAR_FRONT, "VH_Mortar", skip=("s0", "bottom", "top", "s1", "s3"))
        return laid

    def patch_course(self, side, ua, ub, y0, y1, key):
        """Later repair: small pale stones in two half courses."""
        rr = random.Random(crc(self.id, "patch", key))
        n = 2
        for kk in range(n):
            a, b = lerp(y0, y1, kk / n), lerp(y0, y1, (kk + 1) / n)
            u = ua + (rr.uniform(0.05, 0.2) if kk % 2 else 0.0)
            if u > ua + 0.02:
                self.block_face(side, ua + 0.006, u - 0.006, a + 0.006, b - 0.006, "VH_Ashlar", (key, kk, "s"), depth=FD - 0.004,
                                tint=stint(rr, False, 1.0), chip=0.05, wear=0.3)
            while u < ub - 1e-3:
                ln = rr.uniform(0.3, 0.55)
                if ub - (u + ln) < 0.18:
                    ln = ub - u
                self.block_face(side, u + 0.006, u + ln - 0.006, a + 0.006, b - 0.006, "VH_Ashlar", (key, kk, round(u, 3)),
                                depth=FD - 0.006, tint=stint(rr, False, 1.0), chip=0.05, wear=0.3)
                u += ln

    def crater_bowls(self):
        """Rubble core exposed where a shell knocked the face blocks out: a rough bowl covering exactly the hole (the
        knocked-out blocks recorded by courses_face, plus a joint), deepest at the impact point, with loose fragments
        resting on it. The rim blocks around it have deep broken returns (courses_face)."""
        for ci, (side, cx, cy, rx, ry, dp) in enumerate(self.craters):
            F = self.F(side)
            rr = random.Random(crc(self.id, "bowl", ci))
            holes = self.holes.get(ci, [])
            # scars and soot (also for a crater too small to knock a block out)
            self.scars.impact(tuple(F.P(self.u_of(side, cx), cy, 0.07)), max(rx, ry) * 2.3, 1.0)
            if dp > 0.2:
                n = (0.0, 0.0, self.sgn(side))
                self.scars.plume(n, self.zface(side), cx - rx * 0.8, cx + rx * 0.8, cy + ry * 0.2, 1.9, 0.7)
            if not holes:
                continue
            x0 = min(h[0] for h in holes) - 0.05
            x1 = max(h[1] for h in holes) + 0.05
            y0 = max(-0.3, min(h[2] for h in holes) - 0.05)
            y1 = max(h[3] for h in holes) + 0.05
            step = (0.07, 0.2, 0.45)[min(self.lod, 2)]
            nu = max(2, min(40, int((x1 - x0) / step) + 1))
            nv = max(2, min(30, int((y1 - y0) / step) + 1))
            bm = self.mas.bm
            mi = self.mas.mi("VH_AshlarRough")
            bid = self.mas.new_block(tint=stint(rr, True), erode=0.0, scale=1.6)

            def depth(x, y):
                d = math.hypot((x - cx) / (rx * 1.25), (y - cy) / (ry * 1.25))
                k = 0.09 + (dp - 0.09) * max(0.0, 1 - d * d) ** 0.7
                if self.lod < 2:
                    k += 0.035 * (0.5 + 0.5 * nz(Vector((x, y, 0.0)), 6.0, ci * 3.1)) + 0.015 * nz(Vector((x, y, 0.0)), 17.0, 2.0)
                return k
            grid = []
            for j in range(nv + 1):
                row = []
                for i in range(nu + 1):
                    x = lerp(x0, x1, i / nu)
                    y = lerp(y0, y1, j / nv)
                    row.append(bm.verts.new(F.P(self.u_of(side, x), y, -depth(x, y))))
                grid.append(row)
            fs = []
            for j in range(nv):
                for i in range(nu):
                    fs.append(bm.faces.new([grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]]))
            for f in fs:
                f.material_index = mi
                f[self.mas.blk] = bid
                f.normal_update()
            # one consistent orientation for the whole sheet (per-face flips leave black seams on steep cells)
            if sum((f.normal.dot(F.n) for f in fs)) < 0:
                for f in fs:
                    f.normal_flip()
            # loose fragments resting in the bowl (LOD0/1), on the lower half where they would lodge
            if self.lod < 2:
                for m in range(5 if self.lod == 0 else 2):
                    h = rr.choice(holes)
                    x = rr.uniform(h[0] + 0.08, h[1] - 0.08)
                    y = rr.uniform(h[2] + 0.04, lerp(h[2], h[3], 0.45))
                    sz = rr.uniform(0.05, 0.12)
                    dd = -depth(x, y) + sz * 0.45
                    c = F.P(self.u_of(side, x), y, dd)
                    self.stone((c.x - sz, c.y - sz * 0.55, c.z - sz * 0.7), (c.x + sz, c.y + sz * 0.55, c.z + sz * 0.7), "VH_AshlarRough",
                               key=("frag", ci, m), rot=(rr.uniform(-30, 30), rr.uniform(0, 180), rr.uniform(-30, 30)),
                               bev=(0.006, 0.012), chip=0.6)

    def core_fill(self, xa, xb, ytop_full, ybot=0.0):
        """Rubble core of a collapsed / breached section: a heightfield between the two faces just under the broken
        profile, closed by skirts down its sides and ends (so no open edge shows into the hollow between the faces),
        with loose stones only where the break is gentle enough for them to lie."""
        T = self.T
        rr = random.Random(crc(self.id, "core"))
        nx = int((xb - xa) / (0.12 if self.lod == 0 else (0.3 if self.lod == 1 else 0.6))) + 1
        nzs = 6 if self.lod == 0 else (3 if self.lod == 1 else 2)
        z0, z1 = -T / 2 + 0.05, T / 2 - 0.05
        bm = self.mas.bm
        mi = self.mas.mi("VH_AshlarRough")
        bid = self.mas.new_block(tint=stint(rr, True), erode=0.0, scale=1.4)

        def stepped(side, x):
            tops = [t for (a, b, t) in self.laid_tops.get(side, ()) if a <= x <= b]
            return max(tops) if tops else ybot

        def core_y(x, z):
            # just under the stepped top of the face stones that survived (never above them), heaped a little in the
            # middle of the wall where the rubble core sits
            tz = (z - z0) / (z1 - z0)
            t = min(lerp(stepped("out", x), stepped("in", x), tz), ytop_full) - 0.06
            n1 = nz(Vector((x, 0.0, z)), 4.5, 7.7) if self.lod < 2 else 0.0
            n2 = nz(Vector((x, 0.0, z)), 13.0, 3.3) if self.lod == 0 else 0.0
            heap = 0.06 * math.sin(math.pi * tz) * (0.6 + 0.4 * n1) + 0.02 * n2
            return max(ybot + 0.05, t + heap)
        self.core_fn = lambda x: core_y(x, 0.0)
        grid = []
        for j in range(nzs + 1):
            z = lerp(z0, z1, j / nzs)
            grid.append([bm.verts.new(Vector((lerp(xa, xb, i / nx), core_y(lerp(xa, xb, i / nx), z), z))) for i in range(nx + 1)])
        fs = []
        for j in range(nzs):
            for i in range(nx):
                fs.append(bm.faces.new([grid[j][i], grid[j + 1][i], grid[j + 1][i + 1], grid[j][i + 1]]))
        # skirts: long sides (inside the face blocks) and the two ends, 0.7 m deep
        def skirt(edge_verts):
            low = [bm.verts.new(Vector((v.co.x, max(ybot - 0.05, v.co.y - 0.7), v.co.z))) for v in edge_verts]
            for k in range(len(edge_verts) - 1):
                fs.append(bm.faces.new([edge_verts[k], edge_verts[k + 1], low[k + 1], low[k]]))
        skirt(grid[0][::-1])
        skirt(grid[nzs])
        skirt([grid[j][0] for j in range(nzs + 1)])
        skirt([grid[j][nx] for j in range(nzs + 1)][::-1])
        for f in fs:
            f.material_index = mi
            f[self.mas.blk] = bid
            f.normal_update()
        # top sheet faces up by construction; make each skirt face point away from the core's centre line
        ctr = Vector(((xa + xb) / 2, 0.0, 0.0))
        for f in fs:
            c = f.calc_center_median()
            if abs(f.normal.y) < 0.5:
                at_end = abs(c.x - xa) < 1e-3 or abs(c.x - xb) < 1e-3
                out = Vector((c.x - ctr.x, 0.0, 0.0)) if at_end else Vector((0.0, 0.0, c.z))
                if out.length > 1e-6 and f.normal.dot(out) < 0:
                    f.normal_flip()
            elif f.normal.y < 0:
                f.normal_flip()
        # loose stones on the broken top, only where it is gentle
        if self.lod < 2:
            for m in range(int((xb - xa) * (6 if self.lod == 0 else 2))):
                x = rr.uniform(xa + 0.2, xb - 0.2)
                z = rr.uniform(z0 + 0.12, z1 - 0.12)
                sl = abs(core_y(x + 0.2, z) - core_y(x - 0.2, z)) / 0.4
                st = rr.uniform(0.07, 0.18)
                if sl > 0.5 or core_y(x, z) > ytop_full - 0.3:
                    continue
                y = min(core_y(x - st, z), core_y(x + st, z), core_y(x, z))
                self.stone((x - st, y - st * 0.25, z - st * 0.7), (x + st, y + st * 0.55, z + st * 0.7), "VH_AshlarRough", key=("cst", m),
                           rot=(rr.uniform(-15, 15), rr.uniform(0, 180), rr.uniform(-15, 15)), bev=(0.006, 0.014), chip=0.7)

    def cone(self, c, ground=None):
        """Rubble cone against the wall foot: heightfield mound (rough stone) + fallen blocks placed separately."""
        side = c["side"]
        sg = self.sgn(side)
        rr = random.Random(crc(self.id, "cone", side))
        n_u = 18 if self.lod == 0 else (9 if self.lod == 1 else 5)
        n_d = 10 if self.lod == 0 else (5 if self.lod == 1 else 3)
        xa, xb = c["x"] - c["ru"], c["x"] + c["ru"]
        zf = self.zface(side) - sg * 0.35               # starts inside the wall face (the break)
        part = self.kit if self.lod < 3 else self.mas
        bm = part.bm
        mi = part.mi("PW_Rubble")
        bid = part.new_block(erode=0.0, scale=1 / 1.6)
        grid = []
        hull = []
        for j in range(n_d + 1):
            dn = lerp(-0.35, c["out"], j / n_d)
            row = []
            for i in range(n_u + 1):
                x = lerp(xa, xb, i / n_u)
                du = (x - c["x"]) / c["ru"]
                dd = max(0.0, dn) / c["out"]
                r2 = du * du + dd * dd
                g = ground(max(0.0, dn)) if ground else 0.0
                h = c["h"] * max(0.0, 1 - r2) ** 0.75
                if self.lod < 2:
                    h *= 0.85 + 0.3 * (0.5 + 0.5 * nz(Vector((x, 0, dn)), 2.2, 5.1))
                    h += 0.04 * nz(Vector((x, 0, dn)), 9.0, 2.2) * (h > 0.05)
                y = g + max(-0.03, h) - 0.02 - (0.08 if self.lod >= 3 else 0.0)
                p = Vector((x, y, self.zface(side) + sg * dn))
                row.append(bm.verts.new(p))
                if i % max(1, n_u // 4) == 0 and j % max(1, n_d // 3) == 0:
                    hull.append(p.copy())
            grid.append(row)
        fs = []
        for j in range(n_d):
            for i in range(n_u):
                f = bm.faces.new([grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]])
                f.material_index = mi
                f[part.blk] = bid
                fs.append(f)
        for f in fs:
            f.normal_update()
            if sg > 0:              # the grid winds downwards on the +Z side: flip the whole sheet, never per face
                f.normal_flip()
        # rubble pieces on the mound
        if self.lod < 2:
            npc = int(c["ru"] * c["out"] * (15 if self.lod == 0 else 3))
            for m in range(npc):
                x = rr.uniform(xa + 0.2, xb - 0.2)
                dn = rr.uniform(0.0, c["out"] * 0.9)
                du = (x - c["x"]) / c["ru"]
                dd = dn / c["out"]
                r2 = du * du + dd * dd
                if r2 > 0.9:
                    continue
                g = ground(dn) if ground else 0.0
                h = g + c["h"] * max(0.0, 1 - r2) ** 0.75 * 0.9
                roll = rr.random()
                s = (rr.uniform(0.06, 0.15) if roll < 0.68 else rr.uniform(0.17, 0.3) if roll < 0.95 else rr.uniform(0.32, 0.45))
                s *= (1.3 if self.lod == 1 else 1.0)
                z = self.zface(side) + sg * dn
                self.stone((x - s, h - s * 0.55, z - s * 0.75), (x + s * rr.uniform(0.7, 1.4), h + s * 0.55, z + s * 0.75),
                           "VH_AshlarRough" if rr.random() < 0.7 else "VH_Ashlar", key=("cone", side, m),
                           rot=(rr.uniform(-25, 25), rr.uniform(0, 180), rr.uniform(-25, 25)), bev=(0.006, 0.016), chip=0.8)
            # sand blown over the lower mound, weeds rooted in it
            for m in range(3):
                x = c["x"] + rr.uniform(-0.8, 0.8) * c["ru"]
                dn = c["out"] * rr.uniform(0.55, 0.95)
                g = ground(dn) if ground else 0.0
                self.weeds.append((x, g, self.zface(side) + sg * dn, rr.choice(("grass", "grass", "weed")), rr.uniform(0.8, 1.3), rr.uniform(0, 360)))
        self.cones_hull = getattr(self, "cones_hull", []) + [hull]

    def fallen_stones(self, ground=None):
        for i, (x, z, (sx, sy, sz), rot, mat) in enumerate(self.fallen):
            if self.base == "siege":
                # clear of the District gate arch pier and the aquifer seep pipe on the south flank's foot
                x = min(max(x, 1.75), self.L - (1.45 if self.start == "pier" else 0.65))
            side = "in" if z > 0 else "out"
            dn = abs(z) - self.T / 2
            base = 0.0
            for c in self.cones:
                if c["side"] != side:
                    continue
                du = (x - c["x"]) / c["ru"]
                dd = dn / c["out"]
                r2 = du * du + dd * dd
                if r2 < 1:
                    base = max(base, c["h"] * max(0.0, 1 - r2) ** 0.75 * 0.8)
            if ground and side == "out":
                base += ground(dn)
            lo = (x - sx / 2, base - sy * 0.25, z - sz / 2)
            hi = (x + sx / 2, base + sy * 0.75, z + sz / 2)
            self.stone(lo, hi, mat, key=("fallen", i), rot=rot, chip=0.9, bev=(0.012, 0.03))

    # ------------------------------------------------------------------ sand, weeds
    def drift(self, side, xa, xb, width, height, key, ground=None, y=0.0):
        """Wedge of sand along a wall foot (LOD0/1): against the face, tapering to a toe."""
        if self.lod >= 2 or xb - xa < 0.2:
            return
        rr = random.Random(crc(self.id, "drift", key))
        sg = self.sgn(side)
        zf = self.zface(side)
        n = max(4, int((xb - xa) / (0.25 if self.lod == 0 else 0.6)))
        bm = self.kit.bm
        mi = self.kit.mi("VH_Sand")
        bid = self.kit.new_block(scale=1.0)
        rows = [[], [], []]
        for i in range(n + 1):
            t = i / n
            x = lerp(xa, xb, t)
            env = math.sin(math.pi * t) ** 0.35
            h = height * env * (0.55 + 0.9 * (0.5 + 0.5 * nz(Vector((x, 0, zf)), 1.3, rr.random() * 9)) ** 1.5)
            w = width * env * (0.7 + 0.6 * (0.5 + 0.5 * nz(Vector((x, 0, zf)), 0.9, 4.4)))
            g0 = ground(0.0) if ground else 0.0
            g1 = ground(w * 0.4) if ground else 0.0
            g2 = ground(w) if ground else 0.0
            rows[0].append(bm.verts.new(Vector((x, y + g0 + max(h, 0.004), zf + sg * 0.004))))
            rows[1].append(bm.verts.new(Vector((x, y + g1 + max(h, 0.004) * 0.42, zf + sg * (0.02 + w * 0.4)))))
            rows[2].append(bm.verts.new(Vector((x, y + g2 - 0.004, zf + sg * (0.03 + w)))))
        for r_ in range(2):
            for i in range(n):
                f = bm.faces.new([rows[r_][i], rows[r_][i + 1], rows[r_ + 1][i + 1], rows[r_ + 1][i]])
                f.material_index = mi
                f[self.kit.blk] = bid
                f.normal_update()
                if f.normal.y < 0:
                    f.normal_flip()

    def sand_pocket(self, xa, xb, z, side, height, width, ground=None, y=0.0):
        if self.lod >= 2:
            return
        self.drift(side, xa, xb, width, height, ("pocket", round(xa, 2), round(z, 2)), ground=ground, y=y)

    def foot(self, side, corners, run=None, ground=None):
        """Sand along one foot: a continuous low drift plus deeper pockets against the pier / buttress corners."""
        if self.lod >= 2:
            return
        rr = random.Random(crc(self.id, "foot", side))
        xa, xb = run or (-0.02, self.L + 0.02)
        self.drift(side, xa, xb, 0.34, 0.05, ("run", side), ground=ground)
        for (x, sgn_) in corners:
            w = rr.uniform(0.5, 0.95)
            a, b = (x, x + w) if sgn_ > 0 else (x - w, x)
            self.drift(side, a, b, rr.uniform(0.45, 0.7), rr.uniform(0.1, 0.18), ("corner", side, round(x, 2)), ground=ground)
            if rr.random() < 0.7:
                xm = x + sgn_ * rr.uniform(0.1, 0.35)
                dn = rr.uniform(0.08, 0.2)
                self.weeds.append((xm, ground(dn) if ground else 0.0, self.zface(side) + self.sgn(side) * dn,
                                   rr.choice(("grass", "weed", "grass")), rr.uniform(0.7, 1.15), rr.uniform(0, 360)))

    # ------------------------------------------------------------------ fittings
    def plate(self, side, x, y0, y1, w, horizontal):
        """Riveted steel strap over a crack, with rust runoff below."""
        F = self.F(side)
        if horizontal:
            ua, ub = sorted((self.u_of(side, x - w / 2), self.u_of(side, x + w / 2)))
            ya, yb = y0, y1
        else:
            ua, ub = sorted((self.u_of(side, x - w / 2), self.u_of(side, x + w / 2)))
            ya, yb = y0, y1
        F.box(self.kit, ua, ub, ya, yb, FD + 0.006, FD + 0.02, "VH_PaintedSteel")
        if self.lod == 0:
            rr = random.Random(crc(self.id, "rivets", round(x, 2), round(y0, 2)))
            if horizontal:
                pts = [(lerp(ua + 0.05, ub - 0.05, t / 5), yy) for t in range(6) for yy in (ya + 0.045, yb - 0.045)]
            else:
                pts = [(uu, lerp(ya + 0.05, yb - 0.05, t / 6)) for t in range(7) for uu in (ua + 0.045, ub - 0.045)]
            for (uu, yy) in pts:
                if rr.random() < 0.9:
                    self.kit.sphere(F.P(uu, yy, FD + 0.02), 0.016, "VH_Steel", 6, hemi_axis=tuple(F.n))
        n = (0.0, 0.0, self.sgn(side))
        self.drips.add(n, self.zface(side), x - w / 2, x + w / 2, y0, 1.6, 0.85, "rust", soft=0.1)

    def stitch(self, side, x, y0, y1):
        """An old crack running up through several courses, stitched with short steel staples bolted across it
        (crack = a line of battle-damage weight, which Masonry Lit draws as fine cracking and pitting)."""
        F = self.F(side)
        rr = random.Random(crc(self.id, "stitch", side, round(x, 2)))
        n = max(2, int((y1 - y0) / 0.62))
        pts = []
        cx = x
        for k in range(n + 1):
            y = lerp(y0, y1, k / n)
            pts.append((cx, y))
            cx += rr.uniform(-0.16, 0.16)
        for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
            for t in (0.0, 0.33, 0.66):
                self.scars.impact((lerp(xa, xb, t), lerp(ya, yb, t), self.zface(side)), 0.2, 0.75)
        for k in range(n):
            (xa, ya), (xb, yb) = pts[k], pts[k + 1]
            xm, ym = (xa + xb) / 2, (ya + yb) / 2 + rr.uniform(-0.06, 0.06)
            w = rr.uniform(0.34, 0.46)
            ua, ub = sorted((self.u_of(side, xm - w / 2), self.u_of(side, xm + w / 2)))
            F.box(self.kit, ua, ub, ym - 0.028, ym + 0.028, FD + 0.004, FD + 0.014, "VH_Steel")
            if self.lod == 0:
                for uu in (ua + 0.035, ub - 0.035):
                    self.kit.cyl(F.P(uu, ym, FD + 0.012), F.P(uu, ym, FD + 0.03), 0.014, "VH_Steel", 6)
            n_ = (0.0, 0.0, self.sgn(side))
            self.drips.add(n_, self.zface(side), xm - w / 2, xm + w / 2, ym - 0.03, 0.9, 0.7, "rust", soft=0.08)

    def pattress_plate(self, side, x, y):
        """Cast cross-shaped pattress plate on the end of a tie rod (the wall was tied back after a bulge)."""
        F = self.F(side)
        u = self.u_of(side, x)
        a, t = 0.27, 0.045
        F.box(self.kit, u - a, u + a, y - t, y + t, FD + 0.004, FD + 0.02, "VH_Steel")
        F.box(self.kit, u - t, u + t, y - a, y + a, FD + 0.02, FD + 0.036, "VH_Steel")
        sides = 10 if self.lod == 0 else 6
        self.kit.cyl(F.P(u, y, FD + 0.036), F.P(u, y, FD + 0.075), 0.055, "VH_Steel", sides)
        self.kit.cyl(F.P(u, y, FD + 0.075), F.P(u, y, FD + 0.11), 0.04, "VH_Steel", 6)
        if self.lod == 0:
            self.kit.cyl(F.P(u, y, FD + 0.11), F.P(u, y, FD + 0.15), 0.016, "VH_Steel", 6)
        n_ = (0.0, 0.0, self.sgn(side))
        self.drips.add(n_, self.zface(side), x - 0.12, x + 0.12, y - a, 1.5, 0.8, "rust", soft=0.1)

    def spout(self, side, x, y):
        """Stone water spout through the parapet with a heavy runoff streak below."""
        sg = self.sgn(side)
        z0 = self.zface(side)
        za, zb = sorted((z0 - sg * 0.2, z0 + sg * 0.38))
        self.stone((x - 0.13, y - 0.12, za), (x + 0.13, y + 0.03, zb), "VH_Ashlar", key=("spout", side, round(x, 2)),
                   bev=(0.01, 0.018), chip=0.5)
        # dark channel on top of the spout
        zc0, zc1 = sorted((z0, z0 + sg * 0.38))
        self.kit.box((x - 0.05, y + 0.031, zc0), (x + 0.05, y + 0.036, zc1), "VH_Dark")
        n = (0.0, 0.0, sg)
        self.drips.add(n, z0, x - 0.1, x + 0.1, y - 0.12, 3.4, 0.95, soft=0.16, reach=0.5)

    def hesco_basket(self, x0, x1, z0, z1, y0, h, key):
        rr = random.Random(crc(self.id, "hesco", key))
        bm = self.kit.bm
        mi = self.kit.mi("PW_Hesco")
        bid = self.kit.new_block(scale=1 / 0.9)
        n = 4 if self.lod == 0 else (2 if self.lod == 1 else 1)
        xs = [lerp(x0, x1, i / n) for i in range(n + 1)]
        zs = [lerp(z0, z1, i / n) for i in range(n + 1)]
        ys = [lerp(y0, y0 + h, i / n) for i in range(n + 1)]
        cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
        hx, hz = (x1 - x0) / 2, (z1 - z0) / 2

        def bulge(p):
            t = (p.y - y0) / h
            k = (1 - (2 * t - 1) ** 2) * 0.045
            q = p.copy()
            if abs(p.x - cx) > hx - 1e-4:
                q.x += math.copysign(k, p.x - cx) * (1 - (abs(p.z - cz) / hz) ** 4)
            if abs(p.z - cz) > hz - 1e-4:
                q.z += math.copysign(k, p.z - cz) * (1 - (abs(p.x - cx) / hx) ** 4)
            if t > 0.999:
                q.y -= 0.05 * (1 - max(abs(p.x - cx) / hx, abs(p.z - cz) / hz) ** 2) + rr.uniform(0, 0.015)
            return q
        V = {}

        def v(i, j, k):
            if (i, j, k) not in V:
                V[(i, j, k)] = bm.verts.new(bulge(Vector((xs[i], ys[j], zs[k]))))
            return V[(i, j, k)]
        faces = []
        for j in range(n):
            for i in range(n):
                faces.append([v(i, j, 0), v(i + 1, j, 0), v(i + 1, j + 1, 0), v(i, j + 1, 0)])
                faces.append([v(i, j, n), v(i, j + 1, n), v(i + 1, j + 1, n), v(i + 1, j, n)])
                faces.append([v(0, j, i), v(0, j + 1, i), v(0, j + 1, i + 1), v(0, j, i + 1)])
                faces.append([v(n, j, i), v(n, j, i + 1), v(n, j + 1, i + 1), v(n, j + 1, i)])
        for i in range(n):
            for k in range(n):
                faces.append([v(i, n, k), v(i, n, k + 1), v(i + 1, n, k + 1), v(i + 1, n, k)])
        fs = []
        for q in faces:
            f = bm.faces.new(q)
            f.material_index = mi
            f[self.kit.blk] = bid
            fs.append(f)
        bmesh.ops.recalc_face_normals(bm, faces=fs)
        # soil showing on top
        self.kit.box((x0 + 0.06, y0 + h - 0.06, z0 + 0.06), (x1 - 0.06, y0 + h - 0.02, z1 - 0.06), "VH_Sand")
        if self.lod == 0:
            for sx in (x0, x1):
                for sz in (z0, z1):
                    self.kit.box((sx - 0.012, y0, sz - 0.012), (sx + 0.012, y0 + h + 0.01, sz + 0.012), "VH_Steel")

    def sandbag(self, x, y, z, yaw, key, L=0.58, W=0.34, H=0.15):
        rr = random.Random(crc(self.id, "bag", key))
        bm = self.kit.bm
        mi = self.kit.mi("SD_Sack")
        bid = self.kit.new_block(scale=1 / 0.7)
        nu, nv = (6, 4) if self.lod == 0 else ((3, 2) if self.lod == 1 else (1, 1))
        R = Matrix.Rotation(math.radians(yaw), 3, "Y")
        c = Vector((x, y, z))
        V = {}
        L *= rr.uniform(0.92, 1.06)

        def pt(u, w, top):
            # pillow: rounded plan, domed top, flattened bottom
            px = (u - 0.5) * L
            pz = (w - 0.5) * W
            e = max(abs(2 * u - 1), abs(2 * w - 1))
            pinch = 1 - 0.12 * (abs(2 * u - 1) ** 6)
            pz *= pinch
            h = (H * (1 - 0.55 * e ** 3)) if top else 0.0
            if top and self.lod == 0:
                h += 0.01 * nz(Vector((px + x, pz, z)), 11.0, 3.3)
            return c + R @ Vector((px, h, pz))
        for (i, j) in [(i, j) for i in range(nu + 1) for j in range(nv + 1)]:
            V[(i, j, 1)] = bm.verts.new(pt(i / nu, j / nv, True))
        ring = [(i, 0) for i in range(nu)] + [(nu, j) for j in range(nv)] + [(i, nv) for i in range(nu, 0, -1)] + [(0, j) for j in range(nv, 0, -1)]
        for (i, j) in ring:
            V[(i, j, 0)] = bm.verts.new(pt(i / nu, j / nv, False))
        fs = []
        for i in range(nu):
            for j in range(nv):
                fs.append(bm.faces.new([V[(i, j, 1)], V[(i + 1, j, 1)], V[(i + 1, j + 1, 1)], V[(i, j + 1, 1)]]))
        for k in range(len(ring)):
            a, b = ring[k], ring[(k + 1) % len(ring)]
            fs.append(bm.faces.new([V[(a[0], a[1], 0)], V[(b[0], b[1], 0)], V[(b[0], b[1], 1)], V[(a[0], a[1], 1)]]))
        for f in fs:
            f.material_index = mi
            f[self.kit.blk] = bid
        bmesh.ops.recalc_face_normals(bm, faces=fs)

    def bag_row(self, x0, x1, z, rows, base_fn, key, across=False):
        """Stacked sandbags in running bond along x (tops follow base_fn(x))."""
        rr = random.Random(crc(self.id, "bags", key))
        for r_ in range(rows):
            x = x0 + (0.29 if r_ % 2 else 0.0)
            i = 0
            while x < x1 - 0.2:
                y = base_fn(x) + r_ * 0.14
                self.sandbag(x + 0.29, y, z + rr.uniform(-0.03, 0.03), rr.uniform(-7, 7) + (90 if across else 0), (key, r_, i))
                x += 0.6
                i += 1

    def screen_panel(self, sc):
        """Field repair: welded scrap sheet on two I-beam posts across the gap (outer side)."""
        rr = random.Random(crc(self.id, "screen"))
        z = sc["z"]
        for px in (sc["x0"], sc["x1"]):
            # I-beam post (flanges along x)
            y0, y1 = 0.0 if self.base == "breach" else sc["y0"] - 0.8, sc["y1"] + 0.12
            self.kit.box((px - 0.075, y0, z - 0.1), (px + 0.075, y1, z - 0.088), "VH_PaintedSteel")
            self.kit.box((px - 0.075, y0, z + 0.088), (px + 0.075, y1, z + 0.1), "VH_PaintedSteel")
            self.kit.box((px - 0.006, y0, z - 0.088), (px + 0.006, y1, z + 0.088), "VH_PaintedSteel")
            self.drips.add((0.0, 0.0, -1.0), -self.T / 2, px - 0.1, px + 0.1, y1, 2.0, 0.6, "rust", soft=0.1)
        # overlapping sheets, slightly out of plane, with weld beads (LOD0)
        x = sc["x0"] - 0.08
        k = 0
        while x < sc["x1"] - 0.15:
            w = min(rr.uniform(0.95, 1.4), sc["x1"] + 0.1 - x)
            if sc["x1"] + 0.1 - (x + w) < 0.35:
                w = sc["x1"] + 0.1 - x          # last sheet runs to the end (no sliver, and the loop always advances)
            ya = sc["y0"] + rr.uniform(-0.05, 0.1)
            yb = sc["y1"] - rr.uniform(0.0, 0.25)
            dz = -0.105 - 0.012 * (k % 2)
            bid = self.kit.new_block(scale=1 / 0.7, off=(rr.uniform(0, 5), rr.uniform(0, 5)))
            sheet_mat = ("SD_ScrapSheet", "PW_RustSheet", "PW_Corrugated")[(k + rr.randrange(2)) % 3]
            vs, made = self.kit.box((x, ya, z + dz - 0.006), (x + w, yb, z + dz + 0.006), sheet_mat, bid)
            if self.lod == 0:
                for yy in (ya + 0.04, yb - 0.04):
                    self.kit.box((x + 0.02, yy - 0.012, z + dz - 0.012), (x + w - 0.02, yy + 0.012, z + dz - 0.006), "VH_Steel")
            x += max(0.3, w - 0.07)
            k += 1
        # patched on the city side too: the sheet reads from inside through the gap
        self.drips.add((0.0, 0.0, -1.0), -self.T / 2, sc["x0"], sc["x1"], sc["y0"], 1.2, 0.5, "rust", soft=0.3)

    # ------------------------------------------------------------------ shadow mesh (LOD3)
    def massing(self, xa, xb, ytop, ybot=0.0, z0=None, z1=None):
        """Closed solid of the wall body under the broken top (shadow casting only)."""
        T = self.T
        z0 = -T / 2 if z0 is None else z0
        z1 = T / 2 if z1 is None else z1
        xs = {xa, xb}
        if self.profile:
            xs |= {p[0] for p in self.profile if xa < p[0] < xb}
        xs = sorted(xs)
        tops = [max(ybot + 0.05, min(ytop, self.top_at("in", x) - 0.1) - 0.06) for x in xs]
        z0, z1 = z0 + SH_IN, z1 - SH_IN
        bm = self.mas.bm
        mi = self.mas.mi("PW_Shadow")
        V = lambda x, y, z: bm.verts.new(Vector((x, y, z)))
        fb = [V(x, ybot, z1) for x in xs]
        ft = [V(x, t, z1) for x, t in zip(xs, tops)]
        bb = [V(x, ybot, z0) for x in xs]
        bt = [V(x, t, z0) for x, t in zip(xs, tops)]
        fs = []
        for i in range(len(xs) - 1):
            fs.append(bm.faces.new([fb[i], fb[i + 1], ft[i + 1], ft[i]]))
            fs.append(bm.faces.new([bb[i + 1], bb[i], bt[i], bt[i + 1]]))
            fs.append(bm.faces.new([ft[i], ft[i + 1], bt[i + 1], bt[i]]))
        fs.append(bm.faces.new([bb[0], fb[0], ft[0], bt[0]]))
        fs.append(bm.faces.new([fb[-1], bb[-1], bt[-1], ft[-1]]))
        for f in fs:
            f.material_index = mi

    def sbox(self, lo, hi, inset=None):
        """Shadow-caster box, inset from the visible stone so the lit faces never sit inside their own caster."""
        k = SH_IN if inset is None else inset
        lo = (lo[0] + k, lo[1], lo[2] + k)
        hi = (hi[0] - k, hi[1] - k, hi[2] - k)
        if min(hi[i] - lo[i] for i in range(3)) > 0.02:
            self.mas.box(lo, hi, "PW_Shadow")

    def shadow_ns(self):
        S, L, T = self.S, self.L, self.T
        if self.start == "pier":
            self.pier(0.0)
        self.massing(0.0, L, S["sill"][1])
        wa = self.wx0 if self.start != "end" else 0.0
        wb = self.wx1 if self.end != "end" else L
        self.merlons_ns(wa, wb)

    def shadow_ex(self):
        S, L, T = self.S, self.L, self.T
        gate = self.base == "gate"
        self.massing(0.0, L, S["walk"])
        ipt, opt = S["in_par_t"], S["out_par_t"]
        self.sbox((0.0, S["walk"], T / 2 - ipt), (L, S["in_cope"][1] - 0.05, T / 2 + 0.06))
        self.sbox((0.0, S["walk"], -T / 2 - 0.05), (L, S["sill"][1], -T / 2 + opt))
        # same plan-RNG use as build_ex (inner coping lengths, then merlons)
        r = self.P
        if self.base in ("merlons", "siege"):
            r.random()
        x = 0.0
        while x < L - 0.05:
            ln = r.uniform(0.8, 1.2)
            if L - (x + ln) < 0.4:
                ln = L - x
            x += ln
        if gate:
            self.sbox((0.0, S["out_par"][1], -T / 2 - 0.06), (L, S["out_par"][1] + 0.3, -T / 2 + opt))
        else:
            self.merlons_ex()
        if self.start == "pier":
            self.buttress(0.0)
            self.pilaster_out(0.0, 1.0, 0.14, S["string"][0])

    def shadow_bw(self):
        S, L, T = self.S, self.L, self.T
        self.massing(0.0, L, S["cope"][1] - 0.15, ybot=S["found"], z0=-T / 2 - 0.04, z1=T / 2 + 0.04)
        if self.start == "pier":
            self.pilasters_bw(0.0)

    # ------------------------------------------------------------------ kinds
    def build_ns(self):
        S, L, T = self.S, self.L, self.T
        cs = S["courses"]
        top_body = cs[-1]
        # piers (through-stones, alternating joints) at the start
        if self.start == "pier":
            self.pier(0.0)
        # end faces (corners): quoined columns of through-stones
        pairs = list(zip(cs, cs[1:])) + [S["parapet"]]
        if self.start == "end":
            self.end_column(0.0, +1, pairs)
        if self.end == "end":
            self.end_column(L, -1, pairs)
        xa, xb = self.wx0, self.wx1
        ea = 0.0 if self.start == "end" else None
        eb = L if self.end == "end" else None

        def ulimit(ci, y0, y1):
            a, b = xa, xb
            if ea is not None:
                a = ea + (0.5 if ci % 2 == 0 else 0.26)
            if eb is not None:
                b = eb - (0.5 if ci % 2 == 1 else 0.26)
            return a, b
        for side in ("in", "out"):
            self.courses_face(side, xa, xb, cs, ("body", side), ulimit=ulimit)
            # parapet course between the string course and the sill
            self.courses_face(side, xa, xb, [S["parapet"][0], S["parapet"][1]], ("par", side), rough_first=False,
                              ulimit=lambda ci, y0, y1: ulimit(ci + 1, y0, y1), allow_patch=False)
        # string course: through-stones per ~1 m, drip below on both faces
        self.string_course(xa, xb, S["string"], 0.09)
        # crenel sill / merlons
        wa = xa if ea is None else ea
        wb = xb if eb is None else eb
        self.merlons_ns(wa, wb)
        # weathering: runoff under the string course, sill drips at the crenels
        for side in ("in", "out"):
            n = (0.0, 0.0, self.sgn(side))
            self.drips.add(n, self.zface(side), wa, wb, S["string"][0], 1.4, 0.42, soft=0.3)
            self.drips.add(n, self.zface(side), wa, wb, S["sill"][0] + 0.02, 0.45, 0.32, soft=0.3)
        if self.profile:
            self.core_fill(xa + 0.3, xb - 0.3, S["sill"][0])
        # scars scattered low (both faces), more at the foot
        rr = random.Random(crc(self.id, "scars"))
        for k in range(3):
            side = "in" if k < 2 else "out"
            x = rr.uniform(xa + 0.5, xb - 0.5)
            self.scars.impact((x, rr.uniform(0.5, 3.4), self.zface(side)), rr.uniform(0.45, 0.9), rr.uniform(0.5, 0.8))
        corners = []
        if self.start == "pier":
            corners.append((S["pier_w"] / 2, +1))
        if self.end != "end":
            corners.append((L - S["pier_w"] / 2, -1))
        for side in ("in", "out"):
            self.foot(side, corners, run=(self.wx0 + 0.02, self.wx1 - 0.02))

    def pier(self, x):
        S = self.S
        cs = self.S["courses"]
        hw = S["pier_w"] / 2
        dz = self.T / 2 + S["pier_proj"]
        if self.lod >= 3:
            self.sbox((x - hw, 0.0, -dz), (x + hw, S["pier_top"] + 0.12, dz))
            return
        levels = cs + [S["string"][1], S["parapet"][1], S["sill"][1], S["pier_top"]]
        levels = sorted(set(levels))
        for ci, (y0, y1) in enumerate(zip(levels, levels[1:])):
            rough = ci == 0
            mat = "VH_AshlarRough" if rough else "VH_Ashlar"
            grow = 0.05 if rough else 0.0
            if ci % 2 == 1:
                s = 0.12 if (ci // 2) % 2 else -0.12
                self.stone((x - hw - grow, y0 + J / 2, -dz - grow), (x + s - J / 2, y1 - J / 2, dz + grow), mat, key=("pier", ci, 0),
                           bev=(0.012, 0.024), chip=0.35 if y0 < 2.5 else 0.15)
                self.stone((x + s + J / 2, y0 + J / 2, -dz - grow), (x + hw + grow, y1 - J / 2, dz + grow), mat, key=("pier", ci, 1),
                           bev=(0.012, 0.024), chip=0.35 if y0 < 2.5 else 0.15)
            else:
                self.stone((x - hw - grow, y0 + J / 2, -dz - grow), (x + hw + grow, y1 - J / 2, dz + grow), mat, key=("pier", ci),
                           bev=(0.012, 0.024), chip=0.35 if y0 < 2.5 else 0.15)
        self.core_box((x - hw + 0.025, 0.02, -dz + 0.025), (x + hw - 0.025, S["pier_top"] - 0.01, dz - 0.025))
        # pyramid cap
        y0 = S["pier_top"]
        h = S["pier_cap"]
        rr = random.Random(crc(self.id, "piercap"))
        tops = (0, 0, 0, 0)
        c = [Vector((x - hw - 0.05, y0, -dz - 0.05)), Vector((x + hw + 0.05, y0, -dz - 0.05)), Vector((x + hw + 0.05, y0, dz + 0.05)),
             Vector((x - hw - 0.05, y0, dz + 0.05))]
        bid = self.mas.new_block(tint=stint(rr), erode=0.012)
        vs = [self.mas.bm.verts.new(p) for p in c] + [self.mas.bm.verts.new(p + Vector((0, 0.07, 0))) for p in c]
        apex = self.mas.bm.verts.new(Vector((x + rr.uniform(-0.03, 0.03), y0 + h, rr.uniform(-0.03, 0.03))))
        mi = self.mas.mi("VH_Ashlar")
        fs = [self.mas.bm.faces.new([vs[0], vs[3], vs[2], vs[1]])]
        for i in range(4):
            j = (i + 1) % 4
            fs.append(self.mas.bm.faces.new([vs[i], vs[j], vs[4 + j], vs[4 + i]]))
            fs.append(self.mas.bm.faces.new([vs[4 + i], vs[4 + j], apex]))
        for f in fs:
            f.material_index = mi
            f[self.mas.blk] = bid
        bmesh.ops.recalc_face_normals(self.mas.bm, faces=fs)
        edges = list({e for f in fs for e in f.edges})
        eroded_bevel(self.mas, edges, 0.012, 2, seg_len=0.2 if self.lod == 0 else 0)
        for sgn_ in (1, -1):
            self.drips.add((0.0, 0.0, sgn_), sgn_ * dz, x - hw, x + hw, y0, 2.2, 0.5, soft=0.15)
        for sx in (1, -1):
            self.drips.add((sx, 0.0, 0.0), x + sx * hw, -dz, dz, y0, 2.2, 0.45, soft=0.15)
        if self.var.startswith("merlons") or self.base == "impact":
            self.scars.impact((x + 0.3, 3.0, dz), 0.8, 0.8)

    def end_column(self, x, direction, pairs):
        """Corner end: through-stones (quoins alternately long / short along the faces), per (y0, y1) course."""
        T = self.T
        for ci, (y0, y1) in enumerate(pairs):
            ln = 0.5 if ci % 2 == 0 else 0.26
            a, b = (x, x + ln * direction) if direction > 0 else (x - ln, x)
            a, b = min(a, b), max(a, b)
            rough = ci == 0
            self.stone((a + (J / 2 if direction < 0 else 0), y0 + J / 2, -T / 2), (b - (J / 2 if direction > 0 else 0), y1 - J / 2, T / 2),
                       "VH_AshlarRough" if rough else "VH_Ashlar", key=("end", ci), bev=(0.014, 0.026), chip=0.4)
        xa_, xb_ = sorted((x, x + 0.55 * direction))
        self.core_box((xa_, 0.02, -T / 2 + 0.025), (xb_, pairs[-1][1] - 0.01, T / 2 - 0.025))

    def string_course(self, xa, xb, ys, proj, z0=None, z1=None):
        T = self.T
        z0 = -T / 2 - proj if z0 is None else z0
        z1 = T / 2 + proj if z1 is None else z1
        rr = random.Random(crc(self.id, "string", ys))
        x = xa
        k = 0
        segs = []
        while x < xb - 0.05:
            ln = rr.uniform(0.8, 1.25)
            if xb - (x + ln) < 0.4:
                ln = xb - x
            xm = x + ln / 2
            if self.top_both(x - 0.35, x + ln + 0.35) < ys[1] + 0.05:     # no cantilever over the break
                x += ln
                k += 1
                continue
            # drip moulding: chamfered underside
            self.stone((x + J / 2, ys[0], z0), (x + ln - J / 2, ys[1], z1), "VH_Ashlar", key=("str", ys, k), bev=(0.018, 0.03),
                       chip=0.3)
            segs.append((x, x + ln))
            x += ln
            k += 1
        self.slab_runs(segs, ys[0] + 0.02, ys[1] - 0.02, z0 + 0.03, z1 - 0.03)

    def merlons_ns(self, wa, wb):
        S, T, r = self.S, self.T, self.P
        c, mw = S["crenel"], S["merlon_w"]
        span = wb - wa
        n = max(1, round((span + c) / (mw + c)))
        m = (span - (n - 1) * c) / n
        merl = [(wa + i * (m + c), wa + i * (m + c) + m) for i in range(n)]
        if self.base == "merlons" and n >= 2:
            idx = list(range(n))
            r.shuffle(idx)
            self.merlon_state[idx[0]] = "gone"
            self.merlon_state[idx[1]] = "sheared"
            if n > 2 and r.random() < 0.5:
                self.merlon_state[idx[2]] = "pale"
        # sill: through-stones along the whole parapet top (crenel sills and merlon beds)
        sy0, sy1 = S["sill"]
        x = wa
        k = 0
        segs = []
        while x < wb - 0.05:
            ln = r.uniform(0.7, 1.1)
            if wb - (x + ln) < 0.35:
                ln = wb - x
            xm = x + ln / 2
            if self.top_both(x - 0.35, x + ln + 0.35) > sy1 + 0.02 and self.lod < 3:
                self.stone((x + J / 2, sy0, -T / 2 - 0.05), (x + ln - J / 2, sy1, T / 2 + 0.05), "VH_Ashlar", key=("sill", k),
                           bev=(0.014, 0.026), chip=0.3, tops=(-0.02, -0.02, -0.02, -0.02) if self.lod == 0 else None)
                segs.append((x, x + ln))
            x += ln
            k += 1
        self.slab_runs(segs, sy0 + 0.015, sy1 - 0.04, -T / 2 + 0.01, T / 2 - 0.01)
        my0, my1 = S["merlon"]
        cy0, cy1 = S["cap"]
        for i, (a, b) in enumerate(merl):
            st = self.merlon_state.get(i)
            xm = (a + b) / 2
            if self.top_both(a - 0.35, b + 0.35) < my1 + 0.02:
                continue
            if st == "gone":
                # sockets of the lost merlon: a rough, pitted bed
                self.scars.impact((xm, my0, T / 2), 0.9, 0.9)
                continue
            pale = 1.0 if st == "pale" else 0.0
            split = lerp(a, b, r.uniform(0.38, 0.62))
            if st == "sheared":
                # one stone left, broken off on a slant
                self.stone((a + J / 2, my0 + J / 2, -T / 2), (split - J / 2, my1 - 0.18, T / 2), "VH_Ashlar", key=("mer", i, 0),
                           tops=(0.05, -0.12, -0.02, 0.1), chip=0.9, bev=(0.01, 0.03))
                self.scars.impact((split, my0 + 0.3, T / 2), 0.7, 0.9)
                self.core_box((a + 0.025, my0 + 0.01, -T / 2 + 0.025), (split - 0.025, my1 - 0.24, T / 2 - 0.025))
                continue
            self.core_box((a + 0.025, my0 + 0.01, -T / 2 + 0.025), (b - 0.025, cy0 + 0.02, T / 2 - 0.025))
            self.stone((a + J / 2, my0 + J / 2, -T / 2), (split - J / 2, my1 - J / 2, T / 2), "VH_Ashlar", key=("mer", i, 0), pale=pale,
                       chip=0.3)
            self.stone((split + J / 2, my0 + J / 2, -T / 2), (b - J / 2, my1 - J / 2, T / 2), "VH_Ashlar", key=("mer", i, 1), pale=pale,
                       chip=0.3)
            # saddle cap
            self.stone((a - 0.03, cy0, -T / 2 - 0.035), (b + 0.03, cy1 - 0.05, T / 2 + 0.035), "VH_Ashlar", key=("cap", i),
                       tops=(0.0, 0.0, 0.0, 0.0), pale=pale, chip=0.25, bev=(0.016, 0.03))
            self.saddle((a - 0.03, cy1 - 0.05, -T / 2 - 0.035), (b + 0.03, cy1, T / 2 + 0.035), ("saddle", i), pale)
            for side in ("in", "out"):
                self.drips.add((0.0, 0.0, self.sgn(side)), self.zface(side), a, b, cy0, 0.55, 0.4, soft=0.12)
        # fallen merlon / sill stones at the foot are planned in plan(); nothing else here

    def saddle(self, lo, hi, key, pale=0.0):
        """Ridge on a cap stone (triangular prism along x)."""
        if self.lod >= 3:
            return
        rr = random.Random(crc(self.id, key))
        x0, y0, z0 = lo
        x1, y1, z1 = hi
        bid = self.mas.new_block(tint=stint(rr, False, pale), erode=0.01)
        zc = (z0 + z1) / 2
        verts = [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1), (x0, y1, zc), (x1, y1, zc)]
        faces = [[0, 1, 5, 4], [3, 4, 5, 2], [0, 4, 3], [1, 2, 5], [0, 3, 2, 1]]
        vs, fs = self.mas.closed_solid(verts, faces, "VH_Ashlar", bid)
        edges = [e for e in {e for f in fs for e in f.edges} if e.calc_face_angle(0) > math.radians(20)]
        eroded_bevel(self.mas, edges, 0.01, 2, seg_len=0.2 if self.lod == 0 else 0)

    # ---- EX
    def build_ex(self):
        S, L, T = self.S, self.L, self.T
        cs = S["courses"]
        gate = self.base == "gate"
        pairs = list(zip(cs, cs[1:]))
        if self.start == "end":
            self.end_column(0.0, +1, pairs)
            self.stone((0.0, S["walk"], -T / 2), (0.5, S["in_cope"][1], T / 2), "VH_Ashlar", key="endcap0", chip=0.3)
        if self.end == "end":
            self.end_column(L, -1, pairs)
            self.stone((L - 0.5, S["walk"], -T / 2), (L, S["in_cope"][1], T / 2), "VH_Ashlar", key="endcap1", chip=0.3)
        ea = 0.0 if self.start == "end" else None
        eb = L if self.end == "end" else None

        def ulimit(ci, y0, y1):
            a, b = 0.0, L
            if ea is not None:
                a = ea + (0.5 if ci % 2 == 0 else 0.26)
            if eb is not None:
                b = eb - (0.5 if ci % 2 == 1 else 0.26)
            return a, b
        for side in ("in", "out"):
            self.courses_face(side, 0.0, L, cs, ("body", side), ulimit=ulimit)
        self.string_course(0.0, L, S["string"], 0.08, T / 2 - 0.45, T / 2 + 0.08)
        self.string_course(0.0, L, S["string"], 0.08, -T / 2 - 0.08, -T / 2 + 0.45)
        # inner parapet (plain, coped) and outer parapet (crenellated) with the wall walk between
        ip0, ip1 = S["in_par"]
        ipt = S["in_par_t"]
        op0, op1 = S["out_par"]
        opt = S["out_par_t"]
        self.courses_face("in", 0.0, L, [ip0, ip1], ("ipar", "in"), rough_first=False, ulimit=lambda ci, a, b: ulimit(ci + 1, a, b),
                          allow_patch=False)
        self.courses_face("out", 0.0, L, [op0, op1], ("opar", "out"), rough_first=False, ulimit=lambda ci, a, b: ulimit(ci + 1, a, b),
                          allow_patch=False)
        # walk-side faces of both parapets (seen only from above): plain through-blocks
        self.back_blocks(T / 2 - ipt, +1, S["walk"], ip1, "ib")
        if not gate:
            self.back_blocks(-T / 2 + opt, -1, S["walk"], op1, "ob")
        # inner coping
        r = self.P
        x = 0.0
        k = 0
        c0, c1 = S["in_cope"]
        gone_k = None
        if self.base in ("merlons", "siege"):
            gone_k = 1 + int(r.random() * 3)
        isegs = []
        while x < L - 0.05:
            ln = r.uniform(0.8, 1.2)
            if L - (x + ln) < 0.4:
                ln = L - x
            if k != gone_k:
                self.stone((x + J / 2, c0, T / 2 - ipt - 0.04), (x + ln - J / 2, c1 - 0.06, T / 2 + 0.06), "VH_Ashlar", key=("icope", k),
                           chip=0.3, bev=(0.014, 0.026))
                self.saddle((x + J / 2, c1 - 0.06, T / 2 - ipt - 0.04), (x + ln - J / 2, c1, T / 2 + 0.06), ("icsad", k))
                isegs.append((x, x + ln))
            else:
                self.fallen.append((x + ln / 2, T / 2 + 0.55, (ln * 0.9, 0.24, 0.5), (8, 20, -12), "VH_Ashlar"))
                self.scars.impact((x + ln / 2, c0, T / 2), 0.8, 0.9)
            x += ln
            k += 1
        self.drips.add((0.0, 0.0, 1.0), T / 2, 0.0, L, c0, 0.6, 0.4, soft=0.3)
        self.slab_runs(isegs, c0 + 0.015, c1 - 0.09, T / 2 - ipt - 0.01, T / 2 + 0.02)
        if gate:
            # plain outer coping too (the infill between the gate arches has no merlons)
            self.stone((0.0, op1, -T / 2 - 0.06), (L, op1 + 0.3, -T / 2 + opt), "VH_Ashlar", key="gcope", chip=0.2)
        else:
            self.merlons_ex()
        # wall walk flags (seen from raised views only)
        self.walk(T / 2 - ipt, -T / 2 + opt, S["walk"])
        # buttress on the city face, pilaster outside
        if self.start == "pier":
            self.buttress(0.0)
            self.pilaster_out(0.0, 1.0, 0.14, S["string"][0])
        # spouts at the walk level
        if not gate:
            xs = L * 0.5 + (0.6 if self.var.endswith("b") else -0.4)
            self.spout("out", xs, S["walk"] - 0.02)
            self.spout("in", L * 0.5 - 0.9, S["walk"] - 0.02)
        for side in ("in", "out"):
            n = (0.0, 0.0, self.sgn(side))
            self.drips.add(n, self.zface(side), 0.0, L, S["string"][0], 1.6, 0.42, soft=0.3)
        if self.profile:
            self.core_fill(0.3, L - 0.3, S["string"][0])
        rr = random.Random(crc(self.id, "scars"))
        for k in range(4):
            side = "in" if k < 3 else "out"
            self.scars.impact((rr.uniform(0.5, L - 0.5), rr.uniform(0.6, 5.5), self.zface(side)), rr.uniform(0.5, 1.0), rr.uniform(0.5, 0.85))
        if self.base == "siege":
            self.scars.plume((0.0, 0.0, 1.0), T / 2, 0.8, L - 0.6, 3.6, 3.6, 0.55)
        hw = S["buttress_w"] / 2 + 0.06
        a0 = hw + 0.02 if self.start == "pier" else 0.0
        self.foot("in", [(hw, +1)] if self.start == "pier" else [], run=(a0, L - hw - 0.02))
        self.foot("out", [(0.5, +1)] if self.start == "pier" else [], run=(0.52 if self.start == "pier" else 0.0, L - 0.52))

    def back_blocks(self, z, sgn_, y0, y1, key):
        """Walk-side face of a parapet (plain dressed blocks, LOD1 detail)."""
        # frame plane FD behind the face, normal pointing into the walk
        F = Frame((0.0, 0.0, z + sgn_ * FD), (-sgn_ * 1.0, 0.0, 0.0), (0.0, 0.0, -sgn_))
        rr = random.Random(crc(self.id, key))
        x = 0.0
        k = 0
        lod, layout = WM.S.LOD, WM.S.LAYOUT
        WM.S.LOD = max(1, lod)
        WM.S.LAYOUT = random.Random(crc(self.id, key, "layout"))
        while x < self.L - 0.05:
            ln = rr.uniform(0.7, 1.2)
            if self.L - (x + ln) < 0.35:
                ln = self.L - x
            ua, ub = sorted((-sgn_ * x, -sgn_ * (x + ln)))
            ashlar_block(self.mas, F, ua + J / 2, ub - J / 2, y0 + J / 2, y1 - J / 2, key=(key, k), tint=stint(rr), chip=0.0)
            x += ln
            k += 1
        WM.S.LOD, WM.S.LAYOUT = lod, layout

    def merlons_ex(self):
        S, T, L, r = self.S, self.T, self.L, self.P
        opt = S["out_par_t"]
        per, mw = S["period"], S["merlon_w"]
        z0, z1 = -T / 2, -T / 2 + opt
        # crenel sills along the outer parapet
        sy0, sy1 = S["sill"]
        x = 0.0
        k = 0
        osegs = []
        while x < L - 0.05:
            ln = r.uniform(0.7, 1.1)
            if L - (x + ln) < 0.35:
                ln = L - x
            if self.lod < 3:
                self.stone((x + J / 2, sy0, z0 - 0.05), (x + ln - J / 2, sy1, z1 + 0.04), "VH_Ashlar", key=("osill", k), chip=0.3)
                osegs.append((x, x + ln))
            x += ln
            k += 1
        self.slab_runs(osegs, sy0 + 0.015, sy1 - 0.03, z0 - 0.02, z1 + 0.01)
        n = int(L / per + 0.5)
        merl = []
        for i in range(n):
            c = per * (i + 0.5)
            a, b = c - mw / 2, c + mw / 2
            if b > L - 0.05:
                b = L - 0.05
            if a < 0.05:
                a = 0.05
            if b - a > 0.4:
                merl.append((a, b))
        if self.base in ("merlons", "siege") and merl:
            idx = list(range(len(merl)))
            r.shuffle(idx)
            self.merlon_state[idx[0]] = "gone"
            if len(idx) > 1:
                self.merlon_state[idx[1]] = "sheared"
        if self.base == "repair" and merl:
            self.merlon_state[len(merl) // 2] = "pale"
        my0, my1 = S["merlon"]
        cy0, cy1 = S["cap"]
        for i, (a, b) in enumerate(merl):
            st = self.merlon_state.get(i)
            if st == "gone":
                self.scars.impact(((a + b) / 2, my0, -T / 2), 1.0, 0.95)
                self.fallen.append(((a + b) / 2 + r.uniform(-0.8, 0.8), -T / 2 - r.uniform(0.6, 1.5), (0.55, 0.42, 0.62),
                                    (r.uniform(-12, 12), r.uniform(0, 90), r.uniform(-20, 20)), "VH_Ashlar"))
                continue
            if st == "sheared":
                self.stone((a + J / 2, my0 + J / 2, z0), (b - J / 2, my1 - 0.22, z1), "VH_Ashlar", key=("omer", i), tops=(0.12, -0.08, 0.02, 0.1),
                           chip=0.9, bev=(0.01, 0.03))
                self.scars.impact(((a + b) / 2, my1 - 0.2, -T / 2), 0.8, 0.9)
                continue
            pale = 1.0 if st == "pale" else 0.0
            self.stone((a + J / 2, my0 + J / 2, z0), (b - J / 2, my1 - J / 2, z1), "VH_Ashlar", key=("omer", i), pale=pale, chip=0.3)
            self.core_box((a + 0.025, my0, z0 + 0.025), (b - 0.025, cy0 + 0.02, z1 - 0.025))
            self.stone((a - 0.03, cy0, z0 - 0.035), (b + 0.03, cy1 - 0.04, z1 + 0.035), "VH_Ashlar", key=("ocap", i), pale=pale, chip=0.2)
            self.saddle((a - 0.03, cy1 - 0.04, z0 - 0.035), (b + 0.03, cy1, z1 + 0.035), ("osad", i), pale)
            self.drips.add((0.0, 0.0, -1.0), -T / 2, a, b, cy0, 0.7, 0.4, soft=0.12)
        self.drips.add((0.0, 0.0, -1.0), -T / 2, 0.0, L, sy0, 0.5, 0.3, soft=0.3)

    def walk(self, z_in, z_out, y):
        rr = random.Random(crc(self.id, "walk"))
        x = 0.0
        k = 0
        while x < self.L - 0.05:
            ln = rr.uniform(0.7, 1.1)
            if self.L - (x + ln) < 0.3:
                ln = self.L - x
            zc = lerp(z_out, z_in, rr.uniform(0.35, 0.65))
            for (za, zb) in ((z_out, zc), (zc, z_in)):
                self.stone((x + 0.006, y - 0.12, za + 0.006), (x + ln - 0.006, y, zb - 0.006), "VH_PodiumSlab", key=("walk", k, round(za, 2)),
                           chip=0.0, bev=(0.006, 0.012), seg=0.4)
            x += ln
            k += 1
        self.core_box((0.0, y - 0.15, z_out + 0.01), (self.L, y - 0.115, z_in - 0.01))   # bedding under the slab joints
        if self.lod < 2:
            self.drift_top(z_in, z_out, y)

    def drift_top(self, z_in, z_out, y):
        """Sand along the foot of both parapets on the wall walk."""
        for (z, sgn_) in ((z_in, -1), (z_out, 1)):
            rr = random.Random(crc(self.id, "wtop", z))
            n = 10 if self.lod == 0 else 4
            bm = self.kit.bm
            mi = self.kit.mi("VH_Sand")
            rows = [[], [], []]
            for i in range(n + 1):
                x = self.L * i / n
                h = 0.03 + 0.05 * (0.5 + 0.5 * nz(Vector((x, y, z)), 1.1, 3.0))
                w = 0.2 + 0.25 * (0.5 + 0.5 * nz(Vector((x, y, z)), 0.8, 8.0))
                rows[0].append(bm.verts.new(Vector((x, y + h, z + sgn_ * 0.004))))
                rows[1].append(bm.verts.new(Vector((x, y + h * 0.4, z + sgn_ * w * 0.45))))
                rows[2].append(bm.verts.new(Vector((x, y - 0.004, z + sgn_ * w))))
            for r_ in range(2):
                for i in range(n):
                    f = bm.faces.new([rows[r_][i], rows[r_][i + 1], rows[r_ + 1][i + 1], rows[r_ + 1][i]])
                    f.material_index = mi
                    f.normal_update()
                    if f.normal.y < 0:
                        f.normal_flip()

    def buttress(self, x):
        """Stepped buttress on the city face: plinth, lower stage, sloped weathering, upper stage, sloped cap."""
        S, T = self.S, self.T
        hw = S["buttress_w"] / 2
        zf = T / 2
        if self.lod >= 3:
            self.sbox((x - hw - 0.05, 0.0, zf - 0.1), (x + hw + 0.05, 0.55, zf + 0.68))
            self.sbox((x - hw, 0.55, zf - 0.1), (x + hw, 3.6, zf + 0.56))
            self.sbox((x - hw, 3.6, zf - 0.1), (x + hw, 6.3, zf + 0.38))
            return
        cs = S["courses"]
        stages = [(0.0, 0.55, 0.78), (0.55, 3.34, 0.62), (3.80, 6.10, 0.4)]
        for ci, (y0, y1) in enumerate(zip(cs, cs[1:])):
            if y1 > 6.11:
                break
            proj = 0.68 if y1 <= 0.56 else (0.56 if y1 <= 3.35 else (0.38 if y0 >= 3.79 else None))
            if proj is None:
                # weathering course: sloped top from 0.62 to 0.4
                self.stone((x - hw + J / 2, y0 + J / 2, zf - 0.12), (x + hw - J / 2, y1 - J / 2, zf + 0.56), "VH_Ashlar", key=("bw", ci),
                           tops=(0.0, 0.0, -(y1 - y0) * 0.8, -(y1 - y0) * 0.8), chip=0.3)
                continue
            w = hw + (0.05 if proj > 0.6 else 0.0)
            split = ci % 2 == 1
            mat = "VH_AshlarRough" if ci == 0 else "VH_Ashlar"
            if split:
                s = 0.1 if (ci // 2) % 2 else -0.1
                self.stone((x - w + J / 2, y0 + J / 2, zf - 0.12), (x + s - J / 2, y1 - J / 2, zf + proj), mat, key=("bu", ci, 0), chip=0.3)
                self.stone((x + s + J / 2, y0 + J / 2, zf - 0.12), (x + w - J / 2, y1 - J / 2, zf + proj), mat, key=("bu", ci, 1), chip=0.3)
            else:
                self.stone((x - w + J / 2, y0 + J / 2, zf - 0.12), (x + w - J / 2, y1 - J / 2, zf + proj), mat, key=("bu", ci), chip=0.3)
        for (ya, yb, pj) in ((0.02, 0.55, 0.68), (0.55, 3.34, 0.56), (3.80, 6.1, 0.38)):
            self.core_box((x - hw + 0.03, ya, zf - 0.1), (x + hw - 0.03, yb, zf + pj - 0.03))
        # sloped cap into the wall face
        y0 = 6.10
        self.stone((x - hw - 0.03, y0, zf - 0.12), (x + hw + 0.03, y0 + 0.36, zf + 0.42), "VH_Ashlar", key="bcap",
                   tops=(0.0, 0.0, -0.3, -0.3), chip=0.25)
        self.drips.add((0.0, 0.0, 1.0), zf + 0.38, x - hw, x + hw, y0, 2.4, 0.5, soft=0.12)
        self.drips.add((0.0, 0.0, 1.0), zf + 0.56, x - hw, x + hw, 3.34, 2.8, 0.45, soft=0.12)

    def pilaster_out(self, x, w, proj, ytop):
        hw = w / 2
        z = -self.T / 2
        if self.lod >= 3:
            self.sbox((x - hw, 0.0, z - proj), (x + hw, ytop, z + 0.1))
            return
        cs = [c for c in self.S["courses"] if c <= ytop + 1e-6]
        if cs[-1] < ytop - 0.05:
            cs.append(ytop)
        for ci, (y0, y1) in enumerate(zip(cs, cs[1:])):
            self.stone((x - hw + J / 2, y0 + J / 2, z - proj), (x + hw - J / 2, y1 - J / 2, z + 0.12),
                       "VH_AshlarRough" if ci == 0 else "VH_Ashlar", key=("pil", ci), chip=0.3)
        self.core_box((x - hw + 0.025, 0.02, z - proj + 0.025), (x + hw - 0.025, cs[-1] - 0.01, z + 0.1))

    # ---- BW
    def build_bw(self):
        S, L, T = self.S, self.L, self.T
        cs = S["courses"]
        slope = self.spec.get("outer_slope")
        for side in ("in", "out"):
            courses = ([S["found"], -0.36] + cs[1:]) if side == "out" else ([-0.12] + cs[1:])
            self.courses_face(side, 0.0, L, courses, ("body", side))
        if self.start == "pier":
            self.pilasters_bw(0.0)
        self.coping_bw()
        if self.profile:
            self.core_fill(0.25, L - 0.25, S["cope"][0])
        for side in ("in", "out"):
            n = (0.0, 0.0, self.sgn(side))
            self.drips.add(n, self.zface(side), 0.0, L, S["cope"][0], 1.1, 0.45, soft=0.3)
        rr = random.Random(crc(self.id, "scars"))
        for k in range(3):
            side = "out" if k < 2 else "in"
            self.scars.impact((rr.uniform(0.5, L - 0.5), rr.uniform(0.3, 2.2), self.zface(side)), rr.uniform(0.4, 0.8), rr.uniform(0.5, 0.85))
        hw = S["pil_w"] / 2
        corners = [(hw, +1), (L - hw, -1)] if self.start == "pier" else [(L - hw, -1)]
        self.foot("in", corners, run=(hw + 0.02 if self.start == "pier" else 0.0, L - hw - 0.02))

    def pilasters_bw(self, x):
        S, T = self.S, self.T
        hw = S["pil_w"] / 2
        if self.lod >= 3:
            for sg in (1, -1):
                z0, z1 = sorted((sg * (T / 2 - 0.1), sg * (T / 2 + S["pil_proj"])))
                self.sbox((x - hw, S["found"] if sg < 0 else -0.12, z0), (x + hw, S["pil_top"] + 0.1, z1))
            return
        for side in ("in", "out"):
            sg = self.sgn(side)
            zf = self.zface(side)
            ys = [(S["found"] if side == "out" else -0.12)] + [c for c in S["courses"][1:] if c < S["pil_top"]] + [S["pil_top"]]
            for ci, (y0, y1) in enumerate(zip(ys, ys[1:])):
                z0, z1 = sorted((zf - sg * 0.12, zf + sg * S["pil_proj"]))
                self.stone((x - hw + J / 2, y0 + J / 2, z0), (x + hw - J / 2, y1 - J / 2, z1), "VH_AshlarRough" if ci == 0 else "VH_Ashlar",
                           key=("bpil", side, ci), chip=0.35)
            z0, z1 = sorted((zf - sg * 0.1, zf + sg * (S["pil_proj"] - 0.025)))
            self.core_box((x - hw + 0.025, ys[0] + 0.02, z0), (x + hw - 0.025, S["pil_top"] - 0.01, z1))
            # sloped weathering cap tucked under the coping
            y0 = S["pil_top"]
            z0, z1 = sorted((zf - sg * 0.12, zf + sg * (S["pil_proj"] + 0.03)))
            dy = S["cope"][0] - y0 - 0.01
            tops = (0.0, 0.0, -dy * 0.7, -dy * 0.7) if sg > 0 else (-dy * 0.7, -dy * 0.7, 0.0, 0.0)
            self.stone((x - hw - 0.02, y0, z0), (x + hw + 0.02, y0 + dy, z1), "VH_Ashlar", key=("bpc", side), tops=tops, chip=0.3)
            self.drips.add((0.0, 0.0, sg), zf + sg * S["pil_proj"], x - hw, x + hw, y0, 1.6, 0.45, soft=0.1)

    def coping_bw(self):
        S, T, L, r = self.S, self.T, self.L, self.P
        c0, c1 = S["cope"]
        stones = []
        x = 0.0
        while x < L - 0.05:
            ln = r.uniform(0.85, 1.2)
            if L - (x + ln) < 0.4:
                ln = L - x
            stones.append((x, x + ln))
            x += ln
        if self.base == "coping" and len(stones) > 3:
            k = 1 + int(r.random() * (len(stones) - 3))
            self.cope_state[k] = "gone"
            self.cope_state[k + 1] = "gone" if r.random() < 0.5 else "shift"
            self.cope_state[k - 1] = self.cope_state.get(k - 1, "shift")
        csegs = []
        for i, (a, b) in enumerate(stones):
            st = self.cope_state.get(i)
            xm = (a + b) / 2
            if self.top_both(a - 0.35, b + 0.35) < c1 + 0.02:
                continue
            if st == "gone":
                if self.lod < 3:
                    self.core_top(a, b, c0)
                inside = r.random() < 0.5
                self.fallen.append((xm + r.uniform(-0.5, 0.5), (1 if inside else -1) * (T / 2 + (r.uniform(0.45, 0.65) if inside else r.uniform(0.5, 1.2))),
                                    (b - a, 0.3, 0.9), (r.uniform(-10, 10), r.uniform(0, 60), r.uniform(-25, 25)), "VH_Ashlar"))
                self.scars.impact((xm, c0, T / 2), 0.7, 0.8)
                continue
            rot = None
            lift = 0.0
            if st == "shift":
                rot = (r.uniform(-4, 4), r.uniform(-7, 7), r.uniform(-5, 5))
                lift = 0.02
            pale = 1.0 if st == "pale" else 0.0
            if self.lod >= 3:
                continue
            self.cope_stone(a, b, c0 + lift, c1 + lift, ("cope", i), rot, pale)
            csegs.append((a, b))
        self.slab_runs(csegs, c0 + 0.02, c0 + 0.17, -T / 2 + 0.01, T / 2 - 0.01)
        for side in ("in", "out"):
            self.drips.add((0.0, 0.0, self.sgn(side)), self.zface(side), 0.0, L, c0, 1.0, 0.4, soft=0.3)

    def cope_stone(self, a, b, y0, y1, key, rot=None, pale=0.0):
        T = self.T
        rr = random.Random(crc(self.id, key))
        bid = self.mas.new_block(tint=stint(rr, False, pale), erode=0.01)
        ov = 0.06
        ye = y0 + 0.2
        z0, z1 = -T / 2 - ov, T / 2 + ov
        verts = [(a + J / 2, y0, z0), (b - J / 2, y0, z0), (b - J / 2, y0, z1), (a + J / 2, y0, z1),
                 (a + J / 2, ye, z0), (b - J / 2, ye, z0), (b - J / 2, ye, z1), (a + J / 2, ye, z1),
                 (a + J / 2, y1, 0.0), (b - J / 2, y1, 0.0)]
        if rot is not None:
            ctr = Vector(((a + b) / 2, (y0 + y1) / 2, 0.0))
            R = rot_y(rot[1]) @ Matrix.Rotation(math.radians(rot[0]), 3, "X") @ Matrix.Rotation(math.radians(rot[2]), 3, "Z")
            verts = [tuple(ctr + R @ (Vector(p) - ctr)) for p in verts]
        faces = [[0, 3, 2, 1], [0, 1, 5, 4], [2, 3, 7, 6], [4, 5, 9, 8], [6, 7, 8, 9], [0, 4, 8, 7, 3], [1, 2, 6, 9, 5]]
        vs, fs = self.mas.closed_solid(verts, faces, "VH_Ashlar", bid)
        if self.lod == 0 and rr.random() < 0.5:
            v = rr.choice(vs[4:8])
            v.co.y -= rr.uniform(0.02, 0.05)
        edges = [e for e in {e for f in fs for e in f.edges} if e.calc_face_angle(0) > math.radians(15)]
        eroded_bevel(self.mas, edges, 0.014, 2, seg_len=0.16 if self.lod == 0 else 0)

    def core_top(self, a, b, y):
        """Exposed rubble core where a coping stone is gone."""
        T = self.T
        self.stone((a + 0.02, y - 0.1, -T / 2 + 0.04), (b - 0.02, y - 0.02, T / 2 - 0.04), "VH_AshlarRough", key=("ctop", round(a, 2)),
                   tops=(0.03, -0.02, 0.04, -0.03), chip=0.8, bev=(0.01, 0.03))
        rr = random.Random(crc(self.id, "ctop", round(a, 2)))
        if self.lod < 2:
            for m in range(5 if self.lod == 0 else 2):
                x = rr.uniform(a + 0.1, b - 0.1)
                z = rr.uniform(-T / 2 + 0.2, T / 2 - 0.2)
                s = rr.uniform(0.06, 0.13)
                self.stone((x - s, y - 0.03, z - s), (x + s, y + s * 0.8, z + s), "VH_AshlarRough", key=("ctopst", round(a, 2), m),
                           rot=(rr.uniform(-20, 20), rr.uniform(0, 180), 0), chip=0.6, bev=(0.005, 0.012))
            if self.lod == 0:
                self.weeds.append((rr.uniform(a + 0.2, b - 0.2), y - 0.02, rr.uniform(-0.4, 0.4), "grass", 0.7, rr.uniform(0, 360)))

    # ------------------------------------------------------------------ field repairs
    def bag_stack(self, x0, x1, z, support, y_top, key, across=False, max_rows=8):
        """Sandbags stacked in running bond between x0 and x1, each resting on whatever is highest under its footprint
        (support(x) = rubble / basket / wall top; earlier bags raise it), until the next bag would pass y_top."""
        if self.lod >= 3:
            return
        rr = random.Random(crc(self.id, "stack", key))
        res = 0.04
        n = max(1, int((x1 - x0) / res) + 1)
        xs = [x0 + i * res for i in range(n)]
        hmap = [support(x) for x in xs]
        half = (0.17 if across else 0.29)
        pitch = 0.36 if across else 0.6
        for r_ in range(max_rows):
            x = x0 + half + (pitch / 2 if r_ % 2 else 0.0)
            placed = 0
            while x <= x1 - half + 1e-3:
                i0 = max(0, int((x - half - x0) / res))
                i1 = min(n - 1, int((x + half - x0) / res))
                seg = hmap[i0:i1 + 1]
                y = 0.5 * (max(seg) + sum(seg) / len(seg)) - 0.03     # settles into uneven rubble
                if y + 0.15 <= y_top + 0.02:
                    self.sandbag(x, y, z + rr.uniform(-0.03, 0.03), rr.uniform(-6, 6) + (90 if across else 0), (key, r_, round(x, 2)))
                    for i in range(i0, i1 + 1):
                        hmap[i] = max(hmap[i], y + 0.13)
                    placed += 1
                x += pitch
            if not placed:
                break

    def repairs(self, ground_out=None):
        if self.hesco:
            h = self.hesco
            T = self.T
            # tier 1: three baskets along the gap, two deep (the full wall thickness), on the cleared floor;
            # tier 2: two baskets set back on top; sandbags on the flanks and along the top
            n1 = 3
            w1 = (h["x1"] - h["x0"]) / n1
            zs = [(-T / 2 + 0.04, 0.0), (0.0, T / 2 - 0.04)]
            h1, h2 = 1.3, 1.0
            for i in range(n1):
                for k, (za, zb) in enumerate(zs):
                    self.hesco_basket(h["x0"] + i * w1 + 0.015, h["x0"] + (i + 1) * w1 - 0.015, za + 0.01, zb - 0.01, h["y0"], h1, ("t1", i, k))
            top1 = h["y0"] + h1
            xa2, xb2 = h["x0"] + w1 * 0.45, h["x1"] - w1 * 0.45
            w2 = (xb2 - xa2) / 2
            for i in range(2):
                self.hesco_basket(xa2 + i * w2 + 0.015, xa2 + (i + 1) * w2 - 0.015, -0.48, 0.52, top1 - 0.03, h2, ("t2", i))
            top2 = top1 - 0.03 + h2
            wall_top = self.S["cope"][1] if "cope" in self.S else 3.0
            # bags along the second tier and on the first-tier shoulders beside it (both faces of the stack)
            self.bag_stack(xa2 + 0.05, xb2 - 0.05, 0.0, lambda x: top2 - 0.04, wall_top - 0.05, "top", max_rows=2)
            for (xa, xb, kk) in ((h["x0"] + 0.02, xa2 - 0.02, "l"), (xb2 + 0.02, h["x1"] - 0.02, "r")):
                for zz in (-0.3, 0.3):
                    self.bag_stack(xa, xb, zz, lambda x: top1 - 0.04, wall_top - 0.1, ("fl", kk, zz), across=True)
            self.rec["notes"].append("breach closed: six HESCO baskets (two deep) and a second tier, sandbags on the flanks and "
                                     "top; welded sheet screen on posts outside")
            self.foot_boxes.append(("hesco", h["x0"], h["x1"], -T / 2, T / 2, h["y0"], top2))
        if self.screen:
            self.screen_panel(self.screen)
            sc = self.screen
            self.foot_boxes.append(("screen", sc["x0"] - 0.1, sc["x1"] + 0.1, sc["z"] - 0.12, sc["z"] + 0.12, 0.0, sc["y1"]))
        for (x0, x1, z, y0, rows) in self.bagrows:
            # bags on the broken top: each rests on the highest rubble under it
            def sup(x):
                if self.core_fn is not None:
                    return self.core_fn(x) - 0.03
                return min(self.top_at("in", x), self.top_at("out", x)) - 0.12
            self.bag_stack(x0, x1, z, sup, sup(x0) + rows * 0.14 + 0.6, ("row", x0), max_rows=rows)

    # ------------------------------------------------------------------ build all
    def build(self):
        k = self.kind
        ground_out = PL.berms_ground if self.spec.get("outer_slope") else None
        if self.lod >= 3:
            # shadow caster: massing, piers/buttresses, merlons, cones, fallen blocks, repairs (one material)
            {"NS": self.shadow_ns, "EX": self.shadow_ex}.get(k, self.shadow_bw)()
            if k == "BW":
                self.coping_bw()
            self.fallen_stones(ground_out)       # rubble cones and repairs cast with their own (kit) meshes
            return self.finish()
        if k == "NS":
            self.build_ns()
        elif k == "EX":
            self.build_ex()
        else:
            self.build_bw()
        # damage and repairs
        self.crater_bowls()
        for pl in self.plates:
            self.plate(*pl)
        for st in self.stitches:
            self.stitch(*st)
        for (x, y) in self.pattress:
            for side in ("in", "out"):
                self.pattress_plate(side, x, y)
        for c in self.cones:
            self.cone(c, ground_out if c["side"] == "out" else None)
        self.fallen_stones(ground_out)
        self.repairs(ground_out)
        return self.finish()

    def footprint(self):
        """Plan-view boxes (module local x, z; y range) of everything that stands off the wall faces, for the layout
        check against the scene (pw_validate.py): piers/buttresses, cones, fallen blocks, repairs, drifts."""
        T, S = self.T, self.S
        out = list(self.foot_boxes)
        for c in self.cones:
            sg = self.sgn(c["side"])
            za, zb = sorted((sg * T / 2, sg * (T / 2 + c["out"])))
            out.append(("cone", c["x"] - c["ru"], c["x"] + c["ru"], za, zb, 0.0, c["h"]))
        for (x, z, (sx, sy, sz), rot, mat) in self.fallen:
            if self.base == "siege":
                x = min(max(x, 1.75), self.L - (1.45 if self.start == "pier" else 0.65))
            rad = 0.5 * math.hypot(sx, sz)
            out.append(("fallen", x - rad, x + rad, z - rad, z + rad, 0.0, sy))
        if self.kind == "NS" and self.start == "pier":
            dz = T / 2 + S["pier_proj"]
            out.append(("pier", -S["pier_w"] / 2, S["pier_w"] / 2, -dz, dz, 0.0, S["pier_top"]))
        if self.kind == "EX" and self.start == "pier":
            hw = S["buttress_w"] / 2 + 0.05
            out.append(("buttress", -hw, hw, T / 2, T / 2 + 0.68, 0.0, 6.4))
        if self.kind == "BW" and self.start == "pier":
            hw = S["pil_w"] / 2
            out.append(("pilaster", -hw, hw, -T / 2 - S["pil_proj"], T / 2 + S["pil_proj"], 0.0, S["pil_top"]))
        # sand at both feet (pockets reach ~0.75 m)
        out.append(("sand", 0.0, self.L, T / 2, T / 2 + 0.75, 0.0, 0.2))
        out.append(("sand", 0.0, self.L, -T / 2 - 0.75, -T / 2, 0.0, 0.2))
        return [dict(kind=k_, x=[round(x0, 3), round(x1, 3)], z=[round(z0, 3), round(z1, 3)], y=[round(y0, 3), round(y1, 3)])
                for (k_, x0, x1, z0, z1, y0, y1) in out]

    def finish(self):
        coll = bpy.data.collections.get(f"PW_{self.kind}_LOD{self.lod}")
        parts = [self.mas, self.kit]
        finalize_parts(parts)
        if self.lod >= 3:
            # one opaque object, one material slot: only the shadow map sees it
            bm = bmesh.new()
            for part in parts:
                bm.from_mesh(_tmp_mesh(part))
            for f in bm.faces:
                f.material_index = 0
            for v in bm.verts:
                v.co = WM.U(v.co)
            bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
            bmesh.ops.triangulate(bm, faces=bm.faces[:])
            me = bpy.data.meshes.new(f"{self.id}_Shadow")
            bm.to_mesh(me)
            bm.free()
            me.materials.append(WM.material("PW_Shadow"))
            ob = bpy.data.objects.new(f"{self.id}_Shadow", me)
            coll.objects.link(ob)
            return [ob], []
        samples = (20, 8, 4)[self.lod]
        ao = AOBaker(parts, ground_y=0.0, samples=samples, ground_weight=0.3, strength=0.9, dist=3.0)
        objs = [self.mas.build(coll, ao=ao, drips=self.drips, ground_y=0.0, scars=self.scars, macro=0.1, splash=0.3)]
        if len(self.kit.bm.faces):
            ko = self.kit.build(coll, ao=ao, macro=0.0, splash=0.0)
            # fittings and repairs use URP Lit (ignores vertex colour) or the glTF shader graph (multiplies base colour by
            # it): write the sky occlusion as grey, not the masonry's 0.5-neutral block tint, which halved the HESCO
            col = ko.data.color_attributes.get("Col")
            if col is not None:
                for d in col.data:
                    a = d.color[3]
                    v = 0.38 + 0.62 * a
                    d.color = (v, v, v, a)
            objs.append(ko)
        else:
            self.kit.bm.free()
        cols = []
        if self.lod == 2:
            for i, hull in enumerate(getattr(self, "cones_hull", [])):
                cols.append(hull_object(f"{self.id}_ColCone{i}", hull, coll))
        return objs, cols


def _tmp_mesh(part):
    """A part's bmesh as a throwaway mesh (authoring coordinates, no UVs/colours)."""
    me = bpy.data.meshes.new("tmp")
    part.bm.to_mesh(me)
    part.bm.free()
    return me


def hull_object(name, pts, coll):
    """Low convex hull of the cone points (for a convex MeshCollider in Unity)."""
    bm = bmesh.new()
    for p in pts:
        bm.verts.new(WM.U(p))
        bm.verts.new(WM.U((p[0], min(p[1], 0.0) - 0.05, p[2])))
    bmesh.ops.convex_hull(bm, input=bm.verts)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    me.materials.append(WM.material("PW_Collider"))
    return ob


# ====================================================================== weeds (Poly Haven CC0, LOD0 only)
WEED_SPECIES = {"grass": ("grass_medium_01", ["small_a", "small_b", "mid_b"], 0.3),
                "weed": ("weed_plant_02", ["a", "b", "c"], 0.45)}


def load_weeds():
    src = {}
    for key, (model, variants, ratio) in WEED_SPECIES.items():
        before = set(bpy.data.objects)
        g = next((PH / model).glob("*.gltf"))
        bpy.ops.import_scene.gltf(filepath=str(g))
        objs = [o for o in set(bpy.data.objects) - before if o.type == "MESH"]
        meshes = []
        for v in variants:
            cand = [o for o in objs if o.name.startswith(f"{model}_{v}") and not any(s in o.name for s in ("LOD1", "LOD2", "LOD3"))]
            if not cand:
                continue
            o = sorted(cand, key=lambda o: len(o.name))[0]
            me = o.data.copy()
            me.transform(o.matrix_world)
            xs = [p.co.x for p in me.vertices]
            ys = [p.co.y for p in me.vertices]
            zs = [p.co.z for p in me.vertices]
            me.transform(Matrix.Translation((-(min(xs) + max(xs)) / 2, -(min(ys) + max(ys)) / 2, -min(zs))))
            ob = bpy.data.objects.new("dec", me)
            bpy.context.scene.collection.objects.link(ob)
            for s in bpy.context.selected_objects:
                s.select_set(False)
            ob.select_set(True)
            bpy.context.view_layer.objects.active = ob
            d = ob.modifiers.new("d", "DECIMATE")
            d.ratio = ratio
            d.use_collapse_triangulate = True
            bpy.ops.object.modifier_apply(modifier="d")
            meshes.append(ob.data)
            bpy.data.objects.remove(ob, do_unlink=True)
        for o in objs:
            bpy.data.objects.remove(o, do_unlink=True)
        src[key] = meshes
    return src


def weeds_object(mod, src, coll):
    """All weed tufts of a module in one object (origin at the paving: the ground-cover wind bends by height above it)."""
    if not mod.weeds:
        return None
    bm = bmesh.new()
    slots = []
    for (x, y, z, sp, s, yaw) in mod.weeds:
        me = random.Random(crc(mod.id, round(x, 3), round(z, 3))).choice(src[sp])
        M = Matrix.Translation(WM.U((x, y - 0.02, z))) @ Matrix.Rotation(math.radians(yaw), 4, "Z") @ Matrix.Scale(s, 4)
        tmp = me.copy()
        tmp.transform(M)
        remap = []
        for m in tmp.materials:
            nm = m.name if m else "none"
            if nm not in slots:
                slots.append(nm)
            remap.append(slots.index(nm))
        n0 = len(bm.faces)
        bm.from_mesh(tmp)
        bm.faces.ensure_lookup_table()
        for f in bm.faces[n0:]:
            f.material_index = remap[f.material_index] if f.material_index < len(remap) else 0
        bpy.data.meshes.remove(tmp)
    me = bpy.data.meshes.new(f"{mod.id}_Weeds_LOD0")
    bm.to_mesh(me)
    bm.free()
    for nm in slots:
        me.materials.append(bpy.data.materials.get(nm))
    ob = bpy.data.objects.new(f"{mod.id}_Weeds_LOD0", me)
    coll.objects.link(ob)
    return ob


# ====================================================================== main
def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    kinds = ["NS", "EX", "BW"]
    only = None
    lods = [0, 1, 2, 3]
    if "--kinds" in argv:
        kinds = argv[argv.index("--kinds") + 1].split(",")
    if "--only" in argv:
        only = argv[argv.index("--only") + 1]
    if "--lods" in argv:
        lods = [int(v) for v in argv[argv.index("--lods") + 1].split(",")]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    OUT.mkdir(parents=True, exist_ok=True)
    specs = PL.modules()
    weeds = load_weeds() if 0 in lods else None
    t0 = time.time()
    for kind in kinds:
        report = {"source": "art/perimeter_walls_20261001/author_perimeter_walls.py", "date": "2026-10-01", "kind": kind,
                  "units": "Unity metres, module local (see pw_layout.py)", "modules": {}}
        for lod in lods:
            WM.reset_materials()
            coll = bpy.data.collections.new(f"PW_{kind}_LOD{lod}")
            bpy.context.scene.collection.children.link(coll)
            objs = []
            for mid, spec in sorted(specs.items()):
                if spec["kind"] != kind or (only and only not in mid):
                    continue
                t = time.time()
                m = Module(spec, lod)
                o, cols = m.build()
                wobj = weeds_object(m, weeds, coll) if (lod == 0 and weeds) else None
                allo = o + cols + ([wobj] if wobj else [])
                objs += allo
                rec = report["modules"].setdefault(mid, dict(spec=spec, lods={}))
                rec["lods"][f"LOD{lod}"] = {ob.name: sum(len(p.vertices) - 2 for p in ob.data.polygons) for ob in o}
                if wobj:
                    rec["weeds"] = {"instances": len(m.weeds), "triangles": sum(len(p.vertices) - 2 for p in wobj.data.polygons)}
                if cols:
                    rec["colliders"] = [c.name for c in cols]
                rec["notes"] = m.rec["notes"]
                if lod == 0:
                    rec["footprint"] = m.footprint()
                print(f"{mid} LOD{lod}: {sum(rec['lods'][f'LOD{lod}'].values())} tris ({time.time() - t:.1f} s)", flush=True)
            if objs:
                suffix = f"_{only}" if only else ""
                WM.export(objs, OUT / f"PW_{kind}{suffix}_LOD{lod}.glb")
        if report["modules"] and not only:
            (OUT / f"perimeter-walls-{kind}.json").write_text(json.dumps(report, indent=1))
    if not only:
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE / f"perimeter-walls-{'-'.join(kinds)}.blend"))
    print(f"done in {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
