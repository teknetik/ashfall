"""Ward shade sails: geometry, Blender 5.2 headless (1 October 2026).

Reads sail-layout.json (sails.py: layout, validation) and builds, per site, three LOD pairs of glTF models:

* SS_<Site>_Sail_LOD0/1 — the canvas, form-found with the force density method (formfind.py: a prestressed membrane
  between corner fixings, hem cables tuned to a 5-7 % sag, a slight belly), a rolled hem with its wire rope, corner
  plates and rings, and the corner hardware out to the pole padeyes (turnbuckle and shackle, or a salvage rope lashing).
  LOD1 is the same surface sampled every 4th node (0.5 m), used by Unity as the sail's shadow caster at every distance.
* SS_<Site>_Rig_LOD0/1 — 114 mm steel poles raked 4 deg away from the sail, cap, padeyes, festoon hooks; footings:
  dressed-stone blocks (Ward masonry kit) with a steel collar, or welded base plates in a ring of sandbags with a guy
  wire (thimble, clips, turnbuckle) to a sandbagged anchor plate; wire-rope strops on the retrofit service poles
  (I-beams).
  Rig objects are split into casters (poles, blocks) and the rest (hardware, bags, wires) for the shadow settings.
* SS_<Site>_Festoon_LOD0/1 — rubber festoon cable on a parabolic catenary between the pole hooks, lampholders on drop
  leads, warm globe bulbs (a few dead or missing).

Units: Unity metres; each site's models have their origin at the site centre on the paving (sails.json "origin").
Out: unity/AthenHill/Assets/AthenHill/Art/ShadeSails/Models/*.glb and Models/sails.json (origins, triangle counts, the
canvas UV layout for make_textures.py, light positions, colliders).
Run:  $O/blender.sh art/shade_sails_20261001/author_sails.py [-- Site ...]
"""
import bpy, bmesh, json, math, random, sys, zlib
from pathlib import Path
from mathutils import Vector, Matrix
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "art/ward_masonry_kit"))
sys.path.insert(0, str(ROOT / "art/rooftops_20261001"))
import formfind as FF
import ward_masonry as WM
from ward_masonry import Part, U, export, tri_count, finalize_parts
import author_roof_kit as K

OUT = ROOT / "unity/AthenHill/Assets/AthenHill/Art/ShadeSails/Models"
OUT.mkdir(parents=True, exist_ok=True)
LAYOUT = json.loads((HERE / "sail-layout.json").read_text())
CONST = LAYOUT["constants"]

DYE_CLOTH = {"madder": "WS_ClothMadder", "indigo": "WS_ClothIndigo", "natural": "WS_ClothBone", "natural_indigo": "WS_ClothBone"}
# pole paints: tinted copies of VH_Steel's weathered sheet-steel maps (ShadeSailsPass makes them; VH_Paint is grooved)
POLE_PAINT = {"Courtyard": "SS_PoleGrey", "Market": "SS_PoleRed", "Apron": "SS_PoleOlive", "Lattice": "SS_PoleGrey"}
# corner hardware per site: "tb" turnbuckle + shackle, "lash" rope lashing (salvage)
HARDWARE = {"Courtyard": ["tb", "tb", "tb", "tb"], "Market": ["lash", "lash", "lash", "tb"], "Apron": ["tb", "lash", "tb", "tb"],
            "Lattice": ["tb", "tb", "lash"]}
LOD = 0


def rng(*key):
    return random.Random(zlib.crc32(repr(key).encode()))


def V(p):
    return Vector((float(p[0]), float(p[1]), float(p[2])))


def frame(axis):
    a = Vector(axis).normalized()
    ref = Vector((0, 1, 0)) if abs(a.y) < 0.9 else Vector((1, 0, 0))
    u = a.cross(ref).normalized()
    v = a.cross(u).normalized()
    return a, u, v


