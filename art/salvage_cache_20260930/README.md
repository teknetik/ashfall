# Salvage cache v1 — field salvage bundle (30 September 2026)

Candidate replacement visual for `Assets/AthenHill/Prefabs/OuterBerms/SalvageCache.prefab` (the drop left at every
feral-droid wreck). Built outside Unity; **not installed** — nothing under `unity/AthenHill/Assets` was touched.
Status: ready for a Unity audition (AGENTS.md §5 step 6). The native-build check has not been done.

## Design

A Warden scavenger's bundle, built from the droid it was taken from. A boxy section of a worker droid's torso housing
is used as a tray. It has the droid palette (sun-faded bone-white paint, rust-orange panels, gunmetal frame), a cracked
sensor-lens socket and a stencilled chevron with "7-42". It holds a servo actuator with an exposed gear ring, a coil of
salvaged copper filament, bent armour-plate fragments, cut cables with brass terminals and a canvas webbing strap.

A sealed **nanite-core canister** is clamped upright in the back-right corner. Its glass column is the rarity glow. The
canister has a painted orange clamp band, a knurled cap with bolts and four guard bars. The nanite fluid fills the
glass to about 85 %, with a meniscus line and a printed graduation scale.

| | |
|---|---|
| Size | 0.500 (X) × 0.476 (depth) × 0.393 m above the pivot; the base sits 12 mm below the pivot so it beds into uneven ground |
| Pivot | Bottom centre at ground contact; +Y up. The front (sensor socket and stencil) faces **Unity +Z**. This follows from the exporter settings (Blender −Y maps to FBX +Z); check it on first import. Orientation does not matter in play, because caches spawn with a random yaw |
| Canister axis | Unity local (−0.148, y, −0.132): the back-right corner seen from the front. Glass visible from y ≈ 0.22 to 0.33 m, top at 0.393 m |
| Scale | Uniform only (Meshy units × 0.26328). The footprint is squarer than the brief's 0.55 × 0.35 m because Meshy produced a square tray, and the axes were not stretched |

## Deliverables (`export/`)

| File | Contents |
|---|---|
| `SalvageCache.fbx` | Binary FBX 7.4 from Blender's own exporter (`export_scene.fbx`, −Z forward / Y up, Apply Transform, FBX_SCALE_ALL). Metres, identity transforms, one UV set, triangulated, tangent space included. |
| `SalvageCache_Body_BaseColor.png` | 2048², sRGB |
| `SalvageCache_Body_Normal.png` | 2048², OpenGL (+Y), linear |
| `SalvageCache_Body_MaskMap.png` | 2048², linear RGBA: **R metallic, G ambient occlusion, B unused, A smoothness** |
| `SalvageCacheVial_BaseColor.png` / `_Normal.png` / `_MaskMap.png` | 2048² canister atlas, shared by the Vial and Core materials; same channel layout |
| `SalvageCacheVial_Emission.png` | 2048², sRGB greyscale emission mask (only the core islands are non-black) |
| `materials.json` | Material → texture map (used by the review script) |

Meshes and triangles (objects are top-level in the FBX; the `_LODn` suffix makes Unity create a LODGroup):

| Object | Tris | Material slots |
|---|---|---|
| `SalvageCache_Body_LOD0` | 61,754 | 0 `MI_SalvageCache_Body` (Meshy body), 1 `MI_SalvageCache_Vial` (canister hardware, 3,600 tris) |
| `SalvageCache_Core_LOD0` | 192 | 0 `MI_SalvageCache_Core` — **the rarity glow** |
| `SalvageCache_Body_LOD1` | 21,612 | Body, Vial (35 % collapse decimation) |
| `SalvageCache_Core_LOD1` | 96 | Core |
| `SalvageCache_Body_LOD2` | 6,175 | Body, Vial (10 %) |
| `SalvageCache_Core_LOD2` | 48 | Core |
| **Totals** | LOD0 61,946 · LOD1 21,708 · LOD2 6,223 | |

`source/salvage_cache_v1.blend` holds the assembled asset, the procedural canister materials used for baking (hidden
collection `authoring_sources`) and the packed bake images. `build-report.json` records the numbers above, the cut and
cleanup counts and the metallic statistics.

## Unity integration (no runtime code change needed)

1. Copy `export/SalvageCache.fbx` and the seven PNGs, for example to `Assets/AthenHill/Art/OuterBerms/SalvageCache/`.
2. **Model import:** Scale Factor 1 with Convert Units on. Bake Axis Conversion is not needed. Import Normals:
   Import; Tangents: Calculate Mikktspace; Generate Colliders **off**; Generate Lightmap UVs off (the cache is
   spawned dynamically); Mesh Compression off. Unity creates a LODGroup on the model root from the `_LOD0/1/2`
   names. On the Materials tab, remap the three imported materials to the project materials from step 4.
3. **Texture import:** set both `_Normal` files to Texture Type *Normal map*. Clear *sRGB* on both `_MaskMap` files.
   BaseColor and Emission stay sRGB. Max size 2048, mip streaming on, aniso 4–8.
