"""Decal textures for the Ward life pass (Blender 5.2): painted dock marks atlas and a damp-paving patch.
WL_DecalMarks.png 2048x1024, cells 1024x256 (col, row from the top): (0,0) BAY 1, (1,0) BAY 2, (0,1) BAY 3,
(1,1) WEIGH, (0,2) KEEP CLEAR, (1,2) solid line, (0,3) GOODS, (1,3) dashed line. Worn bone paint: alpha = letter mask x
patchy wear x chips. WL_DecalDamp.png 1024x512: damp stone round a tap trough (dark centre, pale mineral tide marks).
Run: blender.sh bake_marks.py"""
import bpy, sys, numpy as np
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
OUT = ROOT / "unity/AthenHill/Assets/AthenHill/Art/WardLife/Textures"
FONT = ROOT / "art/west_gate_20260926/fonts/stardosstencil__StardosStencil-Bold.ttf"
import importlib.util
spec = importlib.util.spec_from_file_location("bg", HERE / "bake_gabion.py")
# reuse helpers without running the bake: copy the few we need
exec(compile("\n".join(l for l in open(HERE / "bake_gabion.py").read().split("\n")
                       if not l.startswith("main()")), "bg", "exec"), globals())

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.samples = 8; sc.cycles.device = "CPU"
sc.render.resolution_x, sc.render.resolution_y = 2048, 1024
sc.render.film_transparent = True
sc.render.image_settings.file_format = "OPEN_EXR"; sc.render.image_settings.color_depth = "32"
sc.view_settings.view_transform = "Standard"
w = bpy.data.worlds.new("w"); w.color = (0, 0, 0); sc.world = w
em = bpy.data.materials.new("white")
nt = em.node_tree; nt.nodes.clear()
o = nt.nodes.new("ShaderNodeOutputMaterial"); e = nt.nodes.new("ShaderNodeEmission"); nt.links.new(e.outputs[0], o.inputs[0])
cells = {(0, 0): "BAY 1", (1, 0): "BAY 2", (0, 1): "BAY 3", (1, 1): "WEIGH", (0, 2): "KEEP CLEAR", (0, 3): "GOODS"}
for (c, r), txt in cells.items():
    cu = bpy.data.curves.new(txt, "FONT"); cu.body = txt
    cu.font = bpy.data.fonts.load(str(FONT)); cu.size = 1.5; cu.align_x = "CENTER"; cu.align_y = "CENTER"
    ob = bpy.data.objects.new(txt, cu); sc.collection.objects.link(ob)
    ob.location = (c * 8 + 4, (3 - r) * 2 + 1, 0)
    ob.data.materials.append(em)
    bpy.context.view_layer.update()
    # fit within the cell (8 x 2 units, margins)
    d = ob.dimensions
    k = min(7.0 / max(d.x, 1e-3), 1.6 / max(d.y, 1e-3), 1.0)
    ob.scale = (k, k, 1)
for (c, r, dashed) in ((1, 2, False), (1, 3, True)):
    x = 0.2
    while x < 7.8:
        seg = 1.2 if dashed else 7.6
        bpy.ops.mesh.primitive_plane_add(size=1, location=(c * 8 + x + seg / 2, (3 - r) * 2 + 1, 0))
        p = bpy.context.active_object; p.scale = (seg, 0.9, 1); p.data.materials.append(em)
        x += seg + (0.8 if dashed else 10)
cd = bpy.data.cameras.new("c"); cd.type = "ORTHO"; cd.ortho_scale = 16
cam = bpy.data.objects.new("c", cd); sc.collection.objects.link(cam); cam.location = (8, 4, 5); sc.camera = cam
sc.render.filepath = str(HERE / "bake/marks.exr")
bpy.ops.render.render(write_still=True)
a = load_exr(HERE / "bake/marks.exr")[..., 3]
h, wd = a.shape
wear = vnoise(wd, 16, 31, 5)[:h, :] if False else None
n1 = vnoise(2048, 24, 31, 5)[:1024, :]
n2 = vnoise(2048, 160, 32, 3)[:1024, :]
paint = a * np.clip(smoothstep(0.25, 0.55, n1) * 0.75 + 0.25, 0, 1) * (n2 > 0.32)
col = np.zeros((h, wd, 4), np.float32)
col[..., 0], col[..., 1], col[..., 2] = 0.82, 0.76, 0.6
col[..., :3] *= (0.85 + 0.2 * n1)[..., None]
col[..., 3] = paint * 0.92
save_png(OUT / "WL_DecalMarks.png", col)
# damp patch: dark wet centre, ragged edge, pale mineral tide lines
H, Wd = 512, 1024
yy, xx = np.mgrid[0:H, 0:Wd].astype(np.float32)
u = (xx / Wd - 0.5) * 2; v = (yy / H - 0.5) * 2
nn = vnoise(1024, 8, 41, 5)[:H, :]
dist = np.sqrt(u ** 2 + (v * 1.0) ** 2) + (nn - 0.5) * 0.55
wet = 1 - smoothstep(0.45, 0.95, dist)
tide = np.exp(-((dist - 0.98) / 0.035) ** 2) * 0.8 + np.exp(-((dist - 0.8) / 0.025) ** 2) * 0.35
d = np.zeros((H, Wd, 4), np.float32)
dark = np.array([0.11, 0.095, 0.075]); pale = np.array([0.62, 0.58, 0.52])
mix = np.clip(tide / (tide + wet + 1e-4), 0, 1)[..., None]
d[..., :3] = dark * (1 - mix) + pale * mix
d[..., 3] = np.clip(wet * 0.85 + tide * 0.25, 0, 0.9) * smoothstep(0.0, 0.08, 1 - np.abs(u)) * smoothstep(0.0, 0.1, 1 - np.abs(v))
save_png(OUT / "WL_DecalDamp.png", d)