# ====================================================================== canvas
def sail_object(name, sail, nodes, faces, origin, uvmap, mat, coll):
    """Mesh object from formfind nodes (Unity coords), per-vertex UVs from the planar layout, smooth shading."""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    idmap = {}
    for k in nodes:
        p = sail.P[k] - origin
        idmap[k] = bm.verts.new(U(p))
    for f in faces:
        try:
            face = bm.faces.new([idmap[k] for k in f])
        except ValueError:
            continue
        for l, k in zip(face.loops, f):
            l[uvl].uv = (float(uvmap[k][0]), float(uvmap[k][1]))
    # U() is a reflection: flip winding so the upper face keeps an outward (+Y) normal
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    bm.normal_update()
    up = sum((f.normal for f in bm.faces), Vector())
    if up.z < 0:                                   # Blender z = Unity y: make the top face the front face
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(WM.material(mat))
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    WM.triangulate(ob)
    return ob


def corner_patch_points(sail):
    return [sail.P[c] for c in sail.corner_ids]


# ====================================================================== hardware primitives (Part, Unity coords)
def eye(part, c, normal, R, r, mat, n=14, m=6):
    K.torus(part, tuple(c), tuple(normal), R, r, mat, n, m)


def shackle(part, pin_c, pin_axis, bow_dir, mat):
    """Bow shackle: pin along pin_axis through pin_c, bow (half torus) towards bow_dir."""
    a = Vector(pin_axis).normalized()
    d = Vector(bow_dir).normalized()
    d = (d - a * d.dot(a)).normalized()
    c = Vector(pin_c)
    w = 0.026
    K.rod(part, tuple(c - a * (w + 0.012)), tuple(c + a * (w + 0.012)), 0.0065, mat, 8)
    # bow: arc from one ear to the other, through c + d*0.06
    pts = []
    n = 10 if LOD == 0 else 5
    for i in range(n + 1):
        t = math.pi * i / n
        pts.append(c + a * (w * math.cos(t)) + d * (0.012 + 0.055 * math.sin(t)))
    K.sweep_tube(part, pts, 0.0065, mat, 8, cap=True)


def turnbuckle(part, a, b, mat):
    """Open-body turnbuckle with eye ends between points a and b (eye centres)."""
    a, b = Vector(a), Vector(b)
    d = b - a
    L = d.length
    ax, u, v = frame(d)
    mid = (a + b) / 2
    body = min(0.16, L * 0.45)
    # body: two side bars and two bosses
    for s in (-1, 1):
        K.rod(part, tuple(mid - ax * body / 2 + u * 0.013 * s), tuple(mid + ax * body / 2 + u * 0.013 * s), 0.0045, mat, 6)
    for s in (-1, 1):
        K.rod(part, tuple(mid + ax * (body / 2 * s - 0.008)), tuple(mid + ax * (body / 2 * s + 0.008)), 0.017, mat, 10)
    # threaded rods into the eyes
    K.rod(part, tuple(a + ax * 0.02), tuple(mid - ax * body / 2), 0.0065, mat, 8)
    K.rod(part, tuple(mid + ax * body / 2), tuple(b - ax * 0.02), 0.0065, mat, 8)
    eye(part, a + ax * 0.0, u, 0.017, 0.0055, mat, 12, 5)
    eye(part, b - ax * 0.0, u, 0.017, 0.0055, mat, 12, 5)


def lashing(part, a, b, key):
    """Salvage rope lashing: four strands between the padeye eye a and the corner ring b, whipped at both ends."""
    a, b = Vector(a), Vector(b)
    ax, u, v = frame(b - a)
    R = rng("lash", key)
    for k in range(4):
        t = 2 * math.pi * k / 4 + R.uniform(-0.3, 0.3)
        off = (u * math.cos(t) + v * math.sin(t))
        pts = [a + off * 0.008, (a * 0.5 + b * 0.5) + off * (0.016 + R.uniform(0, 0.006)) + Vector((0, -0.006, 0)), b + off * 0.01]
        K.sweep_tube(part, pts, 0.0055, "SD_Rope", 5, cap=True)
    if LOD == 0:
        for c, nax in ((a + ax * 0.06, ax), (b - ax * 0.07, ax)):
            for j in range(3):
                K.torus(part, tuple(c + nax * (j * 0.011)), tuple(nax), 0.022, 0.0055, "SD_Rope", 10, 4)


