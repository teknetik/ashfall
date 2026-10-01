"""Ward shade sails: Cycles review renders in Blender 5.2 headless (1 October 2026).

Loads one or more sites' LOD glTFs (Sail, Rig, Festoon) at their world positions, assigns preview materials (the
canvas with its base/normal maps, a thin-canvas translucency and alpha holes; flat versions of the shared Ward
materials), a sandstone ground plane, a 1.8 m figure for scale and the 13:00 sun of the scene clock (survey.json), and
renders player-height and overview views. Context buildings are not loaded (Unity editor captures and the native
lookbook judge the sails in place).

Run: $O/blender.sh art/shade_sails_20261001/review_sails.py -- <tag> <Site,Site|all> [lod] [views] [night]
     views: under,outside,corner,aerial (default all); night = festoon bulbs only, sun off
Out: review/<tag>/<Site>_<view>.png
"""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MODELS = ROOT / "unity/AthenHill/Assets/AthenHill/Art/ShadeSails/Models"
TEX = ROOT / "unity/AthenHill/Assets/AthenHill/Art/ShadeSails/Textures"
LAYOUT = json.loads((HERE / "sail-layout.json").read_text())
REC = json.loads((MODELS / "sails.json").read_text())
SURVEY = json.loads((ROOT / "unity/evidence/shade-sails/20261001/survey-before.json").read_text())


def U(p):
    return Vector((-p[0], -p[2], p[1]))


FLAT = {
    "VH_PaintedSteel": ((0.36, 0.39, 0.32), 0.0, 0.55), "SS_PoleGrey": ((0.33, 0.35, 0.32), 0.0, 0.55),
    "SS_PoleRed": ((0.3, 0.1, 0.07), 0.0, 0.6), "SS_PoleOlive": ((0.2, 0.22, 0.14), 0.0, 0.6), "WS_PaintRed": ((0.38, 0.12, 0.08), 0.0, 0.6),
    "WS_PaintOlive": ((0.22, 0.24, 0.15), 0.0, 0.6), "VH_Steel": ((0.52, 0.52, 0.5), 0.85, 0.42),
    "VH_Dark": ((0.06, 0.06, 0.06), 0.4, 0.6), "VH_Rubber": ((0.035, 0.035, 0.035), 0.0, 0.75),
    "VH_Ashlar": ((0.58, 0.45, 0.32), 0.0, 0.9), "SD_Sack": ((0.5, 0.42, 0.31), 0.0, 0.95), "SD_Rope": ((0.45, 0.38, 0.28), 0.0, 0.9),
    "WS_ClothMadder": ((0.32, 0.08, 0.05), 0.0, 0.85), "WS_ClothIndigo": ((0.06, 0.08, 0.15), 0.0, 0.85),
    "WS_ClothBone": ((0.55, 0.49, 0.38), 0.0, 0.85), "SS_BulbDead": ((0.15, 0.13, 0.11), 0.0, 0.15),
}


