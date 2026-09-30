"""Blender 5.2, Cycles CPU only: review the EXPORTED salvage cache (FBX + PNG maps, rebuilt as URP-Lit-like materials)
on uneven desert ground next to a 1.8 m human marker.

Shots: player-view at 1 m / 4 m / 12 m in warm sun and in shade, the three rarity glows, and an 8-angle turntable.
Run: blender -b --factory-startup --python review_render.py -- <export dir> <out dir> [shots=all|quick] [samples]
"""
import bpy, sys, math, json
from pathlib import Path
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
EXP, OUT = Path(argv[0]).resolve(), Path(argv[1]).resolve()
SHOTS = argv[2] if len(argv) > 2 else "all"
SAMPLES = int(argv[3]) if len(argv) > 3 else 96
OUT.mkdir(parents=True, exist_ok=True)
ROOT = Path(__file__).resolve().parents[3]
GROUND = ROOT / "art/west_gate_20260926/polyhaven/textures/dry_ground_rocks"
SUN = float(argv[4]) if len(argv) > 4 else 6.0
SKY = float(argv[5]) if len(argv) > 5 else 0.12
EXPOSURE = float(argv[6]) if len(argv) > 6 else -0.9
RARITY = {"common": (1.5, 1.35, 1.1), "uncommon": (.45, 1.9, 1.95), "rare": (2.6, 1.45, .3)}  # SalvageCache.cs defaults

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = SAMPLES
sc.cycles.use_denoising = True; sc.cycles.denoiser = "OPENIMAGEDENOISE"
sc.cycles.max_bounces = 6; sc.render.resolution_x, sc.render.resolution_y = 1600, 900
sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Base Contrast"; sc.view_settings.exposure = EXPOSURE
sc.render.film_transparent = False

def img(path, non_color=False):
    im = bpy.data.images.load(str(path), check_existing=True)
    if non_color: im.colorspace_settings.name = "Non-Color"
    return im

# ---------- import the exported asset ----------
fbx = next(EXP.glob("*.fbx"))
bpy.ops.import_scene.fbx(filepath=str(fbx))
objs = [o for o in sc.objects if o.type == "MESH"]
maps = json.loads((EXP / "materials.json").read_text())
def build_lit(mat, spec):
    """URP Lit approximation: _BaseMap, _BumpMap, _MetallicGlossMap (R metal, A smooth), _OcclusionMap (G), _EmissionMap."""
    mat.use_nodes = True; nt = mat.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs[0], out.inputs[0])
    uv = nt.nodes.new("ShaderNodeUVMap"); uv.uv_map = "UVMap"
    def tex(name, nc):
        n = nt.nodes.new("ShaderNodeTexImage"); n.image = img(EXP / name, nc); nt.links.new(uv.outputs[0], n.inputs[0]); return n
    base = tex(spec["base"], False)
    mask = tex(spec["mask"], True)
    sep = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(mask.outputs[0], sep.inputs[0])
    ao_mix = nt.nodes.new("ShaderNodeMix"); ao_mix.data_type = "RGBA"; ao_mix.blend_type = "MULTIPLY"
    ao_mix.inputs[0].default_value = 1.0
    nt.links.new(base.outputs[0], ao_mix.inputs[6]); nt.links.new(sep.outputs[1], ao_mix.inputs[7])
    nt.links.new(ao_mix.outputs[2], bsdf.inputs["Base Color"])
    nt.links.new(sep.outputs[0], bsdf.inputs["Metallic"])
    inv = nt.nodes.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1
    nt.links.new(mask.outputs[1], inv.inputs[1]); nt.links.new(inv.outputs[0], bsdf.inputs["Roughness"])
    nrm = tex(spec["normal"], True); nm = nt.nodes.new("ShaderNodeNormalMap"); nm.uv_map = "UVMap"
    nt.links.new(nrm.outputs[0], nm.inputs[1]); nt.links.new(nm.outputs[0], bsdf.inputs["Normal"])
    if spec.get("emission"):
        em = tex(spec["emission"], False)
        mul = nt.nodes.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"; mul.inputs[0].default_value = 1
        mul.name = "RARITY"; nt.links.new(em.outputs[0], mul.inputs[6]); mul.inputs[7].default_value = (1, 1, 1, 1)
        nt.links.new(mul.outputs[2], bsdf.inputs["Emission Color"]); bsdf.inputs["Emission Strength"].default_value = 1.0
for o in objs:
    for slot in o.material_slots:
        base = slot.material.name.split(".")[0]
        if base in maps: build_lit(slot.material, maps[base])
# LOD0 only in the close shots; LOD1 shown separately
lods = {i: [o for o in objs if o.name.endswith(f"LOD{i}")] for i in range(3)}
lod0, lod1, lod2 = lods[0], lods[1], lods[2]
for o in lod1 + lod2: o.hide_render = True
def show_lod(i):
    for j, os_ in lods.items():
        for o in os_: o.hide_render = j != i