def corner_plate(part, corner, toward, normal, key):
    """Sail corner: a pair of triangular steel plates through the canvas, bolted, with a D-ring at the tip."""
    c = Vector(corner)
    t = Vector(toward).normalized()            # from the fabric corner out to the fixing
    nrm = Vector(normal).normalized()
    t = (t - nrm * t.dot(nrm)).normalized()
    side = nrm.cross(t).normalized()
    L, W, th = 0.15, 0.12, 0.004
    for s in (-1, 1):
        o = nrm * (s * (th / 2 + 0.002))
        tip = c + t * 0.035 + o
        b0 = c - t * L + side * W / 2 + o
        b1 = c - t * L - side * W / 2 + o
        verts = [tuple(tip), tuple(b0), tuple(b1), tuple(tip + nrm * s * th), tuple(b0 + nrm * s * th), tuple(b1 + nrm * s * th)]
        part.closed_solid(verts, [[0, 1, 2], [3, 5, 4], [0, 3, 4, 1], [1, 4, 5, 2], [2, 5, 3, 0]], "VH_Steel")
    if LOD == 0:
        for (du, dv) in ((-0.07, 0.025), (-0.07, -0.025), (-0.11, 0.0)):
            p = c + t * du + side * dv
            K.rod(part, tuple(p - nrm * 0.012), tuple(p + nrm * 0.012), 0.0055, "VH_Dark", 6)
    ring_c = c + t * 0.06
    eye(part, ring_c, side, 0.026, 0.0065, "VH_Steel", 14, 6)
    return ring_c + t * 0.024                   # outer tip of the ring (hardware attaches here)


# ====================================================================== rig
def block_footing(part_stone, part_steel, base, key):
    """Dressed-stone footing (0.8 x 0.8 x 0.5 m) with a chamfered top, a steel collar and four collar bolts."""
    R = rng("block", key)
    b = Vector(base)
    h, w = 0.5, 0.4
    yaw = R.uniform(-8, 8)
    ca, sa = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    def P(x, y, z):
        return (b.x + x * ca + z * sa, b.y + y, b.z - x * sa + z * ca)
    bid = part_stone.new_block(tint=(0.5 + R.uniform(-0.04, 0.04), 0.5, 0.5 + R.uniform(-0.03, 0.03)))
    cs = [P(-w, 0, -w), P(w, 0, -w), P(w, 0, w), P(-w, 0, w), P(-w, h, -w), P(w, h, -w), P(w, h, w), P(-w, h, w)]
    _, made = part_stone.hexa(cs, "VH_Ashlar", bid)
    if made:
        edges = list({e for f in made.values() for e in f.edges if all(v.co.y > h - 0.01 for v in e.verts) or
                      (abs(e.verts[0].co.y - e.verts[1].co.y) > 0.3)})
        WM.eroded_bevel(part_stone, edges, 0.03, 2, 0.12)
    # steel collar and bolts on the top
    K.rod(part_steel, (b.x, b.y + h - 0.005, b.z), (b.x, b.y + h + 0.075, b.z), 0.082, "VH_Steel", 16)
    K.rod(part_steel, (b.x, b.y + h, b.z), (b.x, b.y + h + 0.012, b.z), 0.13, "VH_Steel", 16)
    if LOD == 0:
        for k in range(4):
            t = math.radians(45 + 90 * k + yaw)
            p = Vector((b.x + math.cos(t) * 0.105, b.y + h + 0.012, b.z + math.sin(t) * 0.105))
            K.rod(part_steel, tuple(p), tuple(p + Vector((0, 0.018, 0))), 0.011, "VH_Dark", 6)
    return h


