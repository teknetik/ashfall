# Birch canopy and bed uplights — sources (1 October 2026)

Art-direction review item 11 ("Birch 4b canopy: flat saturated yellow cards") and the section-4 defect on the
courtyard-bed uplights (lens clipped to white ovals, trunks/crowns unlit at night). Unity pass:
`unity/AthenHill/Assets/AthenHill/Editor/BirchCanopyPass.cs`; shader `Shaders/WardCanopy` (**Athen Hill/Ward Canopy**);
assets `Art/BirchCanopy`. Evidence: `unity/evidence/birch-canopy/20261001/`. Not reviewed or accepted by Carl.

## What changes

| Area | Before | After |
| --- | --- | --- |
| `birch 4b` / `birch 3` LOD0–4 meshes | TreesBundleB FBX meshes (leaf cards double-sided, flat card normals, vendor vertex colours unused) | baked copies `Art/BirchCanopy/Meshes/BC_<tree>_<lod>.asset` with identical positions, UVs, submeshes and triangle counts. Vertex colour: **A** crown occlusion (64 sky/ground rays through a 0.3 m leaf-area density grid of LOD0, percentile remap to 0.38–1), **R** season (0 green … 1 turned) per card from exposure, height, 3D noise and a per-card hash, **G** per-card brightness jitter, **B** dry/brown cards (~8 % on 4b, ~4 % on 3). Leaf normals blended 60 % towards crown-volume normals (ellipsoid + blurred density gradient), tangents re-orthogonalised. Bark normals unchanged |
| Materials | vendor URP Lit `leaf y` (yellow `leaf 3 zhel`, tint 1/.895/.703), `leaf`, `bark 1/2/3`; HDRP mask maps read as **metallic 0.17–0.24**; no wind | six materials on **Athen Hill/Ward Canopy** (`BC_Birch4b_Leaf/Bark1/Bark2`, `BC_Birch3_Leaf/Bark2/Bark3`): green `leaf 3` as base, `leaf 3 zhel` as the turned-leaf map blended per card, saturation 1.0 (4b) / 0.95 (3), base colour (.80, .78, .72), smoothness .18 (bark .12), metallic 0, normal .45, crown occlusion on ambient (×1) and direct (×.35), sun transmission .32 + ambient transmission .15 with a 35 % "fill" through the crown, wind 0.10 m (4b) / 0.08 m (3) bending from 3.5→17.5 m / 2.5→12.5 m world height, leaf flutter 0.012 m; bark sways with the crown |
| Renderers | `BatchingStatic` set (scene override) | `BatchingStatic` cleared (wind), Object motion vectors kept; prefab links, LODGroups (cross-fade) and trunk capsules unchanged |
| Bed uplights (2 per bed, `TreeBed_Birch3/4b.prefab`) | 70 / 14 m / 66°–30°, both aimed at the trunk 4.8 m up from 1.3–1.6 m: blown-white streak on the trunk base, upper crown dark | **avenue-side trunk wash** (4b `Tree uplight 42`: 10 / 8 m / 75°–35° at 2.6 m; 3 `Tree uplight 26`: 5.5 / 7 m / 75°–35° at 3.0 m) and **opposite crown beam** (4b `Tree uplight 222`: 45 / 18 m / 46°–16° at 10.5 m; 3 `Tree uplight 206`: 34 / 14 m / 50°–16° at 7 m). Same light objects and positions, still unshadowed, still practical + night-only on the Ward lighting clock |
| Uplight lens | `VH_LampLens` (emission 6, 4.8, 3.3: clipped white ovals) — shared with the hill uplights | `BC_UplightLens` (copy, emission .55, .38, .20) on the clock's emissive list. `VH_LampLens` itself is unchanged (hill ring lenses keep it) |

Triangles are unchanged (birch 4b LOD0–4: 5,496 / 2,959 / 1,645 / 833 / 511; birch 3: 3,422 / 1,744 / 984 / 493 / 300);
draw calls unchanged (same submeshes); light count unchanged (4, no shadows).

## Run order

All Unity steps through `$O/unity.sh <log> AthenHill.Editor.BirchCanopyPass.RunBatch --steps <steps> [--out dir]`
(`$O` = `/home/teknetik/.local/state/ward-programme`; add `-nographics` except for `capture`).

