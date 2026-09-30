"""Salvage cache v1 build (Blender 5.2.1, Cycles on CPU only). Run from the asset folder:
  systemd-run --user --scope -p MemoryMax=10G -p MemoryHigh=8G \
    blender -b --factory-startup --python scripts/build_cache.py -- meshy/run_a

1. Import the Meshy body (never modified on disk), weld glTF seam splits (keeping hard edges), drop floaters,
   fill small holes, normalise: bottom-centre pivot, uniform scale to 0.50 m longest side, sunk 12 mm.
2. Cut Meshy's fused canister out and insert the authored canister (vial.py): hardware + separate glow core.
3. Bake the canister's procedural materials to a 2048 atlas (base, normal, metal/AO/smooth, emission mask) and a
   2048 AO for the body (canister + ground as occluders). Body maps: Meshy 4k -> 2k (linear-light box filter,
   renormalised normals), metallic cleaned (paint/cloth/rubber are not metal).
4. LOD1 (~35 %) and LOD2 (~10 %) by collapse decimation; FBX export with Blender's own exporter.
"""
import bpy, bmesh, sys, json, math, time
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "scripts"))
import vial

argv = sys.argv[sys.argv.index("--") + 1:]
RUN = (HERE / argv[0]).resolve()
TARGET_LONGEST, SINK = 0.50, 0.012
TEX = 2048
EXP = HERE / "export"; SRC = HERE / "source"; EXP.mkdir(exist_ok=True); SRC.mkdir(exist_ok=True)
REPORT = {"built": time.strftime("%Y-%m-%dT%H:%M:%S"), "meshy_run": str(RUN.relative_to(HERE))}
T0 = time.time()
def log(*a): print(f"[{time.time() - T0:6.1f}s]", *a, flush=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.unit_settings.system = "METRIC"; sc.unit_settings.scale_length = 1.0
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"
vl = bpy.context.view_layer

def activate(objs, active=None):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs: o.select_set(True)
    vl.objects.active = active or objs[0]

def tris(o): return sum(len(p.vertices) - 2 for p in o.data.polygons)

# ------------------------------------------------------------------ 1. body import + cleanup
bpy.ops.import_scene.gltf(filepath=str(RUN / "model.glb"))
meshes = [o for o in sc.objects if o.type == "MESH"]
activate(meshes)
bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
if len(meshes) > 1: bpy.ops.object.join()
body = vl.objects.active
for o in list(sc.objects):
    if o != body: bpy.data.objects.remove(o, do_unlink=True)
body.name = "Body"
REPORT["meshy_tris"] = tris(body)
bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.remove_doubles(threshold=1e-5, use_sharp_edge_from_normals=True)
bpy.ops.object.mode_set(mode="OBJECT")
bpy.ops.mesh.customdata_custom_splitnormals_clear()
bpy.ops.object.shade_smooth(keep_sharp_edges=True)
REPORT["sharp_edges_from_meshy_normals"] = sum(1 for e in body.data.edges if e.use_edge_sharp)

bm = bmesh.new(); bm.from_mesh(body.data)
def components(bm):
    bm.faces.ensure_lookup_table(); seen = set(); out = []
    for f in bm.faces:
        if f.index in seen: continue
        st = [f]; comp = []; seen.add(f.index)
        while st:
            x = st.pop(); comp.append(x)
            for e in x.edges:
                for g in e.link_faces:
                    if g.index not in seen: seen.add(g.index); st.append(g)
        out.append(comp)
    return out
comps = components(bm)
floaters = [c for c in comps if len(c) < 30]
bmesh.ops.delete(bm, geom=[f for c in floaters for f in c], context="FACES")
REPORT["floaters_removed"] = [len(c) for c in floaters]
# boundary loops: fill only small ones (large openings are deliberate: e.g. sensor socket)
bnd = [e for e in bm.edges if e.is_boundary]
loops, used = [], set()
for e in bnd:
    if e in used: continue
    loop = [e]; used.add(e); v = e.verts[1]
    while True:
        nxt = [x for x in v.link_edges if x.is_boundary and x not in used]
        if not nxt: break
        loop.append(nxt[0]); used.add(nxt[0]); v = nxt[0].other_vert(v)
    loops.append(loop)
small = [l for l in loops if len(l) <= 24]
filled = bmesh.ops.holes_fill(bm, edges=[e for l in small for e in l], sides=24)
bmesh.ops.triangulate(bm, faces=filled["faces"])
REPORT["boundary_loops"] = sorted(len(l) for l in loops); REPORT["holes_filled"] = len(filled["faces"])
bm.to_mesh(body.data); bm.free()
log("cleanup", REPORT["floaters_removed"], "loops", len(loops), "filled faces", REPORT["holes_filled"])

# normalise: bottom-centre pivot, uniform scale, sink
co = np.empty(len(body.data.vertices) * 3); body.data.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
mn, mx = co.min(0), co.max(0)
k = TARGET_LONGEST / max(mx[0] - mn[0], mx[1] - mn[1])
body.data.transform(Matrix.Translation((-(mn[0] + mx[0]) / 2, -(mn[1] + mx[1]) / 2, -mn[2])))
body.data.transform(Matrix.Scale(k, 4))
body.data.transform(Matrix.Translation((0, 0, -SINK)))
REPORT["meshy_units_bounds"] = [mn.round(4).tolist(), mx.round(4).tolist()]; REPORT["uniform_scale"] = round(k, 5)
def m2f(p):  # Meshy units -> final metres
    return Vector(((p[0] - (mn[0] + mx[0]) / 2) * k, (p[1] - (mn[1] + mx[1]) / 2) * k, (p[2] - mn[2]) * k - SINK))
AX = m2f((0.5625, 0.4996, 0)); AX.z = 0
log("scale", k, "canister axis", tuple(round(x, 4) for x in AX))

# ------------------------------------------------------------------ 2. cut Meshy canister
def in_cut(p):
    r = math.hypot(p.x - AX.x, p.y - AX.y); z = p.z
    if z > 0.2915: return r < 0.0650
    if z > 0.2336: return r < 0.0566
    if z > 0.1100: return r < 0.0535
    return False
bm = bmesh.new(); bm.from_mesh(body.data)
cut = [f for f in bm.faces if in_cut(f.calc_center_median())]
bmesh.ops.delete(bm, geom=cut, context="FACES")
# fragments of the old canister left outside the cut volume
comps = components(bm)
frag = [c for c in comps if len(c) < 400]
bmesh.ops.delete(bm, geom=[f for c in frag for f in c], context="FACES")
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
REPORT["canister_faces_cut"] = len(cut); REPORT["canister_fragments_removed"] = [len(c) for c in frag]
bm.to_mesh(body.data); bm.free()
log("cut", len(cut), "fragments", [len(c) for c in frag], "body tris", tris(body))

# ------------------------------------------------------------------ 3. authored canister
def new_obj(name, bmh):
    me = bpy.data.meshes.new(name); bmh.to_mesh(me); bmh.free()
    o = bpy.data.objects.new(name, me); sc.collection.objects.link(o); o.location = AX; return o
bh, bc = bmesh.new(), bmesh.new(); vial.build(bh, bc, segs=48, bar_segs=10)
hw, core = new_obj("VialHardware", bh), new_obj("VialCore", bc)
for o in (hw, core):
    activate([o]); bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))
