"""URP Lit texture sets for the ranged enemies (headless Blender 5.2; pixels via numpy).
Usage: blender.sh make_textures.py -- <unity Textures dir> <record json>
Writes <name>_BaseMap.png (sRGB), _Normal.png (glTF/OpenGL normal map, as Unity expects), _Mask.png (URP Lit metallic
mask: R metallic = glTF metallicRoughness B, G occlusion = 1, A smoothness = (1 - roughness G) x 0.85 for desert dust)
for FeralGunner (rig body), FeralGunnerGun (forearm gun) and FeralLancer (body, rotors and stators share its atlas),
plus FeralGunner_Emission.png: an optics-only emission mask (the Meshy emission maps are black): the head optic's
triangles (head, forward-facing, saturated red-orange lens texels) rasterised into UV space, gated by texel redness, so
FeralDroid can drive the glow with _EmissionColor. Renders a head close-up with the mask lit as a check."""
import bpy, sys, json, math
from pathlib import Path
import numpy as np
from mathutils import Vector
a = sys.argv[sys.argv.index('--') + 1:]
TEX, RECP = Path(a[0]), Path(a[1]); TEX.mkdir(parents=True, exist_ok=True)
HERE = Path(__file__).parent
rec = {}


def load(glb):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(glb))
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    return meshes


def pixels(img):
    w, h = img.size; p = np.empty(w * h * img.channels, np.float32); img.pixels.foreach_get(p)
    return p.reshape(h, w, img.channels)


def save(arr, path, srgb=True):
    """arr: (h, w, 3|4) float 0..1, bottom row first (Blender pixel order)."""
    h, w, c = arr.shape
    img = bpy.data.images.new(path.stem, w, h, alpha=(c == 4), float_buffer=False)
    img.colorspace_settings.name = 'sRGB' if srgb else 'Non-Color'
    full = np.ones((h, w, 4), np.float32); full[..., :c] = arr
    img.pixels.foreach_set(full.ravel()); img.filepath_raw = str(path); img.file_format = 'PNG'; img.save()
    return str(path)


def material_maps(mat):
    """Images feeding Base Color, Normal (via normal map node), metallic/roughness (separate color) of a glTF material."""
    out = {}
    for n in mat.node_tree.nodes:
        if n.type != 'TEX_IMAGE': continue
        for l in n.outputs['Color'].links:
            to = l.to_node
            if to.type == 'BSDF_PRINCIPLED' and l.to_socket.name == 'Base Color': out['base'] = n.image
            elif to.type == 'NORMAL_MAP': out['normal'] = n.image
            elif to.type in ('SEPARATE_COLOR', 'SEPRGB'): out['mr'] = n.image
            elif to.type == 'BSDF_PRINCIPLED' and l.to_socket.name == 'Emission Color': out['emission'] = n.image
    return out


def export_set(name, mat, smooth_scale=.85):
    m = material_maps(mat); r = {}
    base = pixels(m['base']); r['base'] = save(base[..., :3], TEX / f'{name}_BaseMap.png', True)
    nrm = pixels(m['normal']); r['normal'] = save(nrm[..., :3], TEX / f'{name}_Normal.png', False)
    mr = pixels(m['mr'])
    mask = np.dstack([mr[..., 2], np.ones_like(mr[..., 0]), np.zeros_like(mr[..., 0]), np.clip((1 - mr[..., 1]) * smooth_scale, 0, 1)])
    r['mask'] = save(mask, TEX / f'{name}_Mask.png', False)
    r['stats'] = dict(size=list(m['base'].size), metallic_mean=round(float(mr[..., 2].mean()), 3), metallic_p95=round(float(np.percentile(mr[..., 2], 95)), 3),
                      roughness_mean=round(float(mr[..., 1].mean()), 3), smoothness_scale=smooth_scale)
    return r, base


def raster(UV, tris, size):
    m = np.zeros((size, size), np.float32)
    for uv in tris:
        uv = uv * size
        x0, y0 = np.floor(uv.min(0)).astype(int) - 1; x1, y1 = np.ceil(uv.max(0)).astype(int) + 1
        x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, size - 1), min(y1, size - 1)
        if x1 < x0 or y1 < y0: continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + .5, np.arange(y0, y1 + 1) + .5)
        A, B, Cc = uv; d = (B[1] - Cc[1]) * (A[0] - Cc[0]) + (Cc[0] - B[0]) * (A[1] - Cc[1])
        if abs(d) < 1e-12: continue
        l1 = ((B[1] - Cc[1]) * (xs - Cc[0]) + (Cc[0] - B[0]) * (ys - Cc[1])) / d
        l2 = ((Cc[1] - A[1]) * (xs - Cc[0]) + (A[0] - Cc[0]) * (ys - Cc[1])) / d
        inside = (l1 >= -.02) & (l2 >= -.02) & (1 - l1 - l2 >= -.02)
        m[y0:y1 + 1, x0:x1 + 1] = np.maximum(m[y0:y1 + 1, x0:x1 + 1], inside)
    # 1 px dilation only (Meshy atlases pack unrelated islands edge to edge)
    p = np.pad(m, 1); return np.max([p[1 + dy:1 + dy + size, 1 + dx:1 + dx + size] for dy in (-1, 0, 1) for dx in (-1, 0, 1)], axis=0)


