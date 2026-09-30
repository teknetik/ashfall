# Rendering optimisation 29 Sep 2026: Karaveen truck LODs and Ward tree shadow proxy / LOD2

The native profile counted about 16M triangles per frame. Two assets caused most of that:
the 3.09M-triangle Meshy truck, which had no LODs and cast shadows, and the 3.75M-triangle hero tree,
whose LOD0 was used out to about 92 m and cast shadows into every cascade. This folder contains
the replacement meshes, textures, review renders and a Unity installer.
**Nothing has been installed in Unity yet, and nothing has been measured in the game yet.**
No source FBX, GLB or Unity asset was modified.

## 30 Sep 2026: FBX files re-exported with Blender's exporter

Unity 6000.6's FBX SDK rejected all seven files from the first delivery ("File is corrupted").
They were written by a custom element-tree writer (`scripts/fbxlib.py`). Nothing was installed,
and the scene is unchanged.

- **Root cause:** a type-code bug in that writer. It wrote each Model's `Shading` property, an FBX
  `'C'` (char/bool) value, through Blender's `encode_bin.add_bool`. That call writes Blender's
  internal code `'B'`, which is not a valid FBX property type.
  - `scripts/fbx_typecode_audit.py` walks the raw records and finds `'B'` in all seven rejected
    files and in neither source.
  - With the mapping fixed (`'C'` → `add_char`), round-tripping a known-good FBX through the same
    writer gives a byte-identical file.
  - Blender's own importer accepts `'B'`, which is why the Blender read-back check did not catch it.
- **What was kept:** the rejected files are in `rejected_customwriter/` as `*.fbx.rejected`.
- **How the shipped files are written now:** all seven are written by Blender 5.2.1's official
  exporter, `bpy.ops.export_scene.fbx`, binary 7.4 (`scripts/reexport_blender.py`). Each mesh is
  rebuilt with an identity object transform from the rejected files' verified payload: raw
  vertices, polygons, per-corner normals (Blender free custom normals, read back within 0.02°), UV0
  `UVMap`, material slot names and the tree's `Col` colours.
- **Export settings.** These reproduce both sources' declared conventions: Y up, Z front, X coord,
  `UnitScaleFactor` 1.0, `OriginalUnitScaleFactor` 1.0, and every mesh node at `Lcl Rotation`
  (-90, 0, 0) and `Lcl Scaling` 100.
  - `axis_forward='-Z'`, `axis_up='Y'`.
  - `apply_unit_scale=True` in a metric scene with `scale_length` 1.
  - `apply_scale_options='FBX_SCALE_NONE'`, `global_scale=1.0`.
  - `bake_space_transform=False`, `use_space_transform=True`.
  - `mesh_smooth_type='OFF'`, `use_tspace=False`, `colors_type='LINEAR'`, `object_types={'MESH'}`.
  - Unity's own `Unity-BlenderToFBX.py` uses `FBX_SCALE_ALL`. That would give `UnitScaleFactor` 100
    and node scale 1, which does not match these sources, so it is not used.
- **One content change:** truck LOD0_exact drops 139 zero-area triangles that referenced a vertex
  twice (invalid polygons). It is now 592,401 triangles. Everything else is identical.
- **Checks, all passing** (`verification.json`, `typecode-audit.json`, `*/reimport-validation.json`):
  1. `verify_fbx.py`, raw file parse:
     - FBX 7400, the same GlobalSettings axes and units as the source, and Model transforms within
       7e-6°.
     - Same parent, material names and UV set name.
     - Payload identical to the rejected files: vertices exactly equal, polygons equal, normals
       within 3e-6°, UVs within 5e-8, colours exact.
  2. `fbx_typecode_audit.py`: only standard FBX type codes, with no length or encoding faults.
  3. `validate_reimport.py`: each new file and its source are imported into fresh Blender scenes with
     identical settings.
     - Every new object's `matrix_world` equals the source's to within 1.2e-7.
     - Truck LOD0_exact vertices coincide with source vertices on 100% of a 40k sample (at most
       0.0003 mm), with normal dot 0.99993 on average.
     - The tree's shadow trunk, shadow branches and LOD2 trunk vertices coincide exactly (at most
       0.003 mm).
     - ShadowNear and ShadowProxy sit their intended 3 mm and 15 mm inside the source.
     - Voxel LOD1 and LOD2 sit within 14 mm and 23 mm of the source at p95.
     - Blender's importer merges duplicate or twin faces on load: for example LOD1 imports as 39,960
       triangles, and the tree shadow branches as 117,633 of 137,934. The FBX files contain every
       face; Unity does not merge them.
  4. No FBX-SDK-based tool is installed (fbx2gltf/FBX2glTF, assimp, FBX Python bindings,
     `com.autodesk.fbx`), and Unity was not run. The first real FBX SDK parse will happen on import.