REPORT["vial_tris"] = {"hardware": tris(hw), "core": tris(core)}
# UVs: one shared 2048 atlas for hardware + core
for o in (hw, core): o.data.uv_layers.new(name="UVMap")
activate([hw, core]); bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.smart_project(angle_limit=math.radians(50), island_margin=0.004, area_weight=0.0, scale_to_bounds=False)
bpy.ops.uv.pack_islands(rotate=True, margin=0.006)
bpy.ops.object.mode_set(mode="OBJECT")

# ---- procedural materials (object space == final metres around the canister axis)
def mk_img(name, alpha=False, noncolor=False):
    im = bpy.data.images.new(name, TEX, TEX, alpha=alpha)
    if noncolor: im.colorspace_settings.name = "Non-Color"
    return im
class G:
    def __init__(self, mat):
        mat.use_nodes = True; self.nt = mat.node_tree; self.nt.nodes.clear()
        self.out = self.n("ShaderNodeOutputMaterial")
    def n(self, t, **kw):
        x = self.nt.nodes.new(t)
        for a, b in kw.items(): setattr(x, a, b)
        return x
    def ln(self, a, b): self.nt.links.new(a, b)
    def v(self, x, sock):
        if isinstance(x, (int, float)):
            sock.default_value = (x, x, x, 1) if sock.type == "RGBA" else x
        elif isinstance(x, tuple): sock.default_value = x if len(x) == 4 else (*x, 1)
        else: self.ln(x, sock)
    def m(self, op, a, b=0.0, clamp=False):
        x = self.n("ShaderNodeMath", operation=op, use_clamp=clamp); self.v(a, x.inputs[0]); self.v(b, x.inputs[1]); return x.outputs[0]
    def mr(self, val, a, b, c=0.0, d=1.0, smooth=True):
        x = self.n("ShaderNodeMapRange", clamp=True, interpolation_type="SMOOTHSTEP" if smooth else "LINEAR")
        self.v(val, x.inputs["Value"]); x.inputs["From Min"].default_value = a; x.inputs["From Max"].default_value = b
        x.inputs["To Min"].default_value = c; x.inputs["To Max"].default_value = d; return x.outputs[0]
    def mix(self, t, a, b, color=False):
        x = self.n("ShaderNodeMix", data_type="RGBA" if color else "FLOAT")
        ins = {s.identifier: s for s in x.inputs}; outs = {s.identifier: s for s in x.outputs}
        self.v(t, ins["Factor_Float"]); sfx = "Color" if color else "Float"
        self.v(a, ins["A_" + sfx]); self.v(b, ins["B_" + sfx]); return outs["Result_" + sfx]
    def noise(self, vec, scale, detail=4.0, rough=0.55, dist=0.0):
        x = self.n("ShaderNodeTexNoise"); self.ln(vec, x.inputs["Vector"]); x.inputs["Scale"].default_value = scale
        x.inputs["Detail"].default_value = detail; x.inputs["Roughness"].default_value = rough; x.inputs["Distortion"].default_value = dist
        return x.outputs["Fac"]
    def emit(self, val):
        e = self.n("ShaderNodeEmission"); self.v(val, e.inputs["Color"]); e.inputs["Strength"].default_value = 1.0; return e.outputs[0]
