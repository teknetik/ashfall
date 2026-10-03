"""Ward life pass (3 October 2026), Blender 5.2 headless. Keys:

  bastion   West Gate gun positions rebuilt as real filled gabions (WL_GateBastionS / WL_GateBastionN)
  (props for the Lattice court and Node 07 dock are added by later keys in this file)

Carl's open item after the overnight build: "gabion bastions read as tiled boxes". The round-two bastion
(art/ward_buildings_20261003, gate_bastion) used a flat hessian liner behind a 25 cm wire grid in identical 1 m cells.
Here every basket is a welded-mesh (100 mm) stone gabion: the fill (bake_gabion.py, Masonry Lit so it takes the
per-basket tint, ray-traced occlusion and the old battle damage of the Ward masonry) shows through an alpha-clipped
weathered mesh offset 12 mm in front of it; faces bulge in their lower half and lids sag between the corners; 2 m,
1.5 m and 1 m baskets in a bottom tier and 0.5 m baskets stepped back in a stretcher-bond top tier, each with its own
corner jitter; heavy corner wires and spiral binders at the joints (LOD0). Sandbag courses are draped over whatever is
under them (support heightfield), so they sag into gaps and over the edges. Story per post:
  south (post 1): a top basket blown open long ago, mesh peeled down over the face, fill spilled in a scree on the
                  paving; scorch and shrapnel damage around it; the bags above slump into the gap.
  north (post 2): a bottom basket that burst at its weld line and was patched: its mesh replaced with fresh galvanised
                  panels and paler fill, a strapped steel plate over the worst bulge, the lost top basket replaced
                  by a sandbag course.
The gun platform, pintle weapon, shield, field telephone, plate, props and lamp are the round-two pieces (called from
author_buildings.gate_bastion with its HESCO cells and sack boxes swapped out), so nothing the player already knew
moves. Footprint and colliders stay within the round-two footprint (spawn and gate route untouched).

Run: $O/blender.sh author_life.py -- bastion
Outputs: unity/AthenHill/Assets/AthenHill/Art/WardLife/Models/<Model>_LOD{0,1,2}.glb + <key>.json
"""
import bpy, bmesh, json, math, random, sys
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "art/ward_buildings_20261003"))
import author_buildings as AB
import ward_masonry as WM
from ward_masonry import Part, Frame, stone_tint, drng, export, tri_count
import stones

OUT = ROOT / "unity/AthenHill/Assets/AthenHill/Art/WardLife/Models"
OUT.mkdir(parents=True, exist_ok=True)


# ====================================================================== support heightfield (for draping)
class Support:
    def __init__(self):
        self.boxes = []          # (x0, x1, z0, z1, top)

    def add(self, x0, x1, z0, z1, top):
        self.boxes.append((min(x0, x1), max(x0, x1), min(z0, z1), max(z0, z1), top))

    def at(self, x, z):
        best = 0.0
        for (x0, x1, z0, z1, t) in self.boxes:
            if x0 <= x <= x1 and z0 <= z <= z1 and t > best:
                best = t
        return best

    def smooth(self, x, z, ax, az, reach=0.09):
        """Support under a bag point: averaged along the bag axis (a bag bridges small gaps and droops over edges)."""
        s = 0.0
        for k in (-2, -1, 0, 1, 2):
            s += self.at(x + ax * reach * k / 2, z + az * reach * k / 2) * (1.5 if k == 0 else 1.0)
        return s / 5.5


# ====================================================================== mesh helpers
def grid_surface(part, P, nu, nv, mat, bid, outward):
    """Quad grid over P(u, v) for u, v in [0, 1]; faces turned so their normals agree with outward(u, v)."""
    vs = [[part.bm.verts.new(P(i / nu, j / nv)) for j in range(nv + 1)] for i in range(nu + 1)]
    idx = part.mi(mat)
    fs = []
    for i in range(nu):
        for j in range(nv):
            f = part.bm.faces.new([vs[i][j], vs[i + 1][j], vs[i + 1][j + 1], vs[i][j + 1]])
            f.material_index = idx
            f[part.blk] = bid
            f.normal_update()
            if f.normal.dot(outward((i + 0.5) / nu, (j + 0.5) / nv)) < 0:
                f.normal_flip()
            fs.append(f)
    return fs


def draped_bag(part, support, cx, cz, yaw, mat, lod, L=0.6, W=0.34, H=0.16, seed=0, record=True):
    """A filled sandbag lying along `yaw` (radians about +Y), draped on the support under it; tied ear at one end."""
    rng = random.Random(seed)
    ca, sa = math.cos(yaw), math.sin(yaw)
    nu, nv = (12, 10) if lod == 0 else (5, 6)
    L *= rng.uniform(0.94, 1.05); W *= rng.uniform(0.93, 1.06); H *= rng.uniform(0.9, 1.08)
    ph = rng.uniform(0, 9)
    rows = []
    grounds = [support.smooth(cx + (-1 + 2 * i / nu) * L / 2 * ca, cz + (-1 + 2 * i / nu) * L / 2 * sa, ca, sa) for i in range(nu + 1)]
    for i in range(nu + 1):
        u = -1 + 2 * i / nu
        a = W / 2 * (1 - 0.1 * u ** 4)
        b = H / 2 * max(0.06, (1 - abs(u) ** 3.2)) ** 0.55
        ring = []
        for j in range(nv):
            th = 2 * math.pi * j / nv
            sx = a * math.cos(th)
            st = math.sin(th)
            sy = b + b * st * (0.82 if st > 0 else 0.92)
            lx = u * L / 2 * (1 - 0.04 * (1 - abs(math.cos(th))))
            x = cx + lx * ca - sx * sa
            z = cz + lx * sa + sx * ca
            ground = grounds[i]
            wr = 0.0 if lod > 0 else 0.004 * math.sin(7 * u + ph + 3 * th) * math.sin(5 * th + ph)
            ring.append(part.bm.verts.new((x, ground + sy + wr, z)))
        rows.append(ring)
    idx = part.mi(mat)
    centre = Vector((cx, support.smooth(cx, cz, ca, sa) + H / 2, cz))
    fs = []
    for i in range(nu):
        for j in range(nv):
            k = (j + 1) % nv
            f = part.bm.faces.new([rows[i][j], rows[i + 1][j], rows[i + 1][k], rows[i][k]])
            f.material_index = idx
            fs.append(f)
    for ring, sgn in ((rows[0], -1), (rows[-1], 1)):
        f = part.bm.faces.new(ring if sgn > 0 else ring[::-1])
        f.material_index = idx
        fs.append(f)
    for f in fs:
        f.normal_update()
        if f.normal.dot(f.calc_center_median() - centre) < 0:
            f.normal_flip()
        f.smooth = True
    if lod == 0:
        # tied ear: a flattened, slightly twisted tongue past the +u end
        e0 = Vector((cx + ca * L / 2, 0, cz + sa * L / 2))
        g = support.smooth(e0.x, e0.z, ca, sa)
        side = Vector((-sa, 0, ca))
        tip = e0 + Vector((ca, 0, sa)) * 0.07
        gt = support.smooth(tip.x, tip.z, ca, sa)
        q = [e0 + side * 0.05 + Vector((0, g + H * 0.3, 0)), e0 - side * 0.05 + Vector((0, g + H * 0.3, 0)),
             tip - side * 0.035 + Vector((0, gt + H * 0.12, 0)), tip + side * 0.04 + Vector((0, gt + H * 0.18, 0))]
        vs = [part.bm.verts.new(p) for p in q]
        f = part.bm.faces.new(vs); f.material_index = idx
        vs2 = [part.bm.verts.new(p - Vector((0, 0.004, 0))) for p in q]
        f2 = part.bm.faces.new(vs2[::-1]); f2.material_index = idx
    if record:
        top = support.at(cx, cz) + H * 0.92
        hx, hz = abs(ca) * L / 2 + abs(sa) * W / 2, abs(sa) * L / 2 + abs(ca) * W / 2
        support.add(cx - hx * 0.9, cx + hx * 0.9, cz - hz * 0.9, cz + hz * 0.9, top)