4. **Materials** (Universal Render Pipeline/Lit, Metallic workflow, opaque):
   - `MI_SalvageCache_Body`: Base Map = Body_BaseColor; Metallic Map = Body_MaskMap (Smoothness source Metallic
     Alpha, Smoothness slider 1.0); Normal Map = Body_Normal (1.0); Occlusion Map = Body_MaskMap (URP reads G, strength 1).
   - `MI_SalvageCache_Vial`: the same, using the Vial maps. No emission.
   - `MI_SalvageCache_Core`: Vial maps as above, plus **Emission on**: Emission Map = `SalvageCacheVial_Emission`,
     Emission Color HDR (1.5, 1.35, 1.1) (the script's Common default), Global Illumination: None.
5. **Prefab** (`Prefabs/OuterBerms/SalvageCache.prefab`; edit the prefab, do not rerun `GameplayV2Content.BuildPrefabs`):
   - Delete the child **`Salvage bundle`** (the `Salvage/scrap.prefab` instance at 0.36 scale) and the child
     **`Salvage beacon`** (the cylinder with `SalvageBeacon.mat`).
   - Add the model as a child named `Salvage bundle` at local position (0, 0, 0), rotation (0, 0, 0), scale **(1, 1, 1)**.
   - The model must add **no colliders**, because `LootTests.SalvagePrefabsAreWiredForInteraction` asserts none.
     Set Cast Shadows to On for the Body renderers and to **Off** for the three Core renderers, as the old beacon was.
   - LODGroup (Fade Mode None): LOD0 until **8 %** screen height (about 5.4 m at 60° vertical FOV), LOD1 until **3 %**
     (about 14 m), LOD2 until **0.4 %** (about 100 m), then culled. The glow light and motes keep marking caches beyond that.
   - `SalvageCache` component → **Glow Renderers** = size 3: the MeshRenderers of `SalvageCache_Core_LOD0`,
     `_LOD1` and `_LOD2`. `Refresh()` writes the rarity colour into `_EmissionColor` of those renderers through a
     MaterialPropertyBlock. This works because the Core material has `_EMISSION` enabled. The Body and Vial slots are
     never tinted.
   - Keep `Glow light` (0, 0.7, 0) and `Motes` as they are. Optional: move `Motes` to (−0.148, 0.40, −0.132) with
     shape radius 0.05 so the motes rise from the canister.
6. Verify: EditMode tests `LootTests` and `GameplayV2SceneTests`. Then, in the native Linux player, kill a droid in the
   Outer Berms and check that the cache seats on sloped ground, that Common, Uncommon and Rare read in sun and in
   shade, that the LOD transitions are clean, and the draw/triangle cost.

The Core renderers carry a MaterialPropertyBlock and leave the SRP Batcher, as the old beacon did. The Body renderers
stay batchable.

## Provenance

- **Concepts** (`concepts/`): the OpenAI Images API returned HTTP 429 `credit_balance_exhausted`, so no OpenAI
  image was produced. `scripts/gen_concept.py` is kept for when the credit is restored. The concepts were made with
  Meshy's image endpoints instead (`scripts/meshy_image.py`; routine Meshy generation, pre-approved in AGENTS.md §5).
  Prompts, task IDs and credits are in `meshy/image-tasks.json`.
  - `hero_v1.png`: text-to-image, gpt-image-2, task `01a0ef9c-0474-778e-bfad-92252dc297ed`, 9 credits.
  - `views_v1_0..2.png`: image-to-image multi-view, nano-banana-pro, `01a0ef9d-6abb-76f4-9096-0dac9ca9bb84`, 9 credits.
    The gpt-image-2 attempt `01a0ef9c-cb50-7461-9ced-177b74cb0caa` was refused by the provider and cost 0 credits.
  - `view_front.png` `01a0ef9e-4118-76fc-8007-668be60fd20f`, `view_right.png` `01a0ef9f-1bd0-7542-bce9-798076d668e9`,
    `view_back.png` `01a0ef9f-f680-702f-ac39-6d9f684a116e`: nano-banana-pro, 9 credits each. `view_back` came out as a
    duplicate of the right-hand view and was not used.
- **3D** (`meshy/run_a/`): Multi-Image to 3D task `01a0efa1-30ea-763c-ab0b-6eb25915cca5`, 35 credits. Inputs:
  view_front, hero_v1, view_right, views_v1_2. Options: ai_model latest, geometry_resolution 2k, triangle remesh at
  60,000, PBR, 4k textures, remove_lighting, save_pre_remeshed_model. The client is `scripts/meshy_multi3d.py`, which
  reuses `unity/tools/create_meshy_prop.py`. `model.glb` (60,963 tris), `pre_remeshed.glb`, the 4k base/normal maps,
  the 2k metallic/roughness maps and the thumbnails are the unmodified outputs.
- **Credits:** 80 Meshy credits in total (balance 1495 → 1415). No OpenAI usage.
- **Review ground:** Poly Haven `dry_ground_rocks` (CC0), from `art/west_gate_20260926/polyhaven`.

## Processing (`scripts/`)

- `inspect_meshy.py` checks the raw output before any cleanup: stats plus textured and clay turnarounds in
  `review/inspect_run_a/`. The mesh is one connected shell. There was one 4-face floater. About 294 boundary edges
  are 1–5-edge slits, not openings, and none is visible.
- `build_cache.py` does the rest:
  - Welds the glTF seam splits. Meshy's normal splits are kept as sharp edges, so its normal map still matches.
  - Removes the floater, then normalises the model: uniform scale, bottom-centre pivot, 12 mm sink.
  - Cuts out Meshy's fused, lumpy canister (2,539 faces plus a 263-face leftover fragment).
  - Inserts the authored canister (`vial.py`, lathe profiles in metres).
  - Bakes the canister's procedural materials with Cycles on the CPU: bevelled-edge normals, knurling, edge wear,
    dust in cavities, rust, grime streaks, the painted band, the nanite emission mask and AO.
  - Bakes a 2k AO map for the body.
  - Converts the Meshy 4k maps to 2k with a linear-light box filter and renormalised normals.
  - Cleans the metallic map (mean 0.25 → 0.10). Orange and cream paint, canvas and rubber are no longer metallic;
    copper and bare steel stay metallic.
  - Collapse-decimates LOD1 and LOD2 and exports.
- `review_render.py` re-imports the exported FBX and PNGs as URP-Lit-like materials, so the deliverable is what gets
  reviewed. It renders on uneven displaced ground next to a 1.8 m mannequin and a 1 m ruler (10 cm bands). Cycles
  runs on the CPU at 64 samples with OIDN, using AgX. Lighting is a warm sun at 38° elevation plus sky, and shade
  comes from an occluder that is hidden from the camera. There is no bloom, so these renders are the conservative
  case for how visible the glow is.

Every Blender process ran as `systemd-run --user --scope -p MemoryMax=10G -p MemoryHigh=8G blender -b --factory-startup`,
one at a time, on the CPU only.

## Review (`review/`)

Renders are in `review/v3/`, with contact sheets in `review/`: `distance_sheet.png` (1, 4 and 12 m, sun on top,
shade below), `rarity_sheet.png` (Common, Uncommon, Rare at 2.6 m, sun and shade), `turntable_sheet.png`,
`lod_sheet.png` (LOD0/1/2 at 1.8 m and 8 m) and `clay_canister_sheet.png` (checks the canister cut without texture).
The raw Meshy checks are in `review/inspect_run_a/`.

The scores below follow AGENTS.md §7. They are offline Cycles renders, not native Unity captures.

- **Silhouette and readability, 4/5.** The tall glowing canister and the open tray read clearly at 4 m and 12 m. The
  cache is recognisable next to the 1.8 m marker. Uncommon cyan reads at every distance. In direct sun, Common (warm
  white) and Rare (amber) differ only moderately because there is no bloom; in shade all three are distinct.
- **Material detail at 1 m, 3.5/5.**
  - Good: the Meshy paint wear, chipped cream and orange panels, the gunmetal servo, the copper coil and the canvas
    strap all hold up at player height. The authored canister is crisp (bevelled edges, bolts, painted band, nanite
    swirl, meniscus).
  - Weak: Meshy detail is soft at 1 m. The cable bundle and the plate interiors are fused and blobby in clay. The
    "7-42" stencil is generated, not authored lettering. The canister's procedural steel is slightly cleaner and
    more CG-looking than the photographic Meshy texture beside it.
- **Scale and grounding, 4/5.** Metric and uniform. The 12 mm sink beds the base plate into the displaced ground with
  no visible floating. The footprint (0.50 × 0.48 m) is squarer and bulkier than the brief's 0.55 × 0.35 m.
- **LODs, 4/5.** LOD1 cannot be told apart at 1.8 m. LOD2 softens the plate fragments at 1.8 m and is identical at 8 m.
- **Geometry, 4/5 at the intended views.**
  - No floaters, holes or warped panels are visible. The canister cut is clean from every angle in clay.
  - About 290 tiny non-manifold slits remain from Meshy; none is visible.
  - LOD0 carries hidden interior faces from the Meshy shell.
- **Not yet verified:** the native Unity render, bloom and exposure, mip and aniso behaviour, cost with several
  caches on screen, and the real ground snapping on slopes.

### Remaining defects and next steps

1. Check the glow in the native build. If Common and Rare are too close in sunlight, raise the serialized
   `commonGlow`/`rareGlow` values on the prefab (for example Rare (3.2, 1.2, 0.15)). This needs no code change.
2. If the 1 m close-up is judged too soft, re-texture the body with Meshy at a higher resolution, or hand-author the
   stencil and a detail normal. The geometry is acceptable.
3. Consider a 0.9× uniform scale in the prefab if the cache reads too bulky beside the droid wrecks.
