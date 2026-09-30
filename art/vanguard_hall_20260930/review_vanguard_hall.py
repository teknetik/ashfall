"""Source review renders for the Vanguard Hall rebuild (Blender 5.2, EEVEE).

Run:  blender -b vanguard-hall-source.blend --python-exit-code 1 -P review_vanguard_hall.py -- [LOD0|LOD1] [outdir] [views...]

Assigns preview materials from the Poly Haven sources (box-projected metre UVs, per-block vertex tint for
masonry), a late-afternoon sun + sky, a 1.8 m scale figure, and renders named views. These are source-review
images, not evidence of the game render.
"""
import bpy, math, sys
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
PH = HERE / "polyhaven"
WG = HERE.parents[0] / "west_gate_20260926/polyhaven/textures"
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
LODN = argv[0] if argv else "LOD0"
OUTDIR = Path(argv[1]) if len(argv) > 1 else HERE / "review"
VIEWS = argv[2:]
OUTDIR.mkdir(parents=True, exist_ok=True)


def U(p):
    return Vector((-p[0], -p[2], p[1]))


# tile size in metres, texture set, tint, metallic, roughness scale
SPEC = {
    "VH_Ashlar": ("worn_rock_natural_01", 2.0, (1.0, 0.95, 0.88), 0, 1.0, True),
    "VH_AshlarRough": ("sandstone_cracks", 2.0, (0.93, 0.86, 0.78), 0, 1.0, True),
    "VH_Mortar": ("sandstone_cracks", 1.5, (0.62, 0.56, 0.48), 0, 1.0, False),
    "VH_PodiumSlab": ("sandstone_cracks", 2.0, (0.95, 0.9, 0.84), 0, 1.0, True),
    "VH_DoorSteel": ("rust_coarse_01", 2.2, (0.55, 0.45, 0.4), 0.6, 0.9, False),
    "VH_Steel": ("rusty_metal_sheet", 2.0, (0.75, 0.7, 0.66), 0.7, 0.9, False),
    "VH_PaintedSteel": ("painted_metal_shutter", 2.0, (0.42, 0.45, 0.38), 0.3, 1.0, False),
    "VH_Bronze": ("rust_coarse_01", 1.0, (0.62, 0.44, 0.24), 1.0, 0.55, False),
    "VH_Roof": ("sandstone_cracks", 2.0, (0.7, 0.66, 0.6), 0, 1.0, False),
    "VH_Sand": ("dense_sand", 1.8, (1.0, 0.95, 0.88), 0, 1.0, False),
}


def tex(name, kind):
    d = PH / name
    if not d.exists():
        d = WG / name
    pats = {"diff": "_diff_", "nor": "_nor_gl_", "arm": "_arm_"}
    for f in sorted(d.glob("*")):
        if pats[kind] in f.name:
            return f
    return None


