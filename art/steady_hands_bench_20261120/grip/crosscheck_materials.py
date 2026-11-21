#!/usr/bin/env python3
"""Numbers check of SEAM.md section 9 (no Blender): the materials family's finished plates and bent strap, read from
materials/export/materials.glb in their own node frames, against the grip's interface. A plate seated on the grip's
mark must put every hole within 0.2 mm of its peg or screw hole. Writes grip/export/crosscheck_materials.json."""
import json, struct, os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__))
glb = os.path.join(HERE, '..', 'materials', 'export', 'materials.glb')
d = open(glb, 'rb').read()
n, _ = struct.unpack('<II', d[12:20]); js = json.loads(d[20:20 + n]); binary = d[20 + n + 8:]
ifc = json.load(open(os.path.join(HERE, 'interface.json')))
nodes = js['nodes']; by = {x.get('name'): i for i, x in enumerate(nodes)}
parent = {c: i for i, x in enumerate(nodes) for c in x.get('children', [])}


def positions(node):
    out = []
    m = js['meshes'][nodes[node]['mesh']]
    for pr in m['primitives']:
        a = js['accessors'][pr['attributes']['POSITION']]; bv = js['bufferViews'][a['bufferView']]
        off = bv.get('byteOffset', 0) + a.get('byteOffset', 0); st = bv.get('byteStride', 12)
        for k in range(a['count']):
            out.append(struct.unpack_from('<3f', binary, off + k * st))
    return out


def gl2bl(p):          # glTF (x, y, z) -> Blender (x, -z, y): the node frame as it was modelled
    return (p[0], -p[2], p[1])


res = {'source': 'materials/export/materials.glb', 'generated_from': 'grip/interface.json', 'tolerance_mm': 0.2, 'plates': {}, 'ok': True}
H = ifc['plate']['holes_G']
for side, name, sx in (('left', 'materials_sheet_a_plate', -1.0), ('right', 'materials_sheet_b_plate', 1.0)):
    i = by.get(name)
    if i is None:
        res['plates'][side] = {'error': 'node %s not in the GLB' % name}; res['ok'] = False; continue
    P = [gl2bl(p) for p in positions(i)]
    lo = [min(p[k] for p in P) * 1000 for k in range(3)]; hi = [max(p[k] for p in P) * 1000 for k in range(3)]
    # expected in the plate's own frame (INTERFACE.md): x = U on the right plate, -U on the left; y = S; z 0..2 outward
    us = ifc['plate']['outline_G_us']
    exp_lo = [min(sx * u for u, s in us), min(s for u, s in us), 0.0]; exp_hi = [max(sx * u for u, s in us), max(s for u, s in us), ifc['plate']['thickness']]
    row = {'node': name, 'bounds_mm': [[round(x, 2) for x in lo], [round(x, 2) for x in hi]],
           'expected_bounds_mm': [[round(x, 2) for x in exp_lo], [round(x, 2) for x in exp_hi]], 'holes': {}}
    row['bounds_dev_mm'] = round(max(max(abs(a - b) for a, b in zip(lo, exp_lo)), max(abs(a - b) for a, b in zip(hi, exp_hi))), 2)
    # holes: the punch marks are children of the plate node, so their translation is in the plate's frame
    for k, key in enumerate('ABCD', 1):
        mk = by.get('%s__mark_punch_%d' % (name, k))
        ex = (sx * H[key]['u'], H[key]['s'])
        if mk is None or parent.get(mk) != i:
            row['holes'][key] = {'error': 'mark punch_%d missing or not a child of the plate' % k}; res['ok'] = False; continue
        t = gl2bl(nodes[mk].get('translation', [0, 0, 0]))
        dev = math.hypot(t[0] * 1000 - ex[0], t[1] * 1000 - ex[1])
        # and the hole itself: the rim vertices nearest the expected centre should be the hole radius away
        rr = sorted(math.hypot(p[0] * 1000 - ex[0], p[1] * 1000 - ex[1]) for p in P)[:12]
        row['holes'][key] = {'mark_xy_mm': [round(t[0] * 1000, 2), round(t[1] * 1000, 2)], 'expected_xy_mm': list(ex), 'mark_dev_mm': round(dev, 3),
                             'nearest_rim_mm': round(rr[0], 2), 'expected_radius_mm': H[key]['d'] / 2, 'ok': dev <= 0.2 and abs(rr[0] - H[key]['d'] / 2) <= 0.2}
        res['ok'] = res['ok'] and row['holes'][key]['ok']
    # the outline's sharp corners are rounded to r 2.0, which takes up to 0.4 off an extreme
    row['ok'] = row['bounds_dev_mm'] <= 0.5 and all(h.get('ok') for h in row['holes'].values())
    res['ok'] = res['ok'] and row['ok']
    res['plates'][side] = row
i = by.get('materials_strap_bent')
if i is not None:
    P = [gl2bl(p) for p in positions(i)]
    lo = [min(p[k] for p in P) * 1000 for k in range(3)]; hi = [max(p[k] for p in P) * 1000 for k in range(3)]
    path = ifc['strap']['inner_face_path_G_us']
    # strap frame = G: x = U, y = S, z = P +Y; its outer face is 2.0 outside the inner path
    exp = {'u': [min(u for u, s in path) - 2.0, max(u for u, s in path) + 2.0], 's': [min(s for u, s in path) - 2.0, max(s for u, s in path)], 'y': [-8.5, 8.5]}
    res['strap'] = {'node': 'materials_strap_bent', 'bounds_mm': [[round(x, 2) for x in lo], [round(x, 2) for x in hi]],
                    'expected_about_mm': exp,
                    'dev_mm': round(max(abs(lo[0] - exp['u'][0]), abs(hi[0] - exp['u'][1]), abs(lo[1] - exp['s'][0]), abs(hi[1] - exp['s'][1]), abs(lo[2] - exp['y'][0]), abs(hi[2] - exp['y'][1])), 2)}
    res['strap']['ok'] = res['strap']['dev_mm'] <= 0.6
    res['ok'] = res['ok'] and res['strap']['ok']
json.dump(res, open(os.path.join(HERE, 'export', 'crosscheck_materials.json'), 'w'), indent=1)
print(json.dumps(res, indent=1))