def band(g, z, z0, z1, soft=0.0004):
    return g.m("MULTIPLY", g.mr(z, z0 - soft, z0 + soft), g.mr(z, z1 + soft, z1 - soft))

CH = {}  # material -> {channel: shader socket}
def hardware_material():
    mat = bpy.data.materials.new("MI_SalvageCache_Vial"); g = G(mat)
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]
    sep = g.n("ShaderNodeSeparateXYZ"); g.ln(obj, sep.inputs[0]); x, y, z = sep.outputs
    cxy = g.n("ShaderNodeCombineXYZ"); g.ln(x, cxy.inputs[0]); g.ln(y, cxy.inputs[1])
    rl = g.n("ShaderNodeVectorMath", operation="LENGTH"); g.ln(cxy.outputs[0], rl.inputs[0]); r = rl.outputs["Value"]
    n_fine = g.noise(obj, 260, 8, 0.6); n_mid = g.noise(obj, 70, 5, 0.6); n_big = g.noise(obj, 22, 3, 0.5)
    bev = g.n("ShaderNodeBevel", samples=8); bev.inputs["Radius"].default_value = 0.0011
    geo = g.n("ShaderNodeNewGeometry")
    dot = g.n("ShaderNodeVectorMath", operation="DOT_PRODUCT"); g.ln(bev.outputs[0], dot.inputs[0]); g.ln(geo.outputs["Normal"], dot.inputs[1])
    edge = g.mr(g.m("SUBTRACT", 1.0, dot.outputs["Value"]), 0.006, 0.045)
    edge = g.m("MULTIPLY", edge, g.mr(n_mid, 0.48, 0.66), clamp=True)
    ao = g.n("ShaderNodeAmbientOcclusion", only_local=True, samples=16); ao.inputs["Distance"].default_value = 0.008
    cav = g.mr(g.m("SUBTRACT", 1.0, ao.outputs["AO"]), 0.08, 0.5)
    dust = g.m("MULTIPLY", cav, g.mr(n_big, 0.3, 0.6, 0.5, 1.0), clamp=True)
    # dust also settles on up-facing ledges
    gsep = g.n("ShaderNodeSeparateXYZ"); g.ln(geo.outputs["Normal"], gsep.inputs[0])
    dust = g.m("MAXIMUM", dust, g.m("MULTIPLY", g.mr(gsep.outputs[2], 0.6, 0.95), g.mr(n_mid, 0.35, 0.65, 0.1, 0.8)))
    rust = g.m("MULTIPLY", g.mr(g.noise(obj, 30, 8, 0.7), 0.54, 0.66), g.m("ADD", 0.45, cav), clamp=True)
    smp = g.n("ShaderNodeMapping"); g.ln(obj, smp.inputs[0]); smp.inputs["Scale"].default_value = (1.0, 1.0, 0.12)
    streak = g.mr(g.noise(smp.outputs[0], 90, 4, 0.5), 0.45, 0.7)
    paint = g.m("MULTIPLY", band(g, z, vial.BAND_Z0, vial.BAND_Z1), g.mr(r, 0.0562, 0.0568))
    chip = g.m("MAXIMUM", g.m("MULTIPLY", edge, 1.6), g.mr(n_fine, 0.62, 0.66))
    paint = g.m("MULTIPLY", paint, g.m("SUBTRACT", 1.0, chip), clamp=True)
    knurl_m = g.m("MULTIPLY", band(g, z, vial.KNURL_Z0 + 0.0008, vial.KNURL_Z1 - 0.0008), g.mr(r, 0.0512, 0.0516))
    steel = g.mix(n_fine, (0.075, 0.074, 0.076), (0.13, 0.125, 0.12), True)
    steel = g.mix(g.mr(n_big, 0.3, 0.7), steel, (0.16, 0.14, 0.115), True)  # heat/age tint
    steel = g.mix(g.m("MULTIPLY", streak, 0.55), steel, (0.055, 0.048, 0.042), True)  # grime streaks
    col = g.mix(paint, steel, (0.36, 0.10, 0.03), True)
    col = g.mix(edge, col, (0.40, 0.39, 0.37), True)
    col = g.mix(rust, col, (0.19, 0.085, 0.035), True)
    col = g.mix(dust, col, (0.40, 0.30, 0.19), True)
    metal = g.mix(paint, 1.0, 0.0); metal = g.mix(edge, metal, 1.0); metal = g.mix(rust, metal, 0.25); metal = g.mix(dust, metal, 0.0)
    rough = g.m("ADD", 0.44, g.m("MULTIPLY", n_fine, 0.2)); rough = g.mix(streak, rough, 0.66); rough = g.mix(knurl_m, rough, 0.5)
    rough = g.mix(paint, rough, 0.58); rough = g.mix(edge, rough, 0.3); rough = g.mix(rust, rough, 0.82); rough = g.mix(dust, rough, 0.93)
    # height: diamond knurl on the cap band + paint thickness + fine pitting
    ang = g.m("ARCTAN2", y, x); arc = g.m("MULTIPLY", ang, 0.0518)
    kk = 2 * math.pi / (2 * math.pi * 0.0518 / 200)
    s1 = g.m("ABSOLUTE", g.m("SINE", g.m("MULTIPLY", g.m("ADD", arc, z), kk)))
    s2 = g.m("ABSOLUTE", g.m("SINE", g.m("MULTIPLY", g.m("SUBTRACT", arc, z), kk)))
    kn = g.m("MULTIPLY", g.m("MULTIPLY", s1, s2), knurl_m)
    h = g.m("ADD", g.m("MULTIPLY", kn, 0.0006), g.m("MULTIPLY", paint, 0.00009))
    h = g.m("ADD", h, g.m("MULTIPLY", g.m("MULTIPLY", g.mr(n_fine, 0.55, 0.8), rust), -0.00012))
    h = g.m("ADD", h, g.m("MULTIPLY", n_fine, 0.00002))
    bump = g.n("ShaderNodeBump"); bump.inputs["Strength"].default_value = 1.0; bump.inputs["Distance"].default_value = 1.0
    g.ln(h, bump.inputs["Height"]); g.ln(bev.outputs[0], bump.inputs["Normal"])
    bsdf = g.n("ShaderNodeBsdfPrincipled"); g.ln(col, bsdf.inputs["Base Color"]); g.ln(metal, bsdf.inputs["Metallic"])
    g.ln(rough, bsdf.inputs["Roughness"]); g.ln(bump.outputs[0], bsdf.inputs["Normal"])
    CH[mat.name] = {"base": g.emit(col), "metal": g.emit(metal), "rough": g.emit(rough), "emission": g.emit(0.0),
                    "bsdf": bsdf.outputs[0]}
    g.ln(bsdf.outputs[0], g.out.inputs[0]); return mat, g

