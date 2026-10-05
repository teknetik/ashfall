"""Source review renders of the player's home WallHomeP (Blender 5.2, Cycles on the CPU; not the game's render).

Run:  ~/.local/state/ward-programme/blender.sh art/ward_home_20261005/review_home.py -- [src=<dir>] [views=a,b] [tag=<t>]
      src: folder with WallHomeP_LOD<n>.glb + homep.json (default Unity's WardBuildings/Models); lod=1 renders LOD1.
Imports the model, gives every material a preview shader built from its Unity .mat (base map + tiling + colour, mask
map metallic/smoothness, normal map; MasonryLit materials also take the vertex tint and occlusion) or, for the new
HP_* materials, from this pass's textures and README values; places the record's street-dressing mounts (Poly Haven
prop GLBs with their own materials), the interior lights from the record, a sandstone curtain wall and paving, a 1.8 m
figure, and renders review/<tag>_<view>.png at 1280 x 720. The door leaf is rotated to its open yaw for views marked
open. Views are in building-local Unity metres; U() converts to Blender (Unity (x, y, z) -> Blender (-x, -z, y)), the
same mapping the GLBs were authored with, so the renders are not mirror-imaged (checked: the door is on the viewer's
left from the street, as in the game's cam_wb_home_south captures).
"""
import bpy, json, math, re, sys
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ART = ROOT / "unity/AthenHill/Assets/AthenHill/Art"
OUT = HERE / "review"
OUT.mkdir(exist_ok=True)
URP_LIT = "933532a4fcc9baf4fa0491de14d08ed7"
MASONRY = "fd89adb197a104c26804abf391557c73"
HP = {  # new materials (no Unity .mat yet): base colour, roughness, metallic, texture
    "HP_Insulation": ((1, 1, 1), 0.95, 0.0, HERE / "textures/HP_Insulation.png"),      # tiles every 0.5 m
    "HP_Mirror": ((0.86, 0.87, 0.88), 0.05, 1.0, None),
    "HP_Photo": ((1, 1, 1), 0.45, 0.0, HERE / "textures/HP_Photo.png"),
    "HP_Calendar": ((1, 1, 1), 0.85, 0.0, HERE / "textures/HP_Calendar.png"),
    "HP_Succulent": ((0.33, 0.43, 0.3), 0.55, 0.0, None),
}


def U(p):
    return Vector((-p[0], -p[2], p[1]))


# ------------------------------------------------------------------ Unity material index
MATS = {}
for p in ART.rglob("*.mat"):
    MATS.setdefault(p.stem, p)
GUIDS = {}
for meta in ART.rglob("*.meta"):
    if meta.stem.lower().endswith((".png", ".jpg", ".jpeg", ".tga", ".exr", ".tif")):
        m = re.search(r"^guid: ([0-9a-f]+)", meta.read_text(errors="ignore"), re.M)
        if m:
            GUIDS[m.group(1)] = meta.with_suffix("")
NUM = r"(-?[\d.]+(?:e-?\d+)?)"


def parse_mat(path):
    txt = path.read_text(errors="ignore")

    def tex(name):
        m = re.search(rf"- {name}:\n\s+m_Texture: {{fileID: \d+, guid: ([0-9a-f]+), type: \d+}}\n\s+m_Scale: {{x: {NUM}, y: {NUM}}}\n"
                      rf"\s+m_Offset: {{x: {NUM}, y: {NUM}}}", txt)
        if m and m.group(1) in GUIDS:
            return GUIDS[m.group(1)], (float(m.group(2)), float(m.group(3))), (float(m.group(4)), float(m.group(5)))
        return None

    def flt(name, d):
        m = re.search(rf"- {name}: {NUM}\n", txt)
        return float(m.group(1)) if m else d

    def col(name, d):
        m = re.search(rf"- {name}: {{r: {NUM}, g: {NUM}, b: {NUM}, a: {NUM}}}", txt)
        return tuple(float(m.group(i)) for i in range(1, 5)) if m else d
    sh = re.search(r"m_Shader: {fileID: \d+, guid: ([0-9a-f]+)", txt)
    return {"shader": sh.group(1) if sh else "", "base": tex("_BaseMap"), "bump": tex("_BumpMap"), "mask": tex("_MetallicGlossMap"),
            "color": col("_BaseColor", (1, 1, 1, 1)), "metal": flt("_Metallic", 0.0), "smooth": flt("_Smoothness", 0.5),
            "bumpscale": flt("_BumpScale", 1.0), "emit": col("_EmissionColor", (0, 0, 0, 1)), "surface": flt("_Surface", 0.0),
            "emit_on": "_EMISSION" in txt}