- **Installer:** no functional change is needed. File names, the one-mesh-per-truck-file rule, the
  tree part names (`*_leaves`, `*_branches`, `*_trunk`) and the material slots are unchanged. The
  missing-asset check now also fails, with a clear message, if an FBX imported with no mesh.
- **Review renders:** made from the rejected files, whose geometry is identical, so they still apply.

## Triangle counts

| Asset / level | Triangles | % of source | Use |
| --- | ---: | ---: | --- |
| Truck source (Meshy) | 3,087,121 | 100 | disabled, kept |
| Truck **LOD0_exact** | 592,401 | 19.2 | visible, < ~17 m, does not cast |
| Truck **ShadowNear** | 159,948 | 5.2 | shadows only, LOD0 range |
| Truck **LOD1** | 40,000 | 1.3 | visible, ~17 to 40 m, does not cast |
| Truck **LOD2** | 10,000 | 0.32 | visible, beyond 40 m (culled at ~800 m), does not cast |
| Truck **ShadowProxy** | 9,122 | 0.30 | shadows only, LOD1 and LOD2 ranges |
| Tree LOD0 (unchanged) | 3,748,776 | 100 | visible, no longer casts |
| Tree LOD1 (unchanged) | 1,845,603 | 49 | visible, no longer casts |
| Tree **ShadowProxy** | 292,440 | 7.8 | shadows only, LOD0 and LOD1 ranges (leaves 140,507 / branches 137,934 / trunk 13,999) |
| Tree **LOD2** | 276,439 | 7.4 | visible and casts, beyond ~63 m (leaves 182,873 / branches 78,566 / trunk 15,000) |

Distances assume the scene's MainCamera at 50° FOV and the PC quality level's `lodBias` of 2
(see "LOD transitions").

## Differences from the brief (honest)

1. **Truck LOD0 is 592k triangles, not 120–200k.** The Meshy UV atlas has 193,093 islands, and
   130,513 of them are single triangles. A collapse that keeps UV0 exact (the brief requires
   `KaraveenTruck.mat` to apply unchanged) cannot go below about 550–600k triangles. The shipped
   LOD0 keeps the source UV0, normals and material, with a maximum quadric error of 7.6 mm at scene
   scale. A 160k rebaked LOD0 was tried and not shipped: after decimation the noisy surface
   unwrapped at only 1–14% UV utilisation.
2. **Truck LOD1 and LOD2 have new UV0 and new baked maps.** They use two new material variants,
   `KaraveenTruck_LOD1.mat` and `KaraveenTruck_LOD2.mat`. These are copies of `KaraveenTruck.mat`
   with the same shader and scalars; only the maps change. Keeping the Meshy UVs is impossible at
   40k and 10k triangles.
3. **The truck has two shadow casters.** A 9k proxy under the LOD0 visual self-shadowed the sunlit
   panels: it sat up to 24 mm outside the surface at p95, and the URP PC cascade-0 bias is only a
   few mm. `ShadowNear` (160k, inset 3 mm) therefore casts in the LOD0 range, and the 9.1k
   `ShadowProxy` (inset 15 mm) casts at 17 m and beyond.
4. **The tree proxy cards are enlarged 1.81×, not "slightly".** Leaf cards are also simplified,
   from about 40 to about 9 triangles each. With that, 25% of cards at 1.81× matches the source
   ground-shadow area within 1.5%. The first version kept 16% of cards whole, used 391k leaf
   triangles, and matched worse.
