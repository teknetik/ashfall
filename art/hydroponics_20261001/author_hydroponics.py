"""Ward hydroponics (1 Oct 2026): author the greenhouse fit-out, crops and working-yard props (Blender 5.2, headless).

Carl: "green houses look bare." The two retrofit quonsets (art/ward_retrofit_20260926, "Hydroponics bays") had tiered
trays with a sparse scatter of desert succulents (93k triangles drawn at every distance), flat pink LED slabs floating
without supports and 13.8 m trays with legs only at the ends. This pass fills them as the working heart of Ward's food
supply (lore.md: the hydroponics complex feeds the city; the aquifer is its water):

  * fit-out per quonset: rack legs and bearers every 1.53 m, white NFT channels (four per tray) with net pots, feed
    manifolds and spaghetti lines at the west (tank) end, return gutters and drains at the east end, slim LED bars in
    1.15 m fixtures hung on wires (emissive, on the city light clock in Unity), a floor with weed mat and slatted
    duckboards, rockwool-slab gutters and top wires for vine crops along both long sides, circulation fans and a misting
    line on the ridge, a harvest trolley and crates in the aisle;
  * crops (leaf cards cut from real CC0 leaf photographs, make_textures.py): butterhead, red lollo, cos, rocket, chard,
    basil and mint in the channels at staggered ages (young, mid, mature, a freshly harvested stretch), seedling and
    microgreen trays on the propagation tiers, cordon tomatoes (stripped lower stems, ripening trusses) and runner beans
    (scarlet flowers, pods) on strings;
  * the working yard (props, placed by layout.py): potting bench, compost bays, shade frame with drying herbs, IBC
    nutrient totes with hoses, nursery tables, pallets, harvest-crate produce fills.

Sections: each rack side x third (4.6 m) is one LOD group (LOD0 full plants, LOD1 reduced heads, LOD2 one cross card per
plant) so only nearby crops are detailed. Everything is authored in Unity coordinates (hykit.py) and exported as GLB to
unity/AthenHill/Assets/AthenHill/Art/Hydroponics/ with hy-manifest.json for Editor/HydroponicsPass.cs.

Run: $O/blender.sh author_hydroponics.py [-- --only interior|props] [--review]
"""
import sys, json, math, random, importlib
from pathlib import Path
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hykit
importlib.reload(hykit)
from hykit import Geo, box, quad, tube, cylinder, icosphere, leaf, cross_card, lettuce, chard, basil, seedling_patch, \
    tomato_vine, bean_vine, cell_uv, norm, rot_y, ATLAS

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ONLY = ARGS[ARGS.index("--only") + 1] if "--only" in ARGS else ""
UNITY = Path("/home/teknetik/code/ao2/unity/AthenHill/Assets/AthenHill/Art/Hydroponics")
OUT_INT = UNITY / "Interior"
OUT_PROPS = UNITY / "Props"
TEX = HERE / "textures"
PH = HERE / "polyhaven"
rng = random.Random(20261001)
nrng = np.random.default_rng(20261001)

bpy.ops.wm.read_factory_settings(use_empty=True)

# ------------------------------------------------------------------ materials (Blender side: names are what Unity maps)
_img = {}


def image(p, data=False):
    k = str(p)
    if k not in _img:
        im = bpy.data.images.load(k)
        if data: im.colorspace_settings.name = "Non-Color"
        _img[k] = im
    return _img[k]


