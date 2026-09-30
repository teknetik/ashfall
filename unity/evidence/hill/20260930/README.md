# Hill, hero-tree ring, terminals and hall floodlights — 30 September 2026

Carl's request and sources: `art/hill_20260930/README.md`. **Status: installed, built and natively checked for the
items below. Not visually accepted by Carl yet; no GTA6-level claim.**

## What changed

1. **Hill rebuilt on the Ward masonry kit** (scene root *Ward hill*, `Prefabs/WardHill/WardHill.prefab`): retaining walls
   with quoins and a flush coping band, three stairs with worn/dished treads between raking-coped cheek walls, a stone
   tree ring in the hall/shop stone with curved coping (0.49 m seat), a root-heaved and cramped coping stone, apron,
   flagged paths and landings, kerbed beds, terminal pads and stepping stones, leaf-litter soil with surface roots,
   irrigation standpipe, sand in sheltered corners. Hill LOD0 121,896 / LOD1 24,906 triangles.
2. **Planting** (CC0 Poly Haven, `scatter_hill_plants.py`): grass lawn soil with grass tufts, succulent drifts, ice plant,
   celandine, weeds, Othonna shrubs, stones, two boulders; litter, twigs and stones in the ring. Per-bed LOD groups on
   the new *Athen Hill/Ward Ground Cover* wind shader (reduced motion freezes it).
3. **Terminals**: Carl's Meshy "Reclaim & Save Point" kiosk on the three existing slots, facing the tree, on stone pads,
   with a night screen glow; saved terminal colliders moved onto them. Decorative, as before.
4. **Vanguard Hall floodlights**: Carl's Meshy tripod floodlight replaces the modelled box uplights; the existing spot
   lights moved to the lenses and re-aimed at the nameplate (wider 70° cone).
5. **Retired, kept inactive** (125 objects, `install.json`): old plinth/caps/mound/paths/surface renderers, north-stair
   courtyard stones and ENV stair renderers, the three market boxes, six hill root stones, the hill bench, Hill grass 1–4,
   Hill weathered stones, stair sand decals and joint weeds on the old stairs. All saved hill and stair colliders kept.

## Identity

- Baseline: HEAD `122ba7a8` (clean tree), scene sha256 `8ff809bd…` = `rollback/before-hill-install.unity`; baseline
  player snapshot `/home/teknetik/code/_snapshots_20260930/hill-before-LinuxDevelopment` (14:29 build of that scene).
- Hardware: RTX 3060 12 GB (driver 610.57.04), i9-10850K, 32 GB, OpenGL Core, High preset, render scale 1, 1920×1080 window.

- Final scene sha256 `cd1969d2…`. Builds: development `build-dev-3.json` (last of several iterations; Succeeded, 0 errors,
  348 warnings), release `build-release.json` (Succeeded, 0 errors, 348 warnings). No FXC crash in the logs.

## Native results

- **Real-input hill check** (`tools/check_hill_native.py`, `hill-native-final/hill-native.json`): walked with real W presses
  from West Gate up the +X stair, round the apron, to Linn (E → Dialogue, movement blocked 0.00 m, choice, Escape;
  hill visited), down and up the south stair, over the stepping stones to terminals 02 and 01, down the north stair.
  Heights correct on every stair and on the hilltop (1.53 = collider + skin). Expected blocks: the tree ring stops the
  player at r 3.695 m (collider 3.35 + capsule 0.35), terminal 01's body at 0.76 m from its centre, the north stair
  cheek at x 1.644 (cheek face 2.0 − capsule). PASS.
- **City-loop regression** (`cityloop-native/city-loop.json`, the hall-district check `tools/check_hall_district_city_loop.py`
  launched by `run_cityloop.py`): Vex, Torr, Field Supply porch and door recess, Linn on the hill, Mira → Shop, water
  flask bought and scrap coil sold (25 → 21 → 22 cr), Tool Exchange / Air + Water / Relay Works legs, hall front step
  and terrace (past the floodlights), Lattice → linked. CITY LOOP PASS, Player.log 0 exception lines.
- **Release smoke** (`release-native/`): launched, non-blank render, real keys, no exceptions. PASS.
- **Matched lookbook** (`before-native/` baseline build vs `after-native/` final build; 17 shared cameras × 12:00, 17:00,
  20:30 plus the ten new `cam_hill_*` views; comparison sheets in `comparison/`, including `_before-after-h12.00.jpg`,
  `_before-after-h17.00.jpg` and `_new-hill-cams-h*.jpg`). Night lookbook views keep the player at West Gate, so the
  tree uplights and hall floodlights (> 42 m) are culled there; night lighting is judged on foot (`hill-native-final/fp_*`).
- **On-foot stills** (`hill-native-final/fp_*-h12.00/17.00/20.50.png`, sheet `fp-sheet-final.jpg`): ring from the south
  path, the uplit crown at night, terminal 02 close (screen readable day and night), the west bed, the hall facade and
  a floodlight close-up at noon, dusk and night.

### Frame cost (RTX 3060, OpenGL, High, render scale 1, 1920×1080; uncapped; host shared with desktop apps)

Walk from West Gate up the +X stair to Linn (third-person, 12:00; `walk-ab/summary.json`, alternating runs):

