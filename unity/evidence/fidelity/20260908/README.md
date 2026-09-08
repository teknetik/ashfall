# Meshy fidelity recovery — 8 September 2026

This pass recovers retained source detail in the existing district. It does not
replace the rejected district shops or claim GTA6 visual parity. The production
backlog is [TODO.md](../../../../TODO.md).

## Recovered data

| Asset | Previous runtime | Restored source |
| --- | --- | --- |
| Four talking guards | 5,999 triangles each | 38,071 each, original weights/UVs, same relaxed arms |
| Three mission terminals | 7,696 triangles each, Unlit | 25,656 each, generated tangents and supplied PBR maps |
| Eight salvage families and active west arches | Shared atlases and remapped UVs | Original UVs and per-family source maps, normally 2k |
| Stone weathering | White Lit defaults after shader replacement | Original glTF albedo/normal bindings translated to Lit |

The player, three travelers, yard mechanic and accepted South Ring Gate already
retain their source geometry. No new Meshy generation was necessary. Original
source files and prior versions are retained. The guard processor's byte checks
are in [guard-source-preservation.json](guard-source-preservation.json), and the
source/atlas inventory is [source-audit.json](source-audit.json).

Guard reduction defaults are removed. Future salvage imports use uniform fitting.
Legacy atlas commands refuse to overwrite recovered fidelity materials. Existing
building transforms, foundations, collision and gameplay references remain intact;
fixing already stretched buildings needs a separate placement review.

## Verification records

The comparison was built in `/tmp/athen-fidelity-20260908/unity/AthenHill` from a
copy of the saved working scene. The same scoped recovery was then applied to the
latest main scene, preserving ongoing changes. The comparison scene was never
copied back wholesale. Build reports record render-source fingerprints.

- [Baseline report](comparison/native-baseline/report.json): native 1920×1080,
  100% render scale, 4× MSAA, full textures, high shadows, OpenGL, uncapped.
- `comparison/native-restored/`: restored comparison and passing view timings;
  its route stopped at the historical Ring Gate waypoint inside the new console.
  The main run uses the current front platform and passes the whole route.
- `comparison/attempt-restored-window-size/`: rejected because the actual client
  was 1920×1043; the harness now resizes and verifies dimensions before measuring.
- `comparison/attempt-restored-bounds-diagnostic/`: rejected diagnostic based on
  inflated renderer culling bounds. CPU skin evaluation now uses the original
  bone/bind matrices, matching the importer's centimetre-aware validation.
- `comparison/attempt-restored-stale-build/`: premature test of the earlier build;
  retained and excluded from qualification.

The earlier top-level baseline predates the decal intermediate-render-target fix.
Use the `comparison` baseline for image comparisons, not that earlier build.
Reported zero GPU/draw counters are unavailable measurements, not zero cost.

## Remaining issues

Source recovery improves detail but does not solve repeated architecture, stretched
existing buildings, static idle/talk animation, limited canopy structure or baked
lighting in generated albedo. The walkthrough exposes gaps around the tree roots,
stretched bark and crude close grass. The generator close-up is partly obscured by
an existing crate; it is useful for surface comparison, not full silhouette approval.

The four stale Desert Landscape references proved to be empty, retired objects.
[Inspection](terrain-references.json) and [cleanup](terrain-cleanup.json) preserve
their record. Their removal retained all eight connected terrain renderers,
gameplay and collision. The saved scene reopens without those errors.

## Final main-project qualification

Both [development](development-build.json) and [release](release-build.json) Linux
builds succeeded with **zero errors**, with 3 and 5 warnings respectively. Warnings
include deprecated object-search APIs and Editor MCP reconnects during builds.
[Final identity](final-identity.json) records the Git base, modified source tree
and build-file hashes; this is a working-tree build, not a clean committed revision.

The [native report](native-restored/report.json) passes at 1920×1080, 100% render
scale, 4× MSAA, full textures, high shadows (4096/18 m), post-processing on, VSync
off and no frame cap. Hardware: RTX 3060 **12 GB**, i9-10850K, NVIDIA **595.84**,
Linux/OpenGLCore, Unity **6000.6.0f1**. All nine actors are present.

| Measurement | Result |
| --- | --- |
| Eight fixed-view averages | 202.6–439.0 FPS |
| Worst fixed-view p99 | 6.09 ms |
| Worst fixed-view frame | 20.09 ms; no view frames over 33.33 ms |
| Walking samples | 17,429 frames / 49.65 seconds of moving gameplay |
| Walking average / p50 / p95 / p99 / max | 351.0 FPS / 2.73 / 4.30 / 5.15 / 8.47 ms |
| Player GPU allocation | 1,035 MiB; baseline 861 MiB |
| Total device allocation during final sample | 2,654 MiB, including Editor/desktop |
| Unity source-renderer texture-object memory | 1,148.7 → 690.0 MiB; not total VRAM |

[Raw frames and CPU/SetPass summary](native-restored/cpu-render-summary.json)
retain main-thread and CPU frame timings. GPU timing, draw-call and batch counters
are unavailable on this run. Submitted triangles span rendering passes; they are
not a visible-geometry budget. Measurements were uncapped and taken before video
capture; the normal game's saved frame-limit preference was not changed.

The [keyboard route](native-restored/keyboard-route.json) and
[29 city-loop checks](native-restored/city-loop.json) pass: hill/gate traversal,
four conversations, atomic buy/sell, Lattice destinations, offline Ring Gate,
modal input blocking, pause, pack/notes, mute, reduced motion and return to gate.
CPU skin evaluation verifies all four full-resolution guards at 1.8 m with their
soles at the existing interaction-root ground height. Native runtime errors: none.
The [release smoke check](release/report.json) passes startup, input and pause,
and confirms the release ignores the development QA flag. Test preferences were
isolated from the developer's settings.

[Walkthrough](native-restored/walkthrough.mp4): 26 seconds, 1920×1080, 30 FPS video,
with real movement and wheel zoom into first person. Captured frames at 6 and 15
seconds were reviewed for third-person movement and close tree/ground rendering.
The video capture rate is separate from the measured gameplay frame rate.

## Visual assessment against the production target

These are reviewer estimates, not whole-game AAA acceptance. The material and
geometry recovery is accepted as an improvement over the reduced baseline.

| Category | Before → after / 5 | Remaining defect |
| --- | --- | --- |
| Composition / silhouette | 2 → 2 | Repeated facades, weak canopy structure |
| Scale / construction | 2 → 2 | Existing building proportions and thresholds need individual review |
| Material detail | 2 → 3 | Source detail returns; large facades and bark remain soft at close range |
| Lighting / depth | 2 → 3 | Lit terminals and textured stone improve depth; shaded facades remain too dark |
| Density / storytelling | 2 → 2 | Broad paving and repeated shops still dominate |
| Character / animation | 2 → 2 | Guard silhouettes recover detail; static idle/talk and stiff transitions remain |
| Temporal stability | 3 → 3 | No runtime faults; foliage/grass and shadow edges need further work |
| UI / readability | 4 → 4 | Existing interface retained; in-world labels can overlap HUD regions |

The next visual pass should address the tree's visible structural defects and
establish one convincing street frontage before rolling out more copies.
