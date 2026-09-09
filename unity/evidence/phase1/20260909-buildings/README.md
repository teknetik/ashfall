# Building continuation — 9 September 2026

Basic General and Relay Works have saved, editable native frontage auditions. Six
other stores have individually authored Blender replacements, and Vanguard Hall
has a repaired source. Those seven sources remain staged outside the active scene.
Finery retains its separate unfinished review. **No building is newly accepted by
this record, and Phase 1 remains open.** See the [ten-building ledger](../../../../docs/building-repairs-20260909.md).

## Exact build and changes

The [final identity](final-build-identity.json) records working-tree file hashes
over base commit `d4b867bb22a1489b5cd05373221b55dbec7bd5d4`; this is not a clean
commit build. The saved scene SHA-256 is
`536e62a6b8c0982689217879d1f35abb7a0e9abb1f52f7f4e3eb7cfa9704d909`.
Existing uncommitted courtyard, actor, tree, lighting and surface work is retained.

| Installed frontage | Source / runtime change |
| --- | --- |
| Basic General | Source v3, 386 separate parts / 193,912 triangles. Readable separate lettering, supported cloth, masonry, stock and threshold; uniform fit with the original six gameplay colliders retained. |
| Relay Works | Revision 02 plus revision 04 door seal, 650 parts / 159,764 triangles. Original parcel, uniform fit, separate entrance/roof/services/sign. Nine explicit collider proxies replace the disabled warped shell collider; original porch and steps remain. |

Blender geometry was authored through the live Blender connection and installed
through the live Unity Editor connection. Source geometry/materials, prefabs and
previous versions remain editable. Render chunks were rebuilt and the saved scene
was reopened. The corrected conversion maps Blender `(x,y,z)` to Unity
`(-x,z,-y)`, reversing triangle winding and transforming normals before tangent
recalculation. The initial mirrored lettering is retained as failed evidence in
`basic-general-native`; it is not the final result.

[Preservation comparison](preservation-comparison.json) records all nine actor
transforms unchanged, no lost collider IDs, seven rejected district candidates
still inactive and both existing gate arches active. The [export-position comparison](export-fix-preservation.json)
confirms its two visual parts changed no actors, colliders or candidate states.
Old visuals and mesh assets remain recoverable.

The [development](final-development-build.json) and [release](final-release-build.json)
Linux builds both succeed with zero errors, three development warnings and one release warning (28.67 / 28.30 s).
Build and runtime warnings are retained, including reduced punctual-shadow atlas
resolution; see [warning notes](final-warning-summary.txt) and the original logs.

## Visual evidence and its limits

The corrected final set contains 28 clear native 1920×1080 frames: seven original overview
cameras, six Basic General audit cameras, six Relay audit cameras and nine
supplemental Relay views. [Capture records](verified-native/building-pass-captures.json)
retain camera/state snapshots and image hashes; [validity](verified-native/capture-validity.json)
confirms Play state for every frame. Cameras, noon sun and exposure were preserved
for comparable views. The game HUD remains visible.

The initial baseline attempted 67 frames, but focus loss paused the player during
47 captures. Only 20 are valid unobscured views, including all six Basic General
views. [Baseline validity](baseline-native/capture-validity.json) identifies the
failures; paused images must not be presented as valid matched before evidence.
The final native capture tool now refuses paused captures. The starting saved
scene is preserved in [before-scene.unity](before-scene.unity).

The six store [front comparison](store-sources-front.jpg) is **Blender source
evidence**. Door, left, right, rear and roof contact sheets accompany it; each
retains six separate original PNG views. [Source review](source-review.md) lists
the geometry repairs and remaining defects for every store. Contact sheets show
revision 02. Revision 04 adds correctly positioned door meeting strips where needed, with its own
close-up and part record; the older images are not silently relabelled.

Native [visual review](visual-review.json) keeps material and shaded-lighting
scores at 2.5/5. Blank rear/side walls, limited stock/working props, dark windows
and unfinished service details prevent representative-frontage acceptance.
The six stores and Hall require individual native fitting, material, collision
and moving-view reviews. Plain source geometry is not accepted merely because
its lettering and dimensions are correct.