IMG = {}


def image(path, noncolor=False):
    key = (str(path), noncolor)
    if key not in IMG:
        im = bpy.data.images.load(str(path), check_existing=False)
        if noncolor:
            im.colorspace_settings.name = "Non-Color"
        IMG[key] = im
    return IMG[key]


def tex_node(nt, spec, noncolor=False):
    path, scale, off = spec
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = image(path, noncolor)
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "UVMap"
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (scale[0], scale[1], 1)
    mp.inputs["Location"].default_value = (off[0], off[1], 0)
    nt.links.new(uv.outputs["UV"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], t.inputs["Vector"])
    return t


CACHE = {}


def preview(name):
    base = re.sub(r"\.\d+$", "", name)
    if base in CACHE:
        return CACHE[base]
    m = bpy.data.materials.new("prev_" + base)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    path = MATS.get(base) or MATS.get("SD_" + base) or MATS.get("PH_" + base)
    if base in HP:
        c, r, mt, tx = HP[base]
        bsdf.inputs["Base Color"].default_value = (*c, 1)
        bsdf.inputs["Roughness"].default_value = r
        bsdf.inputs["Metallic"].default_value = mt
        if tx is not None and Path(tx).exists():
            if base == "HP_Insulation":
                t = tex_node(nt, (tx, (2.0, 2.0), (0.0, 0.0)))
            else:
                t = nt.nodes.new("ShaderNodeTexImage")
                t.image = image(tx)
                t.extension = "CLIP"
            nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
    elif path is not None:
        sp = parse_mat(path)
        cr, cg, cb, ca = sp["color"]
        colour_out = None
        if sp["base"]:
            t = tex_node(nt, sp["base"])
            mul = nt.nodes.new("ShaderNodeMix")
            mul.data_type, mul.blend_type = "RGBA", "MULTIPLY"
            mul.inputs["Factor"].default_value = 1.0
            nt.links.new(t.outputs["Color"], mul.inputs[6])
            mul.inputs[7].default_value = (cr, cg, cb, 1)
            colour_out = mul.outputs[2]
        if sp["shader"] == MASONRY:
            va = nt.nodes.new("ShaderNodeVertexColor")
            va.layer_name = ""
            m2 = nt.nodes.new("ShaderNodeMix")
            m2.data_type, m2.blend_type = "RGBA", "MULTIPLY"
            m2.inputs["Factor"].default_value = 1.0
            if colour_out is not None:
                nt.links.new(colour_out, m2.inputs[6])
            else:
                m2.inputs[6].default_value = (cr, cg, cb, 1)
            sc = nt.nodes.new("ShaderNodeMath")
            sc.operation = "MULTIPLY"
            nt.links.new(va.outputs["Alpha"], sc.inputs[0])
            sc.inputs[1].default_value = 2.0
            vc2 = nt.nodes.new("ShaderNodeMix")
            vc2.data_type, vc2.blend_type = "RGBA", "MULTIPLY"
            vc2.inputs["Factor"].default_value = 1.0
            nt.links.new(va.outputs["Color"], vc2.inputs[6])
            comb = nt.nodes.new("ShaderNodeCombineColor")
            for i in range(3):
                nt.links.new(sc.outputs[0], comb.inputs[i])
            nt.links.new(comb.outputs[0], vc2.inputs[7])
            nt.links.new(vc2.outputs[2], m2.inputs[7])
            colour_out = m2.outputs[2]
        if colour_out is not None:
            nt.links.new(colour_out, bsdf.inputs["Base Color"])
        else:
            bsdf.inputs["Base Color"].default_value = (cr, cg, cb, 1)
        bsdf.inputs["Metallic"].default_value = sp["metal"]
        bsdf.inputs["Roughness"].default_value = 1 - sp["smooth"]
        if sp["mask"]:
            mk = tex_node(nt, (sp["mask"][0], sp["base"][1] if sp["base"] else sp["mask"][1], sp["base"][2] if sp["base"] else sp["mask"][2]), True)
            sep = nt.nodes.new("ShaderNodeSeparateColor")
            nt.links.new(mk.outputs["Color"], sep.inputs[0])
            nt.links.new(sep.outputs[0], bsdf.inputs["Metallic"])
            ms = nt.nodes.new("ShaderNodeMath")
            ms.operation = "MULTIPLY"
            nt.links.new(mk.outputs["Alpha"], ms.inputs[0])
            ms.inputs[1].default_value = sp["smooth"]
            inv = nt.nodes.new("ShaderNodeMath")
            inv.operation = "SUBTRACT"
            inv.inputs[0].default_value = 1.0
            nt.links.new(ms.outputs[0], inv.inputs[1])
            nt.links.new(inv.outputs[0], bsdf.inputs["Roughness"])
        if sp["bump"]:
            nb = tex_node(nt, (sp["bump"][0], sp["base"][1] if sp["base"] else sp["bump"][1], sp["base"][2] if sp["base"] else sp["bump"][2]), True)
            nm = nt.nodes.new("ShaderNodeNormalMap")
            nm.uv_map = "UVMap"
            nm.inputs["Strength"].default_value = sp["bumpscale"]
            nt.links.new(nb.outputs["Color"], nm.inputs["Color"])
            nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
        er, eg, eb, _ = sp["emit"]
        if sp["emit_on"] and max(er, eg, eb) > 0.01:
            bsdf.inputs["Emission Color"].default_value = (er, eg, eb, 1)
            bsdf.inputs["Emission Strength"].default_value = 1.0
        if sp["surface"] > 0.5:
            bsdf.inputs["Alpha"].default_value = max(ca, 0.06)
            bsdf.inputs["Roughness"].default_value = 0.05
    else:
        bsdf.inputs["Base Color"].default_value = (1, 0, 1, 1)      # missing: magenta, so it shows in review
        print("MISSING material", base, flush=True)
    if base in ("SS_BulbWarm", "NF_WallLampBulb"):
        bsdf.inputs["Emission Color"].default_value = (1.0, 0.75, 0.45, 1)
        bsdf.inputs["Emission Strength"].default_value = 12.0
    if base in ("WB_LedCyan", "WB_ScreenCyan", "WS_LedCyan"):
        bsdf.inputs["Emission Color"].default_value = (0.3, 0.9, 1.0, 1)
        bsdf.inputs["Emission Strength"].default_value = 6.0
    CACHE[base] = m
    return m


