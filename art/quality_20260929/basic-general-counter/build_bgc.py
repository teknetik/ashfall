"""Basic General counter stock and service-recess dressing - authoring (29 Sep 2026, task t_84b69b7e).

Run:  sh bl.sh --python build_bgc.py
Opens the preserved v3 building source read-only in memory (never saved over), builds the six new modules in A-space
(building-local metres, +Z = towards the avenue, +X = screen-right from the avenue, Y=0 = porch top), hides the superseded
stock/counter objects in the review scene only, and saves basic-general-counter-source-v1.blend + interchange files.
"""
import bpy, math, json, sys, random
from pathlib import Path
from mathutils import Vector, Matrix

OUT = Path('/home/teknetik/code/ao2/art/quality_20260929/basic-general-counter')
sys.path.insert(0, str(OUT))
import bgc_lib as L
from bgc_lib import Part, material

SRC = '/home/teknetik/code/ao2/art/quality_20260909/basic-general/basic-general-source-v3.blend'
bpy.ops.wm.open_mainfile(filepath=SRC)
scene = bpy.data.scenes['Basic General architectural repair']
bpy.context.window.scene = scene
new_col = bpy.data.collections.new('BGC counter dressing (new)'); scene.collection.children.link(new_col)

# ---------------------------------------------------------------- materials
M = material
M('CounterFace', 'BGC_CounterFace', 4.24, unique_uv=True, note='Unique 4096x1024 layout, u=(x+2.12)/4.24, v=y/1.06 (front of the counter, three bays)')
M('CounterTop', 'BGC_CounterTop', 4.24, unique_uv=True, note='Unique 4096x512 layout, u=(x+2.12)/4.24, v=1-(front_edge_distance/0.53)')
M('ShelfPaint', 'BGC_ShelfPaint', .60)
M('ShelfBone', 'BGC_ShelfPaint', .60, base='BGC_ShelfPaint_Bone_BaseColor.png')
M('ShelfOlive', 'BGC_ShelfPaint', .60, base='BGC_ShelfPaint_Olive_BaseColor.png')
for v in ('Sand', 'Olive', 'Blue', 'Red', 'Bone', 'Wax'):
    M('Enamel_' + v, 'BGC_Enamel', .30, base=f'BGC_Enamel_{v}_BaseColor.png')
M('Steel', 'BGC_BareSteel', .50)
M('Brass', 'BGC_BareSteel', .50, base='BGC_BareSteel_Brass_BaseColor.png')
M('Rubber', 'BGC_Rubber', .30)
M('Webbing_Olive', 'BGC_Webbing', .12, base='BGC_Webbing_Olive_BaseColor.png')
M('Webbing_Sand', 'BGC_Webbing', .12, base='BGC_Webbing_Sand_BaseColor.png')
M('Copper', 'BGC_CopperWire', .10)
M('Cable_Slate', 'BGC_CableSheath', .20, base='BGC_CableSheath_Slate_BaseColor.png')
M('Cable_Ochre', 'BGC_CableSheath', .20, base='BGC_CableSheath_Ochre_BaseColor.png')
M('Twine', 'BGC_Twine', .10)
M('Sand', 'BGC_Sand', .50)
M('Clay', 'BGC_Clay', .40)
M('Paper', 'BGC_Paper', .35)

PI = math.pi


def T(x=0, y=0, z=0, ry=0, rx=0, rz=0):
    """Placement matrix: translate after rotating about Y (yaw, degrees), then X, then Z."""
    R = Matrix.Rotation(math.radians(ry), 4, 'Y') @ Matrix.Rotation(math.radians(rx), 4, 'X') @ Matrix.Rotation(math.radians(rz), 4, 'Z')
    return Matrix.Translation((x, y, z)) @ R


def noise2(x, z, s=1.0):
    return .5 + .25 * math.sin(x * 37 * s + 1.3) * math.cos(z * 29 * s + .7) + .25 * math.sin(x * 91 * s + z * 53 * s)


# ================================================================ small parts
def bolt(p, x, y, z, r=.0085, h=.006, mat='Steel', axis='z'):
    """Domed hex-head bolt. Built along +Y then rotated so its head points along +Z (default) or +Y."""
    p.begin()
    p.lathe([(r * 1.35, 0), (r * 1.35, .0015), (r, .0015), (r, h * .7), (r * .55, h), (0, h * 1.02)], mat, .5, segs=6)
    p.end(T(x, y, z, rx=90) if axis == 'z' else T(x, y, z))


def twine_wrap(p, r, y0, y1, turns, tail=.05, tr=.0022, ang0=0.0):
    pts = []
    n = int(turns * 10)
    for i in range(n + 1):
        t = i / n
        a = ang0 + t * turns * 2 * PI
        pts.append((r * math.cos(a), y0 + (y1 - y0) * t, r * math.sin(a)))
    a = ang0 + turns * 2 * PI
    pts.append((r * math.cos(a) + tail * .8 * math.cos(a), y1 - tail * .5, r * math.sin(a) + tail * .8 * math.sin(a)))
    p.tube(pts, tr, 'Twine', .10, sides=4)


def tag(p, x, y, z, w=.052, h=.034, ry=0, string_to=None, rz=0):
    """Blank kraft tag (rules, tallies, stamp ring - no lettering) with a twine loop; UV maps the whole tag to the paper sheet."""
    p.begin()
    p.box((0, 0, 0), (w, h, .0018), 'Paper', .35, bevel=.0008, seg=1,
          over=[(2, 1, 'Paper', .35, lambda co, n: ((co.x + w / 2) / w, (co.y + h / 2) / h)), (2, -1, 'Paper', .35, lambda co, n: (1 - (co.x + w / 2) / w, (co.y + h / 2) / h))])
    p.tube([(-w * .36, h * .5, 0), (-w * .36, h * .62, 0), (-w * .28, h * .74, 0), (0, h * .80, 0), (w * .28, h * .74, 0), (w * .36, h * .62, 0), (w * .36, h * .5, 0)], .0011, 'Twine', .10, sides=4)
    p.end(T(x, y, z, ry=ry, rz=rz))