def flat_mat(name, night):
    m = bpy.data.materials.new("pv_" + name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    if name == "SS_FestoonBulb":
        b.inputs["Base Color"].default_value = (1, 0.8, 0.55, 1)
        b.inputs["Emission Color"].default_value = (1.0, 0.62, 0.32, 1)
        b.inputs["Emission Strength"].default_value = 18.0 if night else 0.6
        b.inputs["Roughness"].default_value = 0.2
        return m
    c, met, r = FLAT.get(name, ((0.5, 0.5, 0.5), 0.0, 0.6))
    b.inputs["Base Color"].default_value = (*c, 1)
    b.inputs["Metallic"].default_value = met
    b.inputs["Roughness"].default_value = r
    return m


def sail_mat(sid):
    m = bpy.data.materials.new("pv_sail_" + sid)
    m.use_nodes = True
    nt = m.node_tree
    nodes, links = nt.nodes, nt.links
    b = nodes["Principled BSDF"]
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(TEX / f"SS_Sail_{sid}_BaseMap.png"))
    nm = nodes.new("ShaderNodeTexImage")
    nm.image = bpy.data.images.load(str(TEX / f"SS_Sail_{sid}_Normal.png"))
    nm.image.colorspace_settings.name = "Non-Color"
    nmap = nodes.new("ShaderNodeNormalMap")
    links.new(nm.outputs["Color"], nmap.inputs["Color"])
    links.new(nmap.outputs["Normal"], b.inputs["Normal"])
    links.new(tex.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.88
    # thin canvas: mix in a translucent lobe (the Unity shader's _WardTranslucency ~0.2)
    tr = nodes.new("ShaderNodeBsdfTranslucent")
    links.new(tex.outputs["Color"], tr.inputs["Color"])
    mix = nodes.new("ShaderNodeMixShader")
    mix.inputs["Fac"].default_value = 0.18
    links.new(b.outputs["BSDF"], mix.inputs[1])
    links.new(tr.outputs["BSDF"], mix.inputs[2])
    # alpha holes (clip)
    tp = nodes.new("ShaderNodeBsdfTransparent")
    gt = nodes.new("ShaderNodeMath"); gt.operation = "GREATER_THAN"; gt.inputs[1].default_value = 0.5
    links.new(tex.outputs["Alpha"], gt.inputs[0])
    mix2 = nodes.new("ShaderNodeMixShader")
    links.new(gt.outputs["Value"], mix2.inputs["Fac"])
    links.new(tp.outputs["BSDF"], mix2.inputs[1])
    links.new(mix.outputs["Shader"], mix2.inputs[2])
    out = nodes["Material Output"]
    links.new(mix2.outputs["Shader"], out.inputs["Surface"])
    return m


def figure(at):
    p = U(at)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.2, depth=1.45, location=(p.x, p.y, 0.725))
    body = bpy.context.active_object
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.12, location=(p.x, p.y, 1.6))
    head = bpy.context.active_object
    m = bpy.data.materials.new("figure"); m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.25, 0.3, 0.38, 1)
    for o in (body, head):
        o.data.materials.append(m)


def base_view(site, c):
    """Eye at 1.65 m, 2.4 m from a footing (a guyed plate if there is one), looking at its foot."""
    poles = site["poles"]
    k = next((i for i, p in enumerate(poles) if p["kind"] == "plate"), next((i for i, p in enumerate(poles) if p["kind"] == "block"), 0))
    b = np.array(poles[k]["base"])
    d = c - b; d[1] = 0; d /= np.linalg.norm(d)
    return ([b[0] + d[0] * 2.4, 1.65, b[2] + d[2] * 2.4], [b[0], 0.35, b[2]])