def helix(part, x, z, y0, y1, r=0.011, pitch=0.075, wire=0.0025, mat="VH_Steel"):
    n = int((y1 - y0) / pitch * 8)
    pts = [Vector((x + r * math.cos(k * math.pi / 4), y0 + (y1 - y0) * k / n, z + r * math.sin(k * math.pi / 4))) for k in range(n + 1)]
    for a, b in zip(pts, pts[1:]):
        part.cyl(a, b, wire, mat, 4, cap=False)


# ====================================================================== the gabion basket
class Basket:
    """One welded-mesh gabion: x0..x1 along the run, z0..z1 depth (z1 = street face), y0..y1 height.
    faces: which faces exist ('front', 'back', 'left', 'right', 'top'); bulge in metres; wire 'old' | 'fresh' | None."""

    def __init__(self, x0, x1, z0, z1, y0, y1, faces=("front", "left", "right", "top"), bulge=0.045, sag=0.025,
                 wire="old", tint=None, seed=0):
        self.x0, self.x1, self.z0, self.z1, self.y0, self.y1 = x0, x1, z0, z1, y0, y1
        self.faces, self.bulge, self.sag, self.wire, self.tint, self.seed = faces, bulge, sag, wire, tint, seed
        rr = random.Random(seed)
        j = lambda: rr.uniform(-0.012, 0.012)
        # corner jitter (x, z at the top four corners); bottoms sit on what is below
        self.cj = [(j(), j()) for _ in range(4)]
        self.slump = []            # extra face deformations: (face, fn(u, v) -> outward offset)

    def corner(self, k, top):
        xs = (self.x0, self.x1, self.x1, self.x0)
        zs = (self.z0, self.z0, self.z1, self.z1)
        dx, dz = self.cj[k] if top else (0.0, 0.0)
        return Vector((xs[k] + dx, self.y1 if top else self.y0, zs[k] + dz))

    def face_fn(self, name):
        """(P(u, v) on the undisplaced face, outward normal, u-length, v-length, bulge weight)"""
        c = [self.corner(k, False) for k in range(4)]
        t = [self.corner(k, True) for k in range(4)]
        def bil(a, b, ta, tb):
            return lambda u, v: (a.lerp(b, u)).lerp(ta.lerp(tb, u), v)
        if name == "front":
            return bil(c[3], c[2], t[3], t[2]), Vector((0, 0, 1)), self.x1 - self.x0
        if name == "back":
            return bil(c[1], c[0], t[1], t[0]), Vector((0, 0, -1)), self.x1 - self.x0
        if name == "left":
            return bil(c[0], c[3], t[0], t[3]), Vector((-1, 0, 0)), self.z1 - self.z0
        if name == "right":
            return bil(c[2], c[1], t[2], t[1]), Vector((1, 0, 0)), self.z1 - self.z0
        if name == "top":
            return (lambda u, v: t[3].lerp(t[2], u).lerp(t[0].lerp(t[1], u), v)), Vector((0, 1, 0)), self.x1 - self.x0
        raise KeyError(name)

    def disp(self, name, u, v, n):
        """Bulge: sides push out in the lower half; lids dip between the corners."""
        if name == "top":
            d = -self.sag * math.sin(math.pi * u) * math.sin(math.pi * v)
            return n * d
        h = self.y1 - self.y0
        w = math.sin(math.pi * u) ** 0.8 * math.sin(math.pi * min(1.0, v * 1.15)) ** 0.7 * (1.0 - 0.45 * v)
        b = self.bulge * (0.6 if h < 0.6 else 1.0)
        d = b * w
        for (fname, fn) in self.slump:
            if fname == name:
                d += fn(u, v)
        # top edge sags a little between the corners
        dy = -self.sag * 0.6 * math.sin(math.pi * u) * smooth01((v - 0.75) / 0.25)
        return n * d + Vector((0, dy, 0))

    def build(self, B, lod):
        """B: builder with parts fill (masonry), wire (alpha), steel (frame) and the support field."""
        rr = random.Random(self.seed + 1)
        tint = self.tint or stone_tint("rough", 0.09)
        fillmat = "WL_GabionFill" if lod == 0 else "WL_GabionFillWired"
        wiremat = "WL_GabionWireFresh" if self.wire == "fresh" else "WL_GabionWire"
        step = 0.16 if lod == 0 else 0.5
        for name in self.faces:
            P0, n, ulen = self.face_fn(name)
            vlen = (self.z1 - self.z0) if name == "top" else (self.y1 - self.y0)
            nu = max(1, round(ulen / step)); nv = max(1, round(vlen / step))
            if lod == 0:
                nu += 1; nv += 1
            def P(u, v, off=0.0, P0=P0, n=n, name=name):
                p = P0(u, v) + self.disp(name, u, v, n)
                if lod == 0 and off == 0.0 and 0 < u < 1 and 0 < v < 1:
                    p += n * 0.006 * WM.nz(p, 9.0, self.seed % 97)
                return p + n * off
            bid = B.fill.new_block(tint=tint)
            grid_surface(B.fill, P, nu, nv, fillmat, bid, lambda u, v, n=n: n)
            if lod == 0 and self.wire and not (name == "front" and not getattr(self, "wire_front", True)):
                # mesh grid aligned to the basket's own corner (UV = box projection in metres + offset)
                c0 = P0(0, 0)
                if name == "front":   ou, ov = -c0.x, -c0.y
                elif name == "back":  ou, ov = c0.x, -c0.y
                elif name == "left":  ou, ov = -c0.z, -c0.y
                elif name == "right": ou, ov = c0.z, -c0.y
                else:                 ou, ov = -c0.x, c0.z
                wb = B.wire.new_block(off=(ou, ov))
                grid_surface(B.wire, lambda u, v, P=P: P(u, v, 0.012), nu, nv, wiremat, wb, lambda u, v, n=n: n)
        if lod == 0 and self.wire:
            # heavy wire on every edge of the basket
            c = [self.corner(k, False) for k in range(4)]
            t = [self.corner(k, True) for k in range(4)]
            for k in range(4):
                B.steel.cyl(c[k], t[k], 0.0045, "VH_Steel", 4, cap=False)
                B.steel.cyl(t[k], t[(k + 1) % 4], 0.0045, "VH_Steel", 4, cap=False)
        B.support.add(self.x0, self.x1, self.z0, self.z1, self.y1 - self.sag * 0.5)


