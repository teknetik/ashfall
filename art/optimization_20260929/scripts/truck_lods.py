"""Karaveen truck LOD chain (29 Sep 2026) - stage 1.

Produces the shipped LOD0_exact and the source render cache used by later stages.
Its LOD1/LOD2/LOD0_baked meshopt geometry and 6.8k shadow proxy are superseded:
LOD1/LOD2 geometry -> truck_voxel_lods.py, shadow casters -> truck_shadow_proxy.py
(see README "Run order").

Source (read-only): unity/AthenHill/Assets/MeshyImports/Mudrunner Convoy_20260910_162611/
    Meshy_AI_Mudrunner_Convoy_0910152501_texture.fbx  (3,087,121 triangles)

Method
- Render vertices = unique (control point, normal index, UV index) triples, exactly
  as Unity welds them on import, so UV seams / normal splits are explicit.
- LOD0_exact: meshoptimizer quadric edge collapse on render vertices. Collapses only
  onto existing vertices: every vertex keeps its original position, UV0 and normal.
  Seam vertices (same position, different UV) only collapse along the seam, so the
  Meshy atlas maps exactly. The atlas has ~193k UV islands, so this floors near
  ~590k triangles (7.6 mm max error in the scene).
- LOD0_baked / LOD1 / LOD2: position-welded collapse (seams ignored) to the brief's
  triangle targets; new UV0 and baked maps come from truck_bake.py (Blender).
- Shadow proxy: position-welded (UV seams ignored), position-only collapse, auto
  normals (60 deg) because URP's shadow normal bias reads them.
- FBX written by cloning the source file's element tree (same GlobalSettings
  axes/units, Model transform, Material.001 slot, UVMap name) and swapping only
  the Geometry payload.

Run with the scratch venv python (numpy + meshoptimizer) under a memory scope.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import fbxlib  # noqa: E402
import meshtools as mt  # noqa: E402

REPO = "/home/teknetik/code/ao2"
SRC = f"{REPO}/unity/AthenHill/Assets/MeshyImports/Mudrunner Convoy_20260910_162611/Meshy_AI_Mudrunner_Convoy_0910152501_texture.fbx"
OUT = f"{REPO}/art/optimization_20260929/truck"
CACHE = f"{REPO}/art/optimization_20260929/cache"
os.makedirs(OUT, exist_ok=True)
os.makedirs(CACHE, exist_ok=True)

BAKED_TARGETS = {"LOD2": 10_000, "LOD1": 40_000, "LOD0_baked": 160_000}
LOD0_EXACT_REL_ERROR = 1e-3
RAW_TO_WORLD = 6.1975354 * 0.65  # FBX raw units -> scene metres (importer 619.75354 x file 0.01, root scale 0.65)
SHADOW_TARGET = 7_000


def main():
    mt.log("parse source")
    root, version = fbxlib.load(SRC)
    geoms = fbxlib.objects(root, b"Geometry")
    assert len(geoms) == 1
    geom = geoms[0]
    g = fbxlib.read_geometry(geom)
    assert (g["poly_size"] == 3).all(), "source expected to be all triangles"
    cp = g["cp"]
    corner_cp = g["corner_cp"]
    nrec = g["layers"]["LayerElementNormal"][0]["children"]
    urec = g["layers"]["LayerElementUV"][0]["children"]
    assert nrec["MappingInformationType"] == "ByPolygonVertex" and nrec["ReferenceInformationType"] == "IndexToDirect"
    assert urec["MappingInformationType"] == "ByPolygonVertex" and urec["ReferenceInformationType"] == "IndexToDirect"
    nvals = fbxlib.arr(nrec["Normals"], np.float64).reshape(-1, 3)
    nidx = fbxlib.arr(nrec["NormalsIndex"], np.int32).astype(np.int64)
    uvals = fbxlib.arr(urec["UV"], np.float64).reshape(-1, 2)
    uidx = fbxlib.arr(urec["UVIndex"], np.int32).astype(np.int64)

    mt.log("render vertices")
    first, c2rv = mt.render_vertices(mt.pack_keys(corner_cp, nidx, uidx))
    rv_cp = corner_cp[first]
    rv_n = nvals[nidx[first]]
    rv_uv = uvals[uidx[first]]
    tris = c2rv.reshape(-1, 3)
    pos = cp[rv_cp]
    weld = mt.weld_by_position(pos)
    np.savez(f"{CACHE}/truck_source_render.npz", positions=pos.astype(np.float32), normals=rv_n.astype(np.float32),
             uv=rv_uv.astype(np.float32), tris=tris.astype(np.int32))
    mt.log(f"source: {len(tris)} tris, {len(pos)} render verts, {len(cp)} control points, {weld.max()+1} welded")

    report = {"source": SRC, "fbxVersion": version,
              "controlPoints": int(len(cp)), "uniqueNormals": int(len(nvals)), "uniqueUVs": int(len(uvals)),
              "settings": {"bakedTargets": BAKED_TARGETS,
                           "lod0ExactRelError": LOD0_EXACT_REL_ERROR,
                           "shadowTarget": SHADOW_TARGET, "method": "meshoptimizer quadric edge collapse onto existing "
                           "vertices; LOD0_exact on UV-split render vertices (seams preserved), baked LODs and "
                           "shadow proxy on position-welded vertices"}}
    report["sourceMesh"] = mt.mesh_report("source", pos, tris, rv_n, rv_uv, weld)
    mt.log(f"source stats {report['sourceMesh']}")
    mt.dump_json(f"{OUT}/truck-lod-report.json", report)

    # --- LOD0 "exact": seam-preserving collapse on render vertices. UV0, normals and
    # the Meshy material are untouched. The source atlas has ~193k UV islands (130k
    # single-triangle islands), so seam preservation floors near ~550-600k triangles;
    # the error bound keeps the collapse geometrically conservative.
    mt.log("simplify LOD0 exact (seam preserving)")
    lod_tris, err = mt.simplify(tris, pos, 1000, target_error=LOD0_EXACT_REL_ERROR, lock_border=True)
    lod_tris = mt.optimize_order(lod_tris, len(pos))
    rep = mt.mesh_report("LOD0_exact", pos, lod_tris, rv_n, rv_uv, weld)
    rep.update({"resultErrorAbsoluteRaw": err, "resultErrorWorldMm": err * RAW_TO_WORLD * 1000,
                "targetRelError": LOD0_EXACT_REL_ERROR, "uv": "source UV0 exact (seams preserved)",
                "normals": "source normals (vertex subset)"})
    report["LOD0_exact"] = rep
    mt.log(f"LOD0 exact: {rep}")
    rep["fbx"] = write_lod(root, version, geom, "LOD0_exact", pos, rv_cp, cp, rv_n, rv_uv, lod_tris)
    np.savez(f"{CACHE}/truck_LOD0_exact.npz", tris=lod_tris.astype(np.int32))
    mt.dump_json(f"{OUT}/truck-lod-report.json", report)

    # --- rebake LOD geometry: welded positions (UV seams ignored), position-only
    # quadric collapse. New UVs + baked maps are produced in Blender (truck_bake.py).
    wpos_idx = np.zeros(weld.max() + 1, np.int64)
    wpos_idx[weld] = np.arange(len(weld))
    wpos = pos[wpos_idx]
    wnorm = rv_n[wpos_idx]
    wtris = weld[tris]
    keep = (wtris[:, 0] != wtris[:, 1]) & (wtris[:, 1] != wtris[:, 2]) & (wtris[:, 0] != wtris[:, 2])
    wtris = wtris[keep]
    ident_all = np.arange(len(wpos))
    report["weldedSource"] = mt.mesh_report("welded", wpos, wtris, wnorm, None, ident_all)
    for name, target in BAKED_TARGETS.items():
        mt.log(f"simplify {name} -> {target}")
        # Position-only quadrics: measured 5.4 / 17.5 / 49.6 mm (world) max error at
        # 160k / 40k / 10k versus 26 / 120 / 516 mm with a 0.5 normal-attribute weight.
        # Shading detail comes back through the baked normal map.
        prune = False
        lt, err = mt.simplify(wtris, wpos, target, lock_border=True)
        used = np.unique(lt)
        remap = np.full(len(wpos), -1, np.int64)
        remap[used] = np.arange(len(used))
        lp = wpos[used]
        ltr = mt.optimize_order(remap[lt], len(used))
        rep = mt.mesh_report(name, lp, ltr, wnorm[used], None, np.arange(len(lp)))
        rep.update({"resultErrorAbsoluteRaw": err, "resultErrorWorldMm": err * RAW_TO_WORLD * 1000,
                    "prune": prune, "uv": "new UV0 + baked maps (see truck_bake.py)"})
        report[name] = rep
        mt.log(f"{name}: {rep}")
        np.savez(f"{CACHE}/truck_{name}_geometry.npz", positions=lp, tris=ltr.astype(np.int32),
                 source_normals=wnorm[used], error_raw=err)
        mt.dump_json(f"{OUT}/truck-lod-report.json", report)

    # --- shadow proxy: welded, position-only collapse, auto normals
    mt.log("shadow proxy")
    sh_tris, err = mt.simplify(wtris, wpos, SHADOW_TARGET, lock_border=False, prune=False)
    used = np.unique(sh_tris)
    remap = np.full(len(wpos), -1, np.int64)
    remap[used] = np.arange(len(used))
    sp = wpos[used]
    st = remap[sh_tris]
    ident = np.arange(len(sp))
    corner_n = mt.smooth_normals_angle(sp, st, ident, 60.0).reshape(-1, 3)
    corner_uv = rv_uv[wpos_idx[used]][st].reshape(-1, 2)
    rep = mt.mesh_report("ShadowProxy", sp, st, None, None, ident)
    rep["resultErrorAbsoluteRaw"] = err
    rep["resultErrorWorldMm"] = err * RAW_TO_WORLD * 1000
    rep["normals"] = "recomputed, area-weighted, 60 degree split"
    report["ShadowProxy"] = rep
    mt.log(f"shadow: {rep}")
    sh_path = f"{OUT}/KaraveenTruck_ShadowProxy.fbx"
    gw = fbxlib.build_geometry_elem(geom, "KaraveenTruck_ShadowProxy", sp, st.ravel(), np.full(len(st), 3),
                                    normals=corner_n, uv=corner_uv)
    fbxlib.write_surgery(root, version, sh_path, {geom.props[0]: gw},
                         model_renames={"Mesh_0": "KaraveenTruck_ShadowProxy"})
    np.savez(f"{CACHE}/truck_ShadowProxy.npz", positions=sp.astype(np.float32), tris=st.astype(np.int32),
             normals=corner_n.astype(np.float32))
    report["ShadowProxy"]["fbx"] = sh_path
    mt.dump_json(f"{OUT}/truck-lod-report.json", report)
    mt.log("done")


def write_lod(root, version, geom, name, pos, rv_cp, cp, rv_n, rv_uv, lod_tris):
    used_rv = np.unique(lod_tris)
    used_cp, cp_inverse = np.unique(rv_cp[used_rv], return_inverse=True)
    rv_to_newcp = np.full(len(pos), -1, np.int64)
    rv_to_newcp[used_rv] = cp_inverse.ravel()
    corner_cp = rv_to_newcp[lod_tris].ravel()
    normals = rv_n[lod_tris].reshape(-1, 3)
    uv = rv_uv[lod_tris].reshape(-1, 2)
    label = f"KaraveenTruck_{name}"
    gw = fbxlib.build_geometry_elem(geom, label, cp[used_cp], corner_cp, np.full(len(lod_tris), 3),
                                    normals=normals, uv=uv)
    path = f"{OUT}/{label}.fbx"
    fbxlib.write_surgery(root, version, path, {geom.props[0]: gw}, model_renames={"Mesh_0": label})
    mt.log(f"wrote {path} ({os.path.getsize(path)/1e6:.1f} MB)")
    return path


if __name__ == "__main__":
    main()
