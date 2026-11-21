# Measure the Meshy scrap pistol (the skin the rebuild is held to) and render it grey and textured from six sides.
# Usage: SH/blender.sh pistol/measure.py -- [--render]
# Writes pistol/work/skin_measure.json, pistol/work/skin_mask_{side,top,front}.npy and pistol/work/skin_*.png
import sys, os, json, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'kit'))
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix
import pframe as PF
import measure as ME

WORK = os.path.join(HERE, 'work') + '/'
os.makedirs(WORK, exist_ok=True)
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
bpy.ops.wm.read_factory_settings(use_empty=True)
skin = PF.import_skin()
tree, verts = ME.world_bvh([skin])
V = np.array([tuple(v) for v in verts])
R = {'scale': PF.S, 'tris': sum(len(p.vertices) - 2 for p in skin.data.polygons)}
lo, hi = V.min(0), V.max(0)
R['bounds_m'] = {'min': [round(float(x), 5) for x in lo], 'max': [round(float(x), 5) for x in hi],
                 'size_mm': [round(float(x) * 1000, 2) for x in hi - lo]}
gl = V / PF.S
R['gltf_size_units'] = [round(float(gl[:, 0].max() - gl[:, 0].min()), 4), round(float(gl[:, 2].max() - gl[:, 2].min()), 4),
                        round(float(gl[:, 1].max() - gl[:, 1].min()), 4)]


def hit(o, d, dist=1.0):
    return tree.ray_cast(Vector(o), Vector(d), dist)[0]


# ---- bore: circle fits of the barrel's outer section at stations ahead of the receiver, and the mouth
FACT_AXIS = (0.00075, 0.05885)       # FACTS / pm_mats AXIS_Y0, AXIS_Z0
bore = []
for x in np.arange(-0.128, -0.060, 0.004):
    ring = ME.section_ring(tree, float(x), FACT_AXIS, 0.03, 96)
    # keep the points that belong to a round section (near the median radius)
    if len(ring) < 40:
        continue
    rr = np.hypot(np.array(ring)[:, 0] - FACT_AXIS[0], np.array(ring)[:, 1] - FACT_AXIS[1])
    med = np.median(rr)
    keep = [p for p, r in zip(ring, rr) if abs(r - med) < 0.0015]
    if len(keep) < 30:
        continue
    cy, cz, r, rms = ME.fit_circle(keep)
    bore.append({'x': round(float(x), 4), 'y': round(cy, 5), 'z': round(cz, 5), 'r_mm': round(r * 1000, 2), 'rms_mm': round(rms * 1000, 3), 'n': len(keep)})
R['barrel_sections'] = bore
good = [b for b in bore if b['rms_mm'] < 0.35]
if good:
    R['bore_axis_fit'] = {'y': round(float(np.mean([b['y'] for b in good])), 5), 'z': round(float(np.mean([b['z'] for b in good])), 5), 'stations': len(good)}
m = hit((-0.3, FACT_AXIS[0], FACT_AXIS[1]), (1, 0, 0))
R['front_hit_on_fact_axis_x'] = round(m.x, 5) if m else None
R['front_most_x'] = round(float(lo[0]), 5)
# muzzle ring: front hits at radii around the axis
ring_hits = {}
for dr in (0.0, 0.002, 0.004, 0.006, 0.008, 0.010, 0.012, 0.014, 0.016, 0.018, 0.020):
    xs = []
    for k in range(12):
        a = 2 * math.pi * k / 12
        h = hit((-0.3, FACT_AXIS[0] + dr * math.cos(a), FACT_AXIS[1] + dr * math.sin(a)), (1, 0, 0))
        xs.append(round(h.x, 4) if h else None)
    ring_hits['%.0fmm' % (dr * 1000)] = xs
R['muzzle_front_hits_x_by_radius'] = ring_hits

