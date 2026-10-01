# North avenue rebuild: Salvage, Repairs, Thread + Hide, Basic General (30 Sep 2026)

Carl (30 Sep 2026): "we recently rebuild a lot of the buildings but we still need to rebuild. general, salvage, thread
and repairs. same stone work, same signage, same weathering." Sources and construction: `art/north_avenue_20260930/README.md`.
**Status: installed, built and natively verified for the checks below. Not visually accepted by Carl; no GTA6-level claim.**
Nothing committed.

## What changed

1. **Three shops rebuilt in stone** on their standard parcels with the hall-district kit, materials and weathering:
   Salvage (west row z 18), Repairs (east row z 9), Thread + Hide (east row z 18). Scene group
   **Ward shops (north avenue)**, prefabs `Prefabs/WardShops/{Salvage,Repairs,ThreadHide}`, LODGroups, box colliders with
   walkable 0.4 m door recesses, family signs (SALVAGE, REPAIRS, THREAD + HIDE) on their sign mounts.
2. **Basic General booth rebuilt in stone** (`Prefabs/WardShops/BasicGeneral`, same group): stone rear and cheek walls on
   the kept collider lines, new stone front piers (two new colliders), red riveted lintel carrying the existing family
   sign, attic course, corrugated roof, security-shutter box, slab porch and step. Mira, the counter dressing, the Stock
   panels, the back panel and the sign are untouched (checked in the verify report).
3. **Lamps**: 16 warm wall lamps (Salvage 3, Repairs 4, Thread + Hide 3 + the display light, Basic General 5 incl. two on
   the inner cheek walls over the counter), all on the Ward lighting clock (lamps practical + night-only; display light
   practical). WS_LedWarm added to the clock's emissive list.
4. **Retired, not deleted** (103 objects, `north-install.json`): `Ward shop architecture/{salvage,repairs,thread_hide}`,
   `Post-war salvage/BLD_shop_{e_04,w_03,w_04} repaired`, their porch/step/interior-floor renderers (colliders kept), the
   three shop shadow proxies, the retrofit cyan blade lights, Basic General's old Masonry, Walls, Rear services, Structure,
   Canopy, Signs, Lights, Threshold, the structural/sign hardware and old sign wear, `AuthoredWorld/BLD_general_porch` and
   `_first_step` renderers, and `Post-war salvage/Basic General repaired`. The retrofit collider `COL_thread_hide_balcony` is
   retired. The combined *Shop retrofits* meshes point at new filtered copies (`Art/WardShops/Retrofit/*_north_avenue.asset`;
   9,016 + 41,781 + 120 + 30 triangles removed; the `_hall_district` copies stay as assets).
5. **Pipeline fix** (`WardShopsPass.RemapPrefabMaterials`, now run by *Refresh models and materials*): after the Repairs gas
   cage was removed from its source, the re-imported model's sub-mesh order shifted under the prefab's stored material
   slots, and the roller shutter rendered as brass (the container as teal paint, the doors yellow). The first native run
   showed it as a glowing orange shutter at noon and dusk. Every slot is now re-mapped from the model's own material names;
   an audit of all nine shop prefabs shows every slot matching.

## Identity

- Baseline: HEAD `b32a8bcf`, clean tree. Scene sha256 before `cd1969d2…581b` (`before-scene-sha256.txt`), after
  `3e913893…c1eb` (`after-scene-sha256.txt`). Rollback copy of the scene: `rollback/before-north-install.unity` (local).
- Baseline player: the 18:06 development build of `b32a8bcf`, moved to
  `/home/teknetik/code/_snapshots_20260930/north-before-LinuxDevelopment`.
- Builds: `build-dev-1.json` (before the slot fix), `build-dev-2.json` (final; Succeeded, 0 errors, 346 warnings),
  `build-release.json` (Succeeded, 0 errors, 626 warnings; the increase is the pre-existing `com.unity.ai.inference`
  compute shaders being recompiled, none from this pass).

## Native results (RTX 3060 12 GB / i9-10850K, OpenGL Core, 1920×1080 window, High preset, render scale 1)