def smooth01(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


class Builder:
    def __init__(self, r, lod):
        self.r, self.lod = r, lod
        self.fill = r.mas
        self.wire = Part(r.name + "_Wire_LOD%d" % lod, wear=False)
        self.steel = r.hard
        self.support = Support()


# ====================================================================== the bastion
def bastion(lod, side=1):
    """side +1 = south post (gate at local +X), -1 = north post."""
    S = side
    ZW = -1.95
    name = "WL_GateBastionS" if S > 0 else "WL_GateBastionN"
    saved = (AB.hesco_cell, AB.sandbag)
    holder = {}

    def no_cell(*a, **k):
        return None

    def bag_proxy(part, c, yaw, L=0.62, W=0.34, H=0.17, mat="WG_Hessian"):
        B = holder["B"]
        rng = drng("platformbag", round(c[0], 2), round(c[1], 2), round(c[2], 2))
        draped_bag(part, B.support, c[0], c[2], yaw + rng.uniform(-0.05, 0.05),
                   rng.choice(("WG_Hessian", "WL_HessianOld", "WL_HessianPale")), lod, L, W, H * 0.95, seed=rng.randrange(1 << 20))

    # The round-two gate_bastion builds the gun position; its cells and sack boxes are swapped for ours. It creates its
    # Ruin first, so the builder is attached through a tiny shim on Ruin.__init__.
    orig_init = AB.Ruin.__init__

    def init_shim(self, nm, lod_, tint, seed):
        orig_init(self, nm, lod_, tint, seed)
        holder["B"] = Builder(self, lod_)
        build_baskets(self, holder["B"], lod_, S, ZW)

    AB.hesco_cell, AB.sandbag = no_cell, bag_proxy
    AB.Ruin.__init__ = init_shim
    try:
        r = AB.gate_bastion(lod, side)
    finally:
        AB.hesco_cell, AB.sandbag = saved
        AB.Ruin.__init__ = orig_init
    B = holder["B"]
    r.name = name
    finish_bastion(r, B, lod, S, ZW)
    return r, B


def build_baskets(r, B, lod, S, ZW):
    rr = drng("bastion-life", S)
    D0, D1 = ZW + 0.05, ZW + 1.05          # back row depth
    X = lambda x: x * S
    def run(lengths, start, z0, z1, y0, y1, gap=0.025):
        out, x = [], start
        for L in lengths:
            out.append((x, x + L - gap))
            x += L
        return [(min(X(a), X(b)), max(X(a), X(b)), z0, z1, y0, y1) for a, b in out]
    bottom = run([2.0, 1.0, 1.5, 1.5], -3.0, D0, D1, 0.0, 1.0)
    top = run([1.0, 2.0, 1.5, 1.5], -3.0, D0, D1 - 0.1, 1.0, 1.5)
    baskets = []
    for i, (x0, x1, z0, z1, y0, y1) in enumerate(bottom):
        kw = dict(faces=("front", "left", "right", "top"), bulge=rr.uniform(0.035, 0.06), sag=0.02, seed=100 + i + 10 * (S > 0))
        if S < 0 and i == 1:          # north post: the burst basket, re-meshed with fresh panels and paler fill
            kw.update(wire="fresh", bulge=0.075, tint=(0.6, 0.58, 0.55))
        baskets.append(Basket(x0, x1, z0, z1, y0, y1, **kw))
    for i, (x0, x1, z0, z1, y0, y1) in enumerate(top):
        if S < 0 and i == 1:
            continue                  # north: lost top basket, replaced by a sandbag course (below)
        kw = dict(faces=("front", "left", "right", "top"), bulge=rr.uniform(0.02, 0.035), sag=0.03, seed=200 + i + 10 * (S > 0))
        b = Basket(x0, x1, z0, z1, y0, y1, **kw)
        if S > 0 and i == 0:          # south: the blown basket, emptied to a low slumped heap, front mesh gone
            b.y1 = 1.24
            b.faces = ("left", "right", "top", "front")
            b.wire = "old"
            b.slump.append(("front", lambda u, v: 0.16 * (1 - v) * math.sin(math.pi * u) ** 0.6))
            b.blown = True
        baskets.append(b)
    # return at the gate end: two bottom cells toward the street, a top basket on the outer one
    xa, xb = sorted((X(2.0), X(3.0)))
    for k, (z0, z1) in enumerate(((ZW + 1.08, ZW + 2.12), (ZW + 2.15, ZW + 3.19))):
        baskets.append(Basket(xa + 0.01, xb - 0.01, z0, z1, 0.0, 1.0, faces=("front", "left", "right", "top") if k else ("left", "right", "top"),
                              bulge=rr.uniform(0.04, 0.06), seed=300 + k + 10 * (S > 0)))
    baskets.append(Basket(xa + 0.06, xb - 0.06, ZW + 2.2, ZW + 3.12, 1.0, 1.5, bulge=0.03, sag=0.03, seed=320 + (S > 0)))
    for b in baskets:
        if getattr(b, "blown", False) and lod == 0:
            b.wire_front = False
        b.build(B, lod)
    B.baskets = baskets
    # spiral binders up the joints between neighbouring baskets (street face, LOD0)
    if lod == 0:
        for (x0, x1, z0, z1, y0, y1) in bottom[:-1] + top[:-1]:
            xe = x1 + 0.0125 if S > 0 else x1 + 0.0125
            helix(B.steel, xe, z1 - 0.01, y0 + 0.02, y1 - 0.03)
    # battle damage and scorch on the fill around the old blast (south) / the burst (north)
    if S > 0:
        r.scars.impact((X(-2.5), 1.2, D1), 1.3, 1.0)
        r.scars.impact((X(-0.4), 0.6, D1), 0.6, 0.7)
    else:
        r.scars.impact((X(-0.5), 0.5, D1), 0.9, 0.8)
        r.scars.impact((X(2.5), 1.1, ZW + 3.2), 0.5, 0.6)


def finish_bastion(r, B, lod, S, ZW):
    D1 = ZW + 1.05
    X = lambda x: x * S
    rr = drng("bastion-finish", S)
    sup = B.support
    # sandbag parapet: two courses along the top tier's street edge (stretcher bond)
    bags = ("WG_Hessian", "WL_HessianOld", "WL_HessianPale")
    for course in range(2):
        x = -2.95 + (0.3 if course else 0.0)
        while x < 2.65:
            cz = D1 - 0.38 + rr.uniform(-0.03, 0.03)
            draped_bag(r.canvas, sup, X(x), cz, rr.uniform(-0.05, 0.05), rr.choice(bags), lod, seed=rr.randrange(1 << 20))
            x += 0.6
    if S < 0:
        # north: the lost top basket replaced by three courses of bags laid as headers and stretchers
        for course in range(3):
            z = ZW + 0.2
            while z < D1 - 0.15:
                x = -1.68 + (0.3 if course % 2 else 0.0)
                while x < -0.25:
                    draped_bag(r.canvas, sup, X(x), z, rr.uniform(-0.06, 0.06), rr.choice(bags), lod, seed=rr.randrange(1 << 20))
                    x += 0.6
                z += 0.33
        # strapped steel plate over the worst of the bulge, two ratchet straps round the basket
        pz = D1 + 0.09
        xa, xb = sorted((X(-0.85), X(-0.2)))
        r.metal.box((xa, 0.18, pz), (xb, 0.78, pz + 0.008), "WG_PlateSteel")
        for y in (0.32, 0.64):
            xa, xb = sorted((X(-1.02), X(0.02)))
            r.metal.box((xa, y - 0.025, pz + 0.008), (xb, y + 0.025, pz + 0.014), "WS_PaintYellow")
    # return top: one course of bags
    xa, xb = sorted((X(2.0), X(3.0)))
    for k in range(3):
        draped_bag(r.canvas, sup, (xa + xb) / 2 + rr.uniform(-0.04, 0.04), ZW + 2.35 + k * 0.36, math.pi / 2 + rr.uniform(-0.06, 0.06),
                   rr.choice(bags), lod, seed=rr.randrange(1 << 20))
    if S > 0:
        blown(r, B, lod, X, ZW)
    # wall-foot sand along the street face (no collider), heavier at the inside corner by the return
    for (x, rx, rz, h) in ((-2.0, 1.4, 0.28, 0.07), (0.3, 1.1, 0.22, 0.05), (1.6, 0.6, 0.3, 0.09)):
        r.mound((X(x), 0.0, D1 + 0.08), rx, rz, h)


def blown(r, B, lod, X, ZW):
    """South post: the blown top basket at x -3..-2: front mesh peeled down over the bottom basket, fill spilled."""
    D1 = ZW + 1.05
    rr = random.Random(5150)
    # peeled mesh flap: hinged at the top of the bottom basket, hanging down its face and curling out at the tear
    if lod == 0:
        x0, x1 = sorted((X(-2.97), X(-2.05)))
        wb = B.wire.new_block(off=(-x0, 0.0))
        idx = B.wire.mi("WL_GabionWire")
        n_u, n_v = 9, 5
        def fp(i, j):
            u, v = i / n_u, j / n_v                       # v from the hinge down
            y = 1.0 - 0.46 * v + 0.03 * math.sin(5 * u + 1)
            z = D1 + 0.045 + 0.16 * v ** 2 + 0.025 * math.sin(7 * u) * v
            return Vector((x0 + (x1 - x0) * u, y, z))
        vs = [[B.wire.bm.verts.new(fp(i, j)) for j in range(n_v + 1)] for i in range(n_u + 1)]
        for i in range(n_u):
            for j in range(n_v):
                if j >= n_v - 2 and rr.random() < 0.45 * (j - n_v + 3) / 2:
                    continue                                  # ragged torn edge
                f = B.wire.bm.faces.new([vs[i][j], vs[i + 1][j], vs[i + 1][j + 1], vs[i][j + 1]])
                f.material_index = idx; f[B.wire.blk] = wb
                f.normal_update()
                if f.normal.z < 0:
                    f.normal_flip()
    # spilled fill: a scree from the breach down over the face and out onto the paving
    n = 90 if lod == 0 else 22
    for k in range(n):
        t = rr.random() ** 0.7
        x = X(rr.uniform(-2.95, -1.75) + rr.gauss(0, 0.12))
        z = D1 + 0.06 + t * rr.uniform(0.25, 0.85)
        s = rr.uniform(0.07, 0.2) * (1.1 - 0.4 * t)
        if lod > 0 and s < 0.13:
            continue
        y = max(0.0, 0.18 * (1 - t) - 0.02) + s * 0.25
        bid = r.rub.new_block(tint=stone_tint("rough", 0.12))
        faces = stones.add_stone(r.rub.bm, (x, y, z), s, rr, subdiv=2 if lod == 0 else 1, flatten_up=(0, 1, 0))
        mi = r.rub.mi("VH_AshlarRough")
        for f in faces:
            f.material_index = mi; f[r.rub.blk] = bid
    r.mound((X(-2.35), 0.0, D1 + 0.35), 0.75, 0.45, 0.16)


def bastion_finish_objs(r, B, lod):
    B.wire.finalize()
    objs = r.finish()
    if len(B.wire.bm.faces):
        objs.append(B.wire.build(r.coll, flat=False))
    for o in objs:
        o.name = o.name.replace("GateBastionN_", r.name + "_").replace("GateBastion_", r.name + "_")
    r.rec["triangles"] = tri_count(objs)
    r.rec["objects"] = {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs}
    return objs


def bastion_lod2(side):
    name = "WL_GateBastionS" if side > 0 else "WL_GateBastionN"
    WM.set_state(2, random.Random(52), name + "_l2")
    coll = bpy.data.collections.new(name + "_LOD2")
    bpy.context.scene.collection.children.link(coll)
    mt = Part(name + "_Fill_LOD2", False)
    mt.box((-3.0, 0.0, -1.95), (3.0, 1.75, -0.9), "WL_GabionFillWired")
    xa, xb = sorted((side * 2.0, side * 3.0))
    mt.box((xa, 0.0, -0.9), (xb, 1.5, 1.24), "WL_GabionFillWired")
    mt.finalize()
    return [mt.build(coll, flat=True)]


def run_bastion(side):
    key = "bastion_s" if side > 0 else "bastion_n"
    report = {"source": "art/ward_life_20261003/author_life.py", "date": "2026-10-03", "key": key,
              "units": "Unity metres local to the bastion root (street-face centre, +Z street, rampart face at z -1.95)", "lods": {}}
    for lod in (0, 1):
        r, B = bastion(lod, side)
        objs = bastion_finish_objs(r, B, lod)
        export(objs, OUT / f"{r.name}_LOD{lod}.glb")
        report["lods"][f"LOD{lod}"] = {"triangles": r.rec["triangles"], "objects": r.rec["objects"]}
        if lod == 0:
            rec = {k: v for k, v in r.rec.items() if k not in ("triangles", "objects")}
            ZW = -1.95
            S = side
            rec["mounts"] = [m for m in rec["mounts"] if not m["name"].startswith("Sandbags on the back row")]
            for m in rec["mounts"]:
                if m["name"] == "Binoculars":
                    m["pos"] = [S * 2.45, 1.47, ZW + 2.95]
            for c in rec["colliders"]:
                if c["name"] == "COL_BackRow":
                    c["center"], c["size"] = [0.0, 0.92, ZW + 0.57], [6.0, 1.84, 1.12]
                if c["name"] == "COL_Return":
                    c["center"], c["size"] = [S * 2.5, 0.78, ZW + 2.13], [1.0, 1.56, 2.12]
            rec["notes"] = [f"WL gate bastion side {side}: welded-mesh stone gabions (2/1.5/1 m bottom tier, 0.5 m top tier), draped sandbags, "
                            + ("blown top basket with spilled fill" if side > 0 else "burst basket re-meshed, plate patch, lost top basket replaced by bags")]
            report.update(rec)
            model = r.name
        print(f"{r.name} LOD{lod}: {r.rec['triangles']} triangles", flush=True)
    objs = bastion_lod2(side)
    export(objs, OUT / f"{model}_LOD2.glb")
    report["lods"]["LOD2"] = {"triangles": tri_count(objs)}
    (OUT / f"{key}.json").write_text(json.dumps(report, indent=1))
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / f"{key}-source.blend"))



