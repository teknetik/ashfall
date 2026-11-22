# SimReady Central Asset Library — Local Blender 5.2 Pipeline (22 November 2026)

This folder (`art/simready_assets_20261122`) contains **72 curated, metric, PBR-ready 3D assets** pulled from [NVIDIA-Omniverse/simready-central](https://github.com/NVIDIA-Omniverse/simready-central) and processed through our local headless **Blender 5.2.2 LTS** pipeline so Claude (or any agent) can cherry-pick assets directly into the Unity game (`unity/AthenHill`).

All 72 packages are verified **CC-BY-4.0** from five public SimReady Central submission indices:
- `submissions/NdotLight/SimReady_Assets` (31 assets)
- `submissions/projectsim/simready-assets` (17 assets)
- `submissions/ForgeCAD/simready-assets` (9 assets)
- `submissions/nvidia/simready-assets` (10 assets)
- `submissions/M-XR/marso-simready` (5 assets)

---

## 1. Where Claude Should Look First

1. **[`catalog.json`](catalog.json)** — Master machine-readable index of all 72 assets. Each record includes:
   - `id`, `title`, `category`, `subcategory`, `description`
   - `lore_fit` — why the asset belongs on Tir / in Ward or the Outer Berms (`lore.md`, `AGENTS.md`).
   - `where_to_use` — concrete target locations, NPCs, shops, or systems in `AthenHill.unity`.
   - `recommended_usage` — whether to use the joined `_LOD0..2.glb` static prop or the multi-node `_parts.glb` assembly.
   - `tags` — searchable tags including Crafting Studio tool/role tags (`tool:vise`, `tool:grinder`, `tool:screwdriver`, `tool:clamp`, `tool:multimeter`, `crafting_studio`, `separable_parts`, `salvage_shop`, `field_supply`, `quantum_tube_dock`, `ward_home`, `berms`).
   - `physical_properties` — exact metric bounding box (`dimensions_m.width_x`, `height_y`, `depth_z` and `dimensions_mm`), `mass_kg`, `rigid_body_count`, USD physics `joints`, and `grasp_points`.
   - `geometry` — `source_triangles`, `parts_glb_triangles`, `lod_triangles` (`LOD0`, `LOD1`, `LOD2`), `part_count`, `is_multi_part`, and full per-node breakdown in `parts` (`node`, `triangles`, `vertices`, `size_mm`, `materials`).
   - `materials` — material names (`SR_<id>_<mat>`) and relative paths to `base_map`, `normal_map`, `gltf_orm_map`, and `unity_urp_mask_map`.
   - `provenance` — dataset, `package_id`, license (`CC-BY-4.0`), author, Wikidata `qcode`, and immutable Hugging Face commit URL.
2. **[`CATALOG.md`](CATALOG.md)** — Quick human- and agent-scannable summary table of all 72 assets.
3. **`assets/<id>/meta.json`** — Individual metadata card inside each asset's own folder.
4. **`review/sheet_*.png`** — Blender Cycles orthographic contact sheets by category, rendered alongside a 1.80 m human scale reference.

---

## 2. Folder Layout per Asset (`assets/<id>/`)

Every asset lives in its own self-contained folder `art/simready_assets_20261122/assets/<id>/`:

```text
art/simready_assets_20261122/
├── README.md                     # This guide
├── CATALOG.md                    # Markdown summary table of all 72 assets
├── catalog.json                  # Master JSON catalog for agent cherry-picking
├── catalog_defs.py               # Curated asset definitions, URLs, and lore/usage annotations
├── fetch_simready.py             # Parallel Hugging Face BOM downloader (resumable, size-verified)
├── build_simready_pipeline.py    # Headless Blender 5.2 USD -> GLB + URP MaskMap + metadata builder
├── review_simready.py            # Headless Blender Cycles contact-sheet renderer
├── review/
│   └── sheet_<category>.png      # Visual contact sheets with 1.80 m hero scale reference
└── assets/
    └── <id>/
        ├── meta.json             # Complete metadata for this asset
        ├── thumbnail.png         # SimReady preview thumbnail
        ├── <id>_LOD0.glb         # Joined static prop LOD0 (<= 30k tris, embedded glTF PBR + AO)
        ├── <id>_LOD1.glb         # Decimated LOD1 (~25% tris)
        ├── <id>_LOD2.glb         # Decimated LOD2 (~8% tris)
        ├── <id>_parts.glb        # Separable sub-meshes preserved as individual nodes (<id>_<part>)
        └── textures/
            ├── SR_<id>_<mat>_BaseMap.png   # sRGB Albedo (capped at 2048px for >=0.75m, 1024px under)
            ├── SR_<id>_<mat>_Normal.png    # OpenGL (+Y) Normal map
            ├── SR_<id>_<mat>_ORM.png       # glTF 2.0 Occlusion (R) / Roughness (G) / Metallic (B)
            └── SR_<id>_<mat>_Mask.png      # Unity URP Lit Mask Map (R=Metallic, G=AO, B=0, A=Smoothness)
```

---

## 3. What the Blender Pipeline Does

1. **USD Stage Inspection (`pxr.Usd`)**:
   - Reads `SimReady_Metadata` from the root USD layer (`mass`, `category`, `qcode`, `author`, `asset_license`, `rigid_body_count`).
   - Traverses the USD hierarchy to record any articulated `UsdPhysics` joints (`RevoluteJoint`, `PrismaticJoint`, `FixedJoint`) and `grasp_identifier` points.
2. **Visual-Only USD Import (`bpy.ops.wm.usd_import`)**:
   - Imports only visible render geometry (`import_render=True`, `import_guide=False`, `import_proxy=False`, `import_visible_only=True`), automatically applying `metersPerUnit` conversion so every asset is in **real-world metres**.
   - Filters out any residual collision/proxy/guide prims.
3. **Metric Grounding & Centering**:
   - Applies world transforms, clears shape keys, centres the XY footprint at `(0, 0)`, and sets the lowest vertex on the ground plane (`Z = 0` in Blender, `Y = 0` in exported glTF/Unity).
4. **Dual GLB Export (`_parts.glb` + `_LOD0..2.glb`)**:
   - **`<id>_parts.glb`**: Keeps every sub-mesh as a separate named node (`<id>_<part>`) so multi-part tools and fixtures (`bench_vise`, `bar_clamp`, `g_clamp`, `angle_grinder`, `utility_knife`, `combination_pliers`, `split_joint_pliers`, `hard_equipment_case`, `red_tool_chest`, `respirator`, `industrial_pipe_valve`, `signal_tower`, etc.) can be pulled straight into **Crafting Studio** (`art/crafting_studio_20261121`) or animated in Unity.
   - **`<id>_LOD0..2.glb`**: Joins the visual parts into a single static prop mesh and generates `LOD0`, `LOD1` (25%), and `LOD2` (8%) via collapse-triangulate decimation.
5. **Dual Material / Texture Output (glTFast & Unity URP Lit)**:
   - Rewires the Blender shader graph to link `Occlusion (R)`, `Roughness (G)`, and `Metallic (B)` cleanly including the `glTF Material Output` occlusion socket, so glTFast imports full PBR + AO directly from the `.glb`.
   - Also writes standalone **Unity URP Lit** textures into `assets/<id>/textures/`, including `*_Mask.png` (`R = Metallic`, `G = Occlusion`, `B = 0`, `A = 1 - Roughness`), matching `art/street_dressing_20260930/prepare_textures.py`.

---

## 4. Re-running or Extending the Pipeline

To add more assets from `NVIDIA-Omniverse/simready-central`, append entries to `catalog_defs.py` and run:

```sh
python3 art/simready_assets_20261122/fetch_simready.py
env -i HOME=$HOME PATH=/usr/bin:/bin /Applications/Blender.app/Contents/MacOS/Blender \
  -b --factory-startup --python-exit-code 1 \
  -P art/simready_assets_20261122/build_simready_pipeline.py
env -i HOME=$HOME PATH=/usr/bin:/bin /Applications/Blender.app/Contents/MacOS/Blender \
  -b --factory-startup --python-exit-code 1 \
  -P art/simready_assets_20261122/review_simready.py
```

When cherry-picking an asset into `unity/AthenHill/Assets/AthenHill/Art/`, remember to add its attribution line from `meta.json` (`provenance.title`, `provenance.author`, `provenance.source_url`, `CC-BY-4.0`) to `unity/AthenHill/Assets/AthenHill/Art/THIRD_PARTY_LICENSES.txt`.