5. **Tree LOD2 casts its own shadows.** It is the only geometry beyond the LOD1 switch and costs
   0.28M triangles. Leaves cast two-sided, as the source did.
6. **LOD distances are limited by `lodBias` 2.** A 21.5 m tree cannot switch LOD before about
   46 m at 50° FOV. The tree's switches are therefore LOD0→LOD1 at about 47 m (it was about 92 m)
   and LOD1→LOD2 at about 63 m, not 45 m. The installer computes this from the live camera FOV and
   `lodBias` and logs it. The switch distances in the table are estimates, not measurements.

## Methods and settings

The FBX files are written by Blender's official exporter; see the 30 Sep section above for the
settings. The first delivery used an FBX element-tree writer, which Unity rejected.
`verification.json` confirms, for every output, the same FBX version, axes, `UnitScaleFactor`, Model
transform, parent, material names and UV layer as the source, with raw bounds within 1% (tree
branches 0.98%). The installer copies the
source ModelImporter scale settings (truck `globalScale` 619.75354, `useFileScale`). It re-checks each
new mesh's bounds against the source mesh in Unity before it saves the scene; on any failure it throws
before saving.

### Truck

- **LOD0_exact**
  - Uses a meshoptimizer quadric collapse on Unity-style render vertices (control point, normal, UV).
  - 592,401 triangles after the re-export dropped 139 invalid zero-area faces.
  - Vertices are a subset of the source, so every kept vertex has its original position, UV and normal.
  - UV seams collapse only along the seam, so the atlas stays watertight.
  - Relative error 1e-3; borders locked (256 open edges in the source).
- **LOD1 and LOD2 geometry**
  - Voxel remesh (8 mm for LOD1, 20 mm for LOD2, scene scale) followed by Blender collapse decimate.
  - Measured deviation, LOD surface to source surface, p99: LOD1 10.6 mm, LOD2 24 mm.
  - Measured deviation, source surface to LOD surface, p95: LOD1 15 mm, LOD2 56 mm. The maxima of
    about 450 mm come from interior or hidden geometry that the level set drops.
  - Folds above 150°: LOD1 1.5%, LOD2 3.5%. The meshoptimizer versions had 3.9% and 10% and were
    rejected (see Review renders).
  - Normals are smooth with a 60° split.
- **UV0 for LOD1 and LOD2**
  - Blender Smart UV Project at 66°, computed on a Laplacian-smoothed copy so residual folds do not
    split islands.
  - Concave packing with a 4 px margin.
  - UV utilisation: LOD1 29% of 2048², LOD2 39% of 1024².
- **Texture transfer (`truck_transfer.py`)**
  - Closest-point transfer, not a Cycles ray bake.
  - For every texel, it finds the nearest point on the source surface and copies source base colour
    and metallic/smoothness there.
  - The source tangent-space normal (source MikkTSpace frame) is re-expressed in the LOD's
    MikkTSpace frame. Unity rebuilds the same frame with `CalculateMikk` on the imported normals.
  - Dilated 8 px.
  - Closest distance p99: LOD1 12 mm, LOD2 28 mm.
- **Shadow casters**
  - Position-welded collapse, inset along the area-weighted vertex normal, normals recomputed with a
    60° split for URP normal bias.
  - Measured protrusion outside the source surface, p95: ShadowProxy 13.7 mm after its inset; the
    un-inset 160k mesh 3.0 mm, which ShadowNear then insets by a further 3 mm.

### Tree

- **Leaf cards**
  - Cards are the 60,378 connected components of the LOD0 leaf mesh, about 40 triangles each.
  - Stratified selection: the fraction per 0.8 m cell, with at least one card per occupied cell so
    canopy tips survive.
  - Each kept card is simplified by a UV-weighted quadric collapse (UV weight 4, normal 0.25).
    Kept vertices keep their exact UV, so the alpha mask maps exactly there. Card flattening is at
    most 3.9 cm.
  - Each card is scaled about its area centroid by *k*.
