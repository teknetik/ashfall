# Ward courtyard reference pass — 8 September 2026

The focused courtyard pass is implemented in the saved Unity scene and both Linux
players. Traversal, city interactions, release controls and the development-bridge
restriction passed. The foreground is closer to the supplied image, but the scene
does **not** yet meet that reference's architecture, density, lighting or character
quality. The visual scores below are an internal assessment, not user acceptance.

## What changed

- Chipped, separately shaped sandstone slabs replace the uniform courtyard paving,
  terminal platform surface, north stairs and one shop threshold. Broad material
  variation uses clean/dusty patches and restrained colour variants.
- Shallow sand fans, small gravel, curved dry grass and sheltered plants gather at
  edges and foundations. Existing local grime, wear and aquifer-leak details remain.
- A sagging patched red canopy, brackets, masonry repairs, pipes and a salvaged
  drum planter give the adjoining shop more depth and use.
- Illustrated Karaveen notices, a Ward watch banner, torn paper and handwritten
  factory paint add specific environmental writing. Main notices face the street.
- Sun/ambient balance and a restrained local baked reflection were adjusted.
  A two-sided thin-surface shader gives cloth/plants matching lighting and moving
  shadows; the existing reduced-motion clock controls their wind.

The accepted terminals, all nine actors, gameplay roots, city layout and existing
colliders are retained. The planter adds one capsule collider clear of the entry.
The saved prefab contains 383 authored parts / 945,108 source triangles. These
counts describe source geometry, not visible or submitted geometry. Full Blender,
FBX and texture sources remain available; tiny gravel is currently over-detailed
and is a candidate for measured runtime simplification before wider rollout.

Source/editing guide: [COURTYARD.md](../../../COURTYARD.md).
Reference, original images, exact generation prompts and source-map provenance:
[reference record](../../../../refs/courtyard_20260908/README.md),
[image-generation.json](../../../../refs/courtyard_20260908/image-generation.json),
[material downloads](../../../../refs/courtyard_20260908/materials/download-manifest.json).
Poly Haven CC0 and original generated-art notices are included in both player folders.

## Tested identity and checks

Base commit: `d4b867bb22a1489b5cd05373221b55dbec7bd5d4`, plus the uncommitted courtyard
working tree. [working-tree-identity.json](working-tree-identity.json) records source,
scene and prefab hashes. Both built `level0` files have SHA-256
`a0ae77817e06a6d797f09d487e5afc8e57be47718192a763c6d2cf9006825411`.
Development build GUID: `7e13c4c346014e8d9c8f6675f972f5b3`.
Release build GUID: `c59cc5e2812d4ab2a7b015a4f8e3356f`.

Unity 6000.6.0f1, URP 17.6.0 and OpenGLCore are unchanged. The source assets were
saved before rebuilding render chunks; the scene was closed and reopened and the
source fingerprint remained current. See [reopened-final.json](reopened-final.json).
Both builds succeeded with zero errors: development 3 warnings / 19.80 seconds;
release 1 warning / 17.95 seconds. The Editor log retains deprecated-API warnings,
MCP connection interruptions during builds and JobTempAlloc warnings at shutdown.
These were not observed as runtime exceptions in the tested players.

The [final native report](after-native/report.json) and [walking record](after-native/walking.json)
cover West Gate, hill/north stairs, terminal stands, the shop tread/porch in both
directions, notice approach and service-wall/leak corner. Movement is real keyboard
input; development diagnostics select camera yaw and inspect position/grounding.
The [city-loop check](after-native/city-loop.json) passed all four conversations,
dialogue choices, modal movement blocking, flask purchase, scrap sale, objectives,
both Lattice destinations, Ring Gate's offline response, inventory, notes, pause,
mute, reduced motion and return to West Gate.

The [release smoke test](release-native/report.json) used only real movement,
left-drag orbit, wheel zoom and pause/resume. Image review confirms arrival at the
courtyard and first-person rendering. It ignored `--athen-qa` and left the supplied
QA quit command unconsumed; no diagnostic files appeared. The player closed normally
with exit code 0. [Runtime log review](runtime-log-review.json) records no detected
script exceptions, shader failures or UI parse errors. Monitor DPI warnings remain.

Two earlier route failures are preserved in `attempt-01-native` and
`attempt-02-native`: a checkpoint stopped while the capsule still touched the higher
porch; a later test line crossed an existing crate. Only the test waypoints changed,
using saved collider bounds; height/grounding assertions stayed intact. See
[route-audit.json](route-audit.json). Material/geometry auditions and the original
scene are also retained. No failures were removed to produce the final result.

## Native performance

Host: RTX 3060 12 GiB, NVIDIA 595.84, i9-10850K, approximately 32 GiB RAM,
Ubuntu 24.04. Native 1920×1080, render scale 1.0, PC quality, MSAA 4×,
4096 shadow map / 18 m shadow distance, full texture setting, post-processing on,
HUD/audio/effects and all nine actors active. Editor closed. No frame generation.
The following development-player samples are uncapped, with VSync off.