def plate_footing(part_steel, part_bags, base, key, axis):
    """Welded base plate with gussets and bolts, ballasted by a ring of sandbags in two layers."""
    R = rng("plate", key)
    b = Vector(base)
    K.bbox(part_steel, (b.x, b.y + 0.01, b.z), (0.5, 0.02, 0.5), "VH_Steel", bev=0.004)
    a = Vector(axis).normalized()
    if LOD == 0:
        for k in range(4):
            t = math.radians(90 * k)
            d = Vector((math.cos(t), 0, math.sin(t)))
            p0 = b + Vector((0, 0.02, 0)) + d * 0.06
            verts = [tuple(p0 + d.cross(Vector((0, 1, 0))) * 0.005), tuple(p0 + d * 0.16 + d.cross(Vector((0, 1, 0))) * 0.005),
                     tuple(p0 + Vector((0, 0.17, 0)) + d.cross(Vector((0, 1, 0))) * 0.005)]
            verts += [tuple(Vector(q) - d.cross(Vector((0, 1, 0))) * 0.01) for q in verts]
            part_steel.closed_solid(verts, [[0, 1, 2], [3, 5, 4], [0, 3, 4, 1], [1, 4, 5, 2], [2, 5, 3, 0]], "VH_Steel")
            for s in (-1, 1):
                q = b + Vector((0, 0.02, 0)) + d * 0.2 + d.cross(Vector((0, 1, 0))) * 0.17 * s
                K.rod(part_steel, tuple(q), tuple(q + Vector((0, 0.02, 0))), 0.012, "VH_Dark", 6)
    # sandbags: a lower ring of five, an upper course of three
    for k in range(5):
        t = 2 * math.pi * k / 5 + R.uniform(-0.15, 0.15)
        c = b + Vector((math.cos(t), 0, math.sin(t))) * 0.36
        K.sandbag(part_bags, (c.x, 0.0, c.z), math.degrees(-t) + 90 + R.uniform(-12, 12), key=(key, "l", k))
    for k in range(3):
        t = 2 * math.pi * k / 3 + 0.5 + R.uniform(-0.2, 0.2)
        c = b + Vector((math.cos(t), 0, math.sin(t))) * 0.3
        K.sandbag(part_bags, (c.x, 0.12, c.z), math.degrees(-t) + 90 + R.uniform(-15, 15), key=(key, "u", k))


def anchor(part_steel, part_bags, at, toward, key):
    """Guy anchor: steel plate with a welded ring, held down by three sandbags (the ring left clear)."""
    R = rng("anchor", key)
    a = Vector(at)
    d = Vector(toward); d.y = 0; d.normalize()
    K.bbox(part_steel, (a.x, 0.01, a.z), (0.42, 0.02, 0.42), "VH_Steel", bev=0.003)
    ring_c = a + d * 0.1 + Vector((0, 0.045, 0))
    eye(part_steel, ring_c, d.cross(Vector((0, 1, 0))), 0.03, 0.007, "VH_Steel", 12, 5)
    side = d.cross(Vector((0, 1, 0)))
    for k, (du, dv, y) in enumerate(((-0.12, -0.1, 0.02), (-0.12, 0.12, 0.02), (-0.1, 0.0, 0.15))):
        c = a + d * du + side * dv
        K.sandbag(part_bags, (c.x, y, c.z), math.degrees(math.atan2(d.x, d.z)) + 90 + R.uniform(-10, 10), w=0.48, d=0.28, h=0.13, key=(key, k))
    return ring_c