def import_glb(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    new = [o for o in bpy.data.objects if o not in before]
    for ob in new:
        if ob.type == "MESH":
            for slot in ob.material_slots:
                if slot.material:
                    slot.material = preview(slot.material.name)
    return new


def mount(rec_m):
    path = rec_m.get("path")
    if not path:
        return
    pid = Path(path).stem[3:]
    glb = ART / f"StreetDressing/Props/{pid}/{pid}_LOD0.glb"
    if not glb.exists():
        print("no prop", glb, flush=True)
        return
    new = import_glb(glb)
    piv = bpy.data.objects.new("mount_" + pid, None)
    bpy.context.scene.collection.objects.link(piv)
    for o in new:
        if o.parent is None:
            o.parent = piv
    piv.location = U(rec_m["pos"])
    piv.rotation_euler = (0, 0, math.radians(-rec_m.get("yaw", 0.0)))   # Unity yaw t -> Blender Z rotation -t


def flat_mat(name, rgba, emit=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = rgba
    b.inputs["Roughness"].default_value = 0.8
    if rgba[3] < 1:
        b.inputs["Alpha"].default_value = rgba[3]
    if emit:
        b.inputs["Emission Color"].default_value = rgba
        b.inputs["Emission Strength"].default_value = emit
    return m


def figure(pos, name="figure"):
    """1.8 m scale figure: body and head, plus the player capsule's 0.7 m footprint on the floor."""
    x, y, z = pos
    mat = flat_mat("figure_" + name, (0.85, 0.86, 0.9, 1))
    bpy.ops.mesh.primitive_cylinder_add(radius=0.17, depth=1.46, location=U((x, y + 0.73, z)))
    bpy.context.active_object.data.materials.append(mat)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.11, location=U((x, y + 1.69, z)))
    bpy.context.active_object.data.materials.append(mat)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.35, depth=0.004, location=U((x, y + 0.004, z)))
    bpy.context.active_object.data.materials.append(flat_mat("foot_" + name, (0.2, 0.9, 0.4, 0.35)))


def context_scene(night):
    # paving, the curtain wall behind the container and a neighbour's wall end
    bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, -0.002))
    bpy.context.active_object.data.materials.append(flat_mat("paving", (0.5, 0.41, 0.31, 1)))
    bpy.ops.mesh.primitive_cube_add(size=1, location=U((0, 3.0, -1.75)))
    w = bpy.context.active_object
    w.scale = (24, 0.5, 6)
    w.data.materials.append(flat_mat("wall", (0.62, 0.48, 0.34, 1)))
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    bpy.context.scene.collection.objects.link(sun)
    sun.data.energy = 0.0 if night else 4.5
    sun.data.angle = math.radians(1.0)
    # sun high in the north-west quarter of the sky (Unity), so the street face gets light as at the game's 13:00 views
    d = Vector((-0.45, -0.75, 0.48)).normalized()           # Unity direction the light travels
    db = U(d)
    sun.rotation_euler = db.to_track_quat("-Z", "Y").to_euler()
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.05, 0.06, 0.09, 1) if night else (0.55, 0.62, 0.72, 1)
    bg.inputs["Strength"].default_value = 0.4 if night else 1.0
    bpy.context.scene.world = world


