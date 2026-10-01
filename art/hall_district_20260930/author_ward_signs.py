"""Ward shop sign family (30 September 2026), Blender 5.2 headless.

Carl: "I don't like the signs so much. I designed one I like a little more in Meshy for General. See if you can do
better." His sign (meshy/basic-general-sign-20260929): dark machined panel, orange BASIC GENERAL, red OPEN, cyan
circuit lines, baked flat to a 22-triangle plate. Target: concept/sign-family-concept-a.png (not yet accepted).

This keeps what works in his design (dark steel, warm amber lettering, a lit OPEN plate, restrained cyan) and makes it
physical: a folded, riveted steel sign box with chamfered corners and a weather cap, a recessed panel, individually
modelled channel letters (emissive amber faces, dark returns), a slim cyan status strip, standoff brackets and a
conduit feed. Basic General's sign keeps his layout (name over an inset red OPEN lightbox) on the same footprint.

Run:  blender -b --python-exit-code 1 -P author_ward_signs.py
Output: unity/AthenHill/Assets/AthenHill/Art/WardShops/Signs/Sign_<key>.glb + signs.json. Sign-local Unity metres:
origin at the wall face behind the sign centre, +Z out of the wall, X along the wall (reading left to right from the
front is -X, as for every Ward sign authored in Blender space), Y up.
"""
import bpy, bmesh, json, math, random, sys
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "art/ward_masonry_kit"))
import ward_masonry as WM
from ward_masonry import Part, U, lerp, export, tri_count, triangulate, material

OUT = ROOT / "unity/AthenHill/Assets/AthenHill/Art/WardShops/Signs"
OUT.mkdir(parents=True, exist_ok=True)
FONT_BLACK = HERE / "fonts/NotoSans-Black.ttf"
FONT_BOLD = HERE / "fonts/NotoSans-Bold.ttf"

SIGNS = {
    "basic_general": dict(text="BASIC GENERAL", w=2.5, h=0.82, standoff=0.0, open=True, feed="top"),
    "relay_works": dict(text="RELAY WORKS", w=3.1, h=0.66, standoff=0.12),
    "air_water": dict(text="AIR + WATER", w=2.6, h=0.62, standoff=0.12),
    "tool_exchange": dict(text="TOOL EXCHANGE", w=3.3, h=0.62, standoff=0.12, strong=True),
    "finery": dict(text="FINERY", w=2.2, h=0.62, standoff=0.12, spacing=1.18),
    "field_supply": dict(text="FIELD SUPPLY", w=3.2, h=0.66, standoff=0.1),
    # north avenue (30 Sep, art/north_avenue_20260930)
    "salvage": dict(text="SALVAGE", w=2.6, h=0.66, standoff=0.12, spacing=1.14),
    "repairs": dict(text="REPAIRS", w=2.4, h=0.62, standoff=0.12, spacing=1.14),
    "thread_hide": dict(text="THREAD + HIDE", w=3.2, h=0.62, standoff=0.12),
}
DEPTH = 0.13          # box depth
RIM = 0.055           # front rim width
RECESS = 0.022        # panel recess behind the rim


def outline(w, h, c, cx=0.0, cy=0.0):
    """Chamfered rectangle (8 points, clockwise seen from the front), centred on (cx, cy)."""
    x, y = w / 2, h / 2
    pts = [(-x + c, y), (x - c, y), (x, y - c), (x, -y + c), (x - c, -y), (-x + c, -y), (-x, -y + c), (-x, y - c)]
    return [(px + cx, py + cy) for px, py in pts]


def prism(part, pts, z0, z1, mat_side, mat_front=None, mat_back=None, front=True, back=True):
    bm = part.bm
    lo = [bm.verts.new(Vector((x, y, z0))) for x, y in pts]
    hi = [bm.verts.new(Vector((x, y, z1))) for x, y in pts]
    n = len(pts)
    fs = []
    ms = part.mi(mat_side)
    for i in range(n):
        j = (i + 1) % n
        f = bm.faces.new([lo[i], lo[j], hi[j], hi[i]]); f.material_index = ms; fs.append(f)
    if front:
        f = bm.faces.new(hi); f.material_index = part.mi(mat_front or mat_side); fs.append(f)
    if back:
        f = bm.faces.new(lo[::-1]); f.material_index = part.mi(mat_back or mat_side); fs.append(f)
    bmesh.ops.recalc_face_normals(bm, faces=fs)
    return lo, hi, fs