def look(cam, eye, target):
    cam.location = U(eye)
    d = U(target) - U(eye)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    tag = argv[0]
    sites = [s["id"] for s in LAYOUT["sails"]] if argv[1] == "all" else argv[1].split(",")
    lod = int(argv[2]) if len(argv) > 2 else 0
    views = argv[3].split(",") if len(argv) > 3 and argv[3] != "all" else ["under", "outside", "corner", "aerial"]
    night = len(argv) > 4 and argv[4] == "night"
    outdir = HERE / "review" / tag
    outdir.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 48 if not night else 64
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = 1280, 720
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.exposure = 0.0 if not night else 1.5
    world = bpy.data.worlds.new("w"); sc.world = world; world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.42, 0.55, 0.75, 1) if not night else (0.004, 0.006, 0.012, 1)
    bg.inputs["Strength"].default_value = 1.0
    if not night:
        sun = next(s for s in SURVEY["sun"] if s["hour"] == 13.0)
        lf = sun["lightForward"]
        d = Vector((-lf[0], -lf[2], lf[1]))
        bpy.ops.object.light_add(type="SUN")
        sl = bpy.context.active_object
        sl.data.energy = 4.2
        sl.data.angle = math.radians(0.6)
        sl.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    # ground
    bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, 0))
    g = bpy.context.active_object
    gm = bpy.data.materials.new("ground"); gm.use_nodes = True
    gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.5, 0.4, 0.29, 1)
    gm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.95
    g.data.materials.append(gm)
    mats = {}
    for sid in sites:
        rec = REC[sid]
        origin = rec["origin"]
        for grp in ("Sail", "Rig", "Festoon"):
            before = set(bpy.data.objects)
            bpy.ops.import_scene.gltf(filepath=str(MODELS / f"SS_{sid}_{grp}_LOD{lod}.glb"))
            for o in set(bpy.data.objects) - before:
                if o.parent is None:
                    o.location = o.location + U(origin)
                if o.type == "MESH":
                    for i, slot in enumerate(o.material_slots):
                        n = slot.material.name.split(".")[0] if slot.material else ""
                        if n.startswith("SS_Sail_"):
                            key = n
                            if key not in mats:
                                mats[key] = sail_mat(n[len("SS_Sail_"):])
                        else:
                            key = n
                            if key not in mats:
                                mats[key] = flat_mat(n, night)
                        slot.material = mats[key]
        if night:
            for l in rec["lights"]:
                bpy.ops.object.light_add(type="POINT", location=U(l["pos"]))
                pl = bpy.context.active_object
                pl.data.energy = l["intensity"] * 60
                pl.data.color = l["color"]
                pl.data.shadow_soft_size = 0.3
    cam_data = bpy.data.cameras.new("cam"); cam = bpy.data.objects.new("cam", cam_data); sc.collection.objects.link(cam); sc.camera = cam
    cam_data.lens = 24
    for sid in sites:
        site = next(s for s in LAYOUT["sails"] if s["id"] == sid)
        fab = np.array(site["fabric"]); c = fab.mean(0)
        hs = [f[1] for f in site["fixings"]]
        lo_k = int(np.argmin(hs)); hi_k = int(np.argmax(hs))
        lo_p, hi_p = np.array(site["fixings"][lo_k]), np.array(site["fixings"][hi_k])
        # the figure stands under the sail, a little towards the low corner
        fig_at = c + (lo_p - c) * 0.35
        figure([fig_at[0], 0, fig_at[2]])
        out_dir = (c - hi_p); out_dir[1] = 0; out_dir /= np.linalg.norm(out_dir)
        V = {
            "under": ([c[0] + (lo_p[0] - c[0]) * 0.6, 1.65, c[2] + (lo_p[2] - c[2]) * 0.6], [hi_p[0], hi_p[1] + 0.6, hi_p[2]]),
            "outside": ([c[0] + out_dir[0] * 11, 1.65, c[2] + out_dir[2] * 11], [c[0], 3.0, c[2]]),
            "corner": ([hi_p[0] + (c[0] - hi_p[0]) * 0.35, 1.65, hi_p[2] + (c[2] - hi_p[2]) * 0.35], [hi_p[0], hi_p[1] - 0.2, hi_p[2]]),
            "hardware": ([hi_p[0] + (c[0] - hi_p[0]) * 0.12, hi_p[1] - 0.25, hi_p[2] + (c[2] - hi_p[2]) * 0.12],
                         [hi_p[0] + (c[0] - hi_p[0]) * 0.04, hi_p[1], hi_p[2] + (c[2] - hi_p[2]) * 0.04]),
            "base": base_view(site, c),
            "aerial": ([c[0] + out_dir[0] * 9 + 3, 11.0, c[2] + out_dir[2] * 9 - 3], [c[0], 2.0, c[2]]),
        }
        for v in views:
            eye, tgt = V[v]
            look(cam, eye, tgt)
            cam_data.lens = {"under": 18, "corner": 18, "hardware": 35, "base": 28}.get(v, 24)
            sc.render.filepath = str(outdir / f"{sid}_{v}{'_night' if night else ''}.png")
            bpy.ops.render.render(write_still=True)
            print("rendered", sc.render.filepath, flush=True)


if __name__ == "__main__":
    main()