def mat_setup(m, spec):
    name, tile, tint, metal, rough_k, vcol = spec
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bs.outputs[0], out.inputs[0])
    uv = nt.nodes.new("ShaderNodeUVMap"); uv.uv_map = "UVMap"
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1 / tile, 1 / tile, 1)
    nt.links.new(uv.outputs[0], mp.inputs[0])
    d = tex(name, "diff")
    base = None
    if d:
        ti = nt.nodes.new("ShaderNodeTexImage"); ti.image = bpy.data.images.load(str(d), check_existing=True)
        nt.links.new(mp.outputs[0], ti.inputs[0])
        mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"; mix.inputs[0].default_value = 1
        nt.links.new(ti.outputs[0], mix.inputs[6]); mix.inputs[7].default_value = (*tint, 1)
        base = mix.outputs[2]
        if vcol:
            ca = nt.nodes.new("ShaderNodeVertexColor"); ca.layer_name = "Col"
            m2 = nt.nodes.new("ShaderNodeMath"); m2.operation = "MULTIPLY"; m2.inputs[1].default_value = 2.0
            mm = nt.nodes.new("ShaderNodeMix"); mm.data_type = "RGBA"; mm.blend_type = "MULTIPLY"; mm.inputs[0].default_value = 1
            vc2 = nt.nodes.new("ShaderNodeVectorMath"); vc2.operation = "SCALE"; vc2.inputs[3].default_value = 2.0
            nt.links.new(ca.outputs[0], vc2.inputs[0])
            nt.links.new(base, mm.inputs[6]); nt.links.new(vc2.outputs[0], mm.inputs[7])
            # occlusion from alpha, applied to albedo at half strength (as in Masonry Lit)
            ao = nt.nodes.new("ShaderNodeMapRange"); ao.inputs[3].default_value = 0.5; ao.inputs[4].default_value = 1.0
            nt.links.new(ca.outputs[1], ao.inputs[0])
            mm2 = nt.nodes.new("ShaderNodeMix"); mm2.data_type = "RGBA"; mm2.blend_type = "MULTIPLY"; mm2.inputs[0].default_value = 1
            nt.links.new(mm.outputs[2], mm2.inputs[6]); nt.links.new(ao.outputs[0], mm2.inputs[7])
            base = mm2.outputs[2]
        nt.links.new(base, bs.inputs["Base Color"])
    a = tex(name, "arm")
    if a:
        ta = nt.nodes.new("ShaderNodeTexImage"); ta.image = bpy.data.images.load(str(a), check_existing=True)
        ta.image.colorspace_settings.name = "Non-Color"
        nt.links.new(mp.outputs[0], ta.inputs[0])
        sep = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(ta.outputs[0], sep.inputs[0])
        rk = nt.nodes.new("ShaderNodeMath"); rk.operation = "MULTIPLY"; rk.inputs[1].default_value = rough_k
        nt.links.new(sep.outputs[1], rk.inputs[0]); nt.links.new(rk.outputs[0], bs.inputs["Roughness"])
        if metal > 0:
            mk = nt.nodes.new("ShaderNodeMath"); mk.operation = "MAXIMUM"; mk.inputs[1].default_value = metal * 0.0
            nt.links.new(sep.outputs[2], mk.inputs[0])
            mx = nt.nodes.new("ShaderNodeMath"); mx.operation = "MAXIMUM"; mx.inputs[1].default_value = metal * 0.6
            nt.links.new(mk.outputs[0], mx.inputs[0]); nt.links.new(mx.outputs[0], bs.inputs["Metallic"])
    n = tex(name, "nor")
    if n:
        tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = bpy.data.images.load(str(n), check_existing=True)
        tn.image.colorspace_settings.name = "Non-Color"
        nt.links.new(mp.outputs[0], tn.inputs[0])
        nm = nt.nodes.new("ShaderNodeNormalMap"); nm.uv_map = "UVMap"
        nt.links.new(tn.outputs[0], nm.inputs[1]); nt.links.new(nm.outputs[0], bs.inputs["Normal"])


