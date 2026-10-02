"""Feral gunner's forearm rivet/arc gun: prepare the Meshy gun for strapping to the gunner's right forearm (Blender 5.2).
Usage: blender.sh prep_gun.py -- <gun model.glb> <out.glb> <out.json> [length_m=0.85]
- Uniform scale to the requested length; turned so the muzzle faces glTF +Z (Blender -Y) with the top up.
- The two hanging D-ring handles under the receiver (sideways holes, so they cannot hold a forearm laid along the gun)
  are removed and replaced by two authored steel strap bands that wrap the forearm and the receiver underside; their UVs
  are transferred from the nearest removed-handle vertices (same painted steel on the gun atlas, one material).
- Origin: the forearm axis point under the FRONT band (the forearm runs along the gun 0.105 m under the receiver).
- Child empty 'Muzzle' 1 cm ahead of the bore, identity rotation (+Z out of the barrel in glTF/Unity).
Renders in <out dir>/renders/gun_*.png."""
import bpy, bmesh, sys, json, math
from pathlib import Path
from mathutils import Vector, Matrix
import numpy as np
a = sys.argv[sys.argv.index('--') + 1:]
SRC, OUT, REC = Path(a[0]), Path(a[1]), Path(a[2]); LENGTH = float(a[3]) if len(a) > 3 else .85
REN = OUT.parent / 'renders'; REN.mkdir(parents=True, exist_ok=True)
rec = dict(source=str(SRC), length_m=LENGTH)
AXIS_DROP = .105                 # forearm axis below the receiver underside (the forearm's dorsal plate reaches 0.08-0.125)
FRONT_BAND, REAR_BAND = .11, .30 # band centres along the gun, metres behind the gun's centre (muzzle side negative)

bpy.ops.wm.read_factory_settings(use_empty=True)
s = bpy.context.scene
bpy.ops.import_scene.gltf(filepath=str(SRC))
meshes = [o for o in s.objects if o.type == 'MESH']
bpy.ops.object.select_all(action='DESELECT')
for o in meshes: o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
if len(meshes) > 1: bpy.ops.object.join()
gun = bpy.context.view_layer.objects.active; gun.parent = None
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
me = gun.data
co = np.array([v.co[:] for v in me.vertices]); lo, hi = co.min(0), co.max(0)
rec['source_bounds'] = dict(min=lo.round(4).tolist(), max=hi.round(4).tolist())
# Meshy frame (Blender): barrel along X with the muzzle at -X, up +Z. Remove the D-ring handles: faces whose centroid
# hangs below the receiver (z < -0.02 Meshy units) inside the two handle spans.
spans = [(-.13, .21), (.35, .70)]
bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
uvl = bm.loops.layers.uv.active
kill, handle_pts = [], []
for f in bm.faces:
    c = f.calc_center_median()
    if c.z < -.02 and any(l0 < c.x < l1 for l0, l1 in spans):
        kill.append(f)
        for l in f.loops: handle_pts.append((*l.vert.co[:], *l[uvl].uv[:]))
rec['handle_faces_removed'] = len(kill)
bmesh.ops.delete(bm, geom=kill, context='FACES')
loose = [v for v in bm.verts if not v.link_faces]; bmesh.ops.delete(bm, geom=loose, context='VERTS')
bm.to_mesh(me); bm.free()
H = np.array(handle_pts)
# normalise: uniform scale to LENGTH, muzzle to -Y (Blender) = +Z glTF, origin on the forearm axis under the front band
scale = LENGTH / (hi[0] - lo[0]); rec['scale'] = round(scale, 5)
cx = (lo[0] + hi[0]) / 2
co = np.array([v.co[:] for v in me.vertices])
bottom = float(np.percentile(co[(co[:, 0] > .2) & (co[:, 0] < .62), 2], 2)) * scale  # receiver underside (Meshy x .2-.62)
rec['receiver_underside_m'] = round(bottom, 4)
def to_gun(p):  # Meshy (x along barrel, muzzle -X; z up) -> gun frame (muzzle -Y, up +Z), metres, origin = front band axis
    x, y, z = (p[0] - cx) * scale, p[1] * scale, p[2] * scale
    return Vector((-y, x - FRONT_BAND, z - bottom + AXIS_DROP))
for v in me.vertices: v.co = to_gun(v.co)
Hm = np.array([to_gun(p[:3])[:] for p in H]); Huv = H[:, 3:5]

