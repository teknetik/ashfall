# The fixed numbers of the rebuilt pistol against the Meshy skin: bounds, silhouettes, bore, rail, trigger, the hand
# grip points and the five other mods. Called from build.py; writes export/outline.json and review/outline_*.png.
import os, json, math
import bpy
import numpy as np
from mathutils import Vector
import measure as ME
import pframe as PF
import pgeom as PG

HERE = os.path.dirname(os.path.abspath(__file__))
MM = 0.001


def _depths(tree, verts):
    """How deep points lie inside a surface: (count deeper than 0.3 mm, max depth mm, count within 1 mm outside)."""
    deep = 0; worst = 0.0; near = 0
    for p in verts:
        nn = tree.find_nearest(p, 0.03)
        if nn[0] is None:
            continue
        ins = (p - nn[0]).dot(nn[1]) < 0
        if ins:
            worst = max(worst, nn[3])
            if nn[3] > 0.0003:
                deep += 1
        elif nn[3] < 0.001:
            near += 1
    return deep, round(worst * 1000, 2), near


def run(F, cards, nomods=False, tol_mm=1.5):
    parts = [o for o in F.parts().values() if o not in cards]
    skin = PF.import_skin()
    R = json.load(open(os.path.join(HERE, 'work', 'skin_measure.json')))
    out = {'skin': 'Art/OuterBerms/ScrapPistol.glb at 0.13674', 'tolerance_mm': tol_mm}
    lo, hi = ME.bounds(parts); slo, shi = ME.bounds([skin])
    out['bounds_mm'] = {'new_min': [round(float(x) * 1000, 2) for x in lo], 'new_max': [round(float(x) * 1000, 2) for x in hi],
                        'skin_min': [round(float(x) * 1000, 2) for x in slo], 'skin_max': [round(float(x) * 1000, 2) for x in shi],
                        'size_new': [round(float(x) * 1000, 2) for x in hi - lo], 'size_skin': [round(float(x) * 1000, 2) for x in shi - slo],
                        'error_min': [round(float(x) * 1000, 2) for x in lo - slo], 'error_max': [round(float(x) * 1000, 2) for x in hi - shi]}
    box = R['mask_box']
    os.makedirs(os.path.join(HERE, 'review'), exist_ok=True)
    out['silhouette'] = {}
    for view in ('side', 'top', 'front'):
        mk, org, st = ME.silhouette(parts, view, box['lo'], box['hi'], box['step'])
        sk = np.load(os.path.join(HERE, 'work', 'skin_mask_%s.npy' % view))
        out['silhouette'][view] = ME.compare_masks(mk, sk, st)
        ME.save_mask_png(os.path.join(HERE, 'review', 'outline_%s.png' % view), [sk, mk])
    # bore: the muzzle ring's outside and the bore's inside, fitted on the new barrel
    bar = bpy.data.objects['pistol_barrel']
    tree, verts = ME.world_bvh([bar])
    ring = ME.section_ring(tree, -0.126, (PG.BORE_Y * MM, PG.BORE_Z * MM), 0.03, 72)
    cy, cz, r, rms = ME.fit_circle(ring)
    mouth = min(v.x for v in verts)
    stree, sverts = ME.world_bvh([skin])
    sring = ME.section_ring(stree, -0.126, (PG.BORE_Y * MM, PG.BORE_Z * MM), 0.03, 72)
    scy, scz, sr, srms = ME.fit_circle(sring)
    out['bore'] = {'new_axis_y_mm': round(cy * 1000, 3), 'new_axis_z_mm': round(cz * 1000, 3), 'new_ring_r_mm': round(r * 1000, 2),
                   'skin_axis_y_mm': round(scy * 1000, 3), 'skin_axis_z_mm': round(scz * 1000, 3), 'skin_ring_r_mm': round(sr * 1000, 2),
                   'facts_axis_y_mm': PG.BORE_Y, 'facts_axis_z_mm': PG.BORE_Z,
                   'axis_error_mm': round(math.hypot(cy - scy, cz - scz) * 1000, 3),
                   'new_mouth_x_mm': round(mouth * 1000, 2), 'skin_mouth_x_mm': round(float(slo[0]) * 1000, 2),
                   'mouth_error_mm': round((mouth - float(slo[0])) * 1000, 2)}
    # rail: left face where the cell mods sit
    ntree, _ = ME.world_bvh(parts)
    rail = []
    for x in (-0.090, -0.075, -0.060, -0.045, -0.035):
        for z in (0.030, 0.038):
            a = ntree.ray_cast(Vector((x, -0.2, z)), Vector((0, 1, 0)), 0.4)[0]
            b = stree.ray_cast(Vector((x, -0.2, z)), Vector((0, 1, 0)), 0.4)[0]
            if a and b:
                rail.append({'x_mm': x * 1000, 'z_mm': z * 1000, 'new_y_mm': round(a.y * 1000, 2), 'skin_y_mm': round(b.y * 1000, 2), 'error_mm': round((a.y - b.y) * 1000, 2)})
    out['rail_left_face'] = {'samples': rail, 'max_error_mm': max(abs(r_['error_mm']) for r_ in rail) if rail else None}
    # trigger and guard
    tr = bpy.data.objects['pistol_trigger']
    tlo, thi = ME.bounds([tr])
    g_new = ntree.ray_cast(Vector((-0.005, 0.0, -0.2)), Vector((0, 0, 1)), 0.4)[0]
    g_skin = stree.ray_cast(Vector((-0.005, 0.0, -0.2)), Vector((0, 0, 1)), 0.4)[0]
    out['trigger'] = {'blade_x_mm': [round(float(tlo[0]) * 1000, 1), round(float(thi[0]) * 1000, 1)], 'blade_z_min_mm': round(float(tlo[2]) * 1000, 1),
                      'skin_blade_x_mm': [-1, 16], 'skin_blade_z_min_mm': -10,      # read from the skin's side silhouette
                      'guard_bottom_new_mm': round(g_new.z * 1000, 2) if g_new else None, 'guard_bottom_skin_mm': round(g_skin.z * 1000, 2) if g_skin else None}
    # grip: the surface along the axis and the two hand points of the view model
    rows = []
    for s in (-45, -30, -15, 0, 15):
        c = PG.GP(0, s)
        for nm, d in (('back', -PG.U_), ('front', PG.U_), ('left', Vector((0, -1, 0))), ('right', Vector((0, 1, 0)))):
            a = ntree.ray_cast(c + d * 0.08, -d, 0.2)[0]; b = stree.ray_cast(c + d * 0.08, -d, 0.2)[0]
            if a and b:
                rows.append({'s_mm': s, 'side': nm, 'new_mm': round((a - c).length * 1000, 2), 'skin_mm': round((b - c).length * 1000, 2),
                             'error_mm': round(((a - c).length - (b - c).length) * 1000, 2)})
    out['grip'] = {'centre_m': [0.080, 0.0, -0.030], 'rake_deg': round(math.degrees(math.atan2(0.42038, 0.90736)), 2), 'surface': rows,
                   'max_error_mm': max(abs(r_['error_mm']) for r_ in rows) if rows else None,
                   'mean_abs_error_mm': round(float(np.mean([abs(r_['error_mm']) for r_ in rows])), 2) if rows else None}
    pts = {'Shooting grip': (0.0448, -0.0828, -0.0295), 'Support grip': (-0.0139, -0.1009, -0.0181)}
    hp = {}
    for nm, v in pts.items():
        p = PF.unity_holder_to_metric(v)
        a = ntree.find_nearest(p)[3]; b = stree.find_nearest(p)[3]
        hp[nm] = {'metric_m': [round(x, 5) for x in p], 'to_new_surface_mm': round(a * 1000, 2), 'to_skin_surface_mm': round(b * 1000, 2), 'error_mm': round((a - b) * 1000, 2)}
    out['hand_points'] = hp
    # the other mods: how their vertices sit against the new pistol, with the skin as the baseline
    if not nomods:
        mods = PF.import_mods()
        mm = {}
        for nm, o in sorted(mods.items()):
            V = [o.matrix_world @ v.co for v in o.data.vertices]
            d_new = _depths(ntree, V); d_skin = _depths(stree, V)
            mm[nm] = {'verts': len(V), 'new': {'deeper_than_0.3mm': d_new[0], 'max_depth_mm': d_new[1], 'within_1mm_outside': d_new[2]},
                      'skin': {'deeper_than_0.3mm': d_skin[0], 'max_depth_mm': d_skin[1], 'within_1mm_outside': d_skin[2]}}
        out['mods'] = mm
        for o in list(mods.values()):
            bpy.data.objects.remove(o, do_unlink=True)
    for o in [o for o in bpy.data.objects if o.name.startswith('SKIN_') or (o.type == 'EMPTY' and not o.get('sh_helper') and o.parent is None and o.name not in ('',))]:
        if o.name.startswith('SKIN_'):
            bpy.data.objects.remove(o, do_unlink=True)
    for o in list(bpy.data.objects):          # whatever else the importers left
        if o.type in ('MESH', 'EMPTY') and 'sh' not in o and not o.get('sh_helper'):
            bpy.data.objects.remove(o, do_unlink=True)
    for m in list(bpy.data.materials):
        if m.users == 0:
            bpy.data.materials.remove(m)
    b = out['bounds_mm']
    worst = max(max(abs(x) for x in b['error_min']), max(abs(x) for x in b['error_max']))
    out['ok'] = bool(worst <= tol_mm and out['bore']['axis_error_mm'] <= 0.1 and abs(out['bore']['mouth_error_mm']) <= 0.1)
    out['worst_bounds_error_mm'] = round(worst, 2)
    json.dump(out, open(os.path.join(F.out, 'outline.json'), 'w'), indent=1)
    F.log('OUTLINE', json.dumps({'bounds_err_min': b['error_min'], 'bounds_err_max': b['error_max'], 'sil': out['silhouette'],
                                 'bore': out['bore']['axis_error_mm'], 'mouth': out['bore']['mouth_error_mm'], 'rail': out['rail_left_face']['max_error_mm'],
                                 'grip_mean': out['grip']['mean_abs_error_mm'], 'grip_max': out['grip']['max_error_mm'], 'ok': out['ok']}))
    if not nomods:
        F.log('MODS', json.dumps(out['mods']))
    return out