# ====================================================================== Lattice court: the water ration point
# The court behind Vanguard Hall where the old Lattice Jack stood. Purpose: Ward's daily water ration. The city lives
# on its aquifer (lore.md), and "keeping the aquifers and markets safe" is the Wardens' quiet duty, so the hall's
# Wardens run a ration tap here under the existing Lattice court sail: a header tank against the south wall (filled
# from AQUIFER 3, stencilled so), its main under riveted trench covers to a four-tap stand over a stone trough, a
# Warden's tally desk with the ration ledger, a ration board, and (placed in Unity) the cans and carts of the queue.
# Coordinates: Unity metres local to the model root, which sits at world (1.9, 0, -34.5), yaw 0.
WP_ORIGIN = (1.9, 0.0, -34.5)


def _L(x, y, z, o=WP_ORIGIN):
    return (x - o[0], y - o[1], z - o[2])


def water_point(lod):
    r = AB.Ruin("WL_WaterPoint", lod, (1.0, 0.96, 0.9), 7300)
    if lod > 0:
        r.stencil = lambda *a, **k: None          # painted text is unreadable beyond the LOD1 cut
    r.pod = r.mas
    m, hd = r.metal, r.hard
    rng = random.Random(7301)
    # header tank on its stone plinth against the south wall, ladder to the north-west, a riveted patch on the face
    tx, tz = _L(1.9, 0, -41.45)[0], _L(1.9, 0, -41.45)[2]
    AB.riveted_tank(r, tx, tz, 0.95, 1.9, "WB_TankBone", plinth_h=0.7, patched=True, ladder_a=math.pi * 0.78, lod=lod)
    # riveted ID plate on stand-offs (flat text would sink into the curved shell)
    m.box((tx - 0.34, 1.12, tz + 0.955), (tx + 0.34, 1.56, tz + 0.975), "WB_PaintBone")
    for (px_, py_) in ((-0.3, 1.16), (0.3, 1.16), (-0.3, 1.52), (0.3, 1.52)):
        hd.sphere((tx + px_, py_, tz + 0.975), 0.012, "VH_Steel", 5, hemi_axis=(0, 0, 1))
    Ft = Frame((tx, 0, tz + 0.978), (1, 0, 0), (0, 0, 1))
    r.stencil("AQUIFER 3", Ft, tx, 1.42, 0.12, 0.58, 0.0, mat="VH_Dark")
    r.stencil("RATION TANK", Ft, tx, 1.24, 0.075, 0.58, 0.0, mat="WS_PaintRed")
    # feed from the aquifer main along the wall foot (from the west), into the tank's side
    m.tube([_L(-6.5, 0.32, -43.05), _L(0.6, 0.32, -43.05), _L(1.2, 0.32, -42.6), _L(1.2, 1.1, -42.35)], 0.055, "WB_PipeTeal", 10)
    for x in (-5.5, -3.5, -1.5, 0.3):
        m.box(_L(x - 0.04, 0.0, -43.2), _L(x + 0.04, 0.32, -42.95), "WB_BlackSteel")        # pipe saddles
    # outlet: elbow out of the tank's north face, gate valve with hand wheel, down into the trench
    ox, oz = _L(1.9, 0, -40.38)[0], _L(1.9, 0, -40.38)[2]
    m.tube([(ox, 0.85, oz - 0.15), (ox, 0.85, oz + 0.2), (ox, 0.02, oz + 0.2)], 0.05, "WB_PipeTeal", 10)
    m.cyl((ox, 0.5, oz + 0.2), (ox, 0.62, oz + 0.2), 0.085, "WB_BlackSteel", 10)
    m.cyl((ox, 0.62, oz + 0.2), (ox, 0.8, oz + 0.2), 0.012, "VH_Steel", 6)
    wheel = [(ox + 0.13 * math.cos(a * math.pi / 6), 0.8, oz + 0.2 + 0.13 * math.sin(a * math.pi / 6)) for a in range(13)]
    m.tube(wheel, 0.01, "WS_PaintRed", 5)
    # trench covers: riveted plates flush with the paving from the tank to the tap stand (the main is buried)
    z = -40.15
    k = 0
    while z < -29.75:
        z1 = min(z + 0.6, -29.75)
        mat = "WG_RustSteel" if rng.random() < 0.35 else "WG_PlateSteel"
        m.box(_L(1.68, -0.01, z + 0.01), _L(2.12, 0.009, z1 - 0.01), mat)
        if lod == 0:
            for (dx, dz) in ((-0.17, 0.05), (0.17, 0.05), (-0.17, z1 - z - 0.07), (0.17, z1 - z - 0.07)):
                hd.sphere(_L(1.9 + dx, 0.009, z + dz), 0.011, "VH_Steel", 5, hemi_axis=(0, 1, 0))
        z = z1
        k += 1
    # stone trough (drained between rations; damp floor), drain grate in front
    tr = dict(x0=0.35, x1=3.45, z0=-29.25, z1=-28.55, h=0.5, t=0.1)
    X0, X1 = _L(tr["x0"], 0, 0)[0], _L(tr["x1"], 0, 0)[0]
    Z0, Z1 = _L(0, 0, tr["z0"])[2], _L(0, 0, tr["z1"])[2]
    T = tr["t"]
    for (c, sz) in ((((X0 + X1) / 2, tr["h"] / 2, Z0 + T / 2), (X1 - X0, tr["h"], T)),
                    (((X0 + X1) / 2, tr["h"] / 2, Z1 - T / 2), (X1 - X0, tr["h"], T)),
                    ((X0 + T / 2, tr["h"] / 2, (Z0 + Z1) / 2), (T, tr["h"], Z1 - Z0 - 2 * T)),
                    ((X1 - T / 2, tr["h"] / 2, (Z0 + Z1) / 2), (T, tr["h"], Z1 - Z0 - 2 * T)),
                    (((X0 + X1) / 2, 0.11, (Z0 + Z1) / 2), (X1 - X0 - 2 * T, 0.22, Z1 - Z0 - 2 * T))):
        r.block(c, sz, (0.0, rng.uniform(-0.004, 0.004), 0.0), mat="VH_Ashlar", part=r.mas)
    r.sand.box((X0 + T, 0.221, Z0 + T), (X1 - T, 0.226, Z1 - T), "VH_Dark")                  # damp slime in the bottom
    gz = _L(0, 0, -28.3)[2]
    m.box((X0 + 0.2, -0.01, gz - 0.12), (X1 - 0.2, 0.004, gz + 0.12), "WB_BlackSteel")
    if lod == 0:
        x = X0 + 0.26
        while x < X1 - 0.22:
            hd.box((x - 0.012, 0.004, gz - 0.11), (x + 0.012, 0.012, gz + 0.11), "VH_Steel")
            x += 0.06
    # riser and four-tap manifold on two posts behind the trough; flow meter on the riser
    rz = _L(0, 0, -29.45)[2]
    rx = _L(1.9, 0, 0)[0]
    m.cyl((rx, 0.0, rz), (rx, 0.95, rz), 0.045, "WB_PipeTeal", 10)
    m.cyl(_L(0.42, 0.95, -29.45), _L(3.38, 0.95, -29.45), 0.04, "WB_PipeTeal", 10)
    for x in (0.42, 3.38):
        m.cyl(_L(x, 0.0, -29.45), _L(x, 1.02, -29.45), 0.035, "WB_BlackSteel", 8)
        m.cyl(_L(x, 0.95, -29.45), _L(x, 0.95, -29.36), 0.05, "WB_BlackSteel", 8)
    m.cyl((rx, 0.48, rz + 0.04), (rx, 0.48, rz + 0.1), 0.085, "WB_BlackSteel", 14)          # meter body
    m.cyl((rx, 0.48, rz + 0.1), (rx, 0.48, rz + 0.105), 0.07, "WB_PaintBone", 14)          # dial
    hd.box((rx - 0.004, 0.48, rz + 0.105), (rx + 0.004, 0.535, rz + 0.11), "VH_Dark")       # needle
    for x in (0.85, 1.55, 2.25, 2.95):
        m.tube([_L(x, 0.95, -29.45), _L(x, 0.95, -29.15), _L(x, 0.8, -29.02)], 0.022, "VH_Brass", 8)
        m.cyl(_L(x, 0.95, -29.32), _L(x, 1.06, -29.32), 0.01, "VH_Steel", 6)
        m.box(_L(x - 0.07, 1.055, -29.33), _L(x + 0.07, 1.075, -29.31), "WS_PaintRed")        # tap handle
    # Warden's tally desk (trestle table), ledger, stamp, lockbox, mug; the ration board on its posts
    dx, dz = _L(5.0, 0, -29.0)[0], _L(5.0, 0, -29.0)[2]
    m.box((dx - 0.62, 0.74, dz - 0.32), (dx + 0.62, 0.78, dz + 0.32), "TR_Timber")
    for sx in (-0.48, 0.48):
        for sz_ in (-1, 1):
            m.box((dx + sx - 0.025, 0.0, dz + sz_ * 0.28 - 0.025), (dx + sx + 0.025, 0.74, dz + sz_ * 0.18 + 0.025) if sz_ < 0 else
                  (dx + sx + 0.025, 0.74, dz + sz_ * 0.28 + 0.025), "TR_TimberDark")
        m.box((dx + sx - 0.02, 0.3, dz - 0.28), (dx + sx + 0.02, 0.34, dz + 0.28), "TR_TimberDark")
    m.box((dx - 0.32, 0.78, dz - 0.12), (dx + 0.02, 0.795, dz + 0.16), "WG_PaperRoster")      # open ledger
    m.box((dx + 0.02, 0.78, dz - 0.12), (dx + 0.32, 0.795, dz + 0.16), "WG_PaperRoster")
    m.box((dx - 0.335, 0.775, dz - 0.135), (dx + 0.335, 0.781, dz + 0.175), "WS_PaintRed")    # its cover
    m.box((dx + 0.38, 0.78, dz - 0.2), (dx + 0.58, 0.9, dz - 0.05), "WB_BlackSteel")          # lockbox
    m.cyl((dx + 0.46, 0.78, dz + 0.12), (dx + 0.46, 0.84, dz + 0.12), 0.022, "VH_Rubber", 8)  # stamp
    m.cyl((dx + 0.46, 0.84, dz + 0.12), (dx + 0.46, 0.89, dz + 0.12), 0.012, "TR_TimberDark", 6)
    m.cyl((dx - 0.48, 0.78, dz + 0.18), (dx - 0.48, 0.87, dz + 0.18), 0.04, "VH_PaintedSteel", 10)   # tin mug
    bx, bz = _L(5.85, 0, -29.4)[0], _L(5.85, 0, -29.4)[2]
    for x in (bx - 0.62, bx + 0.62):
        m.box((x - 0.04, 0.0, bz - 0.04), (x + 0.04, 2.05, bz + 0.04), "TR_TimberDark")
    m.box((bx - 0.7, 1.05, bz + 0.04), (bx + 0.7, 2.0, bz + 0.065), "WB_PaintBone")
    m.box((bx - 0.7, 1.78, bz + 0.065), (bx + 0.7, 2.0, bz + 0.07), "WS_PaintRed")
    Fb = Frame((0, 0, bz + 0.072), (1, 0, 0), (0, 0, 1))
    r.stencil("WATER RATION", Fb, bx, 1.89, 0.12, 1.25, 0.0, mat="WB_StencilPaint")
    r.stencil("TWO CANS A HOUSE", Fb, bx, 1.6, 0.09, 1.25, 0.0, mat="VH_Dark")
    r.stencil("TALLY AT THE DESK", Fb, bx, 1.4, 0.09, 1.25, 0.0, mat="VH_Dark")
    r.stencil("BY ORDER OF THE WARDENS", Fb, bx, 1.17, 0.06, 1.1, 0.0, mat="WS_PaintRed")
    r.scars.impact((tx, 1.7, tz + 1.0), 0.9, 0.8)
    r.rec["colliders"] += [
        {"name": "COL_Tank", "center": [tx, 1.4, tz], "size": [2.4, 2.8, 2.3]},
        {"name": "COL_Trough", "center": [(X0 + X1) / 2, 0.55, (Z0 + Z1) / 2 - 0.1], "size": [X1 - X0, 1.1, Z1 - Z0 + 0.2]},
        {"name": "COL_Desk", "center": [dx, 0.45, dz], "size": [1.24, 0.9, 0.64]},
        {"name": "COL_Board", "center": [bx, 1.0, bz + 0.03], "size": [1.5, 2.05, 0.16]},
        {"name": "COL_Valve", "center": [ox, 0.5, oz + 0.15], "size": [0.35, 1.0, 0.45]},
    ]
    r.rec["notes"].append("water ration point: header tank (AQUIFER 3), buried main under trench covers, 4-tap stand, trough, tally desk, ration board")
    return r


