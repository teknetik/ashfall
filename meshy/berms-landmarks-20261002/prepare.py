"""Berms landmarks for Unity, Blender 5.2 headless (2 Oct 2026). Run through the capped wrapper:
  ~/.local/state/ward-programme/blender.sh /abs/prepare.py -- <LandmarkId> [...]
then: uv run --with pillow --with numpy python textures.py

Per part (source = the accepted Meshy attempt's model.glb, task ids in record.json):
  * join; turn the minimum-area rectangle of the footprint onto the axes (+ the spec's yaw) so the chosen front faces
    Blender -Y (= Unity +Z through glTF/glTFast); scale uniformly to the spec dimension (no axis stretched); base on
    the ground at the footprint centre; optional tilt (the leaning pylon: rotated about its base centre, then lowered
    until the raised edge of its footing meets the ground, so the low edge is buried) and placement (the fallen tube);
  * LOD0 = the delivered Meshy topology, UVs and normals (transform only);
  * LOD1 / LOD2 = copies welded at UV seams, collapse-decimated to the spec ratios, custom normals cleared and shaded
    smooth by angle;
  * two-sided repair on every LOD (Meshy thin sheets — torn canvas, sand drape, cloth flaps, thin plates — have mixed
    winding, and URP Lit culls back faces and does not flip normals for Cull Off): for each face, rays from just in
    front of / behind it over its two hemispheres (never below the horizon) test whether a viewer outside the object
    can see that side. Seen only from behind -> the face is flipped; seen from both sides -> a flipped copy is added.
    Corner normals are carried over (negated on flipped corners);
  * the embedded maps written out byte for byte: base colour and normal into the Unity folder, metal-rough into
    <src>/maps/ (textures.py turns it into the URP Lit mask);
  * box colliders fitted to the solid masses (see fit_colliders), in Unity axes.
After all parts are placed the landmark is recentred so its footprint centre is the origin. Output:
Art/BermsExpanse/Landmarks/<Id>/ and berms-landmarks.json (sizes, colliders, maps, LOD triangles, provenance).
GLBs come from Blender's own glTF exporter without images (Unity materials reference the extracted maps)."""
import bpy, bmesh, json, math, sys, time
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
sys.path.insert(0, str(Path(__file__).resolve().parent))
from landmark_lib import import_join, coords, tris, min_area_rect, footprint_yaw  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / 'unity/AthenHill/Assets/AthenHill/Art/BermsExpanse/Landmarks'
MANIFEST = OUT / 'berms-landmarks.json'
PREFABS = 'Assets/AthenHill/Prefabs/BermsExpanse/Landmarks/'

# fit: ('len' longest horizontal extent | 'z' height, metres). yaw: extra degrees about Z after the footprint
# alignment. tilt: (Blender axis, degrees) about the base centre. place: Blender (x, y) offset and yaw for the part in
# the landmark. colliders: occupancy bands (see fit_colliders). lods: decimation ratios for LOD1, LOD2.
SPECS = {
    'CaravanHaulerWreck': dict(
        parts=[dict(name='Hauler', src='hauler/a1', yaw=0.0, fit=('len', 10.5))],
        bands=[dict(lo=0.4, hi=2.2, top='contig', cap=4.6)], split_len=6.0, col=dict(cell=0.25, close=True, fill_ok=0.72),
        lods=(0.35, 0.10), smooth_angle=35,
        best_side='+Z (Unity): the broadside with the open lockers, water drums and torn canopy; cab at -X',
        note='Sits level on its axles; spilled crates at the tail (+X end).'),
    'AquiferDerrick': dict(
        parts=[dict(name='Derrick', src='derrick/a1', yaw=0.0, fit=('z', 13.0))],
        bands=[dict(lo=0.6, hi=2.0, top='contig', cap=2.8)], split_len=3.0, col=dict(cell=0.2, close=False, fill_ok=0.65),
        lods=(0.35, 0.10), smooth_angle=35,
        best_side='+Z (Unity): ladder leg on the left, wellhead centred, collapsed hut and solar frame on the right (-X)',
        note='Open lattice: the space between the legs is walkable around the wellhead.'),
    'TubePylonFall': dict(
        parts=[dict(name='Pylon', src='pylon/a1', yaw=0.0, fit=('z', 14.0), tilt=('y', 4.0), sink=0.04,
                    bands=[dict(lo=0.5, hi=1.4, top='band'), dict(lo=1.4, hi=7.0, top='band'),
                           dict(lo=7.0, hi=15.0, top='band')]),
               dict(name='Tube', src='tube/a1', yaw=0.0, fit=('z', 2.75), place=(4.5, 10.5, 65.0), sink=0.0,
                    bands=[dict(lo=0.7, hi=3.0, top='contig', cap=3.0)], col=dict(fill_ok=0.45))],
        split_len=4.5, col=dict(cell=0.25, close=True, fill_ok=0.7), lods=(0.35, 0.10), smooth_angle=35,
        best_side='-X / +X (Unity) broadside: the leaning pylon with the fallen tube running out beside it',
        note='The pylon leans 4 degrees toward the fallen tube; its footing is buried on the low side.'),
}