def bottle(p, x, y, z, h=.30, r=.052, body='Enamel_Sand', ry=0, seed=0, label=True, cap='Steel'):
    nr = r * .36
    p.begin()
    prof = [(r * .78, 0), (r * .95, .007), (r, .019), (r, h * .60), (r * .975, h * .67), (r * .82, h * .765), (r * .58, h * .835), (nr * 1.3, h * .895), (nr, h * .925), (nr, h * .955)]
    p.lathe(prof, body, .30, segs=36)
    p.lathe([(r * 1.006, 0.019), (r * 1.006, .026), (r * 1.0, .026), (r, .019)], 'Steel', .5, segs=36, caps=(False, False))      # bottom seam ring (thin)
    ch = h * .955
    p.lathe([(nr * 1.10, ch - .004), (nr * 1.20, ch), (nr * 1.20, ch + .017), (nr * 1.12, ch + .022), (nr * .9, ch + .024), (0, ch + .024)], cap, .5, segs=32)
    p.lathe([(nr * 1.24, ch - .012), (nr * 1.34, ch - .005), (nr * 1.30, ch + .012), (nr * 1.08, ch + .026), (0, ch + .030)], 'Enamel_Wax', .3, segs=28,
            warp=lambda a, hh: 1 + .10 * math.sin(3 * a + seed) + .07 * math.sin(7 * a + seed * 2))
    twine_wrap(p, nr * 1.04 + .0025, h * .885, h * .91, 2.2, tr=.0021, ang0=seed)
    if label:                                    # printed paper sleeve, no lettering
        lh = h * .26
        p.lathe([(r + .0012, h * .20), (r + .0012, h * .20 + lh)], 'Paper', .35, segs=36, caps=(False, False))
    p.end(T(x, y, z, ry=ry))


def olla(p, x, y, z, s=1.0, ry=0, seed=1):
    """Porous clay water jar with rope-through-lugs handle and wax-sealed cork."""
    p.begin()
    prof = [(.032, 0), (.062, .008), (.090, .05), (.100, .105), (.092, .165), (.066, .215), (.040, .246), (.038, .262), (.045, .272), (.047, .285), (.036, .289)]
    p.lathe(prof, 'Clay', .40, segs=44, warp=lambda a, hh: 1 + .012 * math.sin(2 * a + seed) + .008 * math.sin(5 * a + hh * 40))
    p.lathe([(.034, .284), (.034, .300), (.030, .306), (0, .308)], 'Enamel_Wax', .3, segs=24, warp=lambda a, hh: 1 + .08 * math.sin(4 * a + seed))
    for sx in (-1, 1):                            # lugs
        p.lathe([(.011, 0), (.011, .020)], 'Clay', .4, segs=12, caps=(True, True))
    p.tube([(-.056, .243, 0), (-.05, .292, 0), (-.02, .318, 0), (.02, .318, 0), (.05, .292, 0), (.056, .243, 0)], .0055, 'Twine', .10, sides=6)
    twine_wrap(p, .0425, .262, .272, 2.5, tr=.0025, ang0=seed)
    p.end(T(x, y, z, ry=ry) @ Matrix.Diagonal((s, s, s, 1)))


def canteen(p, x, y, z, body='Enamel_Blue', ry=0, rx=0, seed=0, strap='Webbing_Olive'):
    """Flat pilgrim flask: elliptical section (built as geometry, not object scale) with sling."""
    p.begin()
    prof = [(.05, 0, .50), (.085, .012, .42), (.098, .06, .42), (.098, .13, .42), (.086, .17, .44), (.05, .20, .62), (.026, .214, 1.0), (.023, .226, 1.0), (.023, .238, 1.0)]
    p.lathe(prof, body, .30, segs=40)
    p.lathe([(.025, .236), (.027, .240), (.027, .252), (.024, .256), (0, .257)], 'Steel', .5, segs=24)
    # perimeter seam (rolled edge) - flattened torus ring in bare steel
    p.tube([(math.cos(a) * .097, .066 + 0, math.sin(a) * .097 * .42) for a in [i * 2 * PI / 40 for i in range(40)]], .0035, 'Steel', .5, sides=4, closed=True)
    p.tube([(math.cos(a) * .097, .132, math.sin(a) * .097 * .42) for a in [i * 2 * PI / 40 for i in range(40)]], .0035, 'Steel', .5, sides=4, closed=True)
    # webbing sling: closed band around the body plus a neck loop
    sec = [(-.011, -.0012), (.011, -.0012), (.011, .0012), (-.011, .0012)]
    ring = [(math.cos(a) * .1005, .098, math.sin(a) * .1005 * .42) for a in [i * 2 * PI / 44 for i in range(44)]]
    p.sweep(ring, sec, lambda pt: Vector((pt[0], 0, pt[2])), strap, .12, closed=True)
    p.tube([(-.098, .098, .043), (-.09, .16, .046), (-.05, .225, .028), (0, .252, .0), (.05, .225, -.028), (.09, .16, -.046), (.098, .098, -.043)], .0035, 'Twine', .10, sides=4)
    twine_wrap(p, .0275, .224, .236, 2.0, tr=.002, ang0=seed)
    p.end(T(x, y, z, ry=ry, rx=rx))