| Build | avg fps | p50 ms | p95 ms | p99 ms | submitted tris |
| --- | --- | --- | --- | --- | --- |
| baseline (3 runs) | 61.2–62.0 | 16.3–16.7 | 19.8–20.4 | 21.6–22.4 | 16.10–16.14M |
| first install (2 runs) | 58.0–59.1 | 17.1–17.6 | 20.6–20.8 | 22.8–23.7 | 16.87–16.89M |
| final: shadow proxies, lighter plant/prop LODs (2 runs) | 59.2–61.2 | 17.0–17.1 | 19.1–20.9 | 21.1–22.7 | 16.44–16.45M |

The final build costs about 0.4–0.5 ms at p50 on this walk; the average sits at the 60 fps line (one run just under).
The p99 target (16.67 ms) was already missed on this walk before the pass (the hero tree's 3.75M-triangle LOD0 is in view).

cam_hill (elevated overview, 6 s dwell; before load 3.5, after load 5.4):

| Hour | before fps / p50 / p99 ms | after fps / p50 / p99 ms |
| --- | --- | --- |
| 12:00 | 69.6 / 14.34 / 16.27 | 65.2 / 15.24 / 17.65 |
| 17:00 | 74.7 / 13.41 / 14.45 | 68.6 / 14.58 / 16.42 |
| 20:30 | 72.4 / 13.83 / 15.35 | 69.7 / 14.29 / 16.09 |

An earlier after-run of the same view under lighter load measured 67.2 / 14.87 / 16.19 at 12:00 (`after-native-2`,
before the shadow-proxy optimisation), so treat these single dwells as ±1 ms. Not measured: GPU time (unavailable in
this player), VRAM, loading.

Cost controls in the final build: walls/stairs/ring cast shadows through their LOD1 meshes at LOD0; paving, kerbs,
soil, roots, sand and ground cover cast none; planting LOD0 240,640 triangles in five per-zone LOD groups (LOD1 73,502);
kiosk LOD0 45,578 (switches within ~11 m), floodlight LOD0 36,106; hill LOD0 121,896 + 13,288 shadow-proxy triangles.

## Visual review (my scoring against Carl's reference and AGENTS.md §7; not acceptance)

| Category | Score | Notes |
| --- | --- | --- |
| Composition / silhouette | 4 | The stone ring now anchors the tree like the reference; stairs with raking cheeks and capstones, quoined plinth. |
| Scale | 4 | 0.49 m ring seat, 0.25 m risers on the saved colliders, 1.85 m kiosks, 1 m floodlights. |
| Material detail | 3.5–4 | Same ashlar, runoff, rust and battle damage as the hall and shops; lawn and litter textures tile visibly from above. |
| Lighting / depth | 3.5 | Uplights wash the crown and the floodlights the facade at night; low retaining walls read dark brown in shade. |
| Density / storytelling | 3.5–4 | Root-heaved coping with iron cramps, surface roots, aquifer standpipe, stepping stones, succulent drifts; beds lighter than a lawn. |
| Temporal stability | U | Wind on the ground cover runs; no moving walkthrough video was reviewed this pass. |
| UI / readability | 4 | Kiosk screens crisp at arm's length, day and night, with an honest LINK OFFLINE status. |

## Remaining defects and limits

1. The hero tree mesh itself is unchanged; its base now sits in the ring's litter with authored surface roots.
2. Kiosk bodies are decimated from 506k to 45k triangles (LOD0): at arm's length edges are softer than Carl's source.
   The baked Meshy screen UI smeared under decimation, so both screens carry an authored overlay
   (`art/hill_20260930/screen`) that follows his layout. The kiosks are decorative: no save or reclaim interaction exists.
3. The floodlight head was turned up 15°; the rear cyan band bends slightly beside the yoke (visible within ~0.5 m).
   The spot is aimed ~20° above the lamp axis, inside its 62° cone.
4. Retaining walls and stairs in shade are darker than the old light boxes (same stone, bake and weathering as the hall).
5. Beds read as a grassy xeriscape rather than a dense lawn; grass is decimated alpha-card clumps; lawn and litter
   textures repeat when seen from above.
6. Surface roots are smooth procedural tubes (bark from the tileable Phase 1 root material), fine at walking distance.
7. Frame cost on the approach walk is ~0.5 ms higher than baseline; the walk's p99 misses 16.67 ms (as it did before).
8. No walkthrough video; the ground-cover wind was not reviewed in motion. Night lookbook views cull the new lights.
9. The hill community board, benches elsewhere and the tree's canopy were not part of this pass.

## Rollback

Restore `rollback/before-hill-install.unity` over `Assets/AthenHill/Scenes/AthenHill.unity` (sha `8ff809bd…`, the scene
of commit `122ba7a8`) and the render chunks from that commit. For the hall floodlights alone, restore
`art/vanguard_hall_20260930/author_vanguard_hall.py`, `Art/VanguardHall/Models/*` and `Prefabs/VanguardHall/VanguardHall.prefab`
from `122ba7a8`. New assets under `Art/WardHill`, `Art/HillProps`, `Prefabs/WardHill` and `Shaders/WardGroundCover` can stay.