def mat(name, rgb=(.5, .5, .5), rough=.6, metal=0., tex=None, nor=None, alpha_clip=False, emit=None, emit_strength=1., uv_scale=1.):
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    if tex:
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = image(tex)
        if uv_scale != 1:
            mp = nt.nodes.new("ShaderNodeMapping"); tc = nt.nodes.new("ShaderNodeTexCoord")
            mp.inputs["Scale"].default_value = (uv_scale, uv_scale, 1)
            nt.links.new(tc.outputs["UV"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], t.inputs["Vector"])
        nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
        if alpha_clip:
            nt.links.new(t.outputs["Alpha"], b.inputs["Alpha"])
            m.surface_render_method = "DITHERED"
    if nor:
        t2 = nt.nodes.new("ShaderNodeTexImage"); t2.image = image(nor, data=True)
        nm = nt.nodes.new("ShaderNodeNormalMap"); nm.inputs["Strength"].default_value = .6
        nt.links.new(t2.outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = emit_strength
    m.use_backface_culling = not alpha_clip
    return m


MATS = {
    "HY_Crop": dict(rgb=(1, 1, 1), rough=.55, tex=TEX / "HY_CropAtlas.png", nor=TEX / "HY_CropAtlas_Normal.png", alpha_clip=True),
    "HY_PVC": dict(rgb=(1, 1, 1), rough=.35, tex=TEX / "HY_PVC.png"),
    "HY_BlackPlastic": dict(rgb=(.035, .037, .04), rough=.45),
    "HY_Galv": dict(rgb=(.56, .57, .56), rough=.42, metal=.85),
    "HY_Alu": dict(rgb=(.62, .63, .65), rough=.35, metal=.9),
    "HY_LED": dict(rgb=(.95, .8, .95), rough=.3, emit=(1., .42, .88), emit_strength=6.),
    "HY_LEDProp": dict(rgb=(.95, .93, 1.), rough=.3, emit=(.92, .86, 1.), emit_strength=4.),
    "HY_Twine": dict(rgb=(.72, .66, .5), rough=.9),
    "HY_Rockwool": dict(rgb=(.55, .53, .42), rough=.95),
    "HY_GrowBag": dict(rgb=(.86, .86, .83), rough=.55),
    "HY_Floor": dict(rgb=(1, 1, 1), rough=.8, tex=PH / "textures/gravel_concrete_03/gravel_concrete_03_diff_2k.jpg", uv_scale=.5),
    "HY_WeedMat": dict(rgb=(.045, .045, .042), rough=.9),
    "HY_Wood": dict(rgb=(1, 1, 1), rough=.8, tex=PH / "textures/weathered_planks/weathered_planks_diff_2k.jpg"),
    "HY_Soil": dict(rgb=(1, 1, 1), rough=.95, tex=PH / "textures/farm_soil/farm_soil_diff_1k.jpg"),
    "HY_Compost": dict(rgb=(1, 1, 1), rough=.95, tex=PH / "textures/wood_chip_path/wood_chip_path_diff_1k.jpg"),
    "HY_ShadeCloth": dict(rgb=(1, 1, 1), rough=.9, tex=TEX / "HY_ShadeCloth.png", alpha_clip=True),
    "HY_IBC": dict(rgb=(.84, .83, .77), rough=.5),
    "HY_Steel": dict(rgb=(.25, .24, .22), rough=.55, metal=.7),
    "HY_CrateBlue": dict(rgb=(.08, .22, .42), rough=.5),
    "HY_CrateGreen": dict(rgb=(.16, .34, .14), rough=.5),
    "HY_Rubber": dict(rgb=(.03, .03, .028), rough=.8),
    "HY_Hose": dict(rgb=(.1, .3, .16), rough=.5),
    "HY_Water": dict(rgb=(.16, .2, .16), rough=.08),
}
BM = {k: mat(k, **v) for k, v in MATS.items()}

# ------------------------------------------------------------------ Geo -> Blender object
COL = bpy.data.collections.new("Hydroponics"); bpy.context.scene.collection.children.link(COL)


def to_blender(g, name, pivot=(0, 0, 0)):
    """Build a Blender mesh object from a Unity-coordinate Geo (vertices relative to `pivot`)."""
    if not g.f:
        return None
    V = np.asarray(g.v, float) - np.asarray(pivot, float)
    B = np.stack([-V[:, 0], -V[:, 2], V[:, 1]], 1)       # Unity (x, y, z) -> Blender (-x, -z, y)
    faces = [tuple(reversed(f)) for f in g.f]              # the axis change is a mirror: keep faces front-facing
    me = bpy.data.meshes.new(name)
    me.from_pydata(B.tolist(), [], faces)
    mats = sorted(set(g.m), key=lambda m: list(MATS).index(m) if m in MATS else 99)
    for m in mats:
        me.materials.append(BM[m])
    idx = {m: i for i, m in enumerate(mats)}
    me.polygons.foreach_set("material_index", [idx[m] for m in g.m])
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method="BEAUTY", ngon_method="BEAUTY")
    bm.to_mesh(me); bm.free()
    uvl = me.uv_layers.new(name="UVMap")
    lv = np.zeros(len(me.loops), np.int32); me.loops.foreach_get("vertex_index", lv)
    UV = np.asarray(g.uv, float)[lv]
    uvl.data.foreach_set("uv", UV.ravel())
    # normals: custom where given, the face normal elsewhere (primitives without normals have unshared vertices)
    fn = {}
    me.update()
    for p in me.polygons:
        for vi in p.vertices:
            fn.setdefault(vi, p.normal.copy())
    N = []
    for i, q in enumerate(g.n):
        if q is None:
            N.append(fn.get(i, Vector((0, 0, 1))))
        else:
            N.append(Vector((-q[0], -q[2], q[1])).normalized())
    me.normals_split_custom_set_from_vertices(N)
    me.validate(clean_customdata=False)
    ob = bpy.data.objects.new(name, me)
    COL.objects.link(ob)
    P = np.asarray(pivot, float)
    ob.location = (-P[0], -P[2], P[1])
    return ob