def medkit(p, x, y, z, w=.24, h=.16, d=.09, ry=0, body='Enamel_Bone', cross=True, handle=True, seed=0):
    p.begin()
    hb = h * .62
    p.box((0, hb / 2, 0), (w, hb, d), body, .30, bevel=.008, seg=3)
    p.box((0, hb + (h - hb) / 2 - .001, 0), (w + .004, h - hb, d + .004), body, .30, bevel=.008, seg=3)      # lid overlaps tray
    p.box((0, hb, d / 2 + .0015), (w + .002, .0035, .003), 'ShelfPaint', .6, bevel=.001, seg=1)                # dark seam
    if cross:
        cw = min(w, h) * .26
        cy = hb + (h - hb) / 2
        p.box((0, cy, d / 2 + .004), (cw, cw * .32, .003), 'Enamel_Red', .30, bevel=.0008, seg=1)
        p.box((0, cy, d / 2 + .004), (cw * .32, cw, .003), 'Enamel_Red', .30, bevel=.0008, seg=1)
    for sx in (-1, 1):                                # latches and corner plates
        p.box((sx * w * .3, hb, d / 2 + .006), (.028, .030, .008), 'Steel', .5, bevel=.0015, seg=1)
        p.box((sx * (w / 2 - .006), h * .5, d / 2 - .001), (.012, h * .92, .004), 'Steel', .5, bevel=.001, seg=1)
    if handle:                                        # webbing carry loop with steel D-anchors
        sec = [(-.009, -.0012), (.009, -.0012), (.009, .0012), (-.009, .0012)]
        arc = [(x_ * w * .16, h + .002 + .030 * math.sin(PI * (x_ + 1) / 2), 0) for x_ in [i / 8 * 2 - 1 for i in range(9)]]
        p.sweep(arc, sec, (0, 0, 1), 'Webbing_Sand', .12)
        for sx in (-1, 1):
            p.box((sx * w * .16, h + .0015, 0), (.024, .005, .014), 'Steel', .5, bevel=.0015, seg=1)
    p.end(T(x, y, z, ry=ry))


def roll_pack(p, x, y, z, ry=0, L_=.22, r=.052, cloth='Webbing_Olive', vertical=False):
    p.begin()
    p.lathe([(r * .9, 0), (r, .006), (r, L_ - .006), (r * .9, L_)], cloth, .12, segs=32, axis=(1, 0, 0))
    p.lathe([(r * .8, L_ * .5 - L_ * .5 - .0015), (r * .9, -.0015)], 'Rubber', .3, segs=32, axis=(1, 0, 0), caps=(True, False))
    for fx in (.05, L_ - .05):
        sec = [(-.012, -.0016), (.012, -.0016), (.012, .0016), (-.012, .0016)]
        ring = [(fx, math.cos(a) * (r + .002), math.sin(a) * (r + .002)) for a in [i * 2 * PI / 28 for i in range(28)]]
        p.sweep(ring, sec, lambda pt: Vector((0, pt[1], pt[2])), 'Webbing_Sand', .12, closed=True)
        p.box((fx, r + .004, 0), (.016, .008, .026), 'Steel', .5, bevel=.0015, seg=1)
    p.box((L_ * .5, r * 0.3, r + .003), (.05, .05, .0025), 'Enamel_Red', .30, bevel=.001, seg=1)
    p.end(T(x, y + r, z, ry=ry) if not vertical else T(x, y, z, ry=ry) @ Matrix.Rotation(PI / 2, 4, 'Z') @ Matrix.Translation((0, -0, 0)))