def set_rarity(name):
    c = RARITY[name]
    for m in bpy.data.materials:
        if m.use_nodes and "RARITY" in m.node_tree.nodes:
            m.node_tree.nodes["RARITY"].inputs[7].default_value = (*c, 1)
    pk = max(c); glow.data.color = (c[0] / pk, c[1] / pk, c[2] / pk)
# asset bounds
co = [o.matrix_world @ v.co for o in lod0 for v in o.data.vertices]
mn = Vector((min(c.x for c in co), min(c.y for c in co), min(c.z for c in co)))
mx = Vector((max(c.x for c in co), max(c.y for c in co), max(c.z for c in co)))
ctr = (mn + mx) / 2; print("asset bounds", tuple(round(x, 3) for x in mn), tuple(round(x, 3) for x in mx), flush=True)

# prefab point light: Unity 'Glow light' at local (0, 0.7, 0), intensity 1.2, range 3.2
glow = bpy.data.objects.new("glow", bpy.data.lights.new("glow", "POINT")); sc.collection.objects.link(glow)
glow.location = (0, 0, 0.7); glow.data.energy = 6.0; glow.data.shadow_soft_size = 0.03

# ---------- uneven ground (CC0 Poly Haven dry_ground_rocks, displaced) ----------
bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0))
g = bpy.context.object; g.name = "ground"
bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.subdivide(number_cuts=160); bpy.ops.object.mode_set(mode="OBJECT")
gm = bpy.data.materials.new("ground"); gm.use_nodes = True; nt = gm.node_tree; b = nt.nodes["Principled BSDF"]
tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (20, 20, 1)
nt.links.new(tc.outputs["UV"], mp.inputs[0])
def gtex(k, nc):
    n = nt.nodes.new("ShaderNodeTexImage"); n.image = img(GROUND / f"dry_ground_rocks_{k}_2k.jpg", nc); nt.links.new(mp.outputs[0], n.inputs[0]); return n
tint = nt.nodes.new("ShaderNodeHueSaturation"); tint.inputs["Saturation"].default_value = 1.15; tint.inputs["Value"].default_value = 1.05
nt.links.new(gtex("diff", False).outputs[0], tint.inputs["Color"]); nt.links.new(tint.outputs[0], b.inputs["Base Color"])
nt.links.new(gtex("rough", True).outputs[0], b.inputs["Roughness"])
gn = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(gtex("nor_gl", True).outputs[0], gn.inputs[1]); nt.links.new(gn.outputs[0], b.inputs["Normal"])
g.data.materials.append(gm)
# far ground so the horizon is not the 40 m plane edge
bpy.ops.mesh.primitive_plane_add(size=600, location=(0, 0, -0.03)); far = bpy.context.object; far.data.materials.append(gm)
far.data.uv_layers[0].data.foreach_set("uv", [c * 15 for c in (0, 0, 1, 0, 1, 1, 0, 1)])
tx = bpy.data.textures.new("undul", "CLOUDS"); tx.noise_scale = 0.9
d = g.modifiers.new("disp", "DISPLACE"); d.texture = tx; d.strength = 0.07; d.mid_level = 0.5
# keep the ground under the cache near z=0 but uneven around it (the cache sinks ~1.5 cm by design)

# ---------- human scale marker, 1.8 m ----------
mk = bpy.data.materials.new("marker"); mk.use_nodes = True
mk.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.32, 0.34, 0.37, 1)
mk.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.55
def part(kind, loc, scale, rot=(0, 0, 0)):
    if kind == "cyl": bpy.ops.mesh.primitive_cylinder_add(vertices=24, location=loc, rotation=rot)
    else: bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, location=loc, rotation=rot)
    o = bpy.context.object; o.scale = scale; o.data.materials.append(mk); bpy.ops.object.shade_smooth(); return o
HX, HY = -0.95, 0.75
_before = set(sc.objects)
for sx in (-1, 1):
    part("cyl", (HX + sx * .1, HY, .43), (.07, .07, .43))          # legs 0-0.86
    part("cyl", (HX + sx * .25, HY, 1.2), (.045, .045, .3))        # arms
part("sph", (HX, HY, 1.12), (.2, .13, .34))                         # torso 0.78-1.46
part("sph", (HX, HY, 1.52), (.14, .12, .1))                         # shoulders/neck
part("sph", (HX, HY, 1.685), (.095, .105, .115))                    # head, top at 1.80 m
marker = [o for o in sc.objects if o not in _before]
# 1 m ruler with 10 cm bands beside the cache
for i in range(10):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-0.45, -0.30, 0.05 + i * .1)); r = bpy.context.object
    r.scale = (.02, .02, .1); m = bpy.data.materials.new(f"band{i}"); m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (.8, .8, .8, 1) if i % 2 else (.05, .05, .05, 1)
    r.data.materials.append(m)