def export_glb(obs, path):
    bpy.ops.object.select_all(action="DESELECT")
    for o in obs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    loc = [o.location.copy() for o in obs]
    for o in obs:
        o.location = (0, 0, 0)      # each GLB is authored about its own pivot
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True, export_yup=True,
                              export_image_format="NONE", export_tangents=True, export_normals=True, export_apply=True,
                              export_materials="EXPORT", export_vertex_color="NONE", export_extras=False)
    for o, l in zip(obs, loc):
        o.location = l


MANIFEST = {"date": "2026-10-01", "source": "art/hydroponics_20261001/author_hydroponics.py", "sections": [], "props": {}}

# ================================================================== interior
QZ = {"A": 36.7, "B": 28.3}
QX0, QX1 = -41.5, -26.5          # end walls
TX0, TX1 = -40.9, -27.1          # trays
TIER_TOP = (0.76, 1.51)
TIER_LED = (1.30, 2.05)          # bottom face of the retrofit LED slabs (the new bars hang at the same height)
CH_OFF = (-.39, -.13, .13, .39)
STATIONS = [TX0 + .2 + i * (TX1 - TX0 - .4) / 9 for i in range(10)]
THIRDS = [(TX0 + i * (TX1 - TX0) / 3, TX0 + (i + 1) * (TX1 - TX0) / 3) for i in range(3)]
VINE_OFF = 2.45
VINE_X = [-40.35 + i * .5 for i in range(26)]
WIRE_Y = 2.38
GUTTER_Y = .30


def arch_y(dz, W=6.2, H=4.2):
    """Height of the quonset skin at lateral offset dz from the centre line."""
    c = min(1, abs(dz) / (W / 2))
    t = math.acos(c) / math.pi
    return H * math.sin(t * math.pi) ** .85


def racks(q):
    zc = QZ[q]
    gap = zc - 1.6 if q == "A" else zc + 1.6
    outer = zc + 1.6 if q == "A" else zc - 1.6
    return {"gap": gap, "outer": outer}


def vine_z(q, side):
    zc = QZ[q]; r = racks(q)[side]
    return zc + math.copysign(VINE_OFF, r - zc)


# crop recipes: (quonset, side) -> tier -> list over thirds of per-channel kinds
# kinds: butter/lollo/cos/rocket (lettuce), chard, chard_y, basil, mint, seed (seedling trays), micro (microgreens), empty
RECIPES = {
    ("B", "outer"): {0: [["butter", "lollo", "butter", "lollo"]] * 2 + [["butter", "lollo", "harvest", "harvest"]],
                     1: [["cos", "cos", "basil", "basil"]] * 3},
    ("B", "gap"): {0: [["chard", "chard_y", "chard", "chard_y"]] * 3,
                   1: [["seed"] * 4, ["seed"] * 4, ["micro"] * 4]},
    ("A", "gap"): {0: [["butter@young", "lollo@young", "rocket@young", "butter@young"], ["butter@mid", "lollo@mid", "rocket@mid", "butter@mid"],
                       ["butter", "lollo", "rocket", "butter"]],
                   1: [["basil", "basil", "mint", "rocket"]] * 3},
    ("A", "outer"): {0: [["cos", "rocket", "cos", "rocket"]] * 3,
                     1: [["seed"] * 4, ["butter@young", "butter@young", "lollo@young", "lollo@young"], ["micro"] * 4]},
}
VINES = {("B", "outer"): "tomato", ("B", "gap"): "bean", ("A", "gap"): "tomato", ("A", "outer"): "bean"}
SIZE = {"young": (.1, .14), "mid": (.17, .21), None: (.25, .3)}
PITCH = {"young": .16, "mid": .2, None: .24}


def plant(g, kind, age, at, lod, r):
    """One crop plant at `at` (Unity), LOD 0/1 full/reduced; LOD 2 is handled by far_card."""
    s0, s1 = SIZE[age]
    size = r.uniform(s0, s1)
    yaw = r.uniform(0, 6.28)
    if kind in ("butter", "lollo", "cos", "rocket"):
        lettuce(g, "HY_Crop", kind, size * (1.1 if kind == "cos" else 1), nrng, lod=lod, at=at, yaw=yaw)
    elif kind in ("chard", "chard_y"):
        chard(g, "HY_Crop", size * 1.25, nrng, lod=lod, at=at, yaw=yaw, yellow=kind == "chard_y")
    elif kind == "basil":
        basil(g, "HY_Crop", size * .9, nrng, lod=lod, at=at, yaw=yaw)
    elif kind == "mint":
        basil(g, "HY_Crop", size * .8, nrng, lod=lod, at=at, yaw=yaw, cell="mint_leaf")


FAR_CELL = {"butter": "butter_a", "lollo": "oak_red", "cos": "cos_a", "rocket": "oak_green", "chard": "chard_red", "chard_y": "chard_yellow",
            "basil": "basil_leaf", "mint": "mint_leaf"}


