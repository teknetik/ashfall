"""Tool Exchange display vignette and shutter hardware - authoring (29 Sep 2026, task t_3751e0fd).

    sh bl.sh --python build_te.py

Opens the preserved revision-04 building source read-only in memory (never saved over), builds the new modules in A-space
(building-local metres, +X screen-right from the avenue, +Y up, +Z towards the avenue, Y=0 porch top), marks the objects they
supersede (review scene only) and saves tool-exchange-display-source-v1.blend.  Geometry only; PBR maps come from
make_te_textures.py and the layout constants from te_spec.py (shared with the board outlines painted in the texture).
"""
import bpy, bmesh, math, json, sys
from pathlib import Path
from mathutils import Vector, Matrix

OUT = Path('/home/teknetik/code/ao2/art/quality_20260929/tool-exchange-display')
sys.path.insert(0, str(OUT))
import te_lib as L
from te_lib import Part, material
import te_spec as S

SRC = '/home/teknetik/code/ao2/art/quality_20260909/relay-family/store-variants-04/tool_exchange/source.blend'
bpy.ops.wm.open_mainfile(filepath=SRC)
scene = bpy.data.scenes[0]
bpy.context.window.scene = scene
new_col = bpy.data.collections.new('TE display and shutter (new)')
scene.collection.children.link(new_col)

# ------------------------------------------------------------------ materials (maps live in textures/)
M = material
M('Board', 'TE_ToolBoard', None, unique_uv=True, note='Unique 3072x2908 @2048 px/m: u=(x+2.90)/1.5, v=(y-0.78)/1.42 (A-space metres)')
M('Timber', 'TE_Timber', .5)
M('TimberPolished', 'TE_TimberPolished', .5)
M('Steel', 'TE_BareSteel', .5)
M('Brass', 'TE_BareSteel', .5, base='TE_BareSteel_Brass_BaseColor.png')
M('PaintRed', 'TE_ToolPaintRed', .5)
M('Iron', 'TE_CastIron', .4)
M('ToolSteel', 'TE_ToolSteel', .5)
M('Rubber', 'TE_Rubber', .3)
M('Twine', 'TE_Twine', .1)
M('Paper', 'TE_Paper', .35)
M('Sand', 'TE_Sand', .5)
M('Stone', 'TE_Stone', .25)
M('ShutterPaint', 'TE_ShutterPaint', .6)
M('ShutterFit', 'TE_ShutterFit', None, unique_uv=True, note='Unique 4096x1024 @2048 px/m atlas, zones in textures/layout.json (2.0 x 0.5 m)')
M('Glass', 'TE_DisplayGlass', None, unique_uv=True, note='Unique RGBA 2806x2703 @2048 px/m; alpha = opacity (URP transparent, alpha blend)')

PI = math.pi
BZ = S.BOARD['zf']            # board front face, A-space z = 2.042
ATL = json.loads((OUT / 'textures/layout.json').read_text())['atlas']
HOLE_L = .0166                # wrench eyelet centre along the tool


def T(x=0.0, y=0.0, z=0.0, ry=0.0, rx=0.0, rz=0.0):
    """Placement: rotate about Z, then X, then Y (degrees) and translate."""
    R = Matrix.Rotation(math.radians(ry), 4, 'Y') @ Matrix.Rotation(math.radians(rx), 4, 'X') @ Matrix.Rotation(math.radians(rz), 4, 'Z')
    return Matrix.Translation((x, y, z)) @ R


def noise2(x, z, s=1.0):
    return .5 + .25 * math.sin(x * 37 * s + 1.3) * math.cos(z * 29 * s + .7) + .25 * math.sin(x * 91 * s + z * 53 * s)


# ================================================================ helpers
def slab(p, poly, z0, z1, mat, tile, bevel=.002, seg=2, uvfn=None):
    """Extrude a 2D polygon (x, y) between z0 and z1 with bevelled edges (tool blades, plates)."""
    bm = p.bm
    n = len(poly)
    r0 = [bm.verts.new((x, y, z0)) for x, y in poly]
    r1 = [bm.verts.new((x, y, z1)) for x, y in poly]
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
    bm.faces.new(r0[::-1]); bm.faces.new(r1)
    fs = [f for f in bm.faces if f[p.gen] == 0]
    bmesh.ops.recalc_face_normals(bm, faces=fs)
    if bevel:
        edges = list({e for v in r0 + r1 for e in v.link_edges})
        bmesh.ops.bevel(bm, geom=edges, offset=min(bevel, (z1 - z0) * .45), offset_type='OFFSET', segments=seg, profile=.5, affect='EDGES')
    faces = p._new()
    if uvfn:
        p.uv_fn(faces, uvfn)
    else:
        p.uv_box(faces, mat, tile)
    p._tag(faces, mat)
    return faces


def bolt(p, x, y, z, r=.0085, h=.006, mat='Steel', axis='z'):
    """Domed hex-head bolt; axis 'z' -> head points to +Z (the avenue)."""
    p.begin()
    p.lathe([(r * 1.35, 0), (r * 1.35, .0015), (r, .0015), (r, h * .7), (r * .55, h), (0, h * 1.02)], mat, .5, segs=6)
    p.end(T(x, y, z, rx=90) if axis == 'z' else (T(x, y, z, rx=180) if axis == 'yd' else T(x, y, z)))