# ====================================================================== Node 07 goods dock props (north plaza)
# Quantum Tube nodes carry goods only (lore.md); what comes through Node 07 is staged, weighed and tallied here
# before porters take it into the city. Props: pallet, goods canister on a pallet (lying, chocked and strapped),
# canisters standing on a pallet, a platform scale with a dial, the dock board.
def pallet(r, x, z, yaw=0.0, y=0.0, rng=None):
    rng = rng or random.Random(1)
    ca, sa = math.cos(yaw), math.sin(yaw)
    def B(lx0, ly0, lz0, lx1, ly1, lz1, mat):
        c = [(lx0, ly0, lz0), (lx1, ly0, lz0), (lx1, ly0, lz1), (lx0, ly0, lz1), (lx0, ly1, lz0), (lx1, ly1, lz0), (lx1, ly1, lz1), (lx0, ly1, lz1)]
        r.metal.hexa([(x + px * ca - pz * sa, y + py, z + px * sa + pz * ca) for (px, py, pz) in c], mat)
    tm = lambda: rng.choice(("TR_Timber", "TR_TimberDark", "TR_Timber", "TR_TimberFresh"))
    for zz in (-0.45, 0.0, 0.45):                                      # bottom boards
        B(-0.6, 0.0, zz - 0.05, 0.6, 0.022, zz + 0.05, tm())
    for xx in (-0.55, 0.0, 0.55):                                      # blocks
        for zz in (-0.45, 0.0, 0.45):
            B(xx - 0.05, 0.022, zz - 0.05, xx + 0.05, 0.1, zz + 0.05, "TR_TimberDark")
    for xx in (-0.55, 0.0, 0.55):                                      # stringer boards
        B(xx - 0.05, 0.1, -0.5, xx + 0.05, 0.122, 0.5, tm())
    for zz in (-0.45, -0.225, 0.0, 0.225, 0.45):                       # deck boards
        if rng.random() < 0.08:
            continue                                                    # one missing board here and there
        B(-0.6, 0.122, zz - 0.05, 0.6, 0.144, zz + 0.05, tm())
    return 0.144