- ***k* tuning**
  - *k* is chosen by projecting alpha-tested opaque samples (cutoff 0.35, as in `leaves.mat`) along
    three sun directions (shadow proxy) or three view directions (LOD2). Occupancy is compared on
    3 cm and 10 cm grids.
  - Shadow proxy: 25.9% of cards, about 9 triangles per card, *k* 1.809. Coverage error 1.1%,
    IoU 0.81; the sampling-noise baseline is 0.885.
  - LOD2: 50.5% of cards, about 6 triangles per card, *k* 1.464. Coverage error 0.2%, IoU 0.83;
    baseline 0.89.
- **Wood**
  - Shadow branches and trunk: position-welded collapse to 11% and 12%, keeping source normals.
    Thin twig tubes collapse; branch area drops from 263 to 165 m². Twig shadows are mostly under
    leaf shadow.
  - LOD2 branches: Blender collapse decimate with per-corner UV interpolation. A seam-preserving
    collapse floors at about 300k with slivers because of tiled bark UVs (v up to 598) and open
    twig tubes.
  - LOD2 trunk: seam-preserving collapse; bark UVs are exact.
- **Materials**
  - Material slot names are kept (`jacaranda_tree_leaves`, `jacaranda_tree_branches`,
    `jacaranda_tree_trunk`).
  - The installer takes the materials from the matching `Source LOD 0` renderers by part suffix,
    because the tree FBX imports with `materialImportMode` None.

## Review renders (`review/`, Blender Cycles, CPU only)

All views are 1920×1080 with a 50° vertical FOV (the game camera). Far views also have
native-pixel crops and a 2× nearest-neighbour zoom. Each sheet has an amplified difference panel.
`*-review-metrics.json` holds the mean absolute differences, and
`tree-footprint-metrics.json` the shadow-mask metrics.

### Truck

- **`truck_02m_source_vs_LOD0`:** looks the same (same UVs and material). The remaining difference
  is Cycles noise and denoising (mean abs diff 6.8/255).
- **`truck_08m_*`, `truck_16m_*` (LOD1):**
  - Silhouette, wheels, rails and colours hold.
  - Visible at 2× zoom: the **KARAVEEN logo and small panel markings are softer**, a few window and
    grille recesses bake darker, and small dark patches remain on the rear panel where the voxel
    surface bridges rails. Acceptable from 17 m; not a close-up asset.
- **`truck_30m_*`, `truck_45m_*`:** LOD1 and LOD2 are hard to tell from the source at native pixels.
  LOD2 is slightly softer and loses some thin roof-rack detail.
- **`truck_shadownear_*` (LOD0 visible, ShadowNear casting):** close to the source. The difference
  panel shows small lit and shadowed disagreements under rails and around the rear panel. Cycles has
  no shadow bias, so this is a worst case.
- **`truck_shadowmid_*` (LOD1 visible, 9k proxy casting):** matches except one small self-shadow
  wedge at the right edge of the rear panel. The ground shadow matches.
- **Rejected, kept for the record:**
  - `truck_16m_raybake_rejected.jpg`: a Cycles selected-to-active bake smeared rails onto panels.
  - `truck_16m_meshopt_geometry_rejected.jpg`: position-only collapse webbing shaded as dark wedges.

### Tree

- **`tree_front45_*`, `tree_side45_*`, `tree_hill90_*` (LOD0 vs LOD2):**
  - Silhouette and extent match.
  - At 45 m, **LOD2's canopy is still a little more see-through and the main branch structure reads
    darker and more prominent**; the leaf clumps are coarser.
  - At 90 m from the hill the difference is small (mean abs diff 0.24/255).
  - In game, LOD2 only appears beyond about 63 m.
  - `tree_front45_LOD2v1_rejected.jpg` shows the rejected first version (8% whole cards at 2.6×),
    which was clearly sparser.
- **`tree_under_*` (under the canopy, looking up) and `tree_ground_*` (player height):** the source
  casts all its own shadows; the proxy case has LOD0 visible and only the proxy casting. Canopy
  self-shadowing is slightly lighter and the dapple pattern is a little coarser. The trunk and
  ground shadow shapes match.