ruler = [o for o in sc.objects if o.name.startswith("Cube")]

# ---------- sun / sky ----------
world = bpy.data.worlds.new("sky"); sc.world = world; world.use_nodes = True
wn = world.node_tree; bg = wn.nodes["Background"]
sky = wn.nodes.new("ShaderNodeTexSky")
try:
    sky.sky_type = "MULTIPLE_SCATTERING"
except Exception:
    pass
try:
    sky.sun_disc = False  # the sun lamp below is the only direct sun, so the shade occluder works
except Exception:
    pass
sky.sun_elevation = math.radians(38); sky.sun_rotation = math.radians(215); sky.air_density = 1.2; sky.aerosol_density = 2.0
wn.links.new(sky.outputs[0], bg.inputs[0]); bg.inputs[1].default_value = SKY
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sc.collection.objects.link(sun)
sun.data.energy = SUN; sun.data.color = (1.0, 0.9, 0.78); sun.data.angle = math.radians(1.0)
sun.rotation_euler = (math.radians(52), 0, math.radians(-50))  # elevation 38 deg, from camera-left of the default views
# shade caster: a wall slab out of shot, visible to shadows only
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 3)); wall = bpy.context.object
wall.scale = (3.5, 3.5, .1); wall.visible_camera = False; wall.visible_glossy = False; wall.hide_render = True

cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.sensor_width = 36
def shoot(name, dist, height, yaw_deg, lens=40, target=None, res=(1600, 900)):
    t = target or Vector((ctr.x, ctr.y, ctr.z * 0.8))
    a = math.radians(yaw_deg)
    cam.location = (t.x + dist * math.sin(a), t.y - dist * math.cos(a), height)
    cam.rotation_euler = (t - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = lens; sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.filepath = str(OUT / f"{name}.png"); bpy.ops.render.render(write_still=True); print("shot", name, flush=True)

def light(mode):
    shade = mode == "shade"
    wall.hide_render = not shade
    # occluder between the sun and the cache (sun elevation 38 deg, azimuth -50 deg), 3.5 m square at 2.6 m height
    wall.location = (-2.55, -2.14, 2.6) if shade else (0, 0, 30)

set_rarity("uncommon")
shots = []
if SHOTS == "light":
    light("sun"); sc.render.resolution_percentage = 50; shoot("light_sun", 1.0, 1.05, 25, lens=35); light("shade"); shoot("light_shade", 1.0, 1.05, 25, lens=35)
if SHOTS in ("all", "quick", "dist"):
    for mode in ("sun", "shade"):
        light(mode)
        shoot(f"{mode}_01m", 1.0, 1.05, 25, lens=35)
        shoot(f"{mode}_04m", 4.0, 1.7, 25, lens=40)
        if SHOTS != "quick": shoot(f"{mode}_12m", 12.0, 1.9, 25, lens=40)
if SHOTS in ("all", "rarity"):
    light("sun")
    for r in RARITY:
        set_rarity(r); shoot(f"rarity_{r}_sun_03m", 2.6, 1.6, 40, lens=40, res=(1200, 900))
    light("shade")
    for r in RARITY:
        set_rarity(r); shoot(f"rarity_{r}_shade_03m", 2.6, 1.6, 40, lens=40, res=(1200, 900))
    set_rarity("uncommon")
if SHOTS in ("all", "turntable"):
    light("sun")
    for o in ruler + marker: o.hide_render = True
    for i in range(8):
        shoot(f"tt_{i}", 1.35, 0.95, i * 45, lens=40, res=(800, 600))
    for o in ruler + marker: o.hide_render = False
if SHOTS in ("all", "lod"):
    light("sun")
    for i in (0, 1, 2):
        show_lod(i)
        shoot(f"lod{i}_02m", 1.8, 1.25, 25, lens=40, res=(1200, 900))
        shoot(f"lod{i}_08m", 8.0, 1.8, 25, lens=40, res=(1200, 900))
    show_lod(0)
if SHOTS in ("all", "clay"):
    light("sun")
    clay = bpy.data.materials.new("clay"); clay.use_nodes = True
    clay.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.5, 0.5, 0.5, 1)
    saved = {o: [s.material for s in o.material_slots] for o in lod0}
    for o in lod0:
        for s_ in o.material_slots: s_.material = clay
    tgt = Vector((0.148, 0.132, 0.26))
    for i, yaw in enumerate((200, 250, 160, 110)):
        shoot(f"clay_canister_{i}", 0.95, 0.75, yaw, lens=45, target=tgt, res=(1000, 800))
    shoot("clay_whole", 1.4, 1.1, 25, lens=40, res=(1200, 900))
    for o, mats in saved.items():
        for s_, m in zip(o.material_slots, mats): s_.material = m
print("review done", OUT)