- **Real-input walk** (`unity/tools/check_north_avenue_native.py`, `native-3/north-native.json`; `native-2` before the
  slot fix; `native-1` stopped at a pre-existing salvage generator and crate between Basic General and Thread + Hide, which
  the route now passes on their south side): Vex, Torr, Linn and Mira talked to (prompt, E → Dialogue, movement blocked
  0.0 m, choice, Escape); Mira reached between the new piers on the Basic General porch, **flask bought and scrap sold
  (25 → 21 → 22 cr)**; **59 legs reached at the right heights**, including every new porch and **into each new door recess**
  (Thread + Hide x 18.03, Repairs x 18.03, Salvage x −18.03), the Repairs bay, Salvage shutter and Thread + Hide display,
  the hall-district porches and recesses, and **Lattice: E → Grid → node0 → linked to Crosswind Reach**. Player.log: no
  exception lines.
- **First-person stills** at 12:00, 17:00, 20:30 (`native-3/fp_*`, sheets `fp-stills-h*.jpg`):
  Basic General approach and counter, Repairs from the cross street, Thread + Hide balcony, the avenue from its north end,
  Salvage. Editor auditions: `editor-v1*` (whole buildings, close-ups), `editor-v2` (pier base).
- **Frame cost A/B** (`walk-ab/`, `unity/tools/profile_north_walk.py`, three alternating runs per build, the same lane-only
  walk past all four buildings, noon then night with lamps on; conditions in `walk-ab/conditions.txt`):

  | Walk | Baseline fps / p50 / p99 ms / SetPass | North avenue fps / p50 / p99 ms / SetPass |
  | --- | --- | --- |
  | 12:00 | 104.4 / 7.23 / 20.44 / 286 | 100.3 / 7.72 / 20.02 / 294 |
  | 20:30 | 81.3 / 12.17 / 17.14 / 280 | 77.4 / 12.71 / 17.47 / 291 |

  The rebuild costs about +0.5 ms median (≈4 % fps). p99 is above 16.67 ms in **both** builds on this walk (spikes to
  40–50 ms are present before the change). Carl (30 Sep, evening): "We should maybe lower our expectations on frame rate
  for a 3060 rtx. It's an old gpu now." AGENTS.md §7 now sets an average of 60 FPS on High at 1080p with occasional spikes
  accepted: the noon walk meets it, the 20:30 walk averages 77 FPS (81 before). No optimisation was attempted. GPU time is unavailable in this player;
  memory not measured. The single profiled leg in `native-3` (p99 27 ms, host load 6.6) is one noisy run, not an A/B.
- **Release smoke** (`release-native/`): launched, non-blank render, real keys, no exception lines, no QA bridge output.

## Visual review (my scoring against the hall district and Carl's notes; not acceptance)

| Category | Score | Notes |
| --- | --- | --- |
| Same stonework | 4 | Same kit and shader: quoins, dressed margins, chipped arrises, occlusion, deep reveals, flat arches, cornices. Booth piers use two-stone courses. |
| Same weathering / battle history | 4 | Runoff under every ledge, rust under steel, wall-foot soil, impact clusters; Salvage's rubble-filled breach and Repairs' soot add story. |
| Same signage | 4 | Family boxes, amber channel letters, cyan status; Basic General keeps its sign on a new lintel built for it. |
| Silhouette / storytelling | 3.5–4 | Hoist and breach (Salvage), canopy, flue, container (Repairs), balcony with cloth and hides, lit display (Thread + Hide), stone stall with shutter box (Basic General). |
| Night lighting | 4 | Warm pools at every door, counter lit from the cheek walls, lit signs and display. |

## Remaining defects and limits

1. Rooftop pieces (Salvage shed, Repairs container, Thread + Hide drying lines) show only partly from street level.
2. Thread + Hide's display goods and hides are simple modelled shapes (no Meshy props, hides use the tinted linen set).
3. Pits, scars and cracks are shader detail; doors, shutters and sign boxes are plain URP Lit (same limits as the hall district).
4. The birch at (−19.75, 24.4) spreads its crown over Salvage's north wall, as it did over the old shell (footprint unchanged).
5. A litter scatter sits against Basic General's new west pier base (left in place; it reads as debris against the pier).
6. The kept salvage generator and crate still block the direct lane between Basic General and Thread + Hide.
7. Shops remain closed (no interiors); porches keep their original 0.5 m ledge and single step.
8. No concept images; not yet shown to or accepted by Carl.

## Rollback

Restore `rollback/before-north-install.unity` over `Assets/AthenHill/Scenes/AthenHill.unity` (the scene committed in
`b32a8bcf`), then rebuild render chunks. Or in place: delete the *Ward shops (north avenue)* group, re-activate the paths
in `north-install.json`, point the four *Shop retrofits* meshes back at `Art/WardShops/Retrofit/*_hall_district.asset`,
remove the new lights from the Ward lighting clock and rebuild render chunks.