def pole(part_pole, part_steel, p, key, paint):
    """Steel pole from its footing along the raked axis: shaft, cap, sail padeye, festoon hook, guy padeye."""
    axis = Vector(p["axis"])
    base_y = 0.5 if p["kind"] == "block" else 0.02
    b0 = Vector(p["base"]) + Vector((0, base_y, 0))
    top = Vector(p["top"])
    r = p["radius"]
    sides = 18 if LOD == 0 else 8
    part_pole.cyl(tuple(b0 - axis * (0.06 if p["kind"] == "block" else 0)), tuple(top), r, paint, sides, cap=True)
    # cap and galvanised bands (old repair sleeves)
    K.rod(part_steel, tuple(top - axis * 0.004), tuple(top + axis * 0.022), r + 0.006, "VH_Dark", sides)
    if LOD == 0:
        R = rng("bands", key)
        for y in (0.9 + R.uniform(0, 0.4), 2.3 + R.uniform(0, 0.5)):
            c = b0 + axis * y
            K.rod(part_steel, tuple(c), tuple(c + axis * 0.05), r + 0.004, "VH_Steel", sides)
    fix = Vector(p["fixing"])
    out = Vector(p["outward"]); out.y = 0; out.normalize()
    inward = -out
    # sail padeye: plate welded on the sail side, eye at the fixing point
    pc = fix - inward * 0.03
    K.oriented_box(part_steel, tuple(pc + Vector((0, -0.015, 0))), tuple(inward), (0, 1, 0), (0.07, 0.11, 0.012), "VH_Steel")
    eye(part_steel, fix, inward.cross(Vector((0, 1, 0))), 0.022, 0.007, "VH_Steel", 14, 6)
    # festoon hook below it
    hook = fix - Vector((0, CONST["festoon_drop"], 0))
    K.oriented_box(part_steel, tuple(hook - inward * 0.035), tuple(inward), (0, 1, 0), (0.05, 0.06, 0.01), "VH_Steel")
    eye(part_steel, hook, inward.cross(Vector((0, 1, 0))), 0.014, 0.005, "VH_Steel", 12, 5)
    guy_eyes = []
    for k, g in enumerate(p["guys"]):
        d = Vector(g) - Vector(p["base"]); d.y = 0; d.normalize()
        ge = fix + Vector((0, -0.16 - 0.06 * k, 0)) + d * (r + 0.035) - inward * 0.0
        ge = Vector((ge.x, ge.y, ge.z))
        # project onto the pole surface on the guy side
        on_axis = b0 + axis * ((ge - b0).dot(axis))
        ge = on_axis + d * (r + 0.035)
        K.oriented_box(part_steel, tuple(on_axis + d * (r + 0.012)), tuple(d), (0, 1, 0), (0.05, 0.09, 0.012), "VH_Steel")
        eye(part_steel, ge, d.cross(Vector((0, 1, 0))), 0.018, 0.006, "VH_Steel", 12, 5)
        guy_eyes.append(ge)
    return fix, hook, guy_eyes


def service_strop(part_steel, p, key):
    """On an existing retrofit service pole (an I-beam, flanges facing +-Z, 0.20 x 0.26 m): a wire-rope strop choked
    round the beam with a thimble eye and shackle on the face towards the sail at the fixing height; a lighter strop
    lower down carries the festoon hook."""
    base = Vector(p["base"])
    fix = Vector(p["fixing"])
    hx, hz = CONST["service_half"]
    out = Vector(p["outward"]); out.y = 0; out.normalize()
    inward = -out
    for (y, eye_at, R_eye, rr) in ((fix.y, fix, 0.024, 0.0065), (fix.y - CONST["festoon_drop"], fix - Vector((0, CONST["festoon_drop"], 0)), 0.015, 0.005)):
        c = Vector((base.x, y, base.z))
        # rounded rectangle just outside the flanges
        ex, ez, rc = hx + 0.012, hz + 0.012, 0.03
        pts = []
        for (cx, cz, a0) in ((ex - rc, ez - rc, 0), (-(ex - rc), ez - rc, 90), (-(ex - rc), -(ez - rc), 180), ((ex - rc), -(ez - rc), 270)):
            for k in range(4):
                a = math.radians(a0 + 90 * k / 3)
                pts.append(c + Vector((cx + math.cos(a) * rc, 0, cz + math.sin(a) * rc)))
        pts.append(pts[0])
        K.sweep_tube(part_steel, pts, rr, "VH_Steel", 6, cap=False)
        # the choke: both legs run from the beam face out to the eye
        exit_pt = c + inward * min(ex / max(abs(inward.x), 1e-6), ez / max(abs(inward.z), 1e-6))
        side = inward.cross(Vector((0, 1, 0))).normalized()
        for s_ in (-1, 1):
            K.sweep_tube(part_steel, [exit_pt + side * 0.03 * s_, eye_at - inward * R_eye], rr, "VH_Steel", 6, cap=True)
        eye(part_steel, eye_at, side, R_eye, rr * 1.1, "VH_Steel", 12, 5)
    return fix