# ------------------------------------------------------------------ gunner body + optic emission
meshes = load(HERE / 'gunner/rig/rigged.glb')
body = max(meshes, key=lambda o: len(o.data.vertices))
r, base = export_set('FeralGunner', body.data.materials[0], .85)
dg = bpy.context.evaluated_depsgraph_get(); ev = body.evaluated_get(dg); me = ev.to_mesh()
mw = ev.matrix_world
uvl = me.uv_layers.active.data
H_, W_ = base.shape[:2]
tri_uv, tri_c, tri_n, tri_col = [], [], [], []
me.calc_loop_triangles()
for t in me.loop_triangles:
    c = mw @ Vector(t.center); n = (mw.to_3x3() @ t.normal).normalized()
    if c.z < 1.6 or abs(c.x) > .12: continue
    uv = np.array([uvl[l].uv[:] for l in t.loops]); cu = uv.mean(0)
    col = base[min(int(cu[1] * H_), H_ - 1), min(int(cu[0] * W_), W_ - 1), :3]
    tri_uv.append(uv); tri_c.append(c[:]); tri_n.append(n[:]); tri_col.append(col)
tri_uv, tri_c, tri_n, tri_col = map(np.array, (tri_uv, tri_c, tri_n, tri_col))
red = tri_col[:, 0] - np.maximum(tri_col[:, 1], tri_col[:, 2])
# the robot faces -Y in Blender: forward-facing optic glass = n.y < -0.3, strongly red-orange
sel = (tri_n[:, 1] < -.3) & (red > .22) & (tri_col[:, 0] > .4)
rec['gunner_optic'] = dict(triangles=int(sel.sum()), centre=tri_c[sel].mean(0).round(4).tolist() if sel.any() else None,
                           extent=(np.ptp(tri_c[sel], 0)).round(4).tolist() if sel.any() else None)
SZ = H_   # rasterise and gate at the base map's resolution, then average 2x2 down to 1024 (antialiased lens edge)
mask = raster(None, tri_uv[sel], SZ)
rd = base[..., 0] - np.maximum(base[..., 1], base[..., 2])
glow = mask * np.clip((rd - .08) / .25, 0, 1) ** .7
while glow.shape[0] > 1024: glow = glow.reshape(glow.shape[0] // 2, 2, glow.shape[1] // 2, 2).mean((1, 3))
em = np.dstack([glow, glow, glow])
r['emission'] = save(em, TEX / 'FeralGunner_Emission.png', False)
r['emission_lit_texels'] = int((glow > .1).sum())
rec['FeralGunner'] = r
ev.to_mesh_clear()
# check render: head close-up with the emission map lit
s = bpy.context.scene; s.render.engine = 'CYCLES'; s.cycles.device = 'CPU'; s.cycles.samples = 16; s.view_settings.view_transform = 'AgX'
s.render.resolution_x = s.render.resolution_y = 600
mat = body.data.materials[0]; nt = mat.node_tree; bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
for l in list(bsdf.inputs['Emission Color'].links): nt.links.remove(l)
ei = nt.nodes.new('ShaderNodeTexImage'); ei.image = bpy.data.images.load(str(TEX / 'FeralGunner_Emission.png')); ei.image.colorspace_settings.name = 'Non-Color'
nt.links.new(ei.outputs['Color'], bsdf.inputs['Emission Color']); bsdf.inputs['Emission Strength'].default_value = 6
w = bpy.data.worlds.new('w'); s.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[1].default_value = .6
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); s.collection.objects.link(cam); s.camera = cam; cam.data.lens = 70
oc = Vector(rec['gunner_optic']['centre'] or (0, 0, 1.75))
cam.location = oc + Vector((.25, -.75, .1)); cam.rotation_euler = (oc - cam.location).to_track_quat('-Z', 'Y').to_euler()
s.render.filepath = str(HERE / 'renders' / 'gunner_optic_emission.png'); bpy.ops.render.render(write_still=True)

# ------------------------------------------------------------------ forearm gun
meshes = load(HERE / 'gunner/ForearmGun.glb')
gun = next(o for o in meshes if o.name.startswith('ForearmGun'))
r, _ = export_set('FeralGunnerGun', gun.data.materials[0], .85); rec['FeralGunnerGun'] = r

# ------------------------------------------------------------------ lancer (same atlas as lancer/a1/model.glb)
meshes = load(HERE / 'lancer/a1/model.glb')
r, _ = export_set('FeralLancer', meshes[0].data.materials[0], .85); rec['FeralLancer'] = r
RECP.write_text(json.dumps(rec, indent=1)); print('TEXTURES DONE', json.dumps(rec['gunner_optic']))