def core_material():
    mat = bpy.data.materials.new("MI_SalvageCache_Core"); g = G(mat)
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]
    sep = g.n("ShaderNodeSeparateXYZ"); g.ln(obj, sep.inputs[0]); x, y, z = sep.outputs
    ang = g.m("ARCTAN2", y, x)
    fluid = g.mr(z, vial.FILL_Z + 0.0007, vial.FILL_Z - 0.0007)
    menis = g.m("EXPONENT", g.m("MULTIPLY", g.m("POWER", g.m("DIVIDE", g.m("SUBTRACT", z, vial.FILL_Z + 0.0009), 0.0011), 2.0), -1.0))
    mp = g.n("ShaderNodeMapping"); g.ln(obj, mp.inputs[0]); mp.inputs["Scale"].default_value = (1.0, 1.0, 0.33)
    swirl = g.noise(mp.outputs[0], 55, 6, 0.6, 1.6)
    vor = g.n("ShaderNodeTexVoronoi"); g.ln(obj, vor.inputs["Vector"]); vor.inputs["Scale"].default_value = 520
    specks = g.mr(vor.outputs["Distance"], 0.16, 0.05)
    specks = g.m("MULTIPLY", specks, g.mr(g.noise(obj, 90, 2), 0.45, 0.6))
    low = g.mr(z, vial.GLASS_Z0 + 0.004, vial.GLASS_Z0 + 0.022, 0.55, 1.0)
    e = g.m("ADD", 0.30, g.m("MULTIPLY", g.mr(swirl, 0.28, 0.72), 0.62))  # nanite suspension: visible flow, not a flat tube
    e = g.m("ADD", e, g.m("MULTIPLY", specks, 0.6))
    e = g.m("MULTIPLY", e, low)
    e = g.m("ADD", g.m("MULTIPLY", e, fluid), g.m("MULTIPLY", g.m("SUBTRACT", 1.0, fluid), 0.09))
    e = g.m("ADD", e, g.m("MULTIPLY", menis, 0.35), clamp=True)
    # printed graduation scale on the outward (+X+Y) face: ticks every 12 mm, long tick every third
    side = g.m("ABSOLUTE", g.m("SUBTRACT", ang, math.radians(45)))
    zz = g.m("SUBTRACT", z, 0.2255)
    frac = g.m("FRACT", g.m("DIVIDE", zz, 0.012))
    tick_line = g.mr(g.m("ABSOLUTE", g.m("SUBTRACT", frac, 0.5)), 0.47, 0.44)
    idx = g.m("FLOOR", g.m("DIVIDE", g.m("ADD", zz, 0.006), 0.012))
    major = g.m("LESS_THAN", g.m("ABSOLUTE", g.m("SUBTRACT", g.m("FRACT", g.m("DIVIDE", idx, 3.0)), 0.0)), 0.01)
    width = g.m("ADD", 0.13, g.m("MULTIPLY", major, 0.12))
    tick = g.m("MULTIPLY", tick_line, g.m("LESS_THAN", side, width))
    tick = g.m("MULTIPLY", tick, band(g, z, 0.2225, 0.3175, 0.0002))
    spine = g.m("MULTIPLY", g.mr(g.m("ABSOLUTE", g.m("SUBTRACT", side, 0.02)), 0.0065, 0.004), band(g, z, 0.2225, 0.3175, 0.0002))
    tick = g.m("MAXIMUM", tick, spine)
    e = g.mix(tick, e, 0.04)
    col = g.mix(fluid, (0.018, 0.02, 0.023), (0.05, 0.06, 0.062), True)
    col = g.mix(tick, col, (0.60, 0.58, 0.53), True)
    rough = g.mix(tick, 0.07, 0.42)
    bsdf = g.n("ShaderNodeBsdfPrincipled"); g.ln(col, bsdf.inputs["Base Color"]); g.ln(rough, bsdf.inputs["Roughness"])
    bsdf.inputs["Metallic"].default_value = 0.0
    CH[mat.name] = {"base": g.emit(col), "metal": g.emit(0.0), "rough": g.emit(rough), "emission": g.emit(e),
                    "bsdf": bsdf.outputs[0]}
    g.ln(bsdf.outputs[0], g.out.inputs[0]); return mat, g

