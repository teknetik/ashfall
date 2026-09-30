# Vanguard Hall rebuild — native evidence (30 Sep 2026)

User direction (Carl): "this building needs a complete rebuild. it looks terrible." Accepted target: 
`art/vanguard_hall_20260930/concept/vanguard-hall-concept-a.png` ("yes this!"). **Status: installed, built and natively
verified for the checks below. Not visually accepted by the user yet; no GTA6-level claim.**

## What changed

- **Removed from view (kept in the scene, inactive, for rollback):** `Post-war salvage/Vanguard Hall repaired` (the 6,856-triangle
  Meshy hall and its MeshCollider), `Ward district retrofit/Hall banners`, `AuthoredWorld/BLD_hall_plinth`, `BLD_hall_step` and their
  `COL_` colliders. Render chunks rebuilt (fingerprint current).
- **Added:** scene root **Vanguard Hall** = `Prefabs/VanguardHall/VanguardHall.prefab` at (−10, 0, −26.55), scale 1: authored stone civic
  hall (sources and construction: `art/vanguard_hall_20260930/README.md`), 12 box colliders, LODGroup (LOD0 85,094 triangles to 26 % screen
  height, LOD1 41,856), Poly Haven fittings, 6 practical lights (portal ×2, portal recess, rear door, two terrace uplights; all on the Ward
  lighting clock as practical + night-only lights, no shadows) and a mast beacon, 26 weathering decals. `VH_Glass` and `VH_LampLens` are on the
  clock's emissive list. **Vanguard Hall review cameras**: nine `cam_vh_*` player-height views.
- **Moved salvage dressing** that sat inside the new footprint (base pivots, to the ground west of the podium):
  crate scatter 57 (−14.35, 0.505, −27.7) → (−17.35, 0.01, −26.4); scrap scatter 56 (−16.0, 0.505, −29.0) → (−17.6, 0.01, −32.2);
  trash scatter 59 (−15.0, 0.51, −29.97) → (−16.9, 0.01, −34.4).
- The approach is unchanged: podium top 0.5 m and the front step (now 6.5 × 0.25 × 0.8 m) keep the old heights and position; the landmark
  `vanguard_hall` is unchanged. A rear service step was added. The podium stops 6 cm short of the Lattice pad (untouched).
- New shader **Athen Hill/Masonry Lit** (`Art/VanguardHall/Shaders`); Editor pass `Editor/VanguardHallPass.cs`; QA script
  `tools/check_vanguard_hall_traversal.py`. Docs: EDITING.md (*Vanguard Hall rebuild*), README.md (Look and rendering), AGENTS.md baseline row.

## Identity

- Baseline scene sha256 `dceca1f5…daf8` (`baseline-scene-sha256.txt`; working tree over HEAD `782b2ab6`, which already carried
  other sessions' uncommitted inventory/UI edits). Rollback copy: `rollback/before-hall-rebuild.unity` (+ the pass's own copy).
- Final scene sha256 `38f604b0…d9e3` (`after-scene-sha256.txt`). Final material edit after that: `VH_Ashlar` normal scale 0.7.
- Baseline player snapshot: `/home/teknetik/code/_snapshots_20260930/hall-baseline-LinuxDevelopment` (built 09:04 today, old hall).
- Builds (`builds/`): development ×4 (final `development-build-4.json`: Succeeded, 0 errors, 346 warnings), release
  (`release-build.json`: Succeeded, 0 errors, 632 warnings — none from the hall's shader/assets; the console's warnings are Sentis shaders and
  other scripts). Nothing committed.

## Native results (RTX 3060 12 GB / i9-10850K, OpenGL Core, 1920×1080 window, High preset, render scale 1, uncapped)

- **Matched lookbook** (`before-native/` baseline build vs `after-native/` final build; same 9 shared cameras at 17:00, 12:00, 20:30;
  `after-native` adds the nine `cam_vh_*`): sheets in `comparison/*-before-after.jpg` and `comparison/playerheight-h*.jpg`.
  At night the fixed-camera lookbook keeps the player at West Gate, so the circuit culls the hall's lamps (>42 m); night lighting is judged
  from the on-foot stills below.
- **Real-input traversal** (`trav2-native/hall-traversal.json`, repeated in `trav4-native/` with video): Vex prompt at spawn, E → Dialogue,
  movement blocked while modal (0.0 m), Escape → Play. On foot from West Gate via the west lane to the plaza, then front step (y 0.28),
  terrace (0.53), portal recess at the doors, terrace east, off the podium, east side, west side outside the moved salvage, rear, rear step
  (0.30), rear podium (0.53), back to the plaza: every leg reached, no stall, heights within tolerance. Player logs: 0 exception/NullReference lines.