def copper_coil(p, x, y, z, R=.085, a=.028, winds=13, wr=.0052, ry=0, rx=90, mat='Copper', seed=0, ties=2, stand=None, cols=4):
    """Hank of wire: `winds` laps of one continuous strand laid round a ring of mean radius R, stacked cols wide by rows deep
    (smooth hand-off between laps), bound with twine ties. rx=90 puts the ring in the wall plane; stand=True lifts it onto its rim."""
    stand = (rx == 90) if stand is None else stand
    p.begin()
    d = wr * 2.08
    rows = -(-winds // cols)
    per = 16
    pts = []
    for i in range(winds * per + 1):
        t = i / per
        k = min(int(t), winds - 1)
        f = t - k
        s = f * f * (3 - 2 * f) if f > .68 else 0.0
        s = max(0.0, (f - .68) / .32) ** 2 * (3 - 2 * max(0.0, (f - .68) / .32)) if f > .68 else 0.0
        k2 = min(k + 1, winds - 1)
        u0 = ((k % cols) - (cols - 1) / 2) * d; v0 = ((k // cols) - (rows - 1) / 2) * d
        u1 = ((k2 % cols) - (cols - 1) / 2) * d; v1 = ((k2 // cols) - (rows - 1) / 2) * d
        u = u0 + (u1 - u0) * s + .0012 * math.sin(t * 5.3 + seed); v = v0 + (v1 - v0) * s + .0012 * math.cos(t * 4.1 + seed)
        phi = t * 2 * PI + seed
        rad = R + u
        pts.append((rad * math.cos(phi), v, rad * math.sin(phi)))
    p.tube(pts, wr, mat, .10, sides=5)
    e0 = Vector(pts[0]); e1 = Vector(pts[-1])
    tail = Vector((-math.sin(seed), 0, math.cos(seed)))
    p.tube([e1, e1 + tail * .035 + Vector((0, -.006, 0)), e1 + tail * .075 + Vector((0, -.025, .0)), e1 + tail * .105 + Vector((0, -.06, 0))], wr, mat, .10, sides=5)
    p.tube([e0, e0 - tail * .03 + Vector((0, .01, 0)), e0 - tail * .06 + Vector((0, .003, 0))], wr, mat, .10, sides=5)
    hw, hh = cols * d / 2 + wr * 1.7, rows * d / 2 + wr * 1.7
    for k in range(ties):
        ph = seed + PI * (.5 + k)
        cx, cz = math.cos(ph), math.sin(ph)
        cen = Vector((R * cx, 0, R * cz))
        u = Vector((cx, 0, cz)); v = Vector((0, 1, 0))
        ring = [tuple(cen + u * (math.cos(t) * hw) + v * (math.sin(t) * hh)) for t in [i * 2 * PI / 24 for i in range(24)]]
        p.tube(ring, .0027, 'Twine', .10, sides=4, closed=True)
        p.tube([ring[0], tuple(Vector(ring[0]) + u * .03 + v * .035), tuple(Vector(ring[0]) + u * .055 + v * .015)], .0025, 'Twine', .10, sides=4)
    lift = (R + hw) if stand else 0.0
    p.end(T(x, y + lift, z, ry=ry, rx=rx))


def spool(p, x, y, z, ry=0, mat='Copper', wound='Copper', rf=.10, wd=.11, rw=.072, rx=90):
    p.begin()
    p.lathe([(0, -wd / 2 - .005), (rf, -wd / 2 - .005), (rf, -wd / 2 + .004), (rf * .97, -wd / 2 + .006)], 'ShelfOlive', .6, segs=40, axis=(0, 0, 1), caps=(False, False))
    p.lathe([(0, -wd / 2 - .005), (rf, -wd / 2 - .005)], 'ShelfOlive', .6, segs=40, axis=(0, 0, 1), caps=(False, True))
    p.lathe([(0, wd / 2 + .005), (rf, wd / 2 + .005)], 'ShelfOlive', .6, segs=40, axis=(0, 0, 1), caps=(False, True))
    p.lathe([(rf, wd / 2 + .005), (rf, wd / 2 - .004)], 'ShelfOlive', .6, segs=40, axis=(0, 0, 1), caps=(False, False))
    p.lathe([(rw, -wd / 2 + .004), (rw, wd / 2 - .004)], wound, .10, segs=40, axis=(0, 0, 1), swap_uv=True, caps=(False, False))
    p.lathe([(.02, -wd / 2 - .012), (.02, wd / 2 + .012)], 'Steel', .5, segs=16, axis=(0, 0, 1))
    p.tube([(rw, 0, wd / 2 - .004), (rw + .012, .01, wd / 2 + .01), (rw + .05, .02, wd / 2 + .02), (rw + .09, -.02, wd / 2 + .01)], .0052, wound, .10, sides=5)
    p.end(T(x, y + rf, z, ry=ry))


def cable_coil(p, x, y, z, R=.13, a=None, winds=9, ry=0, rx=90, mat="Cable_Slate", seed=0, stand=None):
    copper_coil(p, x, y, z, R=R, winds=winds, wr=.0085, ry=ry, rx=rx, mat=mat, seed=seed, ties=3, stand=stand, cols=3)


def hook(p, x, y, z, reach=.055, drop=.055, r=.0042):
    """Steel S-hook screwed to a rail: forward stub, down, then a curl that rises back."""
    pts = [(x, y, z), (x, y, z + reach * .6)]
    c = (x, y - drop * .35, z + reach)
    for i in range(1, 11):
        t = i / 10 * PI * 1.35
        pts.append((x, y - r * 2 - drop * .35 - (drop * .65) * math.sin(t * .75) + 0, z + reach * (1 - .0) + .012 * math.sin(t) * 0 + (reach * .55) * math.sin(t) * (1 - i / 22)))
    p.tube(pts, r, 'Steel', .5, sides=6)
    return Vector((x, y - drop - .012, z + reach * 1.15))


def shelf_hardware(p, cx, y, retention=False):
    """Steel shelf plate with rolled front lip and down-turn, two gusset brackets, and a back angle."""
    zf, zb = -.812, -1.02
    zc = (zf + zb) / 2
    p.box((cx, y, zc), (.74, .022, zf - zb), 'ShelfPaint', .6, bevel=.003, seg=2)
    lipz = zf + .0055
    p.box((cx, y + .0125 + .019, lipz), (.74, .038, .011), 'ShelfPaint', .6, bevel=.003, seg=2)                       # front up-stand
    p.box((cx, y - .011 - .007, lipz), (.74, .014, .011), 'ShelfPaint', .6, bevel=.003, seg=2)                       # down-turn
    p.tube([(cx - .37, y + .0125 + .038, lipz), (cx + .37, y + .0125 + .038, lipz)], .0038, 'Steel', .5, sides=6, caps=True)  # rolled bead on top of the lip
    for sx in (-1, 1):
        bx = cx + sx * .358
        p.prism([(0, 0), (.0, -.15), (-.15, 0)], 'x', bx - .005, bx + .005, 'ShelfPaint', .6) if False else None
        prof = [(zb + .03, y - .011), (zb + .03, y - .16), (zf - .07, y - .011)]         # (z, y) gusset triangle
        p.prism(prof, 'x', bx - .005, bx + .005, 'ShelfPaint', .6)
        bolt(p, bx + sx * .0055, y - .05, zb + .06, r=.006, h=.005, axis='z') if False else None
    p.box((cx, y - .011 + .022, zb + .006), (.74, .046, .012), 'Steel', .5, bevel=.002, seg=1)                          # back angle
    if retention:                                                                                                  # bottle-stop rod
        for sx in (-1, 1):
            p.tube([(cx + sx * .345, y + .011, lipz + .002), (cx + sx * .345, y + .105, lipz + .002)], .004, 'Steel', .5, sides=6)
        p.tube([(cx - .345, y + .105, lipz + .002), (cx + .345, y + .105, lipz + .002)], .0035, 'Steel', .5, sides=6)


def dust_patch(p, x0, x1, z0, z1, y, amp=.008, seed=1, nx=16, nz=6):
    def fn(x, z):
        u = (x - x0) / (x1 - x0); v = (z - z0) / (z1 - z0)
        edge = max(0.0, min(1, u * (1 - u) * 4)) ** .8 * max(0.0, min(1, v * (1 - v) * 4)) ** .8
        return amp * edge * (.35 + .9 * noise2(x + seed, z, 1.0)) - .0002
    faces = p.grid(nx, nz, fn, (x0, x1), (z0, z1), 'Sand', .5, base=0)
    p.transform_new(Matrix.Translation((0, y, 0)), faces)


# ================================================================ modules
parts = []


def make(name, seed, origin, fn):
    p = Part(name, seed)
    fn(p)
    o = p.finalise(new_col, origin=origin)
    o['module'] = name
    parts.append((name, origin, o))
    return o


# ---- 1. counter -----------------------------------------------------------
def build_counter(p):
    W = 4.24
    ZB, ZF = -1.10, -.72                       # back (wall face) and front of the box
    top = .94
    fv = lambda co, n: ((co.x + W / 2) / W, co.y / 1.06)
    tv = lambda co, n: ((co.x + W / 2) / W, 1 - ((-.70 - co.z) / .53) * -1 - 0 if False else 1 - (co.z - (-.70)) / -.53 * -1)
    # top slab: 4.24 x 0.03 x 0.40 with rolled front nosing; unique top map (v runs from front edge = 1 downward)
    tv = lambda co, n: ((co.x + W / 2) / W, 1 - (-.70 - co.z) / .53 * -1 * -1) if False else ((co.x + W / 2) / W, 1 - (co.z + .70) * -1 / .53 * 1 if False else 1 - ((-.70 - co.z) / .53) * -1 * -1)
    tv = lambda co, n: ((co.x + W / 2) / W, 1 + (co.z + .70) / .53)         # front edge z=-.70 -> v=1; back z=-1.10 -> v=.245
    p.box((0, top - .015, (ZB + -.70) / 2), (W, .03, -.70 - ZB), 'ShelfPaint', .6, bevel=.006, seg=3, over=[(1, 1, 'CounterTop', 4.24, tv)])
    # front box (bays): body and three recessed panels between raised stiles - faces use the unique face map
    p.box((0, (top - .03) / 2, (ZB + ZF) / 2), (W, top - .03, ZF - ZB), 'ShelfPaint', .6, bevel=.003, seg=1, over=[(2, 1, 'CounterFace', 4.24, fv)])
    for sx in (-2.0825, -.6975, .6975, 2.0825):               # raised stiles (front face = unique map; edges/sides = painted steel)
        p.box((sx, (top - .03) / 2, ZF + .006), (.075, top - .03, .014), 'ShelfPaint', .6, bevel=.002, seg=1,
              over=[(2, 1, 'CounterFace', 4.24, fv)])
    # pressed inset frames and stiffener ribs give each bay relief that reads in shade (geometry, not baked shading)
    for x0, x1, rib in ((-2.045, -.735, True), (-.66, .66, False), (.735, 2.045, True)):
        cxm, wid = (x0 + x1) / 2, (x1 - x0) - .10
        for yy in (.135, .835):
            p.box((cxm, yy, ZF + .0105), (wid, .028, .009), 'ShelfPaint', .6, bevel=.0025, seg=2)
        for sx_ in (-1, 1):
            p.box((cxm + sx_ * (wid / 2 - .014), .485, ZF + .0108), (.028, .70, .0096), 'ShelfPaint', .6, bevel=.0025, seg=2)
        if rib:
            p.box((cxm, .485, ZF + .0115), (wid - .05, .034, .011), 'ShelfPaint', .6, bevel=.004, seg=2)
            for k in range(-3, 4):
                bolt(p, cxm + k * (wid - .12) / 6, .485, ZF + .0175, r=.0058, h=.0045)
    p.box((0, .90, ZF + .004), (W, .013, .010), 'ShelfPaint', .6, bevel=.002, seg=1, over=[(2, 1, 'CounterFace', 4.24, fv)])   # top rail
    # centre bay service hatch furniture: pull handle on two standoffs, hasp and a closed padlock (tells the player the bay is a locked store)
    for hx_ in (-.11, .11):
        p.box((hx_, .52, ZF + .0235), (.014, .022, .020), 'Steel', .5, bevel=.002, seg=1)
    p.box((0, .52, ZF + .0365), (.30, .016, .014), 'Steel', .5, bevel=.004, seg=2)
    p.box((.33, .60, ZF + .0155), (.075, .16, .006), 'Steel', .5, bevel=.002, seg=1)                                  # hasp plate on the stile side
    p.box((.245, .60, ZF + .0155), (.09, .05, .006), 'Steel', .5, bevel=.002, seg=1)
    p.begin()
    p.box((0, -.03, 0), (.045, .06, .022), 'Brass', .5, bevel=.004, seg=2)
    p.tube([(-.014, -.002, 0), (-.014, .022, 0), (0, .034, 0), (.014, .022, 0), (.014, -.002, 0)], .0044, 'Steel', .5, sides=6)
    p.end(T(.245, .585, ZF + .0245))
    for bx in (-2.0825, -.6975, .6975, 2.0825, -1.35, -.06, 1.42):
        for by in (.16, .74):
            bolt(p, bx, by, ZF + .0205 if abs(bx) > .5 and abs(abs(bx) - 2.0825) < 1e-3 or abs(abs(bx) - .6975) < 1e-3 else ZF + .0105, r=.0088, h=.0055)
    # steel nosing angle over the front edge, with domed fixings
    p.box((0, top - .0035, -.70 - .0035), (W - .02, .014, .026), 'Steel', .5, bevel=.003, seg=3)
    for i in range(12):
        bx = -1.95 + i * .355
        bolt(p, bx, top + .0035, -.70 - .012, r=.0062, h=.005, axis='y')
    # rubber corner guards and kick strip
    for sx in (-1, 1):
        p.box((sx * (W / 2 - .0165), .47, ZF - .002), (.038, .94, .06), 'Rubber', .3, bevel=.006, seg=2)
    p.box((0, .012, ZF + .010), (W - .09, .024, .026), 'Rubber', .3, bevel=.004, seg=2)
    # dust: banked at the plinth, on the top at the wall corners and in the two dead zones beside the cabinets
    dust_patch(p, -2.05, 2.05, ZF - .01, ZF + .13, .0, amp=.022, seed=3, nx=40, nz=6)
    dust_patch(p, -2.11, -1.55, ZB + .002, ZB + .11, top, amp=.005, seed=5, nx=10, nz=4)
    dust_patch(p, 1.55, 2.11, ZB + .002, ZB + .09, top, amp=.005, seed=7, nx=10, nz=4)


make('BGC_Counter', 11, (0, 0, -1.10), build_counter)


# ---- 2/3. shelf bays ---------------------------------------------------------
def build_left(p):                       # screen-left bay: water and first aid
    cx = -1.72
    y1, y2 = 1.0, 1.48
    shelf_hardware(p, cx, y1, retention=True)
    shelf_hardware(p, cx, y2)
    top1 = y1 + .011; top2 = y2 + .011
    zc = -.90
    olla(p, cx - .245, top1, zc, s=.86, ry=20, seed=1)
    bottle(p, cx - .075, top1, zc, h=.31, r=.05, body='Enamel_Sand', ry=0, seed=1.0)
    bottle(p, cx + .075, top1, zc + .004, h=.265, r=.048, body='Enamel_Olive', ry=35, seed=2.0)
    canteen(p, cx + .235, top1, zc + .004, body='Enamel_Blue', ry=-14, seed=3)
    medkit(p, cx - .165, top2, zc - .005, w=.25, h=.17, d=.095, ry=4, body='Enamel_Bone', seed=1)
    medkit(p, cx - .155, top2 + .17, zc - .005, w=.20, h=.115, d=.085, ry=-7, body='Enamel_Olive', cross=True, handle=False)
    medkit(p, cx + .055, top2, zc + .0, w=.15, h=.215, d=.085, ry=-5, body='Enamel_Bone', seed=2)
    roll_pack(p, cx + .19, top2, zc - .005, ry=90, L_=.22, r=.048, cloth='Webbing_Olive')
    for x_, ty in ((cx - .27, y1 + .0125 + .022), (cx + .12, y1 + .0125 + .022), (cx - .05, y2 + .0125 + .022)):
        tag(p, x_, ty, -.808, ry=0, rz=[3, -4, 2][int(abs(x_) * 7) % 3])
    dust_patch(p, cx - .36, cx + .36, -1.0, -.94, top1, amp=.006, seed=9, nx=12, nz=3)
    dust_patch(p, cx - .36, cx + .36, -1.0, -.94, top2, amp=.005, seed=13, nx=12, nz=3)


def build_right(p):                      # screen-right bay: salvage and wire
    cx = 1.72
    y1, y2 = 1.0, 1.48
    shelf_hardware(p, cx, y1)
    shelf_hardware(p, cx, y2, retention=True)
    top1 = y1 + .011; top2 = y2 + .011
    zc = -.90
    copper_coil(p, cx - .225, top1 + .0, zc, R=.082, a=.026, winds=12, ry=0, rx=90, seed=.6)
    spool(p, cx + .035, top1, zc + .0, ry=0)
    bottle(p, cx + .225, top1, zc, h=.22, r=.042, body='Enamel_Red', ry=10, seed=4.0)
    bottle(p, cx + .30, top1, zc + .006, h=.19, r=.038, body='Enamel_Bone', ry=-25, seed=5.0)
    medkit(p, cx - .245, top2, zc, w=.16, h=.125, d=.09, ry=10, body='Enamel_Olive', cross=True, seed=3)
    copper_coil(p, cx - .04, top2, zc, R=.062, a=.02, winds=10, ry=0, rx=90, seed=2.2)
    cable_coil(p, cx + .21, top2, zc + .0, R=.085, a=.022, winds=8, ry=0, rx=90, mat='Cable_Ochre', seed=1.4)
    canteen(p, cx + .335, top2, zc + .003, body='Enamel_Olive', ry=-8, seed=6, strap='Webbing_Sand')
    for x_, ty in ((cx - .16, y1 + .0125 + .022), (cx + .27, y2 + .0125 + .022)):
        tag(p, x_, ty, -.808, ry=0, rz=3)
    dust_patch(p, cx - .36, cx + .36, -1.0, -.94, top1, amp=.006, seed=17, nx=12, nz=3)
    dust_patch(p, cx - .36, cx + .36, -1.0, -.94, top2, amp=.005, seed=19, nx=12, nz=3)


make('BGC_ShelfBay_L', 21, (-1.72, 0, -1.10), build_left)
make('BGC_ShelfBay_R', 22, (1.72, 0, -1.10), build_right)


# ---- 4/5. hook rails ---------------------------------------------------------
def rail(p, cx, y):
    zw = -1.10
    p.box((cx, y, zw + .026), (.80, .034, .012), 'Steel', .5, bevel=.003, seg=2)
    p.box((cx, y + .0165, zw + .034), (.80, .006, .026), 'Steel', .5, bevel=.002, seg=1)
    for sx in (-1, 1):
        p.box((cx + sx * .36, y, zw + .012), (.04, .05, .026), 'ShelfPaint', .6, bevel=.004, seg=2)
        bolt(p, cx + sx * .36, y + .0, zw + .034, r=.007, h=.006)
    return zw + .032


def build_hooks_L(p):
    cx = -.88
    y = 1.80
    z0 = rail(p, cx, y)
    hx = [-.30, -.15, 0.0, .15, .30]
    tips = [hook(p, cx + dx, y - .022, z0) for dx in hx]
    # (1) sling canteen
    zt = tips[0].z
    canteen(p, cx + hx[0], y - .022 - .098 - .27, zt + .0, body='Enamel_Sand', ry=0, rx=0, seed=2, strap='Webbing_Olive')
    p.tube([(cx + hx[0], y - .034, z0 + .002), (cx + hx[0] - .035, y - .1, zt), (cx + hx[0], y - .155, zt), (cx + hx[0] + .035, y - .1, zt), (cx + hx[0], y - .034, z0 + .002)], .0032, 'Twine', .10, sides=4)
    # (2) bottle hung by a twine bight
    bottle(p, cx + hx[1], y - .034 - .30 - .04, zt - .0, h=.30, r=.048, body='Enamel_Olive', ry=25, seed=4.0)
    p.tube([(cx + hx[1], y - .034, z0 + .002), (cx + hx[1] - .012, y - .10, zt), (cx + hx[1], y - .335, zt)], .0028, 'Twine', .10, sides=4)
    # (3) first-aid pouch hung by its carry loop
    medkit(p, cx + hx[2], y - .034 - .17 - .06, zt - .0, w=.20, h=.16, d=.075, ry=0, body='Enamel_Bone', seed=3)
    p.tube([(cx + hx[2], y - .034, z0 + .002), (cx + hx[2], y - .10, zt), (cx + hx[2], y - .2, zt)], .0028, 'Twine', .10, sides=4)
    # (4) spool of wire, (5) short coil
    tag(p, cx + hx[3] + .0, y - .12, zt - .01, ry=0)
    copper_coil(p, cx + hx[4], y - .034 - .12 - .075, zt, R=.05, winds=10, ry=0, rx=90, stand=False, seed=1.0)
    p.tube([(cx + hx[4], y - .034, z0 + .002), (cx + hx[4], y - .10, zt), (cx + hx[4], y - .22, zt)], .0028, 'Twine', .10, sides=4)


def build_hooks_R(p):
    cx = .88
    y = 1.80
    z0 = rail(p, cx, y)
    hx = [-.30, -.15, 0.0, .15, .30]
    tips = [hook(p, cx + dx, y - .022, z0) for dx in hx]
    zt = tips[0].z
    cable_coil(p, cx + hx[0], y - .034 - .13 * 2 - .0, zt - .0, R=.105, a=.028, winds=9, rx=90, ry=0, stand=False, mat="Cable_Slate", seed=.9)   # hangs on a twine bight, ring in the wall plane
    p.tube([(cx + hx[0], y - .034, z0 + .002), (cx + hx[0], y - .12, zt), (cx + hx[0], y - .22, zt)], .0032, 'Twine', .10, sides=4)
    roll_pack(p, cx + hx[1] - .1, y - .034 - .24, zt, ry=0, L_=.22, r=.045, cloth='Webbing_Sand')
    p.tube([(cx + hx[1], y - .034, z0 + .002), (cx + hx[1], y - .1, zt), (cx + hx[1], y - .17, zt)], .0028, 'Twine', .10, sides=4)
    copper_coil(p, cx + hx[2], y - .034 - .1 - .085, zt, R=.05, winds=10, rx=90, stand=False, ry=0, seed=.3)
    copper_coil(p, cx + hx[3], y - .034 - .1 - .085, zt, R=.045, winds=9, rx=90, stand=False, ry=0, seed=2.0)
    tag(p, cx + hx[2] + .075, y - .16, zt + .03)
    bottle(p, cx + hx[4], y - .034 - .215 - .04, zt, h=.215, r=.04, body='Enamel_Red', ry=-30, seed=6.0)
    for dx in (hx[2], hx[3], hx[4]):
        p.tube([(cx + dx, y - .034, z0 + .002), (cx + dx, y - .1, zt), (cx + dx, y - .155, zt)], .0028, 'Twine', .10, sides=4)


make('BGC_HookRail_L', 31, (-.88, 0, -1.10), build_hooks_L)
make('BGC_HookRail_R', 32, (.88, 0, -1.10), build_hooks_R)


# ---- 6. counter props ----------------------------------------------------------
def build_props(p):
    top = .94
    z = -.90
    # flask rack + three sample flasks
    rx = -1.05
    p.box((rx, top + .01, z), (.40, .02, .13), 'ShelfPaint', .6, bevel=.004, seg=2)
    p.box((rx, top + .13, z - .06), (.40, .022, .016), 'Steel', .5, bevel=.003, seg=2)
    for sx in (-1, 1):
        p.box((rx + sx * .19, top + .09, z - .06), (.016, .16, .016), 'Steel', .5, bevel=.002, seg=1)
    for i, (dx, body, h_) in enumerate(((-.135, 'Enamel_Sand', .27), (0, 'Enamel_Olive', .25), (.135, 'Enamel_Blue', .27))):
        bottle(p, rx + dx, top + .02, z, h=h_, r=.045, body=body, ry=i * 40, seed=7.0 + i)
        ring = [(rx + dx + math.cos(a) * .053, top + .14, z + math.sin(a) * .053) for a in [k * 2 * PI / 20 for k in range(20)]]
        p.tube(ring, .003, 'Steel', .5, sides=4, closed=True)
        p.tube([(rx + dx, top + .14, z - .053), (rx + dx, top + .14, z - .06)], .003, 'Steel', .5, sides=4)
    # medkit stack
    medkit(p, -.60, top, z - .01, w=.26, h=.17, d=.10, ry=6, body='Enamel_Bone', seed=4)
    medkit(p, -.595, top + .17, z - .01, w=.21, h=.12, d=.085, ry=-8, body='Enamel_Red', cross=False, handle=False)
    # ledger with twine tie (no lettering)
    p.begin()
    p.box((0, .011, 0), (.19, .022, .26), 'Paper', .35, bevel=.002, seg=1)
    p.box((0, .0235, 0), (.205, .004, .275), 'Rubber', .3, bevel=.002, seg=1)
    p.box((0, -.0005, 0), (.205, .004, .275), 'Rubber', .3, bevel=.002, seg=1)
    p.box((-.096, .012, 0), (.014, .026, .276), 'Rubber', .3, bevel=.005, seg=2)
    twine_wrap(p, .0, 0, 0, 0)  if False else None
    p.tube([(-.05, .0245, .13), (-.05, .0245, -.13)], .0022, 'Twine', .10, sides=4)
    p.tube([(-.02, .0255, .0), (.03, .0265, .03), (.07, .0255, .0), (.03, .0245, -.03), (-.02, .0255, .0)], .0022, 'Twine', .10, sides=4)
    p.end(T(-.28, top, z - .01, ry=-10))
    # cash tin (steel, hinged lid, hasp)
    p.begin()
    p.box((0, .035, 0), (.20, .07, .13), 'ShelfOlive', .6, bevel=.006, seg=3)
    p.box((0, .076, 0), (.204, .018, .134), 'ShelfOlive', .6, bevel=.006, seg=3)
    p.box((0, .05, .068), (.036, .06, .006), 'Steel', .5, bevel=.002, seg=1)
    p.tube([(-.014, .052, .074), (-.014, .044, .085), (.014, .044, .085), (.014, .052, .074)], .0025, 'Steel', .5, sides=4)
    for sx in (-1, 1):
        p.box((sx * .07, .075, -.066), (.03, .02, .008), 'Steel', .5, bevel=.002, seg=1)
    p.end(T(.40, top, z, ry=8))
    # receipt spike with paper slips
    p.begin()
    p.lathe([(.03, 0), (.03, .008), (.012, .016), (.005, .024)], 'Steel', .5, segs=24)
    p.lathe([(.0035, .022), (.0035, .15), (0, .162)], 'Steel', .5, segs=10)
    for i in range(6):
        p.box((0, .026 + i * .0032, 0), (.075, .0011, .045), 'Paper', .35, bevel=.0004, seg=1, rot=(0, math.radians(i * 22 - 40), 0),
              over=[(1, 1, 'Paper', .35, lambda co, n: (co.x / .075 + .5, co.z / .045 + .5))])
    p.end(T(.66, top, z - .02))
    # sale mat with a sample wire skein
    p.begin()
    p.box((0, .006, 0), (.44, .012, .27), 'Rubber', .3, bevel=.004, seg=2)
    p.end(T(.0, top, z - .015, ry=3))
    copper_coil(p, .01, top + .012 + .034, z - .015, R=.06, winds=12, ry=20, rx=0, stand=False, seed=.5)
    # balance scale (brass): base, column, beam with pointer, two chained pans
    sx_ = 1.03
    p.begin()
    p.lathe([(.075, 0), (.075, .012), (.05, .022), (.016, .05), (.011, .10), (.014, .19), (.019, .203), (.0, .21)], 'Brass', .5, segs=32)
    p.box((0, .215, 0), (.37, .011, .012), 'Brass', .5, bevel=.003, seg=2)
    p.lathe([(0, 0), (.006, 0), (.006, .07), (0, .08)], 'Brass', .5, segs=8, caps=(False, False), axis=(0, 1, 0))
    for ex in (-1, 1):
        p.lathe([(.007, .209), (.007, .225), (0, .228)], 'Steel', .5, segs=10, pos=(ex * .18, 0, 0))
        for k in range(3):
            a = k * 2 * PI / 3
            p.tube([(ex * .18, .215, 0), (ex * .18 + math.cos(a) * .05, .07, math.sin(a) * .05)], .0012, 'Steel', .5, sides=4)
        p.lathe([(0, .056), (.058, .062), (.062, .07), (.058, .072), (.0, .066)], 'Brass', .5, segs=32, pos=(ex * .18, 0, 0))
    p.end(T(sx_, top, z - .015, ry=-6))
    # a few loose paper slips and a receipt curl on the counter, and dust at the wall line
    for i, (px, pz, pr) in enumerate(((.19, -.83, 12), (-.36, -.79, -22), (.86, -.75, 30))):
        p.box((px, top + .0012, pz), (.09, .0012, .058), 'Paper', .35, bevel=.0004, seg=1, rot=(0, math.radians(pr), 0),
              over=[(1, 1, 'Paper', .35, lambda co, n: (co.x / .09 + .5, co.z / .058 + .5))])
    dust_patch(p, -1.3, 1.3, -1.10, -1.03, top + .0006, amp=.005, seed=23, nx=40, nz=3)


make('BGC_CounterProps', 41, (0, 0, -1.10), build_props)

# ---------------------------------------------------------------- summarise
info = {}
for name, origin, o in parts:
    s = L.stats(o)
    info[name] = {'pivotAuthoring': list(origin), **s, 'materialSlots': [m.get('ward_slot') for m in o.data.materials]}
    print(name, s['tris'], 'tris', s['sizeA'])
(OUT / 'build-stats-raw.json').write_text(json.dumps({'parts': info, 'materials': L.RECORDS}, indent=2))

# ---------------------------------------------------------------- review scene: retire superseded objects (review only)
RETIRE = ('Sealed goods tin', 'Tin rolled lid', 'Tin label', 'Stock exact label', 'Stock shelf', 'Counter repair fascia', 'Counter inset plate',
          'Counter plate rivet', 'Service ledge', 'Counter working lip', 'Counter grip paint loss')
retired = []
for o in list(scene.objects):
    if o.name.startswith(RETIRE):
        retired.append(o.name)
        o['bgc_retired'] = True
bpy.data.texts.new('bgc_retired_objects.txt').write('\n'.join(sorted(retired)))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'basic-general-counter-source-v1.blend'), compress=True)
print('SAVED', len(parts), 'parts;', len(retired), 'retired in review scene')