1. Before copying C# into `Assets/`: `python3 ../night_life_20261001/check_compile.py editor staging/BirchCanopyPass.cs`.
2. `survey` → `survey.json` (tree meshes, cards, double-sided pairs, uplights, `VH_LampLens` users, local light budget).
   Scene audit: `AthenHill.Editor.StreetDressingAudit.DumpBatch --out .../audit-before.json -nographics`.
3. `shadercheck` (OpenGL Core compile of every pass of the canopy shader), `build` (materials + lens from
   `canopy-tune.json`, mesh bake → `bake-report.json`; re-run after changing `bake` or `trees` values).
4. `preview` (graphics runs only): the same tree/light/lens values in memory for editor captures before installing.
5. `install` (one time): rollback scene copy, `originals.json` (tree meshes/materials/static flags, bed lights, lens
   slots), then `apply`. `apply` (idempotent): meshes/materials, uplights recomputed from the recorded positions, lens
   slots, lens on the clock, review cameras; saves the bed prefabs and the scene.
6. `verify` → `verify-saved-scene.json` (canopy meshes/shader on every LOD, no static batching, prefab links, trunk
   capsules, uplights on the clock, lens slots, 0 missing materials, chunk fingerprint, cameras).
7. `capture:HOUR:cam+cam` (graphics, ≤ 6 close cameras per run): emulates the light clock (practical lights ×
   strength × distance weight from the camera as viewer, night-only below the threshold, emissive × strength) and
   records a **32-light culling probe** per view (`lightcull-HOUR.json`, see below).
8. `rollback`: restores the vendor meshes/materials/static flags, bed lights and `VH_LampLens` slots, removes the lens
   from the clock and the review cameras (the BC assets stay).

Tuning: edit `canopy-tune.json` → `--steps apply,verify -nographics` (materials, lights, lens) or
`--steps build,apply,verify -nographics` (bake values). `layout_check.py` checks the review camera positions against
the audit (colliders, beds, routes). `crown_stats.py` measures crown colour before/after. `map_trees.py` draws the
area map.

**Rebuild hazards:** `CourtyardTreesPass` *Build assets* or *Retune uplights* rewrite the bed prefabs from
`tree-beds.json` (lens back to `VH_LampLens`, old 70 / 14 m uplights): re-run `BirchCanopyPass --steps apply`.

## Finding: the OpenGL Core visible-light cap

The Linux player runs OpenGL Core, where URP caps the visible lights per camera at **32** (Forward+ counts the main
and fill lights too; `UniversalRenderPipeline.maxVisibleAdditionalLights`, `ShaderConfig.k_MaxVisibleLightCountMobile`).
The saved scene has 140 enabled local lights; the circuit keeps all of them at full strength within 90 m. The probe in
`capture` shows the native culling then keeps the **30 nearest** local lights to the camera and drops the rest: in the
courtyard 68–85 lights are visible and everything beyond ~26–36 m goes dark (e.g. the Vanguard Hall portal lamps and
the street-market lanterns from the birch 4b views). The bed uplights are kept in every bed/crown review view; from wider views
(the hill, cam_courtyard) they can drop out like any other lamp. This is district-wide and outside this pass: options
are Vulkan for the Linux player (256 lights; a graphics-API change, Carl's decision) or a light-budget pass.

## Sources and licences

No new third-party content. Meshes and textures: TreesBundleB (IL.ranch 2020, already in the project; see
`Assets/TreesBundleB/ReadMe.txt`), unmodified (copies only). The shader is a fork of the project's Ward Tree shader
(derived from URP 17.6.0 Lit, Unity Companion License; `UNITY-LICENSE.md` in the shader folder). The bake is computed in C# from the vendor meshes.

## Files

| File | Purpose |
| --- | --- |
| `canopy-tune.json` | every value the pass sets (bake, per-tree season, materials, uplights, lens) |
| `originals.json` | recorded originals (install; used by apply and rollback) |
| `layout_check.py`, `map_trees.py`, `crown_stats.py` | camera placement check, area map, crown colour statistics |
| `staging/` | C# and shader as compile-checked before copying into Assets (git-ignored; the live copies are in Assets) |
| `logs/`, `review/` | Unity logs, maps (git-ignored) |