# ---- side profile rows (top z / bottom z at three y) and widths per x
prof = []
for x in np.arange(-0.135, 0.146, 0.005):
    row = {'x': round(float(x), 3)}
    for y in (-0.012, 0.0, 0.012):
        t = hit((x, y, 0.3), (0, 0, -1)); b = hit((x, y, -0.3), (0, 0, 1))
        row['y%+.0f' % (y * 1000)] = [round(t.z, 4) if t else None, round(b.z, 4) if b else None]
    w = {}
    for z in (0.085, 0.075, 0.059, 0.045, 0.035, 0.025, 0.015, 0.0, -0.02, -0.04, -0.06, -0.08):
        r = hit((x, 0.3, z), (0, -1, 0)); l = hit((x, -0.3, z), (0, 1, 0))
        if r or l:
            w['%+.0f' % (z * 1000)] = [round(r.y * 1000, 1) if r else None, round(l.y * 1000, 1) if l else None]
    row['width_y_right_left_mm_at_z'] = w
    prof.append(row)
R['profile'] = prof

# ---- grip: back strap and front strap x per z, sides per z along the grip axis
GRIP_C0 = Vector((0.080, 0, -0.030)); GRIP_AX = Vector((-0.4633, 0, 1.0)).normalized()
grip = []
for z in np.arange(0.035, -0.096, -0.005):
    back = hit((0.3, 0, z), (-1, 0, 0))
    c = GRIP_C0 + GRIP_AX * ((z - GRIP_C0.z) / GRIP_AX.z)
    f2 = hit((c.x - 0.07, 0, z), (1, 0, 0), 0.2)     # front strap seen from 70 mm ahead of the grip axis
    r = hit((c.x, 0.3, z), (0, -1, 0)); l = hit((c.x, -0.3, z), (0, 1, 0))
    grip.append({'z': round(float(z), 3), 'axis_x': round(c.x, 4), 'back_x': round(back.x, 4) if back else None,
                 'front_x_from_ahead': round(f2.x, 4) if f2 else None,
                 'right_y_mm': round(r.y * 1000, 1) if r else None, 'left_y_mm': round(l.y * 1000, 1) if l else None})
R['grip_rows'] = grip
base = []
for x in np.arange(0.05, 0.141, 0.005):
    b = hit((x, 0, -0.3), (0, 0, 1))
    base.append([round(float(x), 3), round(b.z, 4) if b else None])
R['underside_z_at_y0'] = base

# ---- silhouettes
BOX_LO = (-0.150, -0.045, -0.110); BOX_HI = (0.160, 0.045, 0.110)
R['mask_box'] = {'lo': BOX_LO, 'hi': BOX_HI, 'step': 0.0005}
for view in ('side', 'top', 'front'):
    mk, org, st = ME.silhouette([skin], view, BOX_LO, BOX_HI, 0.0005)
    np.save(WORK + 'skin_mask_%s.npy' % view, mk)
    ME.save_mask_png(WORK + 'skin_mask_%s.png' % view, [mk])
    R['mask_' + view] = {'shape': list(mk.shape), 'origin': [round(org[0], 5), round(org[1], 5)], 'area_cm2': round(float(mk.sum()) * st * st * 1e4, 2)}
json.dump(R, open(WORK + 'skin_measure.json', 'w'), indent=1)
print('MEASURE', json.dumps({k: R[k] for k in ('tris', 'bounds_m', 'gltf_size_units', 'bore_axis_fit', 'front_hit_on_fact_axis_x', 'front_most_x')}))

if '--render' in ARGS:
    import review as RV
    RV.studio(samples=40)
    views = RV.six_views(center=(0.005, 0.0, 0.0), dist=0.8, ortho=0.30)
    for mode in ('textured', 'clay'):
        if mode == 'clay':
            RV.clay([skin])
        for name, cam in views.items():
            RV.render(WORK + 'skin_%s_%s.png' % (mode, name), cam, res=(1500, 1000))
    RV.contact_sheet([WORK + 'skin_textured_%s.png' % n for n in views], WORK + 'skin_sheet_textured.png', cols=3)
    RV.contact_sheet([WORK + 'skin_clay_%s.png' % n for n in views], WORK + 'skin_sheet_clay.png', cols=3)
    # close three-quarter views
    for nm, d in (('q_front_left', (-0.8, -0.9, 0.45)), ('q_rear_left', (0.9, -0.8, 0.35)), ('q_front_right', (-0.8, 0.9, 0.45)), ('q_rear_right_low', (0.9, 0.8, -0.3))):
        cam = RV.look_cam('c_' + nm, (0.0, 0, 0.0), Vector(d).normalized() * 0.55, fov=30)
        RV.render(WORK + 'skin_clay_%s.png' % nm, cam, res=(1500, 1000))
    print('RENDERED')