def U(v):
    """Blender point -> Unity local point (glTF export +Y up, glTFast negates X)."""
    return [round(float(-v[0]), 4), round(float(v[2]), 4), round(float(-v[1]), 4)]


def select_only(ob):
    for o in bpy.context.selected_objects: o.select_set(False)
    ob.select_set(True); bpy.context.view_layer.objects.active = ob


def T(x, y, z):
    return Matrix.Translation((x, y, z))


# ------------------------------------------------------------------ fitting
def fit_part(ob, p):
    me = ob.data
    co = coords(me)
    info = {'source_triangles': tris(me), 'source_bounds': [co.min(0).round(4).tolist(), co.max(0).round(4).tolist()]}
    yaw = footprint_yaw(co) + p.get('yaw', 0.0)
    me.transform(Matrix.Rotation(math.radians(yaw), 4, 'Z'))
    co = coords(me); mn, mx = co.min(0), co.max(0); ext = mx - mn
    axis, metres = p['fit']
    s = metres / (max(ext[0], ext[1]) if axis == 'len' else ext[2])
    me.transform(Matrix.Scale(s, 4) @ T(-(mn[0] + mx[0]) / 2, -(mn[1] + mx[1]) / 2, -mn[2]))
    info.update(align_yaw_deg=round(yaw, 3), scale=round(s, 6), fit=list(p['fit']))
    if p.get('tilt'):
        ax, deg = p['tilt']
        co = coords(me)
        base = co[:, 2] < 0.05                      # the footing's underside before tilting
        me.transform(Matrix.Rotation(math.radians(deg), 4, ax.upper()))
        co = coords(me)
        lift = float(co[base, 2].max())             # the raised edge goes back to the ground, the low edge sinks
        me.transform(T(0, 0, -lift))
        info['tilt'] = {'axis_blender': ax, 'degrees': deg, 'raised_edge_lowered_m': round(lift, 4),
                        'buried_edge_m': round(float(coords(me)[base, 2].min()), 4)}
    if p.get('sink'):
        me.transform(T(0, 0, -p['sink'])); info['sink_m'] = p['sink']
    if p.get('place'):
        px, py, pyaw = p['place']
        me.transform(T(px, py, 0) @ Matrix.Rotation(math.radians(pyaw), 4, 'Z'))
        info['place_blender'] = [px, py, pyaw]
    me.update()
    return info


# ------------------------------------------------------------------ two-sided repair
def fib_dirs(n=96):
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n); th = math.pi * (1 + 5 ** 0.5) * i
    return np.stack([np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)], 1)