def far_card(g, kind, age, at, r):
    s0, s1 = SIZE[age]
    size = r.uniform(s0, s1) * (1.25 if kind.startswith("chard") else 1)
    cross_card(g, "HY_Crop", at, size * .75, size * 1.1, FAR_CELL[kind], yaw=r.uniform(0, 3.14), n=2, centre=np.asarray(at) + [0, .05, 0])


def net_pot(g, at):
    """Black net-pot rim in a channel hole (visible where a plant was just harvested)."""
    at = np.asarray(at, float)
    tube(g, [at + [0, -.01, 0], at + [0, .006, 0]], .026, "HY_BlackPlastic", sides=6)
    quad(g, [at + [-.02, -.004, -.02], at + [-.02, -.004, .02], at + [.02, -.004, .02], at + [.02, -.004, -.02]], "HY_Rockwool",
         uv=[(cell_uv("rockwool")[0], cell_uv("rockwool")[1]), (cell_uv("rockwool")[2], cell_uv("rockwool")[1]),
             (cell_uv("rockwool")[2], cell_uv("rockwool")[3]), (cell_uv("rockwool")[0], cell_uv("rockwool")[3])])


def channel(g, x0, x1, z, y):
    """White NFT channel 0.1 x 0.055 m on the tray top, end caps."""
    w, h = .1, .055
    box(g, ((x0 + x1) / 2, y + h / 2, z), (x1 - x0, h, w), "HY_PVC", uvm=1.0)
    for x in (x0, x1):
        box(g, (x, y + h / 2, z), (.012, h + .006, w + .006), "HY_PVC")


def seed_tray(g, cx, cz, y, lod, r, micro=False):
    """A 0.54 x 0.28 m propagation tray (black) with rockwool plugs and seedlings, or microgreens."""
    L, W, H = .54, .28, .05
    box(g, (cx, y + H / 2, cz), (L, H, W), "HY_BlackPlastic", top=False)
    u0, v0, u1, v1 = cell_uv("microgreens" if micro else "rockwool")
    top = y + H - .008
    quad(g, [(cx - L / 2, top, cz + W / 2), (cx + L / 2, top, cz + W / 2), (cx + L / 2, top, cz - W / 2), (cx - L / 2, top, cz - W / 2)],
         "HY_Crop", uv=[(u0, v0), (u1, v0), (u1, v1), (u0, v1)], normals=[(0, 1, 0)] * 4)
    if micro:
        if lod == 0:   # a low canopy: second, raised layer with the same texture, slightly shifted
            h2 = top + .025 + r.uniform(0, .01)
            quad(g, [(cx - L / 2 + .01, h2, cz + W / 2 - .01), (cx + L / 2 - .01, h2, cz + W / 2 - .01), (cx + L / 2 - .01, h2, cz - W / 2 + .01),
                     (cx - L / 2 + .01, h2, cz - W / 2 + .01)], "HY_Crop", uv=[(u0, v1), (u1, v1), (u1, v0), (u0, v0)], normals=[(0, 1, 0)] * 4)
        return
    if lod == 0:
        seedling_patch(g, "HY_Crop", cx - L / 2 + .01, cx + L / 2 - .01, cz - W / 2 + .01, cz + W / 2 - .01, top, .054, nrng)


def section(q, side, k):
    """Crops on both tiers of one rack third plus the vine crop on that side's long wall. Returns LOD Geos."""
    x0, x1 = THIRDS[k]
    zr = racks(q)[side]
    lods = [Geo(), Geo(), Geo()]
    r = random.Random(f"{q}-{side}-{k}")
    recipe = RECIPES[(q, side)]
    for tier in (0, 1):
        kinds = recipe[tier][k]
        ytop = TIER_TOP[tier]
        for ci, kind in enumerate(kinds):
            z = zr + CH_OFF[ci]
            if kind in ("seed", "micro"):
                if ci == 0:     # trays span the tier width: two rows of trays across, butted along x
                    for row, dz in enumerate((-.2, .2)):
                        xx = x0 + .32
                        while xx + .27 < x1 - .05:
                            for lod in (0, 1):
                                seed_tray(lods[lod], xx, zr + dz, ytop, lod, r, micro=kind == "micro")
                            xx += .56
                continue
            base_kind, _, age = kind.partition("@")
            age = age or None
            pitch = PITCH[age] * (1.25 if base_kind.startswith("chard") else 1)
            xs = np.arange(x0 + pitch * .6, x1 - pitch * .3, pitch)
            for i, x in enumerate(xs):
                at = (x + r.uniform(-.01, .01), ytop + .055, z)
                if base_kind == "harvest":
                    # the east end of these channels was cut this morning: empty pots, a few heads left
                    if x < x1 - 1.6 or r.random() < .15:
                        for lod in (0, 1): plant(lods[lod], "butter" if ci == 2 else "lollo", None, at, lod, r)
                        far_card(lods[2], "butter" if ci == 2 else "lollo", None, at, r)
                    else:
                        net_pot(lods[0], at)
                    continue
                for lod in (0, 1):
                    plant(lods[lod], base_kind, age, at, lod, r)
                far_card(lods[2], base_kind, age, at, r)
    # vines on this side's long wall
    vz = vine_z(q, side)
    face = 0.0 if vz > QZ[q] else math.pi        # trusses hang towards the skin (seen from outside); leaves run along the row
    kind = VINES[(q, side)]
    for x in VINE_X:
        if not (x0 <= x < x1): continue
        base = (x + r.uniform(-.02, .02), GUTTER_Y + .17, vz)
        seed = r.random()
        for lod in (0, 1, 2):
            if kind == "tomato":
                tomato_vine(lods[lod], "HY_Crop", base, WIRE_Y, nrng, lod=min(lod, 1), facing=face,
                            trusses=4 if lod == 0 else 3, string=lod == 0)
            else:
                bean_vine(lods[lod], "HY_Crop", base, WIRE_Y, nrng, lod=min(lod, 1), facing=face)
            if lod == 2: break
    return lods