| Sample | Duration | Frames | Mean FPS | p50 ms | p95 ms | p99 ms | Max ms | >33.33 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Fixed courtyard writing view | 10.18 s | 3,614 | 355.0 | 2.57 | 4.02 | 4.19 | 5.69 | 0 |
| Moving route | 63.36 s | 18,863 | 297.7 | 3.28 | 4.98 | 5.50 | 17.47 | 0 |
| Warmed shop/travel/UI sequence | 25.63 s | 8,701 | 339.4 | 2.49 | 5.04 | 5.52 | 9.08 | 0 |

The recorded samples meet mean FPS ≥60 and p99 ≤16.67 ms. The supplemental sequence
includes 5.29 seconds in Shop (232.4 FPS, p99 5.83 ms) and 6.85 seconds in Grid
(413.9 FPS, p99 3.81 ms). The full interaction sequence warmed those screens before
timing; screenshots/video were outside the timed samples. Cold start/loading time
was not instrumented. This is qualification of these recorded samples on this host,
not an every-route or long-session guarantee.

The first supplemental run inadvertently used the 60 FPS cap and is preserved in
`native-states-capped`: 59.43 mean FPS, p99 16.75 ms, max 127.68 ms, three >33 ms
frames. It also contained screenshots. It is not combined with uncapped results.
The baseline fixed sample used `cam_wear_wall`, whereas the final fixed sample used
`cam_courtyard_writing`; their timings are not a matched-camera performance comparison.

Traversal counters: CPU frame mean 3.36 ms, main thread mean 3.36 ms; submitted
triangles mean 2.35 million, p95 3.51 million, maximum 3.57 million; SetPass mean
53.3, maximum 88. Submitted triangles include rendering passes and are not a visible
triangle count. Draw/batch counters returned nonpositive values; render-thread/GPU
timings were unavailable. None is reported as zero cost.

Process GPU residency sampled at 1,246,969,856 bytes (about 1.16 GiB); RSS 751,560 KiB,
process peak RSS 841,712 KiB. This GPU figure includes more than textures. Resident
texture memory was unavailable. See [performance.json](performance.json),
[hardware.json](hardware.json) and [raw traversal counters](traversal-counters.json).

## Visual review against the supplied target

Ten existing cameras have matched before/after position, lens and 1920×1080 output:
`cam_hill`, `cam_avenue`, `cam_gate`, `cam_grid`, `cam_whompah`, `cam_hero`,
`cam_terminal` and the three `cam_wear_*` views. Four new courtyard/ground/facade/writing
angles supplement them. Lighting changes are intentional. Fixed diagnostic views
retain the live HUD; interaction prompts follow the player, not the diagnostic camera.

- [Matched terminal before](before-native/cam_terminal.png) / [after](after-native/cam_terminal.png).
- [Courtyard](after-native/cam_courtyard.png), [player-height ground](after-native/cam_courtyard_ground.png),
  [facade](after-native/cam_courtyard_facade.png), [writing close-up](after-native/cam_courtyard_writing.png).
- [15-second native walkthrough](after-native/terminal-walkthrough.mp4), 1080p / 30 FPS
  capture with real wheel zoom and strafe. Selected frames at 2, 8 and 12 seconds
  were reviewed for proximity and movement continuity.
- [Release courtyard](release-native/courtyard.png) / [first person](release-native/first-person.png).

Scores use the production guide's 0–5 scale; 4 means strong at the intended distance,
5 means the chosen reference is met. The after column assesses the actual native frame,
including retained content, not just the new assets.

| Category | Before | After | Specific observation / remaining defect |
| --- | ---: | ---: | --- |
| Composition / silhouette | 2 | 3 | Canopy and varied foreground help; the long empty wall and repeated shop masses still dominate. |
| Scale / clearance | 4 | 4 | Existing terminal/actor scale retained; stairs and porch pass grounded traversal. |
| Material detail | 2 | 3 | Better stone variation, edge depth and paper; old facade textures are soft up close and slab seams remain conspicuous. |
| Lighting / depth | 3 | 3 | Warm light, cooler shade and controlled reflection; shaded entrances remain dark and the reference has richer bounce/contact. |
| Density / storytelling | 2 | 3 | Plants, repairs, canopy and readable lore notices add purpose; the surrounding street is still sparse. |
| Characters / animation | 2 | 2 | Existing assignments and motion retained; static talking poses and close character quality remain visible limitations. |
| Temporal stability | — | 3 | Short moving/proximity review shows continuous camera transition; thin plants and detailed seams need a longer shimmer/LOD review. |
| UI / readability | 4 | 4 | Existing HUD and keyboard interactions remain legible and functional. |

This does not reach 4 in every applicable category. The next visual work should
address a complete facade's close-range materials/construction, richer street depth
and purposeful activity, then character idle/turn quality. Extending these courtyard
details alone across the city will not close those larger gaps. No whole-game AAA
or GTA6 parity, delivery schedule or user acceptance is claimed.