def simple(m, color, rough=0.5, metal=0.0, emit=None, alpha=None):
    m.use_nodes = True
    bs = m.node_tree.nodes.get("Principled BSDF") or m.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
    bs.inputs["Base Color"].default_value = (*color, 1)
    bs.inputs["Roughness"].default_value = rough
    bs.inputs["Metallic"].default_value = metal
    if emit:
        bs.inputs["Emission Color"].default_value = (*emit, 1)
        bs.inputs["Emission Strength"].default_value = 8
    out = [n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL"]
    if out:
        m.node_tree.links.new(bs.outputs[0], out[0].inputs[0])


for m in bpy.data.materials:
    if m.name in SPEC:
        mat_setup(m, SPEC[m.name])
    elif m.name == "VH_Glass":
        simple(m, (0.02, 0.025, 0.03), 0.08, 0.0)
    elif m.name == "VH_Dark":
        simple(m, (0.02, 0.02, 0.02), 0.8)
    elif m.name == "VH_Rubber":
        simple(m, (0.03, 0.03, 0.03), 0.6)
    elif m.name == "VH_BeaconRed":
        simple(m, (0.8, 0.05, 0.03), 0.3, emit=(1, 0.05, 0.02))
    elif m.name == "VH_Banner":
        simple(m, (0.38, 0.05, 0.04), 0.9)

sc = bpy.context.scene
for c in sc.collection.children:
    c.hide_render = c.name != LODN
# ground, figure, sun, sky
bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 0, -0.001))
g = bpy.context.object
gm = bpy.data.materials.new("Ground"); simple(gm, (0.55, 0.45, 0.34), 0.95); g.data.materials.append(gm)
bpy.ops.mesh.primitive_cylinder_add(radius=0.22, depth=1.8, location=tuple(U((-3.8, 0.9 + 0.5, 1.6))))
fig = bpy.context.object
fm = bpy.data.materials.new("Figure"); simple(fm, (0.2, 0.3, 0.6), 0.6); fig.data.materials.append(fm)
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
sc.collection.objects.link(sun)
sun.data.energy = 6.0
sun.data.color = (1.0, 0.86, 0.7)
sun.data.angle = math.radians(1.2)
# afternoon sun from the north-west-ish (Unity), low: direction towards (-X south-east)
d = U((0.55, -0.45, -0.7)).normalized()
sun.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
w = sc.world or bpy.data.worlds.new("W")
sc.world = w
w.use_nodes = True
bg = w.node_tree.nodes.get("Background")
sky = w.node_tree.nodes.new("ShaderNodeTexSky")
try:
    sky.sky_type = "HOSEK_WILKIE"
except Exception:
    pass
w.node_tree.links.new(sky.outputs[0], bg.inputs[0])
bg.inputs[1].default_value = 0.35
sc.render.engine = "BLENDER_EEVEE"
sc.render.resolution_x, sc.render.resolution_y = 1600, 900
try:
    sc.eevee.use_raytracing = True
    sc.eevee.taa_render_samples = 32
    sc.eevee.use_shadows = True
except Exception:
    pass
sc.view_settings.view_transform = "AgX"

cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
sc.collection.objects.link(cam)
sc.camera = cam

ALL = {
    "front34": ((9.0, 1.7, 17.0), (-0.5, 6.5, -3.0), 55),
    "front": ((0.0, 1.7, 21.0), (0.0, 6.8, 0.0), 50),
    "portal": ((0.8, 1.65, 5.2), (0.0, 2.8, -0.5), 55),
    "pier": ((6.9, 1.6, 3.2), (4.8, 1.8, 0.2), 55),
    "upper": ((2.0, 1.7, 7.0), (0.6, 8.5, 0.0), 50),
    "east": ((14.0, 1.7, -4.0), (5.0, 5.5, -4.3), 55),
    "west": ((-15.0, 3.0, -1.0), (-5.0, 6.0, -4.3), 55),
    "rear": ((-7.0, 1.7, -19.0), (0.0, 5.5, -8.5), 55),
    "cornice": ((3.5, 1.7, 3.0), (3.0, 11.0, -0.5), 55),
    "nameplate": ((0.0, 1.7, 4.0), (0.0, 5.7, 0.0), 35),
    "roof": ((12.0, 22.0, 14.0), (0.0, 10.0, -4.0), 45),
}
for name, (pos, tgt, fov) in ALL.items():
    if VIEWS and name not in VIEWS:
        continue
    cam.location = U(pos)
    dirv = U(tgt) - U(pos)
    cam.rotation_euler = dirv.to_track_quat("-Z", "Y").to_euler()
    cam.data.sensor_fit = "VERTICAL"
    cam.data.angle_y = math.radians(fov)
    sc.render.filepath = str(OUTDIR / f"{LODN}-{name}.png")
    bpy.ops.render.render(write_still=True)
    print("rendered", name, flush=True)