def fitout(q):
    """Static fit-out of one quonset (LOD0 full, LOD1 without small parts)."""
    zc = QZ[q]
    g0, g1 = Geo(), Geo()
    both = (g0, g1)
    rk = racks(q)
    for side, zr in rk.items():
        # legs, bearers under both trays, diagonal brace at the ends
        for x in STATIONS:
            for dz in (-.5, .5):
                for g in both: box(g, (x, .7, zr + dz), (.04, 1.39, .04), "HY_Galv", top=False)
            for y in (.62, 1.37):
                for g in both: box(g, (x, y, zr), (.04, .04, 1.08), "HY_Galv")
            box(g0, (x, .08, zr), (.035, .035, 1.0), "HY_Galv")
        for x in (STATIONS[0], STATIONS[-1]):
            tube(g0, [(x, .1, zr - .5), (x, 1.3, zr + .5)], .012, "HY_Galv", sides=4)
        # NFT channels on both tiers where the recipe uses channels
        for tier in (0, 1):
            ytop = TIER_TOP[tier]
            for k, (x0, x1) in enumerate(THIRDS):
                kinds = RECIPES[(q, side)][tier][k]
                if kinds[0] in ("seed", "micro"): continue
                for ci in range(4):
                    z = zr + CH_OFF[ci]
                    for g in both: channel(g, x0 + (.05 if k else .1), x1 - (.05 if k < 2 else .1), z, ytop)
            # feed manifold (west end) and spaghetti lines into the channel heads
            xm = TX0 + .06
            for g in both: tube(g, [(xm, ytop + .12, zr - .5), (xm, ytop + .12, zr + .5)], .014, "HY_BlackPlastic", sides=6)
            tube(g0, [(xm, .05, zr + .52), (xm, ytop + .12, zr + .52), (xm, ytop + .12, zr + .5)], .014, "HY_BlackPlastic", sides=6)
            for ci in range(4):
                z = zr + CH_OFF[ci]
                tube(g0, [(xm, ytop + .12, z), (xm + .05, ytop + .13, z), (TX0 + .16, ytop + .065, z)], .0035, "HY_BlackPlastic", sides=3)
            # return gutter (east end) and drain to the floor
            xg = TX1 - .03
            for g in both: box(g, (xg, ytop + .02, zr), (.09, .06, 1.1), "HY_PVC")
            tube(g0, [(xg, ytop - .02, zr + .45), (xg + .02, .08, zr + .45)], .02, "HY_PVC", sides=6)
            # LED bars: two slim housings per tier in 1.15 m fixtures, hung on wires
            yl = TIER_LED[tier]
            n = 11
            span = (TX1 - TX0 - .2) / n
            for i in range(n):
                xa = TX0 + .1 + i * span + .04; xb = xa + span - .08
                k3 = min(2, int(((xa + xb) / 2 - TX0) / ((TX1 - TX0) / 3)))
                k0 = RECIPES[(q, side)][tier][k3][0]
                # propagation tiers (seedlings, microgreens, young heads) run on their own always-on circuit
                led = "HY_LEDProp" if k0 in ("seed", "micro") or k0.endswith("@young") else "HY_LED"
                for dz in (-.13, .13):
                    for g in both:
                        box(g, ((xa + xb) / 2, yl + .018, zr + dz), (xb - xa, .026, .055), "HY_Alu", bottom=False)
                        quad(g, [(xa, yl + .004, zr + dz - .022), (xb, yl + .004, zr + dz - .022), (xb, yl + .004, zr + dz + .022), (xa, yl + .004, zr + dz + .022)],
                             led, normals=[(0, -1, 0)] * 4)
                xm_ = (xa + xb) / 2
                box(g0, (xm_, yl + .034, zr), (.03, .01, .3), "HY_Alu")          # cross bar joining the pair
                if tier == 0:
                    tube(g0, [(xm_, yl + .04, zr), (xm_, TIER_TOP[1] - .12, zr)], .003, "HY_Steel", sides=3)
                else:
                    purlin_z = zc + math.copysign(1.82, zr - zc)
                    tube(g0, [(xm_, yl + .04, zr), (xm_, 3.47, purlin_z)], .0025, "HY_Steel", sides=3)
            # power cable along the fixtures
            tube(g0, [(TX0 + .1, yl + .045, zr), (TX1 - .1, yl + .045, zr)], .006, "HY_BlackPlastic", sides=4)
        # a crop board at the east end of each rack, and tags on the channel ends
        box(g0, (TX1 + .08, 1.05, zr - .35), (.012, .3, .42), "HY_PVC")
        for tier in (0, 1):
            for ci in range(4):
                z = zr + CH_OFF[ci]
                box(g0, (TX1 - .12, TIER_TOP[tier] + .1, z + .03), (.003, .07, .02), "HY_PVC")
    # vine lines: gutter on legs, rockwool slabs, cubes, drip lines, top wire and rib hangers
    for side in ("gap", "outer"):
        vz = vine_z(q, side)
        for g in both: box(g, ((TX0 + TX1) / 2, GUTTER_Y - .03, vz), (TX1 - TX0, .06, .22), "HY_Galv")
        for x in STATIONS:
            box(g0, (x, (GUTTER_Y - .06) / 2, vz), (.03, GUTTER_Y - .06, .03), "HY_Galv", top=False)
        xx = TX0 + .15
        while xx < TX1 - .5:
            for g in both: box(g, (xx + .5, GUTTER_Y + .038, vz), (.98, .075, .2), "HY_GrowBag")
            xx += 1.0
        for x in VINE_X:
            box(g0, (x, GUTTER_Y + .12, vz), (.1, .09, .1), "HY_Rockwool")
            tube(g0, [(x, GUTTER_Y + .2, vz + .07), (x + .02, GUTTER_Y + .12, vz + .09), (x + .04, GUTTER_Y + .09, vz + .12)], .002, "HY_BlackPlastic", sides=3)
        tube(g0, [(TX0 + .1, GUTTER_Y + .09, vz + .13), (TX1 - .1, GUTTER_Y + .09, vz + .13)], .008, "HY_BlackPlastic", sides=5)
        for g in both: tube(g, [(TX0 - .1, WIRE_Y, vz), (TX1 + .1, WIRE_Y, vz)], .004, "HY_Galv", sides=4)
        for i in range(11):
            x = QX0 + i * 1.5
            if TX0 - .2 < x < TX1 + .2:
                ya = arch_y(abs(vz - zc)) - .03
                tube(g0, [(x, ya, vz), (x, WIRE_Y, vz)], .004, "HY_Galv", sides=3)
    # floor: worn concrete, black weed mat under the racks and vines, slatted duckboards down the aisle
    for g in both:
        quad(g, [(QX0 + .05, .012, zc - 3.0), (QX0 + .05, .012, zc + 3.0), (QX1 - .05, .012, zc + 3.0), (QX1 - .05, .012, zc - 3.0)], "HY_Floor",
             uv=[(0, 0), (0, 3), (7.4, 3), (7.4, 0)], normals=[(0, 1, 0)] * 4)
    for zr in list(rk.values()) + [vine_z(q, s) for s in ("gap", "outer")]:
        w = 1.25 if zr in rk.values() else .5
        for g in both:
            quad(g, [(TX0 - .2, .016, zr - w / 2), (TX0 - .2, .016, zr + w / 2), (TX1 + .2, .016, zr + w / 2), (TX1 + .2, .016, zr - w / 2)], "HY_WeedMat",
                 normals=[(0, 1, 0)] * 4)
    x = TX0 + .4
    while x + 1.1 < TX1 - .2:
        for s in range(6):
            for g in ((g0,) if s % 2 else both):
                box(g, (x + .55, .035, zc - .45 + s * .18), (1.1, .03, .1), "HY_Wood", uvm=1.2)
        box(g0, (x + .12, .012, zc), (.06, .02, 1.0), "HY_Wood"); box(g0, (x + .98, .012, zc), (.06, .02, 1.0), "HY_Wood")
        x += 1.2
    # return pipe along the east-end floor and the ridge misting line with drops to nozzles
    for zr in rk.values():
        tube(g0, [(TX1 + .02, .06, zr + .45), (TX1 + .1, .06, zc), (QX1 - .15, .06, zc + .7)], .025, "HY_PVC", sides=6)
    for g in both: tube(g, [(QX0 + .2, 4.02, zc + .1), (QX1 - .2, 4.02, zc + .1)], .012, "HY_BlackPlastic", sides=5)
    for i in range(9):
        xn = QX0 + 1.0 + i * 1.6
        tube(g0, [(xn, 4.02, zc + .1), (xn, 3.85, zc + .1)], .003, "HY_BlackPlastic", sides=3)
        box(g0, (xn, 3.84, zc + .1), (.02, .02, .02), "HY_Galv")
    # circulation fans on the ridge
    for xf in (-37.4, -30.6):
        for g in both:
            cylinder(g, (xf, 3.62, zc), .24, .22, "HY_Steel", sides=14, caps=False, axis="x")
        box(g0, (xf, 3.9, zc), (.04, .3, .04), "HY_Steel")
        cylinder(g0, (xf + .09, 3.62, zc), .06, .12, "HY_Steel", sides=8, axis="x")
        for b in range(4):
            a = b * math.pi / 2 + .3
            p0 = np.array([xf - .02, 3.62, zc]); d = np.array([0, math.cos(a), math.sin(a)]); s_ = np.array([0, -math.sin(a), math.cos(a)])
            bl = [p0 + d * .04 - s_ * .03, p0 + d * .21 - s_ * .06 + [.02, 0, 0], p0 + d * .21 + s_ * .06 - [.02, 0, 0], p0 + d * .04 + s_ * .03]
            quad(g0, bl, "HY_Steel"); quad(g0, bl[::-1], "HY_Steel")
    # aisle life at the east (door) end: a harvest trolley and crates, a stool, a hose on its hook
    tx = TX1 - .9
    tz = zc + (.3 if q == "B" else -.3)
    for y in (.25, .78):
        for g in both: box(g, (tx, y, tz), (1.0, .03, .5), "HY_Galv")
    for dx in (-.48, .48):
        for dz in (-.23, .23):
            box(g0, (tx + dx, .47, tz + dz), (.025, .9, .025), "HY_Galv", top=False)
            cylinder(g0, (tx + dx, .05, tz + dz), .045, .03, "HY_Rubber", sides=8, axis="z")
    tube(g0, [(tx + .5, .95, tz - .22), (tx + .6, .95, tz - .22), (tx + .6, .95, tz + .22), (tx + .5, .95, tz + .22)], .012, "HY_Galv", sides=5)
    crate_x = [tx - .24, tx + .24]
    for i, cx in enumerate(crate_x):
        for g in both: crate(g, (cx, .8, tz), "HY_CrateBlue" if i == 0 else "HY_CrateGreen")
    # harvested heads in the first crate
    for j in range(4):
        lettuce(g0, "HY_Crop", "butter" if j % 2 else "lollo", .22, nrng, lod=1, at=(crate_x[0] - .1 + (j % 2) * .2, .86, tz - .08 + (j // 2) * .16), yaw=j)
    for j in range(3):
        for g in both: crate(g, (QX1 - .5, .0 + j * .245, zc + (-.85 if q == "B" else .85)), "HY_CrateGreen" if j != 1 else "HY_CrateBlue")
    # low stool by the rack end, bucket, coiled hose on a bracket on the end post
    sx, sz = TX1 - .35, zc + (-.7 if q == "B" else .7)
    for g in both: cylinder(g, (sx, .42, sz), .16, .03, "HY_Wood", sides=10)
    for a in range(3):
        an = a * 2.1
        tube(g0, [(sx + .12 * math.cos(an), .41, sz + .12 * math.sin(an)), (sx + .19 * math.cos(an), 0, sz + .19 * math.sin(an))], .014, "HY_Wood", sides=4)
    hose_coil(g0, (QX1 - .12, 1.25, zc + (1.25 if q == "B" else -1.25)), .22, 4)
    # nutrient mixing at the west (tank) end of the aisle: a 200 l blue drum with its lid and dosing line, a wall-mounted
    # dosing unit with a lit display on a post, and two concentrate jugs on the floor
    dx, dz = QX0 + .38, zc - .75
    for g in both:
        cylinder(g, (dx, .44, dz), .29, .88, "HY_CrateBlue", sides=16 if g is g0 else 8)
    cylinder(g0, (dx, .885, dz), .27, .012, "HY_CrateBlue", sides=16)
    for y in (.3, .6):
        cylinder(g0, (dx, y, dz), .295, .025, "HY_CrateBlue", sides=16, caps=False)
    tube(g0, [(dx + .05, .89, dz + .05), (dx + .05, 1.05, dz + .1), (QX0 + .2, 1.2, dz + .4), (TX0 + .06, TIER_TOP[0] + .12, zc - .5)], .006, "HY_BlackPlastic", sides=4)
    px, pz = QX0 + .05, zc + 1.0          # bolted to the end wall's door post
    for g in both:
        box(g, (px + .09, 1.25, pz), (.12, .42, .32), "HY_IBC")
    quad(g0, [(px + .152, 1.32, pz - .08), (px + .152, 1.32, pz + .08), (px + .152, 1.4, pz + .08), (px + .152, 1.4, pz - .08)], "HY_LEDProp",
         normals=[(1, 0, 0)] * 4)
    for k in range(3):
        cylinder(g0, (px + .155, 1.15, pz - .08 + k * .08), .018, .02, "HY_BlackPlastic", sides=8, axis="x")
    tube(g0, [(px + .09, 1.04, pz), (px + .09, .9, pz + .05), (TX0 + .06, TIER_TOP[0] + .12, zc + .5)], .008, "HY_BlackPlastic", sides=4)
    for k, (jx, jz) in enumerate(((QX0 + .3, zc - 1.25), (QX0 + .5, zc - 1.3))):
        box(g0, (jx, .14, jz), (.15, .28, .12), "HY_GrowBag")
        cylinder(g0, (jx, .3, jz - .02), .025, .04, "HY_BlackPlastic", sides=8)
    return g0, g1


def crate(g, c, m):
    """Open plastic harvest crate 0.5 x 0.24 x 0.36 m (base at c)."""
    x, y, z = c; L, H, W = .5, .24, .36; t = .012
    box(g, (x, y + t / 2, z), (L, t, W), m)
    for s in (-1, 1):
        box(g, (x, y + H / 2, z + s * (W / 2 - t / 2)), (L, H, t), m, top=True)
        box(g, (x + s * (L / 2 - t / 2), y + H / 2, z), (t, H, W - 2 * t), m, top=True)


def hose_coil(g, c, r, turns, axis="x"):
    pts = []
    c = np.asarray(c, float)
    for i in range(turns * 12 + 1):
        a = i / 12 * 2 * math.pi
        off = (i / (turns * 12)) * .08
        if axis == "x":
            pts.append(c + [off, r * math.sin(a), r * math.cos(a)])
        else:
            pts.append(c + [r * math.cos(a), off, r * math.sin(a)])
    tube(g, pts, .012, "HY_Hose", sides=5)


def build_interior():
    for q in ("A", "B"):
        g0, g1 = fitout(q)
        pivot = (-34.0, 0.0, QZ[q])
        name = f"HY_Fitout_{q}"
        obs = []
        for i, g in enumerate((g0, g1)):
            o = to_blender(g, f"{name}_LOD{i}", pivot)
            export_glb([o], OUT_INT / name / f"{name}_LOD{i}.glb"); obs.append(o)
        MANIFEST["sections"].append(dict(name=name, kind="fitout", quonset=q, pivot=list(pivot), lods=[len(g0), len(g1)],
                                         glb=[f"Interior/{name}/{name}_LOD{i}.glb" for i in range(2)]))
        print(name, len(g0), len(g1), flush=True)
        for side in ("outer", "gap"):
            for k in range(3):
                lods = section(q, side, k)
                x0, x1 = THIRDS[k]
                pivot = ((x0 + x1) / 2, 0.0, racks(q)[side])
                name = f"HY_Crops_{q}_{side}_{k}"
                for i, g in enumerate(lods):
                    o = to_blender(g, f"{name}_LOD{i}", pivot)
                    export_glb([o], OUT_INT / name / f"{name}_LOD{i}.glb")
                MANIFEST["sections"].append(dict(name=name, kind="crops", quonset=q, side=side, third=k, pivot=list(pivot),
                                                 lods=[len(g) for g in lods], glb=[f"Interior/{name}/{name}_LOD{i}.glb" for i in range(3)],
                                                 vines=VINES[(q, side)]))
                print(name, [len(g) for g in lods], flush=True)


if ONLY in ("", "interior"):
    build_interior()

# ================================================================== yard props (authored at the origin, front +Z)
import hyprops
importlib.reload(hyprops)
if ONLY in ("", "props"):
    PROPS_ONLY = ARGS[ARGS.index("--props") + 1].split(",") if "--props" in ARGS else None
    hyprops.build_all(sys.modules[__name__], PROPS_ONLY)

# ------------------------------------------------------------------ report
man_path = UNITY / "hy-manifest.json"
if man_path.exists() and ONLY:
    old = json.loads(man_path.read_text())
    if ONLY == "props":
        MANIFEST["sections"] = old.get("sections", [])
        if "--props" in ARGS:   # partial rebuild: keep the other props' records
            MANIFEST["props"] = {**old.get("props", {}), **MANIFEST["props"]}
    if ONLY == "interior": MANIFEST["props"] = old.get("props", {})
man_path.parent.mkdir(parents=True, exist_ok=True)
man_path.write_text(json.dumps(MANIFEST, indent=1))
tot = sum(s["lods"][0] for s in MANIFEST["sections"])
print("SECTIONS", len(MANIFEST["sections"]), "LOD0 tris", tot, "PROPS", len(MANIFEST["props"]))
bpy.ops.wm.save_as_mainfile(filepath=str(HERE / ("hydroponics-props.blend" if ONLY == "props" else "hydroponics-source.blend")), compress=True)
print("AUTHOR_DONE")