hw_mat, hw_g = hardware_material(); core_mat, core_g = core_material()
hw.data.materials.append(hw_mat); core.data.materials.append(core_mat)

# ------------------------------------------------------------------ 4. bakes
# ground occluder for AO
bpy.ops.mesh.primitive_plane_add(size=4, location=(0, 0, 0)); ground = vl.objects.active; ground.name = "AO_ground"
world = bpy.data.worlds.new("bake"); sc.world = world
sc.render.bake.margin = 16; sc.render.bake.margin_type = "EXTEND"; sc.render.bake.use_clear = True
sc.cycles.samples = 64; sc.cycles.use_denoising = False
imgs = {c: mk_img(f"SalvageCacheVial_{c}", noncolor=c not in ("base", "emission")) for c in ("base", "metal", "rough", "emission", "normal", "ao")}
def set_target(g, im):
    t = g.nt.nodes.get("BAKE_TARGET") or g.n("ShaderNodeTexImage", name="BAKE_TARGET")
    t.image = im; g.nt.nodes.active = t
def bake_vial(ch, btype):
    for mat, g in ((hw_mat, hw_g), (core_mat, core_g)):
        set_target(g, imgs[ch])
        g.ln(CH[mat.name]["bsdf"] if btype in ("NORMAL", "AO") else CH[mat.name][ch], g.out.inputs[0])
    activate([hw, core])
    kw = dict(type=btype, use_clear=True, margin=16)
    if btype == "NORMAL": kw.update(normal_space="TANGENT")
    bpy.ops.object.bake(**kw); log("baked vial", ch)
