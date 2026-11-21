# Probe of the existing Meshy workbench (SS_Workbench_LOD0.glb) for the fixture layout: what stands on the worktop and
# where, a height map above the worktop, and renders from above, from the front and from the bench camera.
# Read-only on the game's files. Usage: SH/blender.sh fixtures/src/probe_bench.py
# Bench frame used by both of my families (Blender, metres, Z up): origin on the worktop surface under the bench
# pivot, +X = the player's right, -Y = toward the player (bench front), so
#   Unity bench-local (x, y, z) = (-X, Z + 0.8637, -Y).
import bpy, bmesh, os, sys, json, math
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(FIX, '..', '..', '..'))
SS = ROOT + '/unity/AthenHill/Assets/AthenHill/Art/SalvageShop/Props/SS_Workbench/'
OUT = FIX + '/layout/'
os.makedirs(OUT, exist_ok=True)
TOP = 0.8637

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SS + 'SS_Workbench_LOD0.glb')
bench = [o for o in bpy.data.objects if o.type == 'MESH'][0]
bpy.context.view_layer.update()
# move into the bench frame: worktop surface at z = 0
for o in bpy.data.objects:
    if o.parent is None:
        o.matrix_world = Matrix.Translation((0, 0, -TOP)) @ o.matrix_world
bpy.context.view_layer.update()
m = bpy.data.materials.new('bench'); m.use_nodes = True
nt = m.node_tree; b = nt.nodes['Principled BSDF']
t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(SS + 'SS_Workbench_BaseColor.jpg')
nt.links.new(t.outputs['Color'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = 0.7
bench.data.materials.clear(); bench.data.materials.append(m)

bm = bmesh.new(); bm.from_mesh(bench.data); bm.transform(bench.matrix_world)
tree = BVHTree.FromBMesh(bm)
vs = np.array([v.co[:] for v in bm.verts])
print('BOUNDS', vs.min(0), vs.max(0))

# height maps on a 5 mm grid: first hit from just under the print head, and from above everything
STEP = 0.005
xs = np.arange(-1.15, 1.15 + 1e-6, STEP); ys = np.arange(-0.62, 0.62 + 1e-6, STEP)


def hmap(z0):
    H = np.full((len(ys), len(xs)), -1.0, np.float32)
    for j, y in enumerate(ys):
        for i, x in enumerate(xs):
            hit = tree.ray_cast(Vector((x, y, z0)), Vector((0, 0, -1)))
            if hit[0] is not None:
                H[j, i] = hit[0].z
    return H


H_low = hmap(0.55)      # under the print head (its bottom is 0.605 above the worktop)
H_all = hmap(2.0)
np.save(OUT + 'bench_height_under_head.npy', H_low); np.save(OUT + 'bench_height_all.npy', H_all)
flat = (np.abs(H_low) < 0.012)
info = {'frame': 'bench frame: origin on worktop under bench pivot, +X player right, -Y toward player, Z up; '
                 'Unity bench-local = (-X, Z+0.8637, -Y)',
        'grid_step_m': STEP, 'x0': float(xs[0]), 'y0': float(ys[0]), 'nx': len(xs), 'ny': len(ys),
        'bounds_min': [round(float(v), 4) for v in vs.min(0)], 'bounds_max': [round(float(v), 4) for v in vs.max(0)],
        'flat_fraction': round(float(flat.mean()), 3)}
# per-row extent of the flat worktop (|z| < 12 mm) to find what is clear
rows = {}
for j in range(0, len(ys), 10):
    xi = np.where(flat[j])[0]
    rows['%.3f' % ys[j]] = [round(float(xs[xi[0]]), 3), round(float(xs[xi[-1]]), 3), int(len(xi))] if len(xi) else None
info['flat_rows_y_to_xmin_xmax_count'] = rows
# things standing proud of the worktop inside its outline: connected blobs above 15 mm
proud = (H_low > 0.015)
info['proud_fraction'] = round(float(proud.mean()), 3)
json.dump(info, open(OUT + 'bench_probe.json', 'w'), indent=1)

# height picture: grey = worktop level, warm = above, cool = below / nothing
img = np.zeros((len(ys), len(xs), 4), np.float32); img[..., 3] = 1
h = np.clip(H_low, -0.05, 0.55)
img[..., 0] = np.clip(h / 0.55, 0, 1) * 0.9 + 0.1 * flat
img[..., 1] = flat * 0.6 + np.clip(h / 0.25, 0, 1) * 0.3
img[..., 2] = (H_low < -0.012) * 0.6 + flat * 0.6
im = bpy.data.images.new('h', len(xs), len(ys)); im.pixels.foreach_set(img.ravel())
im.filepath_raw = OUT + 'bench_height_under_head.png'; im.file_format = 'PNG'; im.save()

# renders
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 24; sc.cycles.use_denoising = True
sc.render.threads_mode = 'FIXED'; sc.render.threads = 12
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs[0].default_value = (0.8, 0.8, 0.8, 1)
w.node_tree.nodes['Background'].inputs[1].default_value = 1.0
sc.view_settings.view_transform = 'Standard'


def cam(name, loc, look, up=(0, 0, 1), ortho=None, lens=35):
    cd = bpy.data.cameras.new(name); c = bpy.data.objects.new(name, cd); sc.collection.objects.link(c)
    f = Vector(look).normalized(); u = Vector(up).normalized(); r = f.cross(u).normalized(); u = r.cross(f)
    M = Matrix((r, u, -f)).transposed().to_4x4(); M.translation = Vector(loc); c.matrix_world = M
    cd.clip_start = 0.02; cd.clip_end = 50
    if ortho:
        cd.type = 'ORTHO'; cd.ortho_scale = ortho
    else:
        cd.lens = lens; cd.sensor_width = 36
    return c


def shot(c, path, res):
    sc.camera = c; sc.render.resolution_x, sc.render.resolution_y = res; sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


# top view cut just under the print head so the gantry does not hide the worktop
ct = cam('top', (0, 0, 0.58), (0, 0, -1), up=(0, 1, 0), ortho=2.4)
shot(ct, OUT + 'bench_top_under_head.png', (1800, 1000))
ct2 = cam('top_all', (0, 0, 3.0), (0, 0, -1), up=(0, 1, 0), ortho=2.4)
shot(ct2, OUT + 'bench_top_all.png', (1800, 1000))
cf = cam('front', (0, -3, 0.2), (0, 1, 0), ortho=2.6)
shot(cf, OUT + 'bench_front.png', (1800, 1500))
cs = cam('side', (3, 0, 0.2), (-1, 0, 0), ortho=2.6)
shot(cs, OUT + 'bench_side.png', (1800, 1500))
# bench camera: standing eye 1.65 m above the floor, 0.50 m in front of the front edge, 40 degrees down, 35 mm
eye = Vector((0, -0.5833 - 0.50, 1.65 - TOP))
d = Vector((0, math.cos(math.radians(40)), -math.sin(math.radians(40))))
cb = cam('benchcam', eye, d)
shot(cb, OUT + 'bench_cam40.png', (1600, 900))
print('PROBE DONE')