def canister(r, a, b, rad=0.24, lod=0):
    """Goods canister between end centres a and b: composite body, blackened end rings and ribs, two handles, a cyan
    status strip, a paper manifest tag."""
    a, b = Vector(a), Vector(b)
    d = (b - a).normalized()
    L = (b - a).length
    AB.cyl_uv(r.metal, a + d * 0.06, b - d * 0.06, rad, "WB_CylBone", 16)
    for t in (0.0, L - 0.06):
        r.metal.cyl(a + d * t, a + d * (t + 0.06), rad + 0.015, "WB_BlackSteel", 16)
    for t in (L * 0.33, L * 0.67):
        r.metal.cyl(a + d * (t - 0.02), a + d * (t + 0.02), rad + 0.01, "WB_BlackSteel", 16)
    up = Vector((0, 1, 0)) if abs(d.y) < 0.9 else Vector((1, 0, 0))
    side = d.cross(up).normalized()
    top = side.cross(d).normalized()
    if top.y < 0 and abs(d.y) < 0.9:
        top = -top
    for t in (0.12, L - 0.12):
        p = a + d * t + top * (rad + 0.012)
        r.metal.tube([p - d * 0.06, p - d * 0.05 + top * 0.06, p + d * 0.05 + top * 0.06, p + d * 0.06], 0.012, "VH_Steel", 6)
    c = a + d * (L * 0.5) + side * (rad + 0.002)
    r.glow.hexa([c - d * 0.12 - top * 0.015, c + d * 0.12 - top * 0.015, c + d * 0.12 + top * 0.015, c - d * 0.12 + top * 0.015,
                 c - d * 0.12 - top * 0.015 + side * 0.006, c + d * 0.12 - top * 0.015 + side * 0.006,
                 c + d * 0.12 + top * 0.015 + side * 0.006, c - d * 0.12 + top * 0.015 + side * 0.006], "WB_LedCyan")
    t0 = a + d * 0.12 + top * (rad + 0.08) + side * 0.03
    r.metal.box(tuple(t0 - Vector((0.04, 0.0, 0.03))), tuple(t0 + Vector((0.04, 0.003, 0.03))), "WG_PaperNotice")
    for e in (a, b):
        r.metal.cyl(e - d * 0.004, e + d * 0.004, rad * 0.55, "WB_BlackSteel", 12)


