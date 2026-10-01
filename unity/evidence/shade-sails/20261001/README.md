# Shade sails — evidence, 1 October 2026

Pass: `Assets/AthenHill/Editor/ShadeSailsPass.cs`; sources, run order and design notes:
[art/shade_sails_20261001/README.md](../../../../art/shade_sails_20261001/README.md). Not reviewed or accepted by Carl.
Tested against the working tree of 1 Oct ~18:00 (branch `ward/next-level`, base 3ebd801b + today's uncommitted passes,
including night life, West Gate arches, rooftops, night facade, wall-foot drifts and the birch canopy pass installed meanwhile).

## What changed in the saved scene

* New root **Ward shade sails** with four prefab instances (`Prefabs/ShadeSails/SS_Courtyard/Market/Apron/Lattice.prefab`):
  Courtyard terminals sail, Market rest sail, West Gate apron sail, Lattice court sail.
* 7 unshadowed festoon point lights added to `CityLightCircuit.practicalLights` and `nightOnlyLights` (136 → 143,
  82 → 89; no stale entries); `SS_FestoonBulb` added to `emissiveMaterials` (`survey-before.json` vs `survey.json`).
* New root **Shade sail review cameras** (8 disabled cameras `cam_ss_*`).
* Nothing retired or moved; no render-chunk source touched (`chunkFingerprintMatches: true`).
* Rollback: `rollback/before-shade-sails.unity` (the scene before the first install), or delete the two roots and the
  seven lights from the clock lists.

## Files

| File | Content |
| --- | --- |
| `audit-before.json`, `audit-after-install.json` | StreetDressingAudit before and after the install |
| `survey-before.json`, `survey.json` | lights, cameras, sun by hour, mesh probes (service poles = I-beams, tree canopy edge, bunting); before/after |
| `build-assets.json` | triangles per prefab and LOD, shadow casters, lights, colliders, unmapped materials (none) |
| `install.json`, `reinstall.json` | instances, light paths, clock registration, chunk fingerprints (last reinstall: prefabs rebuilt for the I-beam strops and pole paint) |
| `verify-saved-scene.json` | verify of the saved scene: prefab links, LOD triangles, casters, materials/shaders, lights on the clock, colliders, cameras — **0 problems** |
| `editor-r1` … `editor-r5` | editor captures (graphics, ≤ 6 close cameras per run): r1 first install at 13:00; r2 after the shadow-proxy fix, 13:00 + 20:30; r3 the remaining cameras; r4 market + hardware probes; r5 final pole paint and warm bulbs |

Placement validation (`art/shade_sails_20261001/layout-report.txt` and `layout-report-installed.txt`): 0 problems before
and after the install; one accepted warning (the faded top of the barrel-fire smoke passes under the market sail's high
corner).

## Numbers

LOD0 98.5k triangles (sails 50.4k, rigs 23.8k, festoons 24.3k), LOD1 28.8k; shadow casters at LOD0 5.3k triangles
(four 256–480-triangle canvas proxies + poles and stone footings); 7 lights, none shadowed; textures ≈ 27 MB at full
mips, streaming. No frame-time, city-loop or native measurements were taken by this pass (the orchestrator's combined
batch test measures them).

## Defects and open points known now

* The canvas undersides are fairly dark at noon (transmission 0.18–0.32 of the sun through the cloth); judge in the
  native 13:00 lookbook — raise `_WardTranslucency` on `SS_Sail_*` if they read as flat brown.
* Editor captures show every practical light at full strength by day (the clock does not run in the Editor), so the
  bulbs glow at 13:00 there; in the player they drop to 4 % by day.
* The market sail sits above the barrel fire's faded smoke top (accepted warning); check for hard intersections of
  smoke particles with the canvas at 20:30.
* The courtyard's two north poles and the apron's two east poles stand on stone footings without guys (guys would cross
  the stair foot, the Field Supply steps or the arch walk); structurally optimistic for sails this size.
* No moving walkthrough or LOD-transition review; festoon cable and canvas edges may shimmer under TAA at distance.
* Shadow cost of the big casters is not measured here (the canopies cover ~25–55 m² each): see the combined A/B at 13:00.