# ------------------------------------------------------------------ strap bands
def band(y0, name):
    """Rounded-rectangle steel strap around the forearm axis (x, z) and the receiver underside, 3.5 cm wide."""
    hw, z_lo, z_hi, r, t, w = .07, -.062, AXIS_DROP + .012, .022, .009, .035
    pts = []
    corners = [(hw - r, z_hi - r, 0), (-hw + r, z_hi - r, 90), (-hw + r, z_lo + r, 180), (hw - r, z_lo + r, 270)]
    for cx_, cz_, a0 in corners:
        for k in range(7):
            ang = math.radians(a0 + 90 * k / 6)
            pts.append((cx_, cz_, math.cos(ang), math.sin(ang)))
    bmb = bmesh.new(); uvb = bmb.loops.layers.uv.new('UVMap')
    rings = []
    for dy in (-w / 2, w / 2):
        for off in (r + t, r):   # outer, inner
            rings.append([bmb.verts.new((cx_ + dx * off, y0 + dy, cz_ + dz * off)) for cx_, cz_, dx, dz in pts])
    n = len(pts)
    o0, i0, o1, i1 = rings
    for k in range(n):
        k2 = (k + 1) % n
        bmb.faces.new([o0[k], o0[k2], o1[k2], o1[k]])      # outer skin
        bmb.faces.new([i0[k], i1[k], i1[k2], i0[k2]])      # inner skin
        bmb.faces.new([o0[k], i0[k], i0[k2], o0[k2]])      # rim
        bmb.faces.new([o1[k], o1[k2], i1[k2], i1[k]])      # rim
    bmesh.ops.recalc_face_normals(bmb, faces=bmb.faces)
    # UVs: nearest removed-handle vertex, after moving the band onto the handle cloud's centre
    hc = Hm.mean(0); bc = np.array([0, y0, (z_lo + z_hi) / 2])
    for f in bmb.faces:
        for l in f.loops:
            p = np.array(l.vert.co[:]) - bc + hc
            l[uvb].uv = Huv[int(np.argmin(((Hm - p) ** 2).sum(1)))]
    m = bpy.data.meshes.new(name); bmb.to_mesh(m); bmb.free()
    o = bpy.data.objects.new(name, m); s.collection.objects.link(o); m.materials.append(me.materials[0])
    return o
bands = [band(0.0, 'Band front'), band(REAR_BAND - FRONT_BAND, 'Band rear')]   # the receiver lies toward +Y (gun frame)
bpy.ops.object.select_all(action='DESELECT')
for o in [gun] + bands: o.select_set(True)
bpy.context.view_layer.objects.active = gun; bpy.ops.object.join()
gun.name = 'ForearmGun'; gun.data.name = 'ForearmGun'
co = np.array([v.co[:] for v in me.vertices])
muzzle_pts = co[co[:, 1] < co[:, 1].min() + .006]
mz = Vector((float(muzzle_pts[:, 0].mean()), float(co[:, 1].min()) - .01, float(muzzle_pts[:, 2].mean())))
muz = bpy.data.objects.new('Muzzle', None); s.collection.objects.link(muz); muz.parent = gun; muz.location = mz
muz.empty_display_size = .05
rec['gun_bounds'] = dict(min=co.min(0).round(4).tolist(), max=co.max(0).round(4).tolist())
rec['muzzle_blender'] = [round(x, 4) for x in mz]
rec['muzzle_gltf'] = [round(mz.x, 4), round(mz.z, 4), round(-mz.y, 4)]
rec['triangles'] = sum(len(p.vertices) - 2 for p in me.polygons)
rec['bands_gun_y'] = [0.0, REAR_BAND - FRONT_BAND]
bpy.ops.object.select_all(action='DESELECT'); gun.select_set(True); muz.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT), export_format='GLB', use_selection=True, export_yup=True, export_apply=False,
                          export_animations=False, export_image_format='AUTO')

# ------------------------------------------------------------------ renders (forearm proxy cylinder for scale)
s.render.engine = 'CYCLES'; s.cycles.device = 'CPU'; s.cycles.samples = 20; s.cycles.use_denoising = True
s.view_settings.view_transform = 'AgX'
wd = bpy.data.worlds.new('w'); s.world = wd; wd.use_nodes = True
wd.node_tree.nodes['Background'].inputs[0].default_value = (.55, .58, .62, 1); wd.node_tree.nodes['Background'].inputs[1].default_value = .8
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); s.collection.objects.link(sun)
sun.data.energy = 3.0; sun.rotation_euler = (math.radians(40), 0, math.radians(-35))
bpy.ops.mesh.primitive_cylinder_add(radius=.05, depth=.3, location=(0, .26 - .15, 0), rotation=(math.radians(90), 0, 0))  # forearm proxy: elbow 0.26 behind the front band
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); s.collection.objects.link(cam); s.camera = cam
def shoot(name, target, dist, yaw, pitch, lens=50, res=(900, 600)):
    cam.data.lens = lens; s.render.resolution_x, s.render.resolution_y = res
    t = Vector(target); y = math.radians(yaw); p = math.radians(pitch)
    cam.location = t + Vector((math.sin(y) * math.cos(p) * dist, -math.cos(y) * math.cos(p) * dist, math.sin(p) * dist))
    cam.rotation_euler = (t - cam.location).to_track_quat('-Z', 'Y').to_euler()
    s.render.filepath = str(REN / f'{name}.png'); bpy.ops.render.render(write_still=True)
C = (0, -.1, .05)
shoot('gun_side', C, 1.5, -90, 5); shoot('gun_front34', C, 1.4, -35, 15); shoot('gun_rear34', C, 1.4, 140, 25)
shoot('gun_under', C, 1.3, -60, -40); shoot('gun_muzzle', tuple(mz), .45, -20, 8, res=(600, 600))
REC.write_text(json.dumps(rec, indent=1)); print('GUN DONE', rec['triangles'])