def dock_canisters_lying(lod):
    r = AB.Ruin("WL_CanisterPallet", lod, (1, 1, 1), 7400)
    rng = random.Random(7401)
    h = pallet(r, 0, 0, 0, rng=rng)
    for zz in (-0.25, 0.25):
        for xx in (-0.4, 0.4):
            r.metal.box((xx - 0.05, h, zz - 0.2), (xx + 0.05, h + 0.08, zz + 0.2), "TR_TimberDark")   # chocks
        canister(r, (-0.56, h + 0.25, zz), (0.56, h + 0.25, zz), 0.235, lod)
    for xx in (-0.2, 0.2):                                                                            # ratchet straps
        pts = [(xx, 0.13, -0.52), (xx, 0.4, -0.5), (xx, 0.64, -0.25), (xx, 0.64, 0.25), (xx, 0.4, 0.5), (xx, 0.13, 0.52)]
        r.metal.tube(pts, 0.012, "WS_PaintYellow", 4)
    r.rec["colliders"].append({"name": "COL_Load", "center": [0, 0.33, 0], "size": [1.22, 0.66, 1.05]})
    return r


def dock_canisters_standing(lod):
    r = AB.Ruin("WL_CanisterStand", lod, (1, 1, 1), 7500)
    rng = random.Random(7501)
    h = pallet(r, 0, 0, 0, rng=rng)
    for (x, z) in ((-0.3, -0.22), (0.3, -0.22), (0.0, 0.25)):
        canister(r, (x, h, z), (x, h + 1.05, z), 0.23, lod)
    r.rec["colliders"].append({"name": "COL_Load", "center": [0, 0.6, 0], "size": [1.22, 1.2, 1.05]})
    return r