def two_side_fix(ob, eps=5e-4, per_side=64):
    """Flip faces only seen from behind; add flipped copies of faces seen from both sides (see module doc)."""
    t0 = time.time()
    me = ob.data
    cn = np.empty(len(me.loops) * 3, np.float32); me.corner_normals.foreach_get('vector', cn); cn = cn.reshape(-1, 3)
    bm = bmesh.new(); bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    lay = bm.loops.layers.float_vector.new('cn_keep')
    k = 0
    for f in bm.faces:
        for l in f.loops:
            l[lay] = Vector(cn[k]); k += 1
    bvh = BVHTree.FromBMesh(bm)
    D = fib_dirs(256)
    D = D[D[:, 2] > -0.05]                          # a viewer never stands below the ground
    flip, dup, both_hidden = [], [], 0
    for f in bm.faces:
        n = np.array(f.normal)
        if not n.any(): continue
        c = f.calc_center_median()
        vis = []
        for sgn in (1.0, -1.0):
            ns = n * sgn
            cand = D[D @ ns > 0.15]
            if len(cand) > per_side: cand = cand[np.linspace(0, len(cand) - 1, per_side).astype(int)]
            o = c + Vector(ns * eps)
            seen = False
            for d in cand:
                if bvh.ray_cast(o, Vector(d))[0] is None: seen = True; break
            vis.append(seen)
        front, back = vis
        if back and not front: flip.append(f)
        elif back and front: dup.append(f)
        elif not front: both_hidden += 1
    new_faces = []
    if dup:
        res = bmesh.ops.duplicate(bm, geom=dup)
        new_faces = [g for g in res['geom'] if isinstance(g, bmesh.types.BMFace)]
    rev = flip + new_faces
    if rev:
        bmesh.ops.reverse_faces(bm, faces=rev)
        for f in rev:
            for l in f.loops: l[lay] = -l[lay]
    bm.to_mesh(me); bm.free()
    attr = me.attributes['cn_keep']
    v = np.empty(len(me.loops) * 3, np.float32); attr.data.foreach_get('vector', v)
    me.attributes.remove(me.attributes['cn_keep'])
    me.normals_split_custom_set(v.reshape(-1, 3).tolist())
    invalid = me.validate(clean_customdata=False)
    me.update()
    return {'faces': len(me.polygons), 'validate_fixed': bool(invalid), 'flipped': len(flip), 'duplicated_two_sided': len(dup), 'hidden_both_sides': both_hidden,
            'seconds': round(time.time() - t0, 1)}


# ------------------------------------------------------------------ LODs
def make_lod(ob, ratio, name, smooth_angle):
    lod = bpy.data.objects.new(name, ob.data.copy()); lod.data.name = name
    bpy.context.scene.collection.objects.link(lod)
    bm = bmesh.new(); bm.from_mesh(lod.data)
    v0 = len(bm.verts)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-4)
    v1 = len(bm.verts)
    bm.to_mesh(lod.data); bm.free()
    select_only(lod)
    try: bpy.ops.mesh.customdata_custom_splitnormals_clear()
    except RuntimeError: pass
    d = lod.modifiers.new('d', 'DECIMATE'); d.ratio = ratio; d.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier='d')
    lod.data.validate(clean_customdata=False)
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(smooth_angle))
    return lod, [v0, v1]


# ------------------------------------------------------------------ maps / export
def save_maps(ob, dst_unity, dst_src, stem):
    out = {}
    m = next(s.material for s in ob.material_slots if s.material and s.material.use_nodes)
    bsdf = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')

    def src_image(sock):
        stack = [l.from_node for l in bsdf.inputs[sock].links]
        while stack:
            n = stack.pop()
            if n.type == 'TEX_IMAGE' and n.image: return n.image
            for inp in n.inputs: stack += [l.from_node for l in inp.links]
        return None
    for key, sock in (('BaseColor', 'Base Color'), ('MetalRough', 'Metallic'), ('Normal', 'Normal')):
        img = src_image(sock)
        if not img or not img.packed_file: raise RuntimeError(f'{stem}: no packed {key} map')
        data = img.packed_file.data
        ext = '.png' if data[:4] == b'\x89PNG' else '.jpg'
        (dst_src / f'source_{key}{ext}').write_bytes(data)
        if key != 'MetalRough':
            (dst_unity / f'{stem}_{key}{ext}').write_bytes(data); out[key] = f'{stem}_{key}{ext}'
        else:
            out['MetalRoughSource'] = str((dst_src / f'source_{key}{ext}').relative_to(ROOT))
        out[key + '_size'] = list(img.size)
    out['Mask'] = f'{stem}_Mask.png'
    m.name = stem
    return out