VIEWS = {   # name: (eye, target, lens, door_open, ortho_scale)
    "ext_closed": ((0.6, 1.62, 7.6), (0.2, 1.45, 0.0), 22, False, None),
    "ext_open": ((2.6, 1.62, 4.6), (0.9, 1.35, 0.4), 22, True, None),
    "doorway_west": ((1.35, 2.12, 0.92), (-2.6, 1.15, -0.35), 17, True, None),
    "doorway_east": ((0.75, 2.12, 0.85), (2.6, 1.35, -0.95), 17, True, None),
    "locker": ((1.1, 2.05, 0.55), (1.12, 1.45, -1.0), 22, True, None),
    "bunk": ((-1.25, 1.98, 0.5), (-2.45, 0.95, -0.75), 20, True, None),
    "inside_out": ((-2.3, 2.05, 0.15), (1.4, 1.55, 1.0), 17, True, None),
    "plan": ((0.0, 2.45, 0.35), (0.0, 0.0, 0.35), 0, True, 6.6),
}


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    kv = dict(a.split("=", 1) for a in args if "=" in a)
    night = "night" in args
    src = Path(kv.get("src", ART / "WardBuildings/Models"))
    lod = int(kv.get("lod", "0"))
    tag = kv.get("tag", "home")
    names = kv["views"].split(",") if "views" in kv else list(VIEWS)
    rec = json.loads((src / "homep.json").read_text())
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    objs = import_glb(src / f"WallHomeP_LOD{lod}.glb")
    leaf = next(o for o in objs if "DoorLeaf" in o.name)
    for o in objs:          # bulbs, LED and readout are emissive shells round the lights: they must not shadow them
        if "Glow" in o.name:
            o.visible_shadow = False
    for m_ in rec.get("mounts", []):
        mount(m_)
    context_scene(night)
    for L in rec["lights"]:
        kind = "SPOT" if L["type"] == "spot" else "POINT"
        lo = bpy.data.objects.new(L["name"], bpy.data.lights.new(L["name"], kind))
        sc.collection.objects.link(lo)
        lo.location = U(L["pos"])
        lo.data.color = L["color"][:3]
        lo.data.shadow_soft_size = 0.02
        watts = {"Home ceiling light": 70, "Home reading lamp": 25, "Home status LED": 0.4, "Porch light": 40}.get(L["name"], 30)
        lo.data.energy = watts
        if kind == "SPOT":
            lo.data.spot_size = math.radians(L.get("angle", 60))
            lo.data.spot_blend = 0.4
            d = U(L["target"]) - U(L["pos"])
            lo.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    a = rec["anchors"]
    before = set(bpy.data.objects)
    figure(a["locker_use"]["pos"][:1] + [a["locker_use"]["floor_y"]] + a["locker_use"]["pos"][2:], "locker")
    figure(a["wake_point"]["pos"], "wake")
    figs = [o for o in bpy.data.objects if o not in before]
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = int(kv.get("samples", "64"))
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = 1280, 720
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.exposure = float(kv.get("exposure", "0.0"))
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    for v in names:
        eye, tgt, lens, door_open, ortho = VIEWS[v]
        for o in figs:          # scale figures only in the wide views; they would block the close-ups
            o.hide_render = v in ("locker", "bunk", "inside_out", "ext_closed")
        leaf.rotation_mode = "XYZ"
        leaf.rotation_euler = (0, 0, math.radians(-rec["anchors"]["door_hinge"]["openYaw"]) if door_open else 0.0)
        cam.data.clip_start = 0.02
        if ortho:
            cam.data.type = "ORTHO"
            cam.data.ortho_scale = ortho
            cam.location = U(eye)
            cam.rotation_euler = (0, 0, 0)       # looking down Blender -Z = Unity -Y
            cam.rotation_euler.z = math.radians(180)
        else:
            cam.data.type = "PERSP"
            cam.data.lens = lens
            e, t = U(eye), U(tgt)
            cam.location = e
            cam.rotation_euler = (t - e).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = str(OUT / f"{tag}_{v}{'_night' if night else ''}.png")
        bpy.ops.render.render(write_still=True)
        print("wrote", sc.render.filepath, flush=True)


main()
