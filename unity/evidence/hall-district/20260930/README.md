# Hall district pass: hall weathering, five stone shops, sign family, battle grime (30 Sep 2026)

Carl's requests (30 Sep 2026) and sources: `art/hall_district_20260930/README.md`. **Status: installed, built and natively
verified for the checks below. Not visually accepted by Carl yet; no GTA6-level claim.** Nothing committed.

## What changed

1. **Vanguard Hall weak spots.** The hall script now uses the shared kit `art/ward_masonry_kit`: ray-traced vertex sky
   occlusion (reveals, soffits, portal and ground line darken; open faces don't), per-block tint spread and broad drift,
   cushioned faces with real bevelled and eroded arrises (the committed hall had no bevels on block beds and its
   dressed-margin geometry was never built), chips and spalls, deeper mortar. **Athen Hill/Masonry Lit** gained runoff
   streaks from a world-space streak map, mineral deposits, rust trails under steel, worn/dirty arrises, dust on
   upward faces, and (step 5) old battle damage. Runoff sources: entablature, walls under the soffit, string course,
   coping, sills, scuppers, corbels, brackets, lamps, nameplate. Hall LOD0 85,094 → 149,908 triangles, LOD1 41,976;
   LOD0 now to 40 % screen height (was 26 %). Menu: *Athen Hill → Vanguard Hall → Apply weathering pass*.
2. **Five neighbouring shops rebuilt in stone** (Relay Works, Air + Water, Tool Exchange, Finery, Field Supply): scene
   group **Ward shops (hall district)**, prefabs `Prefabs/WardShops`, LODGroups (LOD0 55–74k, LOD1 13–17k triangles),
   box colliders with walkable 0.4 m door recesses, 3 wall lamps each (15 lamps + the Tool Exchange display light, all
   on the Ward lighting clock; lamps practical + night-only). 667 old objects retired (inactive, not deleted; list in
   `shops-install.json`): the retrofit shop groups, Meshy salvage shells, porch/step renderers (their colliders kept),
   the old Tool Exchange display, Finery's Phase 1 frontage and courtyard/reference-street canopies, parcel decals and
   wall-mounted dressing. The combined *Ward district retrofit / Shop retrofits* meshes now point at filtered copies
   (`Art/WardShops/Retrofit/*`; originals untouched in `WardRetrofit.glb`), 81,374 triangles removed inside the parcels.
   The accepted 29 Sep Air + Water filter bank stays (its vessels/anchors kept active as prefab-instance overrides).
3. **Signs**: new family (`Prefabs/WardShops/Signs`), one per shop plus **Basic General sign (hall district family)** at
   Carl's sign's position; his baked Meshy plate (*Basic General neon sign*) is inactive, not deleted.
   Sign letters/OPEN/cyan are emissive materials on the light clock.
4. **Tool Exchange sci-fi**: glazed display alcove in dark steel with cyan LED strips and five Meshy props (nanofab bench,
   powered tool wall, servo arm, drone, plasma cutter; 150 Meshy credits, `meshy/tool-exchange-scifi-20260930`).
5. **Battle grime** (Carl: "this place saw a battle take place long ago", West Gate as the look): baked impact clusters
   (UV2.y) drive dense pitting, shrapnel scars with dark scorched rims, hairline cracks; soot plumes above chosen
   openings; heavier wall-foot dirt up to ~2.3 m; darker grime-packed joints and arrises; deeper spalls. Applied to the hall
   and the shops (shared material VH_Ashlar etc.).

## Identity

- Baseline: HEAD `fe7f350d` (hall rebuild), clean tree; scene sha256 `38f604b0…d9e3` (`before-shops-scene-sha256.txt`);
  baseline player snapshot `/home/teknetik/code/_snapshots_20260930/hall-district-before-LinuxDevelopment` (11:22 build).
- Final scene sha256 `8ff809bd…0cb2` (`after-scene-sha256.txt`). Rollback copy: `rollback/before-shops-install.unity`.
- Builds: development `build-dev-3.json` (Succeeded, 0 errors, 346 warnings, all 192 Masonry Lit ForwardLit variants
  compiled), release `build-release.json` (Succeeded, 0 errors, 346 warnings). `build-dev-2` had 1 error: the shader
  compiler (FXC) crashed on one Masonry Lit variant under memory pressure; the crack function was simplified and
  rebuilt (dev-3).

## Native results (RTX 3060 12 GB / i9-10850K, OpenGL Core, 1920×1080 window, High preset, render scale 1)

- **Real-input city loop** (`cityloop-native/city-loop.json`, `check_hall_district_city_loop.py`), everything walked with
  real W presses from West Gate: Vex (prompt, E → Dialogue, movement blocked 0.0 m, choice, Escape), Torr at the mission
  slab, Field Supply porch and **into its door recess**, Linn on the hill, Mira at Basic General → Shop, **bought a water
  flask (25 → 21 cr, flask +1) and sold a scrap coil (21 → 22 cr, scrap −1)**, then the Tool Exchange porch/display and
  **door recess**, the Air + Water **door recess**, the Relay Works porch by the shutter, the hall front step and terrace,
  the Lattice step and pad: **E → Grid, link ready, node0 → linked to Crosswind Reach**. All 37 legs reached with correct
  heights (porches 0.53, steps 0.28), 4/4 conversations, flask/scrap/link objectives set. Player.log: 0 exception lines.
- **Matched lookbook** (`before-native/` baseline build vs `after-native/` final build; 27 cameras × 12:00, 17:00, 20:30,
  including the nine hall review cameras and audit/district views of each shop; sheets in `comparison/*.jpg`,
  `comparison/_sheet-a.jpg`, `_sheet-b.jpg`, `_basic-general-sign.jpg`). Night lookbook views keep the player at West
  Gate, so lamps > 42 m away are culled: night is judged on foot.
- **First-person stills on foot** (`cityloop-native/fp_*-h20.50.png`, `-h17.00.png`; sheets `fp-stills-h20.50.jpg`,
  `fp-stills-h17.00.jpg`): west row, east row, hall from the plaza, Tool Exchange display, Basic General sign, Air + Water door.
- **Frame cost at cam_salvage_hall** (6 s uncapped dwell; host load 5.8–6.9 before, 10.9–16.4 after because other sessions
  were busy, so read as local and noisy):

  | Hour | Before fps / p50 / p99 ms / SetPass | After fps / p50 / p99 ms / SetPass |
  | --- | --- | --- |
  | 12:00 | 167.6 / 5.94 / 7.67 / 156 | 151.8 / 6.51 / 7.92 / 166 |
  | 17:00 | 110.6 / 9.02 / 10.61 / 200 | 118.8 / 8.37 / 9.93 / 206 |
  | 20:30 | 179.4 / 4.90 / 12.02 / 178 | 207.9 / 4.68 / 7.14 / 188 |

  Inside the 16.67 ms target. Not measured: a moving traversal profile, GPU time (unavailable in this player), VRAM.
- **Release smoke** (`release-native/`): launched, non-blank render, real keys, no exception lines, no QA bridge output.

## Visual review (my scoring against the street concept and Carl's notes; not acceptance)

| Category | Score | Notes |
| --- | --- | --- |
| Hall: shade and edges | 4 | Shaded faces now carry occlusion gradients, tint spread, cushioned faces and broken arrises; close-ups show chips. |
| Hall: runoff and grime | 3.5–4 | Streaks under sills/cornice/scuppers and rust under steel read at street distance; impact clusters and soot give history. |
| Shops: construction | 4 | Quoins, deep reveals, lintels/flat arches, cornices, parapets, real door recesses; each shop has its own silhouette. |
| Shops: storytelling | 3.5 | Relay mast, Air + Water tank and filters, Finery awning/shutters, Field Supply canopy; skyline has less cyan tech than the old retrofit. |
| Tool Exchange sci-fi | 3.5 | Lit steel alcove, cyan strips and fabrication kit read as tech at night; the stone shell itself is not sci-fi. |
| Signs | 3.5–4 | Legible day and night, physical box and letters; plainer than Carl's circuit-detailed Meshy sign (his call). |
| Night lighting | 4 | Warm pools on stone at every door, amber signs, lit display; lamps follow the clock. |

## Remaining defects and limits

1. Street paving and porch tops are much cleaner than the walls; no battle debris/scorch decals on the ground yet.
2. Steel doors, shutters and sign boxes use plain URP Lit: no scars or grime beyond their textures.
3. Pits, scars and cracks are shader detail: at under ~1 m they read as flat albedo/normal marks, not missing stone.
4. The old retrofit's cyan blade signs and some rooftop clutter left with the retired shells; the skyline is quieter.
5. Tool Exchange: the display glass has a heavy central mullion; props were inspected only through the glass.
6. Porches keep their original 0.5 m ledge with one central step (unchanged colliders); shops remain closed (no interiors).
7. Signs, filter bank and Meshy props have no LODs of their own (small; culled by the shop/sign LODGroups at 1–1.2 %).
8. Frame cost measured at one view only; no moving-traversal profile or memory measurement in this pass.
9. Concepts (`art/hall_district_20260930/concept`) were not shown to Carl before building; they are targets, not acceptance.

## Rollback

Restore `rollback/before-shops-install.unity` over `Assets/AthenHill/Scenes/AthenHill.unity` (the install pass's own copy,
sha `38f604b0…`, the scene committed in `fe7f350d`). For the hall weathering alone, restore `art/vanguard_hall_20260930/author_vanguard_hall.py`,
`Art/VanguardHall/Models`, `Art/VanguardHall/Materials`, `Art/VanguardHall/Shaders` and `Editor/VanguardHallPass.cs` from
`fe7f350d`. Assets under `Art/WardShops`, `Prefabs/WardShops` and `Art/VanguardHall/Textures/WardRunoff_Streaks.png` can stay.