- **`tree_foot55_*`, `tree_foot30_*` (top-down ground shadow, sun at 55° and 30°):**
  - Shadow area ratio 0.994 and 0.986.
  - Shadow-mask IoU 0.846 and 0.849 at 3.3 cm/px, and 0.86 at 13 cm/px.
  - The difference is in the fine hole pattern inside the canopy shadow, not in the footprint.

## LOD transitions (set by the installer, logged before and after)

`h = worldSize × lodBias / (2 · d · tan(fov/2))`, clamped to at most 0.98. Each level is at most
75% of the previous one.

| Asset | Before | After |
| --- | --- | --- |
| Truck | no LODGroup | 0.98 (about 16.7 m), 0.41 (40 m), cull 0.0205 (about 800 m) |
| Tree | 0.5 (about 92 m), cull 0.015 | 0.98 (about 47 m), 0.735 (about 63 m), cull 0.015 |

Lowering `lodBias` from 2 to 1 on the PC quality level would halve every LOD distance in the city.
That is a separate decision and is not made here.

## Known compromises and remaining risks

- None of this has been measured in Unity or the native player yet. After installing, run the usual
  warmed traversal (evidence under `unity/evidence/rendering/20260929/`) and check:
  - the frame time;
  - URP self-shadow acne on the truck (cascades 0–1);
  - LOD pops at about 17, 40, 47 and 63 m. CrossFade is on with a 0.12 fade width.
- **Truck LOD1 and LOD2 carry a small texture-memory cost:** a 2k set and a 1k set (3 maps each,
  mip streaming on).
- **Tree:**
  - The proxy leaves use the source `leaves.mat`, so wind stays identical. Enlarged cards sway at
    the same world-space amplitude.
  - LOD0 and LOD1 no longer cast. Their `TwoSided` and `On` casting modes are logged so the change
    can be reverted.
  - The proxy cards are bigger, so dappled ground light near the trunk is coarser than the source.
- **Vertex colours:** the tree outputs keep the source's constant `Col` layer. Tree tangents are
  dropped and recomputed by Unity (`CalculateMikk`); the source imported them.

## Files to copy (destination is under `unity/AthenHill/`)

```
art/optimization_20260929/truck/KaraveenTruck_LOD0_exact.fbx      -> Assets/AthenHill/Art/Optimized/20260929/Truck/
art/optimization_20260929/truck/KaraveenTruck_LOD1.fbx            -> Assets/AthenHill/Art/Optimized/20260929/Truck/
art/optimization_20260929/truck/KaraveenTruck_LOD2.fbx            -> Assets/AthenHill/Art/Optimized/20260929/Truck/
art/optimization_20260929/truck/KaraveenTruck_ShadowNear.fbx      -> Assets/AthenHill/Art/Optimized/20260929/Truck/
art/optimization_20260929/truck/KaraveenTruck_ShadowProxy.fbx     -> Assets/AthenHill/Art/Optimized/20260929/Truck/
art/optimization_20260929/truck/textures/KaraveenTruck_LOD1_BaseColor.png          -> .../Truck/Textures/
art/optimization_20260929/truck/textures/KaraveenTruck_LOD1_Normal.png             -> .../Truck/Textures/
art/optimization_20260929/truck/textures/KaraveenTruck_LOD1_MetallicSmoothness.png -> .../Truck/Textures/
art/optimization_20260929/truck/textures/KaraveenTruck_LOD2_BaseColor.png          -> .../Truck/Textures/
art/optimization_20260929/truck/textures/KaraveenTruck_LOD2_Normal.png             -> .../Truck/Textures/
art/optimization_20260929/truck/textures/KaraveenTruck_LOD2_MetallicSmoothness.png -> .../Truck/Textures/
art/optimization_20260929/tree/WardTree_ShadowProxy.fbx           -> Assets/AthenHill/Art/Optimized/20260929/Tree/
art/optimization_20260929/tree/WardTree_LOD2.fbx                  -> Assets/AthenHill/Art/Optimized/20260929/Tree/
art/optimization_20260929/unity/OptimizedLodInstaller.cs          -> Assets/AthenHill/Editor/
```

