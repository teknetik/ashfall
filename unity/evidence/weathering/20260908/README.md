# Localized Ward weathering · 8 September 2026

The saved native scene now includes localized sand, foundation grime, standing
scuffs, wall runoff, material variation, sheltered weeds and layered Ward notices.
Both Linux players were rebuilt after final placement adjustments and passed the
checks below. This completes the focused wear installation; the district's wider
contemporary visual target still requires further art work and user review.

## Installed content and editing

- **Ward surface wear** contains 61 editable URP Decal Projectors. Sand follows
  stair edges and the mission slab; grime surrounds the three terminal bases.
  Scuffed standing areas and the central walking routes remain accessible.
- Three stone/paving material variants retain the source textures and normal
  maps with a broad world-space variation mask. The glTFast stone material needs
  explicit property translation into URP Lit; that correction is included.
- Ten dry and two green clumps reuse the existing hill-grass geometry and wind
  shader. Green growth is confined to a small aquifer service fitting and damp
  patch. New details add no gameplay collision.
- Older Tube Authority paint sits behind Warden and Karaveen notices. An aquifer
  notice marks the green patch. The graffiti reads **THE FACTORIES NEVER HEARD
  THE ORDERS STOPPED.**, avoiding an invented war origin for the Fall. Paper is
  represented by flat decals with worn outlines; curled paper meshes are absent.
- Terminal dirt opacity was increased from 0.48 to 0.8 and standing scuffs from
  0.3 to 0.48 during final review. Paper proportions were corrected to 4:3 and
  graffiti moved clear of the pillar. `installation.json` records the initial
  installation; the saved scene and `WardWeatheringPass.PolishNotices` record
  these later placement changes.

The Screen Space decal feature uses Medium normal reconstruction under the
existing OpenGLCore/URP 17.6 configuration. **Intermediate Texture = Always**
avoids a missing color target in URP's fixed-camera render path. The custom Lit
derivative preserves the installed package's lighting interfaces and adds broad
variation in its Forward pass. A later rendering-path change needs shader review.