def guy(part_steel, a, b, key):
    """Guy wire from the pole eye a to the anchor ring b: wire, thimble clips at the top, turnbuckle near the ground."""
    a, b = Vector(a), Vector(b)
    d = (b - a)
    L = d.length
    ax = d.normalized()
    tb_a = b - ax * 0.75
    tb_b = b - ax * 0.42
    K.sweep_tube(part_steel, [a, tb_a], 0.0045, "VH_Steel", 6, cap=True)
    K.sweep_tube(part_steel, [tb_b, b], 0.0045, "VH_Steel", 6, cap=True)
    turnbuckle(part_steel, tb_a, tb_b, "VH_Steel")
    if LOD == 0:
        for k in range(2):
            c = a + ax * (0.06 + 0.05 * k)
            K.rod(part_steel, tuple(c - ax * 0.012), tuple(c + ax * 0.012), 0.011, "VH_Dark", 8)


# ====================================================================== festoons
def festoon(part_cable, part_lit, part_dead, s, key):
    pts = [Vector(p) for p in s["points"]]
    K.sweep_tube(part_cable, pts, 0.0055, "VH_Rubber", 6, cap=True)
    R = rng("festoon", key)
    dead = set(R.sample(range(len(s["bulbs"])), max(1, len(s["bulbs"]) // 12)))
    missing = set(R.sample(range(len(s["bulbs"])), max(0, len(s["bulbs"]) // 20))) - dead
    for k, bp in enumerate(s["bulbs"]):
        c = Vector(bp)
        drop = 0.03 + R.uniform(0, 0.02)
        holder_top = c - Vector((0, 0.008, 0))
        holder_bot = holder_top - Vector((0, 0.048, 0))
        part_cable.cyl(tuple(holder_top + Vector((0, 0.006, 0))), tuple(holder_bot), 0.016, "VH_Rubber", 10 if LOD == 0 else 6, cap=True)
        if k in missing:
            continue
        bc = holder_bot - Vector((0, 0.03 + drop * 0.2, 0))
        tgt = part_dead if k in dead else part_lit
        seg = 10 if LOD == 0 else 6
        tgt.sphere(tuple(bc), 0.03, "SS_BulbDead" if k in dead else "SS_FestoonBulb", seg)
        tgt.cyl(tuple(holder_bot), tuple(bc + Vector((0, 0.018, 0))), 0.012, "SS_BulbDead" if k in dead else "SS_FestoonBulb", 8 if LOD == 0 else 5, cap=False)
    if LOD == 0:                                   # wraps at the hooks
        for end, nxt in ((pts[0], pts[1]), (pts[-1], pts[-2])):
            d = (nxt - end).normalized()
            for j in range(3):
                K.torus(part_cable, tuple(end + d * (0.02 + j * 0.012)), tuple(d), 0.009, 0.004, "VH_Rubber", 8, 4)


# ====================================================================== per site
def build_site(site, lod):
    global LOD
    LOD = lod
    K.LOD = lod
    WM.set_state(lod, random.Random(7), "ss_" + site["id"])
    WM.reset_materials()
    sid = site["id"]
    fab = np.array(site["fabric"])
    spacing = 0.125
    sail = FF.Sail(fab, spacing=spacing, sag=dict(Courtyard=0.06, Market=0.055, Apron=0.06, Lattice=0.05)[sid], belly=0.06)
    origin = np.array([round(float(fab[:, 0].mean()), 2), 0.0, round(float(fab[:, 2].mean()), 2)])
    # planar UVs (metres in the best-fit plane) -> [0, 1] with a 3 % margin; same for both LODs
    puv, pc, e1, e2, nrm = sail.plane_uv()
    # rotate the planar frame so the sail fills the square texture best (smallest bounding square)
    best = None
    for deg in range(0, 180, 2):
        t = math.radians(deg)
        R2 = np.array([[math.cos(t), -math.sin(t)], [math.sin(t), math.cos(t)]])
        q = puv @ R2.T
        ext = float((q.max(0) - q.min(0)).max())
        if best is None or ext < best[0]:
            best = (ext, t)
    t = best[1]
    R2 = np.array([[math.cos(t), -math.sin(t)], [math.sin(t), math.cos(t)]])
    puv = puv @ R2.T
    e1, e2 = math.cos(t) * e1 - math.sin(t) * e2, math.sin(t) * e1 + math.cos(t) * e2
    lo = puv.min(0)
    S = float((puv.max(0) - lo).max()) * 1.06
    off = lo - (S - (puv.max(0) - lo)) / 2
    uv = (puv - off) / S
    coll = bpy.data.collections.new(f"SS_{sid}_LOD{lod}")
    bpy.context.scene.collection.children.link(coll)
    mat = f"SS_Sail_{sid}"
    objs_sail = []
    if lod == 0:
        nodes = range(len(sail.P))
        faces = sail.F
    else:
        keep, faces = sail.lod_nodes(4)
        nodes = sorted(set(keep.values()))
    objs_sail.append(sail_object(f"SS_{sid}_Fabric_LOD{lod}", sail, nodes, faces, origin, uv, mat, coll))
    # hem (rolled canvas round the wire rope), corner plates and rings, hardware to the padeyes
    hem = Part(f"SS_{sid}_Hem_LOD{lod}", wear=False)
    corners = Part(f"SS_{sid}_Corners_LOD{lod}", wear=False)
    cloth = DYE_CLOTH[site["dye"]]
    step = 1 if lod == 0 else 4
    for s_edges in sail.side_edges:
        chain = [s_edges[0][0]] + [e[1] for e in s_edges]
        chain = chain[::step] + ([chain[-1]] if (len(chain) - 1) % step else [])
        pts = [Vector(sail.P[k] - origin) for k in chain]
        # pull the hem tube's ends back from the corner (the corner plate covers them)
        K.sweep_tube(hem, pts, 0.012 if lod == 0 else 0.014, cloth, 7 if lod == 0 else 4, cap=True)
    n_up = Vector(nrm)
    tips = []
    for k, cid in enumerate(sail.corner_ids):
        c = Vector(sail.P[cid] - origin)
        fixp = Vector(np.array(site["fixings"][k]) - origin)
        tip = corner_plate(corners, c, fixp - c, n_up, (sid, k))
        tips.append(tip)
        kind = HARDWARE[sid][k]
        if kind == "tb":
            d = (fixp - tip)
            L = d.length
            ax = d.normalized()
            sh_pin = fixp - ax * 0.0
            shackle(corners, sh_pin, n_up.cross(ax), -ax, "VH_Steel")
            turnbuckle(corners, tip + ax * 0.012, fixp - ax * 0.075, "VH_Steel")
        else:
            lashing(corners, fixp, tip, (sid, k))
    parts_sail = [p for p in (hem, corners) if len(p.bm.faces)]
    finalize_parts(parts_sail)
    objs_sail += [p.build(coll, ao=None, macro=0.0, splash=0.0) for p in parts_sail]
    # ---- rig
    stone = Part(f"SS_{sid}_Stone_LOD{lod}", wear=True)
    pole_p = Part(f"SS_{sid}_Poles_LOD{lod}", wear=False)
    steel = Part(f"SS_{sid}_Steel_LOD{lod}", wear=False)
    bags = Part(f"SS_{sid}_Bags_LOD{lod}", wear=False)
    colliders = []
    for k, p in enumerate(site["poles"]):
        pp = dict(p)
        for key in ("base", "top", "fixing"):
            pp[key] = (np.array(p[key]) - origin).tolist()
        pp["guys"] = [(np.array(g) - origin).tolist() for g in p["guys"]]
        if p["kind"] == "service":
            service_strop(steel, pp, (sid, k))
            continue
        if p["kind"] == "block":
            block_footing(stone, steel, pp["base"], (sid, k))
            colliders.append(dict(name=f"COL_Footing_{k}", center=[pp["base"][0], 0.25, pp["base"][2]], size=[0.84, 0.5, 0.84]))
        else:
            plate_footing(steel, bags, pp["base"], (sid, k), pp["axis"])
            colliders.append(dict(name=f"COL_Ballast_{k}", center=[pp["base"][0], 0.14, pp["base"][2]], size=[1.0, 0.28, 1.0]))
        fix, hook, guy_eyes = pole(pole_p, steel, pp, (sid, k), POLE_PAINT[sid])
        top = Vector(pp["top"])
        colliders.append(dict(name=f"COL_Pole_{k}", a=pp["base"], b=list(top), radius=0.075))
        for j, g in enumerate(pp["guys"]):
            ring = anchor(steel, bags, g, Vector(pp["base"]) - Vector(g), (sid, k, j))
            guy(steel, guy_eyes[j], ring, (sid, k, j))
            colliders.append(dict(name=f"COL_GuyAnchor_{k}_{j}", center=[g[0], 0.13, g[2]], size=[0.55, 0.26, 0.55]))
    parts_rig = [p for p in (stone, pole_p, steel, bags) if len(p.bm.faces)]
    finalize_parts(parts_rig)
    objs_rig = []
    for p in parts_rig:
        if p is stone:
            objs_rig.append(p.build(coll, ao=None, ao_fn=lambda q, n: 0.55 + 0.45 * max(0.0, min(1.0, q.y / 0.5)), macro=0.08, splash=0.3))
        else:
            objs_rig.append(p.build(coll, ao=None, macro=0.0, splash=0.0))
    # ---- festoons
    cable = Part(f"SS_{sid}_FestoonCable_LOD{lod}", wear=False)
    lit = Part(f"SS_{sid}_FestoonBulbs_LOD{lod}", wear=False)
    dead = Part(f"SS_{sid}_FestoonDead_LOD{lod}", wear=False)
    for j, s in enumerate(site["festoons"]):
        ss = dict(s)
        ss["points"] = (np.array(s["points"]) - origin).tolist()
        ss["bulbs"] = (np.array(s["bulbs"]) - origin).tolist()
        festoon(cable, lit, dead, ss, (sid, j))
    parts_f = [p for p in (cable, lit, dead) if len(p.bm.faces)]
    finalize_parts(parts_f)
    objs_f = [p.build(coll, ao=None, macro=0.0, splash=0.0) for p in parts_f]
    rec = dict(origin=origin.tolist(), spacing=spacing if lod == 0 else spacing * 4, sags=sail.sags,
               nodes=len(sail.P), uv=dict(origin=pc.tolist(), e1=e1.tolist(), e2=e2.tolist(), normal=nrm.tolist(), off=off.tolist(), size=S),
               outline_uv=uv[sail.loop].round(5).tolist(), corners_uv=uv[sail.corner_ids].round(5).tolist(),
               corner_heights=[float(sail.P[c][1]) for c in sail.corner_ids],
               grid_uv=uv[::7].round(4).tolist(), grid_y=sail.P[::7, 1].round(3).tolist(),
               colliders=colliders, lowest=float(sail.P[:, 1].min()))
    return objs_sail, objs_rig, objs_f, rec


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    only = set(argv)
    rec_path = OUT / "sails.json"
    record = json.loads(rec_path.read_text()) if rec_path.exists() else {}
    for site in LAYOUT["sails"]:
        sid = site["id"]
        if only and sid not in only:
            continue
        entry = dict(name=site["name"], dye=site["dye"], kind=site["kind"], lights=site["lights"], lods={})
        for lod in (0, 1):
            bpy.ops.wm.read_factory_settings(use_empty=True)
            objs_sail, objs_rig, objs_f, rec = build_site(site, lod)
            for grp, objs in (("Sail", objs_sail), ("Rig", objs_rig), ("Festoon", objs_f)):
                export(objs, OUT / f"SS_{sid}_{grp}_LOD{lod}.glb")
                entry["lods"].setdefault(grp, {})[f"LOD{lod}"] = {o.name: tri_count([o]) for o in objs}
            if lod == 0:
                entry.update(rec)
            print(f"SS_{sid} LOD{lod}: sail {tri_count(objs_sail)}, rig {tri_count(objs_rig)}, festoon {tri_count(objs_f)} triangles", flush=True)
        record[sid] = entry
    rec_path.write_text(json.dumps(record, indent=1))
    print("wrote", rec_path)


if __name__ == "__main__":
    main()