def dock_pallet(lod):
    r = AB.Ruin("WL_Pallet", lod, (1, 1, 1), 7600)
    pallet(r, 0, 0, 0, rng=random.Random(7601))
    return r


def floor_scale(lod):
    r = AB.Ruin("WL_FloorScale", lod, (1, 1, 1), 7700)
    m = r.metal
    m.box((-0.6, 0.0, -0.6), (0.6, 0.06, 0.6), "WS_Deck")
    for sx in (-1, 1):                                                     # ramp lips front and back
        m.hexa([(-0.6, 0.0, sx * 0.6), (0.6, 0.0, sx * 0.6), (0.6, 0.0, sx * 0.78), (-0.6, 0.0, sx * 0.78),
                (-0.6, 0.06, sx * 0.6), (0.6, 0.06, sx * 0.6), (0.6, 0.0, sx * 0.78), (-0.6, 0.0, sx * 0.78)], "WB_BlackSteel")
    m.box((0.62, 0.0, -0.1), (0.72, 0.03, 0.1), "WB_BlackSteel")
    m.cyl((0.67, 0.0, 0.0), (0.67, 1.12, 0.0), 0.04, "WB_BlackSteel", 10)    # column beside the platform
    m.cyl((0.67, 1.25, -0.06), (0.67, 1.25, 0.06), 0.16, "WB_BlackSteel", 20)
    m.cyl((0.67, 1.25, 0.06), (0.67, 1.25, 0.066), 0.135, "WB_PaintBone", 20)
    r.hard.box((0.665, 1.25, 0.066), (0.675, 1.36, 0.072), "WS_PaintRed")
    m.cyl((0.67, 1.12, 0.0), (0.67, 1.1, 0.0), 0.06, "WB_BlackSteel", 10)
    m.tube([(0.67, 0.05, 0.0), (0.62, 0.02, 0.05), (0.55, 0.02, 0.2)], 0.008, "VH_Rubber", 4)
    r.rec["colliders"].append({"name": "COL_Column", "center": [0.67, 0.7, 0.0], "size": [0.35, 1.4, 0.35]})
    return r


def dock_board(lod):
    r = AB.Ruin("WL_DockBoard", lod, (1, 1, 1), 7800)
    if lod > 0:
        r.stencil = lambda *a, **k: None          # painted text is unreadable beyond the LOD1 cut
    m = r.metal
    for x in (-0.72, 0.72):
        m.box((x - 0.045, 0.0, -0.045), (x + 0.045, 2.2, 0.045), "TR_TimberDark")
    m.box((-0.8, 1.0, 0.045), (0.8, 2.1, 0.07), "WB_PaintBone")
    m.box((-0.8, 1.84, 0.07), (0.8, 2.1, 0.075), "WB_PipeTeal")
    F = Frame((0, 0, 0.078), (1, 0, 0), (0, 0, 1))
    r.stencil("NODE 07 GOODS DOCK", F, 0.0, 1.97, 0.11, 1.45, 0.0, mat="WB_StencilPaint")
    r.stencil("BAYS 1-2  INBOUND", F, 0.0, 1.66, 0.085, 1.4, 0.0, mat="VH_Dark")
    r.stencil("BAY 3  OUTBOUND", F, 0.0, 1.47, 0.085, 1.4, 0.0, mat="VH_Dark")
    r.stencil("WEIGH AND TALLY ALL GOODS", F, 0.0, 1.22, 0.07, 1.4, 0.0, mat="WS_PaintRed")
    m.box((0.38, 1.06, 0.075), (0.62, 1.15, 0.09), "WG_PaperNotice")           # pinned manifest
    r.rec["colliders"].append({"name": "COL_Board", "center": [0, 1.1, 0], "size": [1.7, 2.2, 0.2]})
    return r


def tally_desk(lod):
    """The dock tally clerk's standing desk: a slanted lectern on a crate base, manifest boards, a ledger, a stool."""
    r = AB.Ruin("WL_TallyDesk", lod, (1, 1, 1), 7900)
    m = r.metal
    m.box((-0.45, 0.0, -0.3), (0.45, 0.85, 0.3), "TR_TimberDark")
    m.hexa([(-0.5, 0.85, -0.35), (0.5, 0.85, -0.35), (0.5, 1.02, 0.35), (-0.5, 1.02, 0.35),
            (-0.5, 0.88, -0.35), (0.5, 0.88, -0.35), (0.5, 1.05, 0.35), (-0.5, 1.05, 0.35)], "TR_Timber")
    for (x, mat) in ((-0.22, "WG_PaperRoster"), (0.2, "WG_PaperNotice")):
        m.hexa([(x - 0.15, 0.885, -0.2), (x + 0.15, 0.885, -0.2), (x + 0.15, 1.035, 0.2), (x - 0.15, 1.035, 0.2),
                (x - 0.15, 0.893, -0.2), (x + 0.15, 0.893, -0.2), (x + 0.15, 1.043, 0.2), (x - 0.15, 1.043, 0.2)], mat)
    m.cyl((0.42, 1.05, 0.3), (0.42, 1.06, 0.3), 0.05, "VH_Brass", 10)          # bell push / stamp pad
    m.box((-0.44, 0.3, 0.3), (0.44, 0.33, 0.33), "TR_TimberDark")
    r.rec["colliders"].append({"name": "COL_Desk", "center": [0, 0.52, 0], "size": [1.0, 1.05, 0.7]})
    return r


def run_model(key, fn, lods=(0, 1)):
    report = {"source": "art/ward_life_20261003/author_life.py", "date": "2026-10-03", "key": key, "lods": {}}
    model = None
    for lod in lods:
        r = fn(lod)
        objs = r.finish()
        export(objs, OUT / f"{r.name}_LOD{lod}.glb")
        report["lods"][f"LOD{lod}"] = {"triangles": r.rec["triangles"], "objects": r.rec["objects"]}
        if lod == 0:
            report.update({k: v for k, v in r.rec.items() if k not in ("triangles", "objects")})
            model = r.name
        print(f"{r.name} LOD{lod}: {r.rec['triangles']} triangles", flush=True)
    report["model"] = model
    (OUT / f"{key}.json").write_text(json.dumps(report, indent=1))


KEYS = {"bastion": lambda: (run_bastion(1), run_bastion(-1)),
        "waterpoint": lambda: run_model("waterpoint", water_point),
        "dock": lambda: [run_model(k, f) for k, f in (("canister_pallet", dock_canisters_lying), ("canister_stand", dock_canisters_standing),
                                                       ("pallet", dock_pallet), ("floor_scale", floor_scale), ("dock_board", dock_board),
                                                       ("tally_desk", tally_desk))]}


def main():
    names = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else list(KEYS)
    for k in names:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        KEYS[k]()


if __name__ == "__main__":
    main()