def framed_box(part, w, h, z0, frame_mat, panel_mat, chamfer, rim=RIM, recess=RECESS, depth=DEPTH, cy=0.0):
    """Sign box: sides + back, front rim ring and a recessed panel."""
    bm = part.bm
    z1 = z0 + depth
    outer = outline(w, h, chamfer, 0.0, cy)
    inner = outline(w - 2 * rim, h - 2 * rim, max(0.01, chamfer - rim * 0.6), 0.0, cy)
    lo, hi, fs = prism(part, outer, z0, z1, frame_mat, front=False)
    ring_in = [bm.verts.new(Vector((x, y, z1))) for x, y in inner]
    ring_rc = [bm.verts.new(Vector((x, y, z1 - recess))) for x, y in inner]
    n = len(outer)
    mf, mp = part.mi(frame_mat), part.mi(panel_mat)
    new = []
    for i in range(n):
        j = (i + 1) % n
        f = bm.faces.new([hi[i], hi[j], ring_in[j], ring_in[i]]); f.material_index = mf; new.append(f)
        f = bm.faces.new([ring_in[i], ring_in[j], ring_rc[j], ring_rc[i]]); f.material_index = mf; new.append(f)
    f = bm.faces.new(ring_rc); f.material_index = mp; new.append(f)
    for f in new:
        f.normal_update()
    # outward orientation: front faces +Z, recess walls inwards (towards the panel centre)
    for f in new:
        c = f.calc_center_median()
        if abs(f.normal.z) > 0.5:
            if f.normal.z < 0:
                f.normal_flip()
        else:
            if f.normal.dot(Vector((-c.x, cy - c.y, 0))) < 0:
                f.normal_flip()
    edges = [e for e in {e for v in hi for e in v.link_edges} if all(v in hi for v in e.verts)]
    part.bevel_edges(edges, 0.008, 2)
    return z1, inner


def letters(coll, name, text, font, size, centre, depth, width_limit, face_mat, return_mat, squeeze=0.84, spacing=1.06):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = text
    cu.font = bpy.data.fonts.load(str(font), check_existing=True)
    cu.size = size
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.extrude = depth / 2
    cu.bevel_depth = 0.0015
    cu.bevel_resolution = 1
    cu.space_character = spacing
    cu.resolution_u = 5
    ob = bpy.data.objects.new(name, cu)
    coll.objects.link(ob)
    ob.rotation_euler = (math.radians(90), 0, 0)       # faces Blender -Y = Unity +Z
    ob.location = U(centre)
    bpy.context.view_layer.update()
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.convert(target="MESH")
    ob = bpy.context.view_layer.objects.active
    pts = [ob.matrix_world @ v.co for v in ob.data.vertices]
    width = (max(p.x for p in pts) - min(p.x for p in pts)) * squeeze
    k = min(1.0, width_limit / width) if width > 0 else 1.0
    ob.scale = (squeeze * k, k, k)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    me = ob.data
    me.materials.clear()
    me.materials.append(material(face_mat))
    me.materials.append(material(return_mat))
    for p in me.polygons:
        p.material_index = 0 if p.normal.y < -0.7 else 1      # front faces lit, returns dark
        p.use_smooth = False
    uvl = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uvl.data[li].uv = (co.x * 2.0, co.z * 2.0)
    col = me.color_attributes.new("Col", "BYTE_COLOR", "CORNER")
    for d in col.data:
        d.color = (0.5, 0.5, 0.5, 1.0)
    triangulate(ob)
    return ob, width * k


