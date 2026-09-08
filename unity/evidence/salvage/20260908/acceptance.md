# Post-war salvage — native Unity acceptance

Eight Meshy models are installed in the saved Unity scene and both Linux builds. The pass replaces 16 existing instances and adds 82 props. Lattice Jack was excluded; the separate Ring Gate replacement and actor gameplay roots/routes are preserved.

## Visual record

- [Before: map tour](before/tour-contact.png) and [POI inventory](survey/inventory.json).
- [After: native screenshot gallery](native-final/tour-contact.jpg).
- [Front/side/back reference sheets](../../../../refs/salvage_20260908/reference-contact.jpg).
- [Imported model previews](import/contact.png), [Meshy provenance](../../../../meshy/salvage-20260908/README.md) and [placements](placements.json).

The new stepped shop silhouettes, chipped stone bands, exposed pipework, patched red awnings and dark scratched panels follow the turnaround sheets. The hall and shop door scales remain readable beside the existing actors. Dirt and salvage collect around yard edges, benches and shop fronts, while the avenue and stairs remain walkable. The original tree and gate geometry were retained.

Subjective 0–5 scorecard against the city's art brief and retained concepts:

| Trait | Hill | Avenue | Gate |
|---|---:|---:|---:|
| Palette | 4 | 4 | 4 |
| Sky / haze | 4 | 4 | 4 |
| Silhouette | 3 | 3 | 4 |
| Light direction | 4 | 4 | 4 |
| Roughness | 4 | 4 | 4 |
| Density | 4 | 4 | 3 |
| Scale | 4 | 4 | 4 |
| HUD integration | 4 | 4 | 4 |

The new facades match their turnaround silhouettes, but the retained tree still
differs from the original irregular hero-tree concept. The gate court also stays
more open than the shop yards. Those limits keep the historical whole-city beauty
phase open; they do not leave any of the eight selected Meshy imports unfinished.

## Checks

- Continuous real-keyboard route: **42 checkpoints passed**, covering the hill stairs, Basic General, all eight shop porches, mission terminals, hall porch and east wreck.
- All four dialogues, modal movement blocking, flask purchase, scrap sale, both tested Lattice destinations, offline Ring notice, pause, inventory, notes, mute, reduced motion and reset passed.
- Release launch, visible rendering, keyboard input and absence of the development QA listener passed. No runtime exceptions appeared in the accepted native logs.
- Both build calls returned `Succeeded`. The raw [release build summary](linux-build.json) retains Unity's two reported error entries and three warnings; the prior Ring Gate build also reported two error entries despite success. This report does not relabel the build output as warning-free.

## Performance

Recorded on RTX 3060 / i9-10850K, Linux, OpenGL 4.5, 1920×1080, PC quality, uncapped and VSync off. This is desktop evidence, not a medium-laptop qualification.

| View | Average FPS | p99 frame time |
|---|---:|---:|
| cam_hill | 281.0 | 4.50 ms |
| cam_avenue | 306.1 | 4.03 ms |
| cam_gate | 466.7 | 2.93 ms |
| cam_salvage_shop | 571.5 | 2.54 ms |
| cam_salvage_general | 415.6 | 3.04 ms |
| cam_salvage_hall | 643.6 | 2.17 ms |
| cam_salvage_yard | 526.2 | 2.50 ms |
| cam_salvage_board | 482.7 | 2.67 ms |
| cam_salvage_wreck | 651.1 | 2.01 ms |
| cam_terminal | 462.7 | 2.76 ms |
| cam_whompah | 537.6 | 2.45 ms |

Walking averaged **439.6 FPS**, p99 **3.36 ms**, slowest sampled moving frame **5.17 ms**. All accepted moving samples exceeded 58 FPS.

Independent OpenGL tracing counted at most **80 draw submissions** including HUD and shadow passes. Unity's native draw counter returned zero, so it is not used as draw evidence. The conservative fixed-camera visible-mesh count peaks at **240,101 triangles**. GPU submissions peak at **582,394 triangles across all depth, shadow and color passes**; that is a different measurement from visible scene geometry.

A shared 4096² PBR atlas and 18 saved render chunks control the additional rendering cost. Small material families combine across cells; large building batches keep spatial culling. Original models, textures, prefabs and collision sources remain editable.

## Corrections and evidence scope

The initial native run (`native/`) exposed a false collision across the generated Basic General front. It was fixed by retaining its original doorway/porch collision. The later fixed-view run (`native-final/`) passed every render/performance check but its straight diagonal route attempted to walk through the visible salvage stack at (5,18). The corrected route goes around the stack and passed in `native-route-final/`; the scene/build did not change between those two runs. Earlier failed reports remain intact.

The first atlas build rejected a stale chunk fingerprint after prefab reimport. The final build reloads the persisted scene before the final rebuild, preserving the stale-source guard. `gl-trace/` and `gl-trace-atlas/` show the earlier over-budget draws; only `gl-trace-final/` is accepted for the final draw budget.

Raw combined evidence is in [qualification.json](qualification.json). Editing and source regeneration are documented in [Unity EDITING.md](../../../EDITING.md#post-war-salvage). This completes the requested salvage asset pass; it does not claim the historical whole-game concept-likeness work is complete.