for ch in ("base", "metal", "rough", "emission"): bake_vial(ch, "EMIT")
bake_vial("normal", "NORMAL")
world.light_settings.distance = 0.035; sc.cycles.samples = 128
bake_vial("ao", "AO")
for mat, g in ((hw_mat, hw_g), (core_mat, core_g)): g.ln(CH[mat.name]["bsdf"], g.out.inputs[0])

# body AO on Meshy UVs (canister + ground occlude)
bmat = body.data.materials[0]; bmat.name = "MI_SalvageCache_Body"
body_ao = mk_img("SalvageCache_Body_ao", noncolor=True)
bt = bmat.node_tree.nodes.new("ShaderNodeTexImage"); bt.image = body_ao; bmat.node_tree.nodes.active = bt
world.light_settings.distance = 0.06
activate([body]); bpy.ops.object.bake(type="AO", use_clear=True, margin=16); log("baked body AO")
bmat.node_tree.nodes.remove(bt)

# ------------------------------------------------------------------ 5. texture composition (numpy)
def px(im):
    a = np.empty(im.size[0] * im.size[1] * 4, np.float32); im.pixels.foreach_get(a)
    return a.reshape(im.size[1], im.size[0], 4)
def save(arr, name, noncolor):
    h, w = arr.shape[:2]; im = bpy.data.images.new(name, w, h, alpha=True)
    if noncolor: im.colorspace_settings.name = "Non-Color"
    im.pixels.foreach_set(np.ascontiguousarray(arr, np.float32).ravel())
    im.filepath_raw = str(EXP / f"{name}.png"); im.file_format = "PNG"; im.save(); return im