def tag(p, x, y, z, w=.052, h=.034, ry=0.0, rz=0.0):
    """Blank kraft repair tag (rule bands, tally ticks, stamp ring - NO lettering) with a twine loop, hung from its top edge."""
    p.begin()
    p.box((0, 0, 0), (w, h, .0018), 'Paper', .35, bevel=.0008, seg=1,
          over=[(2, 1, 'Paper', .35, lambda co, n: ((co.x + w / 2) / w, (co.y + h / 2) / h)),
                (2, -1, 'Paper', .35, lambda co, n: (1 - (co.x + w / 2) / w, (co.y + h / 2) / h))])
    p.tube([(-w * .36, h * .5, 0), (-w * .36, h * .62, 0), (-w * .28, h * .74, 0), (0, h * .80, 0), (w * .28, h * .74, 0), (w * .36, h * .62, 0), (w * .36, h * .5, 0)],
           .0011, 'Twine', .10, sides=4)
    p.end(T(x, y, z, ry=ry, rz=rz))


def cord_hank(p, x, y, z, R=.034, winds=8, wr=.0034, seed=1.2, cols=3):
    """Hank of cord: `winds` laps of one continuous strand laid round a ring (ring in the wall plane, x-y), bound with two twine ties."""
    p.begin()
    d = wr * 2.08
    rows = -(-winds // cols)
    per = 16
    pts = []
    for i in range(winds * per + 1):
        t = i / per
        k = min(int(t), winds - 1)
        f = t - k
        s = max(0.0, (f - .68) / .32) ** 2 * (3 - 2 * max(0.0, (f - .68) / .32)) if f > .68 else 0.0
        k2 = min(k + 1, winds - 1)
        u0 = ((k % cols) - (cols - 1) / 2) * d; v0 = ((k // cols) - (rows - 1) / 2) * d
        u1 = ((k2 % cols) - (cols - 1) / 2) * d; v1 = ((k2 // cols) - (rows - 1) / 2) * d
        u = u0 + (u1 - u0) * s + .0012 * math.sin(t * 5.3 + seed); v = v0 + (v1 - v0) * s + .0012 * math.cos(t * 4.1 + seed)
        phi = t * 2 * PI + seed
        rad = R + u
        pts.append((rad * math.cos(phi), v, rad * math.sin(phi)))
    p.tube(pts, wr, 'Twine', .10, sides=5)
    e0 = Vector(pts[0]); e1 = Vector(pts[-1])
    tail = Vector((-math.sin(seed), 0, math.cos(seed)))
    p.tube([e1, e1 + tail * .030 + Vector((0, -.006, 0)), e1 + tail * .060 + Vector((0, -.022, 0)), e1 + tail * .085 + Vector((0, -.050, 0))], wr, 'Twine', .10, sides=5)
    p.tube([e0, e0 - tail * .03 + Vector((0, .01, 0)), e0 - tail * .05 + Vector((0, .003, 0))], wr, 'Twine', .10, sides=5)
    hw, hh = cols * d / 2 + wr * 1.7, rows * d / 2 + wr * 1.7
    for k in range(2):
        ph = seed + PI * (.5 + k)
        cx, cz = math.cos(ph), math.sin(ph)
        cen = Vector((R * cx, 0, R * cz)); u = Vector((cx, 0, cz)); v = Vector((0, 1, 0))
        ring = [tuple(cen + u * (math.cos(t) * hw) + v * (math.sin(t) * hh)) for t in [i * 2 * PI / 24 for i in range(24)]]
        p.tube(ring, .0024, 'Twine', .10, sides=4, closed=True)
    # ring lies in the (x, z) plane in its own frame; stand it in the wall plane (x, y)
    p.end(T(x, y, z, rx=90))


def dust_patch(p, x0, x1, z0, z1, y, amp=.006, seed=1, nx=24, nz=6):
    def fn(x, z):
        u = (x - x0) / (x1 - x0); v = (z - z0) / (z1 - z0)
        edge = max(0.0, min(1, u * (1 - u) * 4)) ** .8 * max(0.0, min(1, v * (1 - v) * 4)) ** .8
        return amp * edge * (.35 + .9 * noise2(x + seed, z, 1.0)) - .0002
    faces = p.grid(nx, nz, fn, (x0, x1), (z0, z1), 'Sand', .5, base=0)
    p.transform_new(Matrix.Translation((0, y, 0)), faces)


def peg(p, x, y, z0, length=.060, rest=False, mat='Steel'):
    """Bare-steel tool peg screwed into the board/rail, pointing to +Z. rest=True adds the up-turned curl that keeps a tool on it."""
    p.begin()
    p.lathe([(0, 0), (.0085, 0), (.0085, .0018), (.0038, .0022), (.0038, .010)], mat, .5, segs=14, axis=(0, 0, 1), caps=(False, False))
    p.end(T(x, y, z0))
    z1 = z0 + length
    if rest:
        pts = [(x, y, z0 + .008), (x, y, z1 - .030), (x, y + .003, z1 - .013), (x, y + .011, z1 - .003), (x, y + .024, z1 - .003), (x, y + .0245, z1 - .004)]
    else:
        pts = [(x, y, z0 + .008), (x, y, z1 - .004), (x, y, z1)]
    p.tube(pts, .0035, mat, .5, sides=8)


def A_of(local_pt, origin, deg):
    q = S.rot(local_pt, deg)
    return (q[0] + origin[0], q[1] + origin[1])


parts = []


def make(name, seed, origin, fn):
    p = Part(name, seed)
    fn(p)
    o = p.finalise(new_col, origin=origin)
    o['module'] = name
    parts.append((name, origin, o))
    return o


# ================================================================ 1. display case (board, liners, bench)
def build_case(p):
    W = S.BOARD_W
    cx = (S.BOARD['x0'] + S.BOARD['x1']) / 2
    y0, y1 = S.BOARD['y0'], S.BOARD['y1']
    bu = lambda co, n: ((co.x - S.BOARD['x0']) / W, (co.y - y0) / (y1 - y0))
    p.box((cx, (y0 + y1) / 2, (S.BOARD['zb'] + BZ) / 2), (W, y1 - y0, BZ - S.BOARD['zb']), 'Timber', .5, bevel=.0015, seg=1,
          over=[(2, 1, 'Board', 1.0, bu)])
    zl0, zl1 = BZ, S.WALL_REAR_Z
    for sx in (S.BOARD['x0'] + .0075, S.BOARD['x1'] - .0075):
        p.box((sx, (y0 + y1) / 2, (zl0 + zl1) / 2), (.015, y1 - y0, zl1 - zl0), 'Timber', .5, bevel=.002, seg=1)
    p.box((cx, y1 - .0075, (zl0 + zl1) / 2), (W - .03, .015, zl1 - zl0), 'Timber', .5, bevel=.002, seg=1)
    bx0, bx1 = S.BOARD['x0'] + .015, S.BOARD['x1'] - .015
    bcx = (bx0 + bx1) / 2
    top = S.BENCH['y']
    zf = 2.435
    p.box((bcx, top - .016, (BZ + zf) / 2), (bx1 - bx0, .032, zf - BZ), 'Timber', .5, bevel=.003, seg=2)
    p.box((bcx, (y0 + top - .032) / 2, zf - .008), (bx1 - bx0, top - .032 - y0, .016), 'Timber', .5, bevel=.002, seg=1)
    p.box((bcx, top + .030, BZ + .010), (bx1 - bx0, .060, .020), 'Timber', .5, bevel=.003, seg=2)
    for sx in (bx0 + .12, bcx, bx1 - .12):
        p.box((sx, top - .045, (BZ + zf) / 2), (.030, .026, zf - BZ - .04), 'Timber', .5, bevel=.002, seg=1)
    p.box((bcx + .12, top + .0006, zf - .045), (.90, .0012, .075), 'TimberPolished', .5, bevel=0, seg=1)       # palm-polished forearm strip
    dust_patch(p, bx0 + .02, bx1 - .02, BZ + .02, BZ + .13, top, amp=.0055, seed=3, nx=60, nz=6)
    dust_patch(p, bx0 + .02, bx0 + .30, BZ + .02, zf - .02, top, amp=.0035, seed=8, nx=16, nz=14)
    dust_patch(p, bx1 - .28, bx1 - .02, BZ + .02, zf - .02, top, amp=.0030, seed=11, nx=14, nz=14)


make('TE_DisplayCase', 11, (-2.15, S.BOARD['y0'], S.WALL_REAR_Z), build_case)

# wrench eyelet position on the board (peg passes through it)
_wo = S.PLACEMENT['PipeWrench']['origin']; _wd = S.PLACEMENT['PipeWrench']['deg']
WR_HOLE = A_of((HOLE_L, 0), _wo, _wd)
WR_PEG = (WR_HOLE[0], WR_HOLE[1] + .003)


# ================================================================ 2. peg rail with pegs, repair tags, cord hank; the wrench's own peg
def build_rail(p):
    rc = (S.BOARD['x0'] + S.BOARD['x1']) / 2
    rl = 1.42
    p.box((rc, S.RAIL_Y, BZ + .014), (rl, .045, .028), 'Timber', .5, bevel=.004, seg=2)
    for k in range(6):
        sx = S.BOARD['x0'] + .09 + k * (rl - .18) / 5 + (.006 if k % 2 else -.004)
        bolt(p, sx, S.RAIL_Y + (.008 if k % 2 else -.006), BZ + .028, r=.0058, h=.0035)
    dust_patch(p, rc - rl / 2 + .04, rc + rl / 2 - .04, BZ + .002, BZ + .026, S.RAIL_Y + .0225, amp=.0045, seed=21, nx=40, nz=3)
    RZ = BZ + .028
    for key in ('saw_loop', 'spare_a', 'spare_b'):
        px, py = S.PEGS[key]
        peg(p, px, py, RZ, length=.048)
    peg(p, WR_PEG[0], WR_PEG[1], BZ, length=.056)                              # the wrench hangs on this peg through its eyelet
    # two repair tags hung from the empty saw peg (the saw is out for sharpening)
    sx, sy = S.PEGS['saw_loop']
    zt = RZ + .026
    p.tube([(sx, sy + .0055, zt), (sx - .004, sy - .004, zt), (sx - .006, sy - .028, zt), (sx - .008, sy - .050, zt)], .0016, 'Twine', .10, sides=4)
    tag(p, sx - .008, sy - .078, zt, w=.068, h=.046, rz=-6)
    p.tube([(sx, sy + .0055, zt + .003), (sx + .010, sy - .006, zt + .003), (sx + .016, sy - .032, zt + .003), (sx + .022, sy - .056, zt + .003)], .0014, 'Twine', .10, sides=4)
    tag(p, sx + .022, sy - .080, zt + .006, w=.048, h=.032, rz=9)
    # cord hank on a spare peg, hung by a twine bight round the peg
    hx, hy = S.PEGS['spare_a']
    ring = [(hx + .0058 * math.cos(a), hy + .0058 * math.sin(a), RZ + .022) for a in [i * 2 * PI / 16 for i in range(16)]]
    p.tube(ring, .0018, 'Twine', .10, sides=4, closed=True)
    p.tube([(hx, hy - .0058, RZ + .022), (hx, hy - .035, RZ + .022), (hx, hy - .058, RZ + .022)], .0022, 'Twine', .10, sides=4)
    cord_hank(p, hx, hy - .104, RZ + .022)


make('TE_PegRail', 12, (-2.15, S.RAIL_Y, BZ), build_rail)


# ================================================================ 3. pipe wrench (hangs by its eyelet on a board peg)
def build_wrench(p):
    poly = [tuple(pt) for pt in S.PIPE_WRENCH[0]]
    poly[0] = (.028, -.0137); poly[-1] = (.028, .0137)                       # the eyelet boss replaces the first 28 mm
    T1 = .022
    slab(p, poly, 0.0, T1, 'PaintRed', .5, bevel=.0022, seg=2)
    p.lathe([(.0065, 0), (.0166, 0), (.0166, T1), (.0065, T1)], 'PaintRed', .5, pos=(HOLE_L, 0, 0), axis=(0, 0, 1), segs=28, caps=(False, False))
    p.lathe([(.0065, 0), (.0065, T1)], 'ToolSteel', .5, pos=(HOLE_L, 0, 0), axis=(0, 0, 1), segs=28, caps=(False, False))          # bore
    for zc_ in (T1 + .0022, -.0022):                                              # cast centre rib on both faces
        p.box((.165, 0, zc_), (.26, .0085, .0044), 'PaintRed', .5, bevel=.0012, seg=1)
    # knurled adjusting nut standing proud of both faces
    p.lathe([(0.0, .335), (.0155, .336), (.0175, .341), (.0175, .372), (.0155, .377), (0.0, .378)], 'ToolSteel', .5, pos=(0, 0, .011), axis=(1, 0, 0), segs=36,
            warp=lambda a, h: 1 + (.045 * math.cos(30 * a) if .341 < h < .372 else 0.0))
    for i, t in enumerate((.10, .32, .55, .78)):                                  # hook-jaw teeth
        a = Vector((.425, -.008)).lerp(Vector((.405, .010)), t)
        p.box((a.x, a.y, .011), (.006, .0045, .018), 'Steel', .5, bevel=.0006, seg=1, rot=(0, 0, math.radians(-42 + i * 3)))
    for zz, sgn in ((T1, 1), (0.0, -1)):                                          # pivot rivet heads
        p.begin()
        p.lathe([(.0075, 0), (.0075, .0012), (.0055, .0025), (0, .0030)], 'Steel', .5, segs=14, axis=(0, 0, 1), caps=(False, True))
        p.end(T(.398, .050, zz) if sgn > 0 else T(.398, .050, zz, rx=180))


spec = S.PLACEMENT['PipeWrench']
zb_w = BZ + .010
o_w = spec['origin']
make('TE_ToolPipeWrench', 13, (WR_HOLE[0], WR_HOLE[1], zb_w),
     lambda p: (p.begin(), build_wrench(p), p.end(T(o_w[0], o_w[1], zb_w, rz=spec['deg']))))


# ================================================================ 4. lump hammer (rests on two curl pegs)
def build_hammer(p):
    zc = .0295
    warp = lambda a, h: 1 + .012 * math.sin(2 * a + h * 9)
    p.lathe([(0.0, -.004), (.0100, -.003), (.0124, .003), (.0132, .012), (.0124, .030), (.0113, .075), (.0107, .120), (.0111, .160)], 'TimberPolished', .5,
            pos=(0, 0, zc), axis=(1, 0, 0), segs=24, warp=warp, caps=(False, False))
    p.lathe([(.0111, .160), (.0114, .200), (.0122, .240), (.0126, .270), (.0126, .302), (0.0, .304)], 'Timber', .5,
            pos=(0, 0, zc), axis=(1, 0, 0), segs=24, warp=warp, caps=(False, False))
    p.lathe([(0.0, -.004), (.0100, -.003)], 'TimberPolished', .5, pos=(0, 0, zc), axis=(1, 0, 0), segs=24, warp=warp, caps=(False, True))
    p.box((.2675, 0, zc), (.059, .100, .059), 'ToolSteel', .5, bevel=.0065, seg=3, over=[(1, 1, 'Steel', .5, None), (1, -1, 'Steel', .5, None)])
    p.box((.2675, 0, zc), (.066, .034, .066), 'ToolSteel', .5, bevel=.007, seg=2)
    p.box((.3012, 0, zc), (.0035, .022, .0075), 'Steel', .5, bevel=.0008, seg=1)
    p.box((.3012, 0, zc), (.0035, .0075, .022), 'Steel', .5, bevel=.0008, seg=1)


spec = S.PLACEMENT['LumpHammer']
zb_h = BZ + .0065
o_h = spec['origin']
make('TE_ToolLumpHammer', 14, (o_h[0], o_h[1], zb_h),
     lambda p: (p.begin(), build_hammer(p), p.end(T(o_h[0], o_h[1], zb_h, rz=spec['deg']))))
hammer_pegs = [A_of((xl, -.0119 - .0035), o_h, spec['deg']) for xl in (.055, .195)]


# ================================================================ 5. bolt cutters (rubber-dipped grips, repair tag on the lower arm)
def build_cutters(p):
    army = lambda x: .034 - .016 * x / .42
    zc = .017
    for sg in (1, -1):
        arm = [(0, sg * .022), (0, sg * .046), (.42, sg * .030), (.42, sg * .006)]
        slab(p, arm, .006, .028, 'ToolSteel', .5, bevel=.0025, seg=2)
        ang = math.atan2(sg * (army(.245) - army(0)), .245)
        p.box((.1225, sg * army(.1225), zc), (.245, .030, .028), 'Rubber', .3, bevel=.009, seg=3, rot=(0, 0, ang))
        p.box((.004, sg * army(.004), zc), (.010, .050, .030), 'Rubber', .3, bevel=.004, seg=2)
        p.box((.246, sg * army(.246), zc), (.008, .033, .032), 'Rubber', .3, bevel=.003, seg=1, rot=(0, 0, ang))
    slab(p, S.CUTTERS[2], 0, .036, 'ToolSteel', .5, bevel=.003, seg=2)
    for sg in (1, -1):
        blade = [(.548, sg * .0305), (.600, sg * .0165), (.600, sg * .0018), (.588, sg * .0040), (.548, sg * .0200)]
        slab(p, blade, .008, .028, 'Steel', .5, bevel=.0008, seg=1)
    p.box((.595, 0, .018), (.014, .0032, .026), 'Iron', .4, bevel=0, seg=1)
    for zz, sgn in ((.036, 1), (0.0, -1)):
        p.begin()
        p.lathe([(.0125, 0), (.0125, .0014), (.010, .0034), (.0075, .0045), (0, .0048)], 'Steel', .5, segs=6, axis=(0, 0, 1), caps=(False, True))
        p.end(T(.500, 0, zz) if sgn > 0 else T(.500, 0, zz, rx=180))
    # repair tag on a twine loop round the lower arm, hanging in front of the board
    gx = .30
    gy = -army(gx)
    ring = [(gx, gy + .0205 * math.cos(a), zc + .0215 * math.sin(a)) for a in [i * 2 * PI / 20 for i in range(20)]]
    p.tube(ring, .0016, 'Twine', .10, sides=4, closed=True)
    p.tube([(gx, gy - .0205, zc), (gx, gy - .034, zc + .002), (gx, gy - .046, zc + .003)], .0016, 'Twine', .10, sides=4)
    tag(p, gx, gy - .046 - .032, zc + .004, w=.046, h=.058, rz=-8)


spec = S.PLACEMENT['BoltCutters']
zb_c = BZ + .014
o_c = spec['origin']
make('TE_ToolBoltCutters', 15, (o_c[0], o_c[1], zb_c),
     lambda p: (p.begin(), build_cutters(p), p.end(T(o_c[0], o_c[1], zb_c, rz=spec['deg']))))
cutter_pegs = [A_of((xl, -(.034 - .016 * xl / .42) - .0115 - .0035 - .0008), o_c, spec['deg']) for xl in (.085, .30)]


# ================================================================ 6. rest pegs for hammer and cutters
def build_rest_pegs(p):
    for (x, y) in hammer_pegs + cutter_pegs:
        peg(p, x, y, BZ, length=.064, rest=True)


make('TE_RestPegs', 16, (-2.15, 1.5, BZ), build_rest_pegs)


# ================================================================ 7. bench tools: whetstone on a cradle, G-clamp with tag, file
def build_bench(p):
    top = S.BENCH['y']
    # whetstone in a timber cradle
    p.begin()
    p.box((0, .011, 0), (.250, .022, .070), 'Timber', .5, bevel=.003, seg=2)
    for sx in (-1, 1):
        p.box((sx * .119, .030, 0), (.014, .030, .074), 'Timber', .5, bevel=.003, seg=2)
    stone_top = lambda co, n: ((co.x + .10) / .25, (co.z + .0225) / .25)
    p.box((0, .022 + .014, 0), (.200, .028, .045), 'Stone', .25, bevel=.0035, seg=2, over=[(1, 1, 'Stone', .25, stone_top)])
    p.end(T(-1.80, top, 2.235, ry=6))
    # G-clamp standing on its bottom arm: cast frame, threaded screw, swivel pad, T-bar and a tagged twine tie
    p.begin()
    path = [(.070, .012), (.030, .012), (.000, .016), (-.030, .028), (-.050, .050), (-.056, .078), (-.048, .108), (-.028, .128), (0.0, .138), (.030, .142), (.070, .142)]
    sec = [(-.0055, -.009), (.0055, -.009), (.0055, .009), (-.0055, .009)]
    p.sweep([(x, y, 0.0) for x, y in path], sec, (0, 0, 1), 'Iron', .4)
    p.box((.070, .014, 0), (.030, .024, .026), 'Iron', .4, bevel=.003, seg=2)
    p.box((.070, .142, 0), (.032, .022, .026), 'Iron', .4, bevel=.003, seg=2)
    p.lathe([(.0052, .010), (.0058, .030), (.0052, .050), (.0058, .070), (.0052, .090), (.0058, .112), (.0052, .150)], 'ToolSteel', .5, pos=(.070, 0, 0), axis=(0, 1, 0), segs=14,
            warp=lambda a, h: 1 + (.10 * math.sin(h * 900) if .04 < h < .12 else 0.0))
    p.lathe([(.0135, .022), (.0135, .030), (.0095, .035), (.005, .035)], 'Steel', .5, pos=(.070, 0, 0), axis=(0, 1, 0), segs=20, caps=(True, False))
    p.tube([(.070, .1560, -.052), (.070, .1560, .052)], .0038, 'Steel', .5, sides=8)
    for sz in (-1, 1):
        p.lathe([(0, 0), (.0068, 0), (.0068, .004), (.0045, .0095), (0, .010)], 'Steel', .5, pos=(.070, .156, sz * .052), axis=(0, 0, sz), segs=12)
    ring = [(.070 + .0058 * math.cos(a), .156 + .0058 * math.sin(a), .038) for a in [i * 2 * PI / 16 for i in range(16)]]
    p.tube(ring, .0018, 'Twine', .10, sides=4, closed=True)
    p.tube([(.070, .1502, .038), (.071, .128, .039), (.072, .112, .039)], .0016, 'Twine', .10, sides=4)
    tag(p, .072, .088, .039, w=.050, h=.034, rz=-4)
    p.end(T(-2.44, top, 2.22, ry=32) @ Matrix.Scale(1.5, 4))
    # flat file with ash handle lying across the bench, tip resting on the timber
    p.begin()
    p.lathe([(0, -.090), (.0100, -.088), (.0148, -.070), (.0156, -.045), (.0140, -.016), (.0110, -.004)], 'TimberPolished', .5, axis=(1, 0, 0), segs=22, caps=(False, True))
    p.lathe([(.0116, -.010), (.0118, .002)], 'Brass', .5, axis=(1, 0, 0), segs=22, caps=(False, False))
    p.lathe([(.0075, -.028), (.0065, .006)], 'Steel', .5, axis=(1, 0, 0), segs=8, caps=(False, False))
    blade = [(0.0, -.0110), (.220, -.0115), (.260, -.0010), (.220, .0115), (0.0, .0110)]
    slab(p, blade, -.0022, .0022, 'Steel', .5, bevel=.0006, seg=1)
    p.end(T(-1.74, top + .0156 + .0009, 2.36, ry=-12) @ Matrix.Rotation(math.radians(-2.6), 4, 'Z') @ Matrix.Rotation(PI / 2, 4, 'X'))


make('TE_BenchTools', 17, (-2.15, S.BENCH['y'], 2.24), build_bench)


# ================================================================ 8. display lamp housing (no light, no emissive; light anchor is a handoff decision)
def build_lamp(p):
    x0 = -1.78
    p.box((x0, 2.178, 2.150), (.10, .014, .06), 'ShutterPaint', .6, bevel=.003, seg=2)                       # soffit plate
    for bx in (-.032, .032):
        bolt(p, x0 + bx, 2.171, 2.150, r=.0062, h=.004, axis='yd')
    p.tube([(x0, 2.171, 2.150), (x0, 2.135, 2.150), (x0, 2.100, 2.165), (x0, 2.085, 2.205), (x0, 2.088, 2.245)], .0075, 'Iron', .4, sides=8)      # swan neck
    prof = [(.020, 0), (.030, .014), (.062, .052), (.092, .086), (.096, .092), (.090, .092), (.086, .086), (.056, .050), (.026, .016), (.016, .006)]
    p.lathe(prof, 'PaintRed', .5, pos=(x0, 2.010, 2.270), axis=(0, 1, 0), segs=40, caps=(False, False))
    p.lathe([(.016, .006), (.0, .0)], 'Brass', .5, pos=(x0, 2.010, 2.270), axis=(0, 1, 0), segs=16, caps=(False, True))
    p.lathe([(.0, .052), (.010, .049)], 'Brass', .5, pos=(x0, 2.010, 2.270), axis=(0, 1, 0), segs=16, caps=(False, True))


make('TE_DisplayLamp', 18, (-1.78, 2.185, 2.15), build_lamp)


# ================================================================ 9. shutter guide rails (formed channel, retains the slat edges) - one per side
def build_guide(p, x0, d, wear_len, wear_y0):
    """x0 = masonry reveal face (A-space); d = +1 running right from the left reveal, -1 running left from the right reveal."""
    y0, y1 = .090, 2.750
    zr0, zr1, zf0, zf1, zl = 2.5825, 2.5945, 2.660, 2.672, 2.722
    yc = (y0 + y1) / 2
    cx = lambda a, b: x0 + d * (a + b) / 2
    p.box((cx(0, .012), yc, (zr0 + zf1) / 2), (.012, y1 - y0, zf1 - zr0), 'ShutterPaint', .6, bevel=.0018, seg=1)              # web on the masonry
    p.box((cx(0, .068), yc, (zr0 + zr1) / 2), (.068, y1 - y0, zr1 - zr0), 'ShutterPaint', .6, bevel=.0018, seg=1)              # rear flange
    p.box((cx(0, .085), yc, (zf0 + zf1) / 2), (.085, y1 - y0, zf1 - zf0), 'ShutterPaint', .6, bevel=.0018, seg=1)              # front flange over the slat edge
    p.box((cx(.075, .085), yc, (zf1 + zl) / 2), (.010, y1 - y0, zl - zf1), 'ShutterPaint', .6, bevel=.0015, seg=1)             # formed return lip
    p.box((cx(0, .140), 2.585, zf1 + .004), (.140, .320, .008), 'ShutterPaint', .6, bevel=.002, seg=2)                         # top bracket plate to the drum casing
    for bx in (.035, .105):
        for by in (2.475, 2.695):
            bolt(p, x0 + d * bx, by, zf1 + .008, r=.0085, h=.006)
    for by in (.42, 1.02, 1.62, 2.22):                                                                                          # fixings through the front flange
        bolt(p, x0 + d * .030, by, zf1, r=.0075, h=.0055)
    p.box((cx(.016, .066), wear_y0 + wear_len / 2, zf1 + .0025), (.050, wear_len, .005), 'Steel', .5, bevel=.0012, seg=1)     # rub plate, bare where hands push
    for k in range(3):
        bolt(p, x0 + d * .041, wear_y0 + .035 + k * (wear_len - .07) / 2, zf1 + .005, r=.0052, h=.0038)


make('TE_ShutterGuide_L', 21, (-.70, 0.0, 2.605), lambda p: build_guide(p, -.70, 1, .46, .70))
make('TE_ShutterGuide_R', 22, (2.75, 0.0, 2.605), lambda p: build_guide(p, 2.75, -1, .26, .82))


# ================================================================ 10. shutter hardware: handle plates, D-handles, lock box, hasp, padlock, kick plate
def build_shutter_hw(p):
    Z0 = 2.655
    atl = lambda zone, ox, oy: (lambda co, n: ((ATL[zone]['x0'] + (co.x - ox)) / 2.0, (ATL[zone]['y0'] + (co.y - oy)) / .5))
    hy = .82
    for zone, hx in (('HandlePlate_L', .475), ('HandlePlate_R', 1.575)):
        w, h = ATL[zone]['w'], ATL[zone]['h']
        ox, oy = hx - w / 2, hy - h / 2
        p.box((hx, hy, Z0 + .004), (w, h, .008), 'ShutterPaint', .6, bevel=.003, seg=2, over=[(2, 1, 'ShutterFit', 1.0, atl(zone, ox, oy))])
        for bx in (.03, w - .03):
            for by in (.03, h - .03):
                bolt(p, ox + bx, oy + by, Z0 + .008, r=.0075, h=.0055)
        for px in (hx - .130, hx + .130):
            p.lathe([(.0105, 0), (.0085, .012), (.0075, .040), (.0090, .062)], 'Brass', .5, pos=(px, hy, Z0 + .008), axis=(0, 0, 1), segs=14, caps=(True, True))
        p.tube([(hx - .135, hy, Z0 + .0715), (hx + .135, hy, Z0 + .0715)], .0115, 'Brass', .5, sides=10)
    lx, ly = 1.025, .820
    lw, lh = ATL['LockBox']['w'], ATL['LockBox']['h']
    p.box((lx, ly, Z0 + .025), (lw, lh, .050), 'ShutterPaint', .6, bevel=.005, seg=2, over=[(2, 1, 'ShutterFit', 1.0, atl('LockBox', lx - lw / 2, ly - lh / 2))])
    for bx in (.028, lw - .028):
        for by in (.028, lh - .028):
            bolt(p, lx - lw / 2 + bx, ly - lh / 2 + by, Z0 + .050, r=.0075, h=.0055)
    ex, ey = lx, ly + .020
    escuv = lambda co, n: ((ATL['Escutcheon']['x0'] + .05 + (co.x - ex)) / 2.0, (ATL['Escutcheon']['y0'] + .05 + (co.y - ey)) / .5)
    esc_faces = p.lathe([(.042, 0), (.042, .0025), (.038, .0040)], 'ShutterFit', 1.0, pos=(ex, ey, Z0 + .050), axis=(0, 0, 1), segs=36, caps=(True, True))
    p.uv_fn([f for f in esc_faces if f.normal.z > .5], escuv)
    hw, hh = ATL['Hasp']['w'], ATL['Hasp']['h']
    hy0 = ly - lh / 2 - hh + .012
    p.box((lx, hy0 + hh / 2, Z0 + .005), (hw, hh, .010), 'ShutterPaint', .6, bevel=.003, seg=2, over=[(2, 1, 'ShutterFit', 1.0, atl('Hasp', lx - hw / 2, hy0))])
    for by in (.03, hh - .03):
        bolt(p, lx, hy0 + by, Z0 + .010, r=.0072, h=.005)
    sy_ = hy0 + .085
    p.tube([(lx - .034, sy_, Z0 + .010), (lx - .034, sy_, Z0 + .041), (lx + .034, sy_, Z0 + .041), (lx + .034, sy_, Z0 + .010)], .0042, 'Steel', .5, sides=8)     # staple
    py_ = hy0 + .060
    p.box((lx, py_ - .030, Z0 + .026), (.058, .058, .028), 'Brass', .5, bevel=.007, seg=3)                                                                       # padlock body
    zs = Z0 + .026
    p.tube([(lx - .019, py_, zs), (lx - .019, py_ + .026, zs), (lx - .012, py_ + .038, zs), (lx, py_ + .043, zs), (lx + .012, py_ + .038, zs), (lx + .019, py_ + .026, zs),
            (lx + .019, py_, zs)], .0038, 'Steel', .5, sides=8)                                                                                                     # shackle through the staple
    kx0, ky0, kw, kh = .425, .100, 1.20, .10
    p.box((kx0 + kw / 2, ky0 + kh / 2, Z0 + .003), (kw, kh, .006), 'ShutterPaint', .6, bevel=.002, seg=2, over=[(2, 1, 'ShutterFit', 1.0, atl('KickPlate', kx0, ky0))])
    for k in range(7):
        bolt(p, kx0 + .05 + k * (kw - .10) / 6, ky0 + kh - .022, Z0 + .006, r=.0065, h=.0048)


make('TE_ShutterHardware', 23, (1.025, 0.0, 2.655), build_shutter_hw)


# ================================================================ 11. display glazing (same panes as revision 04; clear glass with dust film)
def build_glass(p):
    for i, (gx0, gx1) in enumerate(S.GLASS['panes']):
        z0, z1 = S.GLASS['z0'], S.GLASS['z1']
        y0, y1 = S.GLASS['y0'], S.GLASS['y1']
        pw = gx1 - gx0
        fn = lambda co, n, gx0=gx0, pw=pw, i=i: (i * .5 + .5 * (co.x - gx0) / pw, (co.y - y0) / (y1 - y0))
        p.box(((gx0 + gx1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), (pw, y1 - y0, z1 - z0), 'Glass', 1.0, bevel=.0012, seg=1,
              over=[(2, 1, 'Glass', 1.0, fn), (2, -1, 'Glass', 1.0, fn)])


make('TE_DisplayGlazing', 24, (-2.15, S.GLASS['y0'], S.GLASS['z0']), build_glass)
gm = bpy.data.materials['TE_Glass']
pb = gm.node_tree.nodes['Principled BSDF']
for n_ in gm.node_tree.nodes:
    if n_.type == 'TEX_IMAGE' and n_.image and n_.image.name.endswith('DisplayGlass_BaseColor.png'):
        gm.node_tree.links.new(n_.outputs['Alpha'], pb.inputs['Alpha'])
        n_.image.alpha_mode = 'STRAIGHT'
gm['alphaMode'] = 'blend'

# ================================================================ summarise
info = {}
for name, origin, o in parts:
    s = L.stats(o)
    info[name] = {'pivotAuthoring': list(origin), **s, 'materialSlots': [m.get('ward_slot') for m in o.data.materials]}
    print(name, s['tris'], 'tris', s['sizeA'], s['boundsAmin'], s['boundsAmax'])
(OUT / 'build-stats-raw.json').write_text(json.dumps({'parts': info, 'materials': L.RECORDS,
                                                       'pegs': {'wrench': list(WR_PEG), 'hammer': [list(x) for x in hammer_pegs], 'cutters': [list(x) for x in cutter_pegs]}}, indent=2))

RETIRE = ('tool_exchange Recessed tool display dark recess', 'tool_exchange Recessed tool display glass', 'tool_exchange Shutter guide rail',
          'tool_exchange Shutter lift handle')
retired = []
for o in list(scene.objects):
    if o.name.startswith(RETIRE):
        retired.append(o.name)
        o['te_retired'] = True
bpy.data.texts.new('te_retired_objects.txt').write('\n'.join(sorted(retired)))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'tool-exchange-display-source-v1.blend'), compress=True)
print('SAVED', len(parts), 'parts;', len(retired), 'retired in review scene')