## Native gameplay and measured performance

The final build passes the real-input [warm-up](verified-native/warmup-route.json)
and [measured traversal](verified-native/measured-route.json) through all ten building
approaches/porches, hill stairs, mission slab and the retained district route.
All nine actors, HUD, shadows and existing effects remain active. The day clock
is held at noon for comparison; simulation time is 1.0 and actors keep moving.

The [134.57-second uncapped traversal](verified-native/traversal-performance.json)
records 24,519 frames on the RTX 3060 / i9-10850K host, with the authoring apps
closed: native 1920×1080, OpenGLCore, render scale 1.0, MSAA 4, full texture setting,
4096 main shadows / 18 m distance, VSync off, no frame generation.

| Metric | Final traversal |
| --- | ---: |
| Average FPS | 182.20 |
| p50 / p95 / p99 | 4.44 / 10.11 / 12.02 ms |
| Maximum | 21.78 ms |
| Frames over 33 / 50 ms | 0 / 0 |
| Main-thread / CPU mean | 5.49 / 5.49 ms |
| GPU time / render-thread time | Unavailable |
| Draws / batches / resident texture bytes | Unavailable |
| Submitted triangles, mean / maximum | 7.67 M / 25.24 M across renderer passes |
| SetPass mean / maximum | 54.29 / 125 |

This traversal meets the current average and p99 criteria on this host. It is
not a visual acceptance or an all-condition performance qualification. Main-thread
time includes waits; submitted triangles are not visible source triangle counts.

The separate [real-input city loop](verified-native/city-loop.json) passes four
dialogues, movement blocking in modals, flask purchase, scrap sale, inventory,
notes, pause, audio/reduced-motion controls, Lattice travel and Ring Gate's offline
response. [Interaction timing](verified-native/interaction-performance.json) retains
all states separately. Its maximum is 136.41 ms. The retained [hitch record](verified-native/interaction-hitches.json) records Dialogue 136.41 ms, Shop 109.47 ms, Grid 125.76 ms. These transition hitches remain open and are not hidden by the traversal result.

The verified [Relay clip](verified-native/relay_works-first-person-motion.mp4) and [Basic General porch-approach clip](verified-native/basic_general-approach-first-person-motion.mp4) each contain 10 seconds of native 1080p/30 FPS real input. [Door contact](verified-native/door-contact.json) confirms sustained forward input stops at the closed Relay proxy with 0.000000 m continued displacement. The Basic General direct diagnostic clip overlaps Mira and is marked invalid; the replacement uses the real porch approach. Her existing placement partly obscures the counter view.

[Hardware and memory](verified-native/hardware.json) records driver 595.84, 12 GiB VRAM, native process GPU allocation 1.74 GiB and RSS 2.10 GiB after the route and interactions. GPU allocation is not a texture-residency measurement. Loading was kept outside the warmed timing sample; no separate loading-time qualification is claimed.

The shipping [release smoke test](release-native/report.json) passes startup, nonblank rendering and real keyboard input, with no runtime exceptions. The release ignores the development QA option and creates no command snapshot. [Startup](release-native/startup.png) and [pause](release-native/pause.png) captures are retained. This bounded smoke test supplements the development-player route and interaction assertions.

## Provenance and recovery

Original sources and production scripts live under
`art/quality_20260909/basic-general`, `relay-family` and `vanguard-hall`.
[Store revision manifest](../../../../art/quality_20260909/relay-family/store-variants-04/manifest.json)
tracks each replacement. Shared material provenance remains in
[THIRD_PARTY_LICENSES.txt](../../../AthenHill/Assets/AthenHill/Art/THIRD_PARTY_LICENSES.txt),
including the original 4k Fabric Pattern 07 maps. No source maps were discarded
to create these runtime frontages. Original rejected Meshy candidates and their
[rejection record](../../../../meshy/district-20260908/README.md) are preserved.

Earlier subdirectories record intermediate builds. In particular, the
`relay-native` traversal and first-person images predate the two-part door seal.
The folder named `final-native` predates the export-position correction and retains the failed first-person seam. Its original identity is `before-export-fix-final-build-identity.json`. Evidence in `verified-native` belongs to the corrected final development build above.