def export(ob, path):
    select_only(ob)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True, export_yup=True,
                              export_image_format='NONE', export_tangents=True, export_normals=True, export_apply=True,
                              export_materials='EXPORT', export_vertex_color='NONE', export_extras=False)


# ------------------------------------------------------------------ colliders
def surface_points(me, density=0.015, cap=400, seed=7):
    """Points on the surface: every vertex plus area-weighted samples (about one per `density` m^2)."""
    co = coords(me)
    me.calc_loop_triangles()
    lt = np.empty(len(me.loop_triangles) * 3, np.int64); me.loop_triangles.foreach_get('vertices', lt); lt = lt.reshape(-1, 3)
    a, b, c = co[lt[:, 0]], co[lt[:, 1]], co[lt[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    n = np.minimum(np.ceil(area / density).astype(int), cap)
    idx = np.repeat(np.arange(len(lt)), n)
    rng = np.random.default_rng(seed)
    r1, r2 = rng.random(len(idx)), rng.random(len(idx))
    s = np.sqrt(r1)
    p = (1 - s)[:, None] * a[idx] + (s * (1 - r2))[:, None] * b[idx] + (s * r2)[:, None] * c[idx]
    return np.concatenate([co, p])


def grid_fill(occ, close=True):
    """Close 1-cell gaps (dilate, erode; optional) and fill enclosed holes."""
    def shift_or(g):
        o = g.copy()
        o[1:] |= g[:-1]; o[:-1] |= g[1:]; o[:, 1:] |= g[:, :-1]; o[:, :-1] |= g[:, 1:]
        return o

    def shift_and(g):
        o = g.copy()
        o[1:] &= g[:-1]; o[:-1] &= g[1:]; o[:, 1:] &= g[:, :-1]; o[:, :-1] &= g[:, 1:]
        return o
    g = (shift_and(shift_or(occ)) | occ) if close else occ.copy()
    outside = np.zeros_like(g); h, w = g.shape
    stack = [(i, j) for i in range(h) for j in (0, w - 1)] + [(i, j) for j in range(w) for i in (0, h - 1)]
    while stack:
        i, j = stack.pop()
        if i < 0 or j < 0 or i >= h or j >= w or outside[i, j] or g[i, j]: continue
        outside[i, j] = True
        stack += [(i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)]
    return g | ~outside


def components(g):
    lab = np.zeros(g.shape, int); n = 0
    for i, j in zip(*np.nonzero(g)):
        if lab[i, j]: continue
        n += 1; stack = [(i, j)]
        while stack:
            a, b = stack.pop()
            if a < 0 or b < 0 or a >= g.shape[0] or b >= g.shape[1] or lab[a, b] or not g[a, b]: continue
            lab[a, b] = n
            stack += [(a + da, b + db) for da in (-1, 0, 1) for db in (-1, 0, 1) if da or db]
    return lab, n


def fit_colliders(pts, bands, split_len, cell=0.25, close=True, fill_ok=0.7, gap=0.6, shrink=0.05, min_cells=3,
                  min_side=0.15, min_area=0.1):
    """Box colliders for the solid masses. For each band (lo..hi metres above the ground) the points in that band are
    rasterised on a `cell` grid (optionally closed across one-cell gaps; enclosed holes filled) and split into connected
    masses. Each mass gets an oriented minimum-area box; a mass whose box is under `fill_ok` filled or longer than
    `split_len` is cut in two (guillotine: the cut, along either box axis at the 20-80 % quantiles, that leaves the
    best-filled pair) until its boxes fit. A box runs from below the ground (-0.5 m, for uneven terrain) or the band's
    bottom up to the band top ('band'), or to the top of the geometry stacked continuously above the band's bottom
    inside the box footprint with no vertical gap over `gap` ('contig', capped). Gaps between masses wider than about
    one cell stay open."""
    boxes = []
    x0, y0 = pts[:, 0].min() - cell, pts[:, 1].min() - cell
    jitter = np.array([[-1, -1], [-1, 1], [1, -1], [1, 1]]) * cell * 0.5

    def rect(cells):
        cxy = (cells + 0.5) * cell + [x0, y0]
        deg, c, ext = min_area_rect((cxy[:, None, :] + jitter[None]).reshape(-1, 2), step=1.0)
        return deg, c, ext, len(cells) * cell * cell / max(ext[0] * ext[1], 1e-6), cxy

    for bi, band in enumerate(bands):
        sel = pts[(pts[:, 2] >= band['lo']) & (pts[:, 2] <= band['hi'])]
        if not len(sel): continue
        ij = np.floor((sel[:, :2] - [x0, y0]) / cell).astype(int)
        occ = np.zeros(ij.max(0) + 3, bool); occ[ij[:, 0], ij[:, 1]] = True
        g = grid_fill(occ, close)
        lab, n = components(g)

        def fit(cells, depth):
            if len(cells) < min_cells: return
            deg, c, ext, fill, cxy = rect(cells)
            if depth < 6 and len(cells) >= 2 * min_cells and (fill < fill_ok or ext[0] > split_len):
                best = None
                a = math.radians(deg)
                for ax in (np.array([math.cos(a), math.sin(a)]), np.array([-math.sin(a), math.cos(a)])):
                    t = (cxy - c) @ ax
                    for q in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8):
                        cut = np.quantile(t, q)
                        A, B = cells[t <= cut], cells[t > cut]
                        if len(A) < min_cells or len(B) < min_cells: continue
                        fa, fb = rect(A)[3], rect(B)[3]
                        score = (fa * len(A) + fb * len(B)) / len(cells)
                        if best is None or score > best[0]: best = (score, A, B)
                if best and (ext[0] > split_len or best[0] > fill + 0.04):
                    fit(best[1], depth + 1); fit(best[2], depth + 1)
                    return
            a = math.radians(deg); u = np.array([math.cos(a), math.sin(a)]); v = np.array([-math.sin(a), math.cos(a)])
            rel = pts[:, :2] - c
            inside = (np.abs(rel @ u) <= ext[0] / 2) & (np.abs(rel @ v) <= ext[1] / 2)
            zs = pts[inside, 2]
            zin = zs[(zs >= band['lo']) & (zs <= band['hi'])]
            if not len(zin): return
            if band['top'] == 'band':
                top = min(band['hi'], float(zin.max()))
                bottom = -0.5 if bi == 0 else band['lo']
            else:
                # the solid stack: from the lowest geometry under the band's lowest point (ground drape below 5 cm
                # ignored) up through continuous geometry; a mass floating above the ground (a pipe run) keeps its gap
                z0 = float(zin.min())
                below = np.sort(zs[(zs >= 0.05) & (zs < z0)])[::-1]
                for z in below:
                    if z0 - z > gap: break
                    z0 = z
                top = z0
                for z in np.sort(zs[zs >= z0]):
                    if z - top > gap: break
                    top = z
                top = min(top, band.get('cap', 99.0))
                bottom = -0.5 if z0 < 0.5 else z0 - 0.05
            w, d = ext[0] - 2 * shrink, ext[1] - 2 * shrink
            if min(w, d) < min_side or w * d < min_area: return   # slivers: single braces, cable ends, fins
            boxes.append({'center_b': [float(c[0]), float(c[1]), (top + bottom) / 2], 'size_b': [w, d, top - bottom],
                          'angle_b': deg, 'band': bi, 'fill': round(float(fill), 3)})
        for k in range(1, n + 1):
            fit(np.argwhere(lab == k), 0)
    return boxes


def boxes_unity(boxes, name):
    out = []
    for i, b in enumerate(boxes):
        cx, cy, cz = b['center_b']
        w, d, h = b['size_b']
        out.append({'name': f'{name} {i + 1:02d}', 'center': U((cx, cy, cz)), 'size': [round(w, 3), round(h, 3), round(d, 3)],
                    'yaw': round(-b['angle_b'], 2), 'band': b['band'], 'fill': b['fill']})
    return out


# ------------------------------------------------------------------ main
def main():
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    ids = [a for a in args if a in SPECS] or list(SPECS)
    rec = json.loads((HERE / 'record.json').read_text())['models']
    OUT.mkdir(parents=True, exist_ok=True)
    man = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    for lid in ids:
        spec = SPECS[lid]
        bpy.ops.wm.read_factory_settings(use_empty=True)
        dst = OUT / lid; dst.mkdir(parents=True, exist_ok=True)
        parts, objs = [], []
        for p in spec['parts']:
            ob = import_join(HERE / p['src'] / 'model.glb')
            info = fit_part(ob, p)
            stem = f"{lid}_{p['name']}"
            src_maps = HERE / p['src'] / 'maps'; src_maps.mkdir(exist_ok=True)
            maps = save_maps(ob, dst, src_maps, stem)
            ob.name = ob.data.name = stem + '_LOD0'
            objs.append(ob)
            r = rec[p['src'].replace('/', '_')]
            parts.append(dict(name=p['name'], stem=stem, source=f"meshy/berms-landmarks-20261002/{p['src']}/model.glb",
                              task=r['task'], credits=r.get('credits'), request=r['request'], maps=maps, **info))
        # recentre the landmark: footprint centre at the origin (ground stays at z = 0)
        allco = np.concatenate([coords(o.data) for o in objs])
        cx, cy = (allco[:, 0].min() + allco[:, 0].max()) / 2, (allco[:, 1].min() + allco[:, 1].max()) / 2
        for o in objs: o.data.transform(T(-cx, -cy, 0)); o.data.update()
        # colliders from the fitted LOD0 surfaces (per part: its own bands)
        cols = []
        for p, o in zip(spec['parts'], objs):
            pts = surface_points(o.data)
            cols += fit_colliders(pts, p.get('bands', spec.get('bands')), p.get('split_len', spec['split_len']),
                                  **{**spec.get('col', {}), **p.get('col', {})})
        colliders = boxes_unity(cols, 'COL')
        if '--colliders-only' in args:                  # iterate on the collider fit without rebuilding the LODs
            cur = json.loads(MANIFEST.read_text())
            cur[lid]['colliders'] = colliders; MANIFEST.write_text(json.dumps(cur, indent=1))
            print(lid, 'colliders', len(colliders), flush=True)
            continue
        # LODs (from the fitted, unrepaired LOD0), two-sided repair per LOD, export
        for part, o in zip(parts, objs):
            l1, w1 = make_lod(o, spec['lods'][0], part['stem'] + '_LOD1', spec['smooth_angle'])
            l2, w2 = make_lod(o, spec['lods'][1], part['stem'] + '_LOD2', spec['smooth_angle'])
            part['lod_welded_vertices'] = [w1, w2]
            part['two_sided_repair'] = []
            part['lod_triangles'] = []
            part['lods'] = []
            for i, lo in enumerate((o, l1, l2)):
                part['two_sided_repair'].append(two_side_fix(lo))
                part['lod_triangles'].append(tris(lo.data))
                f = f"{part['stem']}_LOD{i}.glb"
                export(lo, dst / f); part['lods'].append(f)
                print(lid, f, part['lod_triangles'][-1], part['two_sided_repair'][-1], flush=True)
        allco = np.concatenate([coords(o.data) for o in objs])
        mn, mx = allco.min(0), allco.max(0)
        size = [round(float(mx[0] - mn[0]), 3), round(float(mx[2] - mn[2]), 3), round(float(mx[1] - mn[1]), 3)]
        man[lid] = {
            'prefab': PREFABS + lid + '.prefab', 'size': size,
            'bounds_unity': {'min': U((mx[0], mn[1], mn[2])), 'max': U((mn[0], mx[1], mx[2]))},
            'footprint_xz': [size[0], size[2]], 'ground_y': 0.0,
            'parts': parts, 'colliders': colliders, 'lod_ratios': list(spec['lods']),
            'best_side': spec['best_side'], 'note': spec['note'],
            'recentre_blender_xy': [round(float(cx), 4), round(float(cy), 4)],
            'prepared': time.strftime('%Y-%m-%dT%H:%M:%S'),
        }
        cur = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}   # merge: other landmarks may run at once
        cur[lid] = man[lid]
        MANIFEST.write_text(json.dumps(cur, indent=1))
        print(lid, 'size', size, 'colliders', len(colliders), flush=True)


if __name__ == '__main__':
    main()