`deliverables.sha256` lists checksums for these 14 files. Do not copy anything from
`rejected_customwriter/`: those files are the FBX SDK-rejected first delivery, kept for reference.

Install steps:

1. With the Editor closed (or with the scene saved), copy the files above.
2. Let Unity import them.
3. Run **Athen Hill ▸ Rendering ▸ Install truck and tree LODs**, or in batch mode:
   `Unity -batchmode -projectPath unity/AthenHill -executeMethod AthenHill.Editor.OptimizedLodInstaller.InstallBatch -quit`.

What the installer does:

- It refuses to run if any open scene is dirty or if the install marker
  (`Optimized LODs 20260929`) already exists.
- It configures the importers: same scale as the source, normals imported, `CalculateMikk`
  tangents, no materials. The normal map is imported as `NormalMap`; metallic/smoothness as linear.
- It creates the two truck material variants.
- On the truck, it adds the LODGroup and children under `Karaveen truck/Optimized LODs 20260929`,
  and disables (does not delete) the `Karaveen truck/Visual` renderer.
- On the tree, it switches the LOD0/LOD1 renderers to shadows Off, adds
  `Shadow proxy/{LOD0 range, LOD1 range}` and `Source LOD 2`, and sets the transitions.
- It saves the scene and writes `unity/evidence/rendering/20260929/lod-install.json`.

For rollback, revert the scene file. The assets can stay.

The installer has not been run. It compiles with no errors or warnings against Unity 6000.6.0f1's
managed assemblies and the project's Newtonsoft.Json, using the Editor's bundled Roslyn `csc`
(output went to a scratch directory).

The new FBX files are not covered by `.gitattributes`: LOD0_exact is 22.6 MB and the tree files are
12–15 MB. Add LFS patterns for `Art/Optimized/20260929/**/*.fbx` if they are committed.

## Reproducing (run order)

All work ran in `scripts/`. Python ran in a venv with numpy, scipy, Pillow and meshoptimizer
0.2.30a0; `fbxlib.py` imports Blender 5.2.1's bundled `io_scene_fbx` parser and writer. Blender
ran with `systemd-run --user --scope -p MemoryMax=12G`, one asset per process, with Cycles on CPU
only. Large intermediate caches (about 1.3 GB, in `cache/`) were deleted after review; every script
regenerates them.

- **Truck:**
  1. `truck_lods.py` (source cache + LOD0_exact)
  2. `blender truck_voxel_lods.py` (imports helpers from `truck_decimate_eval.py`)
  3. `blender truck_unwrap.py -- LOD2 LOD1`
  4. `blender truck_tangents.py --` (source tangents)
  5. `truck_transfer.py LOD2 LOD1`
  6. `truck_write_baked.py`
  7. `truck_shadow_proxy.py`
  8. `blender truck_review.py`
  9. `compose_review.py truck`
  10. `truck_proxy_protrusion.py 0` (caster deviation)
- **Tree:**
  1. `tree_extract.py`
  2. `blender tree_lod2_branches.py`
  3. `tree_proxies.py` (wood parts + first-pass leaf tuning)
  4. `tree_lod2_cards.py shadow`
  5. `tree_lod2_cards.py lod2`
  6. `tree_write.py`
  7. `blender tree_review.py`
  8. `compose_review.py tree`
  9. `tree_footprint_metrics.py`
- **FBX export** (30 Sep, replaces the custom writer):
  1. `blender reexport_blender.py -- truck`
  2. `blender reexport_blender.py -- tree`
- **Checks:**
  1. `fbx_typecode_audit.py typecode-audit.json <files>`
  2. `blender validate_reimport.py -- truck`
  3. `blender validate_reimport.py -- tree`
  4. `verify_fbx.py`, which writes `verification.json` (all pass).

Reports: `truck/truck-summary.json` is the final truck record; `truck/truck-lod-report.json` is the
raw log and also holds superseded entries. `tree/tree-lod-report.json` holds all tuning trials; its
final choices are under `shadowLeavesV2`, `lod2LeavesV2` and `final`.