- **Walkthrough video:** `trav4-native/hall-traversal.mp4` (grim frame capture at ~20 fps of the floated window, 1280 px; x11grab reads black
  from XWayland GL windows). Frames sheet: `comparison/walkthrough-frames.jpg`.
- **First-person stills at the hall** (real follow camera, eye 1.65 m, player on foot): `trav4-native/fp_*-h20.50.png` and `-h17.00.png`,
  sheet `comparison/fp-stills-night-dusk.jpg`. At 20:30 the portal lamps give warm pools on the facade, the uplights light the nameplate and
  banner, and the recess lamp lights the doors.
- **Frame cost at cam_salvage_hall** (6 s dwell, `lookbook.json`; host load 6–11 during the baseline, 3.6–5 after, so read as local):

  | Hour | Before fps / p50 / p99 ms / SetPass | After fps / p50 / p99 ms / SetPass |
  | --- | --- | --- |
  | 17:00 | 122.0 / 8.22 / 9.61 / 168 | 109.1 / 9.16 / 11.25 / 200 |
  | 12:00 | 214.8 / 4.56 / 6.60 / 126 | 190.8 / 5.32 / 7.38 / 156 |
  | 20:30 | 288.6 / 3.31 / 5.45 / 145 | 222.1 / 4.35 / 6.65 / 178 |

  About +1 ms per frame on the hall-dominated view, far inside the 16.67 ms target. GPU time and draw counters are unavailable in this player.
- **Memory at cam_salvage_hall** (`mem-before.out`, `mem-after.out`, Unity counters): texture current +11 MB (4,587 → 4,598 MB), desired +11 MB,
  theoretical full resolution +176 MB (streaming mipmaps active), Unity allocated +34 MB. Driver VRAM not measured.
- **Release smoke** (`release-native/report.json`): `--athen-qa` probe folder stayed empty (bridge absent), non-blank render, still running
  after real keys, no exception lines. Two earlier attempts failed to create a GL context because the Editor was still open (folders kept as
  `release-native-attempt*`).

## Visual review (my scoring against the accepted concept; not acceptance)

| Category | Score | Notes |
| --- | --- | --- |
| Composition / silhouette | 4 | Battered piers, deep portal, pilastered upper storey, projecting cornice, attic and mast match the concept. |
| Scale | 4 | 2.9 × 3.8 m civic doors, 1.65 m eye views and podium/step heights read correctly. |
| Material detail | 3.5 | Modelled ashlar with per-block tint, bevels and chips; strong at mid range. Close up the arrises are uniformly clean and faces uniform. |
| Lighting / depth | 4 dusk & night, 3.5 noon | Lamps, uplights and recess lamp make it a night landmark; faces in full shade read flat. |
| Density / storytelling | 3.5 | Strapped pier, steel wraps, repair plate, bricked-up window, conduit, AC, mast, banner; runoff decals are faint. |
| Temporal stability | not assessed | Video shows no obvious popping; LOD0→LOD1 switch not reviewed in motion. |

## Remaining defects and limits

1. Shaded faces (rear, west in the afternoon) look flat: even block sizes, little macro grime or AO gradient.
2. Stone edges are clean everywhere except ~10 % small chips; no deeper spalling or erosion at pier bases or drip lines.
3. Runoff and wall-foot decals are very subtle; sand drifts are barely visible.
4. Small barred windows can read as flat glass colour by day (interior mapping; cool rooms now disabled).
5. The mast reads thin from the plaza; roof dressing is simple (only seen from high ground).
6. The nameplate lettering is 15k triangles in LOD0 (heavy for a sign, but only drawn near).
7. Full city-loop regression (all four NPCs, trade, Lattice travel) was not re-run; only the Vex prompt/dialogue regression and the hall
   traversal. The Lattice pad and its approach were not touched.
8. The scene and docs also carry other sessions' uncommitted work (inventory/pack UI); nothing was committed.

## Rollback

Restore `rollback/before-hall-rebuild.unity` over `Assets/AthenHill/Scenes/AthenHill.unity`, or in place: delete the *Vanguard Hall* and
*Vanguard Hall review cameras* roots, reactivate the six retired objects, move the three salvage props back (positions above), remove the hall
lights and `VH_Glass`/`VH_LampLens` from the Ward lighting clock, and Rebuild Render Chunks. Assets under `Art/VanguardHall`,
`Prefabs/VanguardHall` and the shader can stay; nothing else references them.