def s2l(c): return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
def l2s(c): return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(np.maximum(c, 0), 1 / 2.4) - 0.055)
def half(a): return a.reshape(a.shape[0] // 2, 2, a.shape[1] // 2, 2, a.shape[2]).mean((1, 3))

# vial atlas
vb, vm, vr, ve, vn, vao = (px(imgs[c]) for c in ("base", "metal", "rough", "emission", "normal", "ao"))
vb[..., 3] = 1; save(vb, "SalvageCacheVial_BaseColor", False)
vn[..., 3] = 1; save(vn, "SalvageCacheVial_Normal", True)
mask = np.dstack([vm[..., 0], vao[..., 0], np.zeros_like(vm[..., 0]), 1 - vr[..., 0]]); save(mask, "SalvageCacheVial_MaskMap", True)
ve[..., 3] = 1; save(ve, "SalvageCacheVial_Emission", False)

# body: Meshy 4k -> 2k
def load(fn, nc=True):
    im = bpy.data.images.load(str(RUN / fn)); im.colorspace_settings.name = "Non-Color" if nc else "sRGB"; return im
base = px(load("texture_base_color.png"))
while base.shape[0] > TEX: base = np.dstack([l2s(half(s2l(base[..., :3]))), np.ones(tuple(s // 2 for s in base.shape[:2]) + (1,), np.float32)])
save(base, "SalvageCache_Body_BaseColor", False)
nrm = px(load("texture_normal.png"))[..., :3] * 2 - 1
while nrm.shape[0] > TEX: nrm = half(nrm)
nrm /= np.maximum(np.linalg.norm(nrm, axis=2, keepdims=True), 1e-6)
save(np.dstack([nrm * .5 + .5, np.ones(nrm.shape[:2] + (1,), np.float32)]), "SalvageCache_Body_Normal", True)
met = px(load("texture_metallic.png"))[..., 0]; rgh = px(load("texture_roughness.png"))[..., 0]
while met.shape[0] > TEX: met = half(met[..., None])[..., 0]
while rgh.shape[0] > TEX: rgh = half(rgh[..., None])[..., 0]
# metallic cleanup: push grey values to metal/non-metal; painted cream/orange, canvas and dark rubber are dielectric
b = base[..., :3]; mxc, mnc = b.max(2), b.min(2); sat = (mxc - mnc) / np.maximum(mxc, 1e-4)
warm = b[..., 0] - b[..., 2]
paint = np.clip((sat - 0.30) / 0.15, 0, 1) * np.clip((mxc - 0.30) / 0.1, 0, 1) * (b[..., 0] > b[..., 1])  # orange paint
cream = np.clip((mxc - 0.50) / 0.1, 0, 1) * np.clip((warm - 0.035) / 0.03, 0, 1)
copper = np.clip((sat - 0.45) / 0.1, 0, 1) * np.clip((b[..., 0] - 0.35) / 0.1, 0, 1) * (met > 0.8)
m2 = np.clip((met - 0.30) / 0.45, 0, 1); m2 = m2 * m2 * (3 - 2 * m2)
m2 = m2 * (1 - 0.9 * np.clip(paint + cream, 0, 1)); m2 = np.maximum(m2, copper)
REPORT["body_metallic_mean"] = {"meshy": round(float(met.mean()), 3), "cleaned": round(float(m2.mean()), 3)}
bao = px(body_ao)[..., 0]
bao = 0.25 + 0.75 * bao  # keep AO as contact shading, not black
save(np.dstack([m2, bao, np.zeros_like(m2), 1 - rgh]), "SalvageCache_Body_MaskMap", True)
log("textures written")

# ------------------------------------------------------------------ 6. final materials (URP Lit layout), join, LODs
def lit(mat, prefix, emission=False):
    mat.use_nodes = True; nt = mat.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled"); nt.links.new(bsdf.outputs[0], out.inputs[0])
    def t(fn, nc):
        n = nt.nodes.new("ShaderNodeTexImage"); n.image = bpy.data.images.load(str(EXP / fn), check_existing=True)
        n.image.colorspace_settings.name = "Non-Color" if nc else "sRGB"; return n
    bc = t(f"{prefix}_BaseColor.png", False); mk = t(f"{prefix}_MaskMap.png", True); nm = t(f"{prefix}_Normal.png", True)
    sp = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(mk.outputs[0], sp.inputs[0])
    mul = nt.nodes.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"
    ins = {s.identifier: s for s in mul.inputs}; ins["Factor_Float"].default_value = 1
    nt.links.new(bc.outputs[0], ins["A_Color"]); nt.links.new(sp.outputs[1], ins["B_Color"])
    nt.links.new({s.identifier: s for s in mul.outputs}["Result_Color"], bsdf.inputs["Base Color"])
    nt.links.new(sp.outputs[0], bsdf.inputs["Metallic"])
    inv = nt.nodes.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1
    nt.links.new(mk.outputs[1], inv.inputs[1]); nt.links.new(inv.outputs[0], bsdf.inputs["Roughness"])
    nmap = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(nm.outputs[0], nmap.inputs["Color"]); nt.links.new(nmap.outputs[0], bsdf.inputs["Normal"])
    if emission:
        em = t(f"{prefix}_Emission.png", False); nt.links.new(em.outputs[0], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = 1.5
# keep the procedural canister materials in the .blend as authoring sources
hw_mat.name = "SRC_SalvageCache_Vial_procedural"; core_mat.name = "SRC_SalvageCache_Core_procedural"
src_hw, src_core = hw_mat, core_mat
hw_mat = bpy.data.materials.new("MI_SalvageCache_Vial"); lit(hw_mat, "SalvageCacheVial")
core_mat = bpy.data.materials.new("MI_SalvageCache_Core"); lit(core_mat, "SalvageCacheVial", emission=True)
lit(bmat, "SalvageCache_Body")
hw.data.materials[0] = hw_mat; core.data.materials[0] = core_mat
bpy.data.objects.remove(ground, do_unlink=True)

# keep an unjoined authoring copy of the canister (procedural materials) in a hidden collection
srcc = bpy.data.collections.new("authoring_sources"); sc.collection.children.link(srcc)
for o, m in ((hw, src_hw), (core, src_core)):
    c = o.copy(); c.data = o.data.copy(); c.data.materials[0] = m; c.name = "SRC_" + o.name; srcc.objects.link(c)
srcc.hide_render = True; vl.layer_collection.children[srcc.name].exclude = True

body.data.uv_layers[0].name = "UVMap"
# apply canister placement, join hardware into the body (slot 0 body, slot 1 vial)
for o in (hw, core):
    activate([o]); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
activate([body, hw], body); bpy.ops.object.join()
body.name = body.data.name = "SalvageCache_Body_LOD0"; core.name = core.data.name = "SalvageCache_Core_LOD0"
assert [m.name for m in body.data.materials] == ["MI_SalvageCache_Body", "MI_SalvageCache_Vial"], [m.name for m in body.data.materials]

def lod(src, ratio, name):
    c = src.copy(); c.data = src.data.copy(); sc.collection.objects.link(c); c.name = c.data.name = name
    d = c.modifiers.new("dec", "DECIMATE"); d.decimate_type = "COLLAPSE"; d.ratio = ratio; d.use_collapse_triangulate = True
    activate([c]); bpy.ops.object.modifier_apply(modifier="dec"); return c
b1 = lod(body, 0.35, "SalvageCache_Body_LOD1"); c1 = lod(core, 0.5, "SalvageCache_Core_LOD1")
b2 = lod(body, 0.10, "SalvageCache_Body_LOD2"); c2 = lod(core, 0.25, "SalvageCache_Core_LOD2")
objs = [body, core, b1, c1, b2, c2]
for o in objs:
    o.data.uv_layers[0].name = "UVMap"
    while len(o.data.uv_layers) > 1: o.data.uv_layers.remove(o.data.uv_layers[1])
REPORT["tris"] = {o.name: tris(o) for o in objs}
REPORT["tris_total"] = {f"LOD{i}": sum(tris(o) for o in objs if o.name.endswith(f"LOD{i}")) for i in range(3)}
co = np.array([tuple(v.co) for o in (body, core) for v in o.data.vertices])
REPORT["bounds_m"] = {"min": co.min(0).round(4).tolist(), "max": co.max(0).round(4).tolist(), "size": (co.max(0) - co.min(0)).round(4).tolist()}
REPORT["canister_axis_m"] = [round(AX.x, 4), round(AX.y, 4)]
log("tris", REPORT["tris"])

# ------------------------------------------------------------------ 7. export (official FBX exporter) + blend
activate(objs)
bpy.ops.export_scene.fbx(filepath=str(EXP / "SalvageCache.fbx"), use_selection=True, object_types={"MESH"},
                         apply_unit_scale=True, apply_scale_options="FBX_SCALE_ALL", axis_forward="-Z", axis_up="Y",
                         bake_space_transform=True, use_mesh_modifiers=True, mesh_smooth_type="OFF", use_tspace=True,
                         use_custom_props=False, add_leaf_bones=False, path_mode="STRIP", embed_textures=False,
                         use_triangles=True, bake_anim=False)
maps = {"MI_SalvageCache_Body": {"base": "SalvageCache_Body_BaseColor.png", "normal": "SalvageCache_Body_Normal.png", "mask": "SalvageCache_Body_MaskMap.png"},
        "MI_SalvageCache_Vial": {"base": "SalvageCacheVial_BaseColor.png", "normal": "SalvageCacheVial_Normal.png", "mask": "SalvageCacheVial_MaskMap.png"},
        "MI_SalvageCache_Core": {"base": "SalvageCacheVial_BaseColor.png", "normal": "SalvageCacheVial_Normal.png", "mask": "SalvageCacheVial_MaskMap.png",
                                 "emission": "SalvageCacheVial_Emission.png"}}
(EXP / "materials.json").write_text(json.dumps(maps, indent=1))
for im in bpy.data.images:
    if im.name.startswith(("SalvageCacheVial_", "SalvageCache_Body_ao")) and not im.filepath: im.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(SRC / "salvage_cache_v1.blend"), compress=True)
(HERE / "build-report.json").write_text(json.dumps(REPORT, indent=1))
log("done", json.dumps(REPORT["tris_total"]))