Original atlas, generation prompt and exact-text SVG sources are preserved in
`refs/weathering_20260908`. Shader derivatives retain Unity's license. No supplied
Meshy model or source map was downsampled for this pass. See
[editing controls](../../../EDITING.md#localized-ward-surface-wear--8-september-2026).

## Native evidence

The tested saved working tree is based on `798f8f0302c99e79ddd0b3d2bf604e5ecff884fb`.
[final-identity.json](final-identity.json) records hashes of the scene, renderer,
weathering assets and built data. It includes the concurrent Meshy fidelity
restoration, settings and other existing work. Hashes were checked again after
the native tests and matched. This is not an isolated weathering-only A/B build.

| Evidence | Result |
| --- | --- |
| [Development build](development-build.json) | Succeeded; 0 errors, 1 warning |
| [Release build](release-build.json) | Succeeded; 0 errors, 3 warnings |
| [14-waypoint keyboard route](after-native/walking.json) | West Gate, hill stairs, terminal standing areas, service wall and leak corner passed |
| [29 city-loop checks](after-native/city-loop.json) | Four dialogues, modal blocking, flask purchase/scrap sale, Lattice, offline Ring Gate, objectives, pause, pack/notes and reset passed |
| [Native report](after-native/report.json) | Nine actors, full 1920×1080 render scale; ten named camera captures |
| [Release smoke](release/report.json) | Nonblank rendering and real keys passed; development QA option ignored |
| [Moving terminal review](after-native/terminal-walkthrough.mp4) | 15 seconds, 1920×1080 at 30 FPS; real wheel zoom into first person and strafing |

The saved scene was reopened before final adjustments and both builds; the render
chunk freshness guard passed. Initial install checks recorded unchanged gameplay
and collider signatures. Final logs contain no runtime exceptions. The development
shutdown log retains Unity's small immediate-allocation diagnostic; it is not a
measurement of gameplay memory or loading performance. Build warnings remain
recorded above rather than being described as warning-free.

Views: [terminal before](before-native/cam_wear_terminal.png),
[terminal after](after-native/cam_wear_terminal.png),
[stairs after](after-native/cam_wear_steps.png),
[service wall after](after-native/cam_wear_wall.png),
[first-person terminal](after-native/first-person-terminal.png).
The seven canonical cameras and terminal/stair close-ups retain their matched
positions, lens and 1080p output. The wall camera was relocated to frame the
service bay, so its earlier image is **not** a matched comparison. Original
`before-scene.unity` and `before-PC_Renderer.asset` remain recovery sources;
do not restore them wholesale over unrelated subsequent edits.

## Measured performance

RTX 3060 (12 GiB), i9-10850K, NVIDIA 595.84, Linux/OpenGLCore, Unity 6000.6.0f1,
PC quality, 1920×1080 at render scale 1.0, 4× MSAA, 4096 shadow resolution,
18 m shadow distance, full texture resolution and post processing. Nine actors,
HUD, shadows and atmosphere were active. VSync and frame cap were disabled in
isolated QA preferences; user preferences were preserved. Video encoding ran
after the timing samples.

| Sample | Duration / frames | Average FPS | p50 / p95 / p99 ms | Max ms | >33.33 ms |
| --- | --- | --- | --- | --- | --- |
| Warm fixed wall view | 10.18 s / 4,358 | 428.08 | 2.18 / 3.08 / 3.54 | 4.25 | 0 |
| Real-input route, including waypoint pauses | 61.00 s / 21,170 | 347.08 | 2.77 / 4.10 / 4.62 | 9.41 | 0 |
| Separate city-loop / modal sequence | 29.49 s / 11,471 | 388.98 | 2.32 / 3.84 / 4.73 | 114.93 | 3 |

Moving frames alone comprise 37.50 s / 12,859 frames: 342.91 FPS, p99 4.70 ms.
The measured route passes average ≥60 FPS and p99 ≤16.67 ms on this recorded
host/profile. [The additional city-loop timing](after-verbs/report.json) includes
dialogue, shop, travel, pause, inventory and notes states in a separate launch at
the same settings. Its shop/travel p99 times were 3.50/3.87 ms. Three 107–115 ms
hitches were recorded, one each in dialogue, shop and travel. The test also makes
synchronous screenshot captures in those three states, so this evidence does
not isolate ordinary UI transition hitches from capture overhead. The raw samples
retain those frames. The earlier baseline was capped at 60 FPS on a contended
host and must not be used to infer a speedup.

Mean CPU frame/main-thread times were 2.88/2.88 ms. Mean submitted triangles
across passes were 433,930 (max 961,999), and SetPass averaged 38.91 (max 58).
Visible-only triangles, draw calls, batches, GPU/render-thread timings, resident
texture memory, peak process RAM and loading duration were unavailable. All-zero
or invalid counters are not evidence of zero cost. A single `nvidia-smi` sample
reported 1,035 MiB for this player; it includes all GPU allocations, not just
textures, and is not a peak. Raw profiles and [qualification.json](qualification.json)
retain these distinctions.

## Visual review and remaining defects

Scores use the production guide's 0–5 scale against the contemporary target,
assessed at the terminal, stair and wall close-ups. They support review and are
not a claim of user acceptance or whole-game quality parity.

| Category | Score | Observation |
| --- | --- | --- |
| Composition / silhouette | 3 | Clear existing landmarks and local detail placement; broad paving remains repetitive |
| Scale | 4 | Small deposits, notices and clumps fit pedestrian scale; no route obstruction |
| Material detail | 3 | Paving variation and local grime connect the terminals to the ground; coarse stone normals and simple paper still limit proximity quality |
| Lighting / depth | 3 | Wear reads in sun and shade; the existing warm lighting remains broad and uniform |
| Density / storytelling | 4 locally | Sand collects at edges, growth is sheltered, and notices identify Ward's services; wider street density remains sparse |
| Characters / animation | 2 | Existing static talking poses and simple vegetation geometry remain visible; this pass does not replace them |
| Temporal stability | 3 | No obvious new decal flicker in the short moving sample; longer traversal and distant fading were not exhaustively reviewed |
| UI / readability | 4 | Existing HUD remains usable; notices are readable at the service-wall viewpoint |

The changes improve localized wear without resolving the existing tree structure,
repeated facade design, coarse close-up stone, simple grass blades or static NPC
poses. The new notices are deliberately restrained but remain fairly flat and
clean at close range; richer torn paper and hand-painted lettering are further
art work. Do not present the successful functional/performance checks as visual
acceptance of those remaining limitations.