def build_sign(key, spec):
    WM.set_state(0, random.Random(hash(key) & 0xffff), "sign_" + key)
    WM.reset_materials()
    coll = bpy.data.collections.new("Sign_" + key)
    bpy.context.scene.collection.children.link(coll)
    body = Part(f"Sign_{key}_Body", wear=False)
    glow = Part(f"Sign_{key}_Glow", wear=False)
    w, h, so = spec["w"], spec["h"], spec["standoff"]
    ch = min(0.12, h * 0.18)
    z0 = so
    z1, inner = framed_box(body, w, h, z0, "WS_SignFrame", "WS_SignPanel", ch)
    zp = z1 - RECESS
    # weather cap over the top edge
    body.box((-w / 2 - 0.03, h / 2 + 0.004, z0 - 0.01), (w / 2 + 0.03, h / 2 + 0.018, z1 + 0.035), "WS_SignFrame")
    body.box((-w / 2 - 0.03, h / 2 - 0.01, z1 + 0.025), (w / 2 + 0.03, h / 2 + 0.018, z1 + 0.035), "WS_SignFrame")
    # rivets on the rim
    n = max(6, int(w / 0.2))
    for i in range(n):
        x = lerp(-w / 2 + ch + 0.05, w / 2 - ch - 0.05, i / (n - 1))
        for y in (h / 2 - RIM / 2, -h / 2 + RIM / 2):
            body.sphere((x, y, z1), 0.008, "WS_SignRivet", 6, hemi_axis=(0, 0, 1))
    for x in (-w / 2 + RIM / 2, w / 2 - RIM / 2):
        for y in (-h * 0.18, h * 0.18):
            body.sphere((x, y, z1), 0.008, "WS_SignRivet", 6, hemi_axis=(0, 0, 1))
    # panel seam lines (fabricated from two sheets)
    body.box((-0.004, -h / 2 + RIM, zp), (0.004, h / 2 - RIM, zp + 0.003), "WS_SignFrame") if not spec.get("open") else None
    # standoff brackets and bolts into the wall
    if so > 0:
        for x in (-w * 0.34, w * 0.34):
            for y in (h * 0.28, -h * 0.28):
                body.box((x - 0.03, y - 0.03, 0.0), (x + 0.03, y + 0.03, 0.012), "WS_SignRivet")
                body.cyl((x, y, 0.012), (x, y, so + 0.005), 0.016, "WS_SignRivet", 8)
    # conduit feed: from the right end (reader's right = -X) into the wall, or from the top (booth sign)
    if spec.get("feed") == "top":
        body.tube([(-w * 0.42, h / 2 + 0.02, z0 + 0.05), (-w * 0.42, h / 2 + 0.25, z0 + 0.05)], 0.014, "WS_SignRivet", 8)
    else:
        body.tube([(-w / 2 - 0.005, 0.0, z0 + 0.05), (-w / 2 - 0.12, 0.0, z0 + 0.05), (-w / 2 - 0.12, -h / 2 - 0.2, z0 + 0.05),
                   (-w / 2 - 0.12, -h / 2 - 0.2, 0.0)], 0.014, "WS_SignRivet", 8)
        body.box((-w / 2 - 0.19, -h / 2 - 0.3, 0.0), (-w / 2 - 0.05, -h / 2 - 0.12, 0.05), "WS_SignFrame")
    # cyan status: slim strip lower-left (reader's left = +X) and a lamp at the other end; full strip when "strong"
    ly = -h / 2 + RIM + 0.03
    if spec.get("strong"):
        glow.box((-w / 2 + RIM + 0.06, ly - 0.007, zp), (w / 2 - RIM - 0.06, ly + 0.007, zp + 0.006), "WS_SignCyan")
    else:
        glow.box((w / 2 - RIM - 0.34, ly - 0.007, zp), (w / 2 - RIM - 0.06, ly + 0.007, zp + 0.006), "WS_SignCyan")
    glow.box((-w / 2 + RIM + 0.05, ly - 0.014, zp), (-w / 2 + RIM + 0.078, ly + 0.014, zp + 0.008), "WS_SignCyan")
    objs = []
    rec = {"key": key, "text": spec["text"], "size": [w, h], "standoff": so, "front": z1 + 0.035}
    if spec.get("open"):
        # name across the upper panel; inset OPEN lightbox below (red letters behind a dark bezel)
        ow, oh = 0.78, 0.27
        oy = -h / 2 + RIM + 0.05 + oh / 2
        framed_box(body, ow, oh, zp - 0.005, "WS_SignFrame", "WS_SignDark", 0.04, rim=0.025, recess=0.015, depth=0.03, cy=oy)
        txt, tw = letters(coll, f"Sign_{key}_Letters", spec["text"], FONT_BLACK, h * 0.46, (0, oy + oh / 2 + (h / 2 - RIM - (oy + oh / 2)) / 2, zp + 0.0175),
                          0.035, w - 2 * RIM - 0.2, "WS_SignLetter", "WS_SignReturn", spacing=spec.get("spacing", 1.06))
        otxt, _ = letters(coll, f"Sign_{key}_Open", "OPEN", FONT_BLACK, oh * 0.78, (0, oy, zp - 0.005 + 0.03 - 0.015 + 0.008), 0.012, ow - 0.14,
                          "WS_SignRed", "WS_SignReturn", squeeze=0.9, spacing=1.12)
        objs += [txt, otxt]
        rec["open"] = {"centre": [0, oy], "size": [ow, oh]}
    else:
        txt, tw = letters(coll, f"Sign_{key}_Letters", spec["text"], FONT_BLACK, h * 0.7, (0, 0.012, zp + 0.0175), 0.035,
                          w - 2 * RIM - 0.34, "WS_SignLetter", "WS_SignReturn", spacing=spec.get("spacing", 1.06))
        objs.append(txt)
    rec["letter_width"] = tw
    body.finalize(); glow.finalize()
    objs = [body.build(coll, flat=False), glow.build(coll, flat=True)] + objs
    rec["triangles"] = tri_count(objs)
    export(objs, OUT / f"Sign_{key}.glb")
    print(key, rec["triangles"], "tris, letters", round(tw, 2), "m", flush=True)
    return rec


def main():
    """blender -b -P author_ward_signs.py [-- key ...]: only the named signs are rebuilt (their records merged into
    signs.json); the source .blend is written only for a full run."""
    keys = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else list(SIGNS)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    path = OUT / "signs.json"
    old = json.loads(path.read_text())["signs"] if path.exists() and len(keys) < len(SIGNS) else {}
    recs = dict(old)
    recs.update({k: build_sign(k, SIGNS[k]) for k in keys})
    path.write_text(json.dumps({"source": "art/hall_district_20260930/author_ward_signs.py", "date": "2026-09-30",
                                "signs": recs}, indent=1))
    if len(keys) == len(SIGNS):
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE / "signs-source.blend"))
    else:
        bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "art/north_avenue_20260930/north-signs-source.blend"))


main()
