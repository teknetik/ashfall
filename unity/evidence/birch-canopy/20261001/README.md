# Birch canopy and bed uplights — evidence (1 October 2026)

Pass: `Assets/AthenHill/Editor/BirchCanopyPass.cs`, shader `Shaders/WardCanopy`, sources and run order
`art/birch_canopy_20261001/README.md`. Working tree of branch `ward/next-level` on top of `3ebd801b`, with the other
1 Oct passes uncommitted. Not reviewed or accepted by Carl. Per the revised definition of done no player build, native
lookbook, A/B profile or city loop was run for this pass: frame time, the native night look and the moving/TAA
behaviour are for the orchestrator's combined batch-3 test.

## Installed state (saved scene, `verify-saved-scene.json`: 0 problems)

- `birch 4b`, `birch 3`: all five LOD renderers on baked copies `Art/BirchCanopy/Meshes/BC_*` (same triangles:
  4b 5,496 / 2,959 / 1,645 / 833 / 511, 3: 3,422 / 1,744 / 984 / 493 / 300) and six **Athen Hill/Ward Canopy** materials;
  prefab links to `TreesBundleB/Prefab/universal/birch/*.prefab`, LODGroups and trunk capsules intact; static batching
  cleared on the LOD renderers (wind). Bake statistics: `bake-report.json` (LOD0 4b: 1,640 cards, season mean 0.58,
  p10–p90 0.29–0.86, 130 dry cards, crown occlusion p10/median/p90 0.37/0.70/0.92).
- Bed uplights (same four light objects, practical + night-only on the clock): trunk wash + crown beam per bed (values in
  the art README and `apply.json`). Lens slots → `BC_UplightLens` (4 renderers), on the clock's emissive list;
  `VH_LampLens` untouched.
- Review cameras (scene root *Birch canopy review cameras*, disabled, player height 1.62 m): **cam_bc_4b_crown**,
  **cam_bc_4b_under**, **cam_bc_4b_bed**, **cam_bc_3_crown**, **cam_bc_3_bed** (13:00 for the crowns, 20:30 for the beds
  and `under`). Placement check: `art/birch_canopy_20261001/layout_check.py` → 0 problems (clear of colliders, beds
  and routes). Nothing else was placed or moved; chunk fingerprint matches.
- Rollback: `--steps rollback` (uses `art/birch_canopy_20261001/originals.json`), or the scene copy
  `rollback/before-birch-canopy.unity`.

## Captures (editor, OpenGL Core, 1920×1080, the light clock emulated with the camera as viewer)

| Folder | What |
| --- | --- |
| `editor-before/` | before the pass: 4b/3 crowns at 13:00, beds at 20:30, light-cull probes |
| `editor-r1`–`r3/` | in-memory iterations (r1 first bake; r2 transmission fill and warmer leaves; r3 split uplight roles, dim lens) |
| `editor-after/` | installed state from the saved scene (`sheet.jpg` contact sheet) |
| `crown-before-after.jpg` | cam_bc_4b_crown 13:00 crop, before / after |

Crown colour (`crown-colour-stats.json`, cam_bc_4b_crown 13:00, non-sky crown pixels): mean HSV saturation 0.71 →
0.52 (**−28 %**), HSV value −5 %, median hue 31° → 35° (orange → yellow-green), hue spread 3.7° → 6.1°. Rec.709
luminance +7 % (yellow-green is more luminous than orange at equal value), p90 unchanged. A darker variant (base colour
.70: value −12 %) read as a dead olive tree and was rejected.

## Uplight finding: the 32-light cap (`lightcull-*.json` in each capture folder)

URP on OpenGL Core keeps at most 32 visible lights per camera (main + fill + 30 local). The probe culls each review
view twice (unlimited and 32): 68–85 local lights are visible in the courtyard views and the kept set is exactly the
30 nearest to the camera (kept ≤ 26.0–35.6 m, dropped ≥ 26.1–35.9 m). The bed uplights are kept in all bed and crown
views (a test with *Important* render mode was inconclusive: they were already kept). The 30 Sep "trunks unlit at
20:30–21:00" frames are not reproduced from the bed cameras in the current scene; what was wrong there now is the blown trunk base and the
clipped lens, both fixed. From farther away (hill, wide courtyard views) the uplights — and the Vanguard Hall portal
lamps, the market lanterns etc. — are dropped by this cap. District-wide; reported to the orchestrator.

## Known remaining defects

- Value is only slightly lower (see above); if the crown still competes with the Hill Tree in the native cam_hill
  frame, lower `materials.leaf._BaseColor` in `canopy-tune.json` (`apply`, no rebake).
- Night: only the lower crown near the trunk is warm-lit; the outer crown reads pale grey-green under the moon.
- Vendor leaf normal map shows faint vein stripes at grazing angles (normal strength .45); crossed branch-stub cards in
  birch 4b are visible from directly below (vendor geometry, unchanged).
- Wind and TAA behaviour of the moving leaves not reviewed in motion (editor stills only); LOD cross-fade colour
  continuity not checked in motion.
- Hill ring uplight lenses still use `VH_LampLens` (emission 6, the value that clipped on the beds); not checked here —
  shared material outside this pass.
- `CourtyardTreesPass` *Build assets* / *Retune uplights* revert the bed lights and lens: re-run `apply`.
