# Phase 0 — repo and Blender probe

Date: 2026-09-07. **Phase 0 acceptance: PASS.** Scope is Phase 0 of `AGENTS.md`;
this is not the playable city MVP. Phases 1–7 remain separate sessions
as required by the guide.

## Blender gate

Passed through the live Blender MCP connection, Blender 5.2.1 LTS, add-on 1.6,
protocol 5. Poly Haven, Sketchfab, and Hyper3D/Rodin settings were all disabled.
The original default scene remains in the saved `.blend`; new work lives in
`AthenHill_Phase0_Probe`. The GLB exports only the selected object in that scene.

| Check | Evidence |
| --- | --- |
| 2 m blue cube | `PROBE_CUBE`, exact decoded runtime bounds `[-1,0,-1]` → `[1,2,1]` |
| Metric / transform | One unit per metre; ground-centred identity node transform |
| Mesh budget | 44 triangles, 96 split vertices, 132 valid indices, no degenerates |
| Materials / UVs | One blue material, metalness 0, roughness 0.78, UV0 and UV1 |
| Runtime file | `public/assets/probe.glb`, 5,564 bytes, one scene/node/mesh/primitive |
| Export copy | `blender/exports/probe.glb`, byte-identical |
| Probe render | `previews/probe.png`, 512×512, visibly grounded blue bevelled cube |
| Named renders | Six `blender/previews/cam_*.png`, each 1280×720 |
| Saved source | `blender/scenes/00_probe.blend` and `blender/probe.py` |

Independent asset review decoded the binary positions/indices, checked materials,
UVs, dimensions and export isolation, and viewed the probe image. A first export
also included the original default scene as a second unused scene; restricting
the exporter with `use_active_scene=True` removed it. The verified final file
contains only the probe.

## Skill-loading ledger

Director: `/Users/carl.draper/.agents/skills/threejs-game-director/SKILL.md` read.
The following sibling `SKILL.md` files under the same root were read:

- `threejs-gameplay-systems`
- `threejs-aaa-graphics-builder`
- `threejs-game-ui-designer`
- `threejs-debug-profiler`
- `threejs-qa-release`
- `threejs-3d-generator`
- `threejs-image-generator`
- `threejs-audio-generator`

The runtime worker read the gameplay, UI, and QA phase references before editing.
The packaged gameplay scaffold was generated in a temporary directory and adapted
to the project's Phase 0 scope. Unrelated starter gameplay was excluded.

## Reference ledger

Paths are relative to `/Users/carl.draper/.agents/skills/`.

| Family | Loaded references |
| --- | --- |
| Gameplay | `threejs-gameplay-systems/references/gameplay-workflows.md`; `checklists/new-game-definition-of-done.md` |
| Graphics foundation | `threejs-aaa-graphics-builder/references/implementation-blueprint.md`; `model-recipes.md`; `render-recipes.md`; `checklists/material-lighting-quality.md`; `checklists/procedural-model-quality.md`; `checklists/performance-safe-visual-detail.md` |
| UI | `threejs-game-ui-designer/references/ui-patterns.md`; `checklists/game-ui-quality.md`; `checklists/hud-readability.md`; `checklists/responsive-ui-fit.md` |
| Debug/profile | `threejs-debug-profiler/references/debug-profile-checklists.md`; `checklists/performance-profile.md` |
| QA/release | `threejs-qa-release/references/qa-release-checklists.md`; `checklists/visual-verification.md`; `checklists/playtest-qa.md`; `checklists/release.md` |

Physics selection and controller references are deferred to Phase 1. Generator API
and integration references are deferred until their relevant asset phases; no
Tripo, Gemini, or ElevenLabs operation was performed. Premium visual scorecards
are deferred; Phase 0 deliberately contains a primitive probe. No skill-generated
premium acceptance is claimed.

## External asset sourcing ledger

Chosen sources follow the user's guide: original Blender MCP geometry, Codex
image generation for later frozen reference frames/textures, original generated
or synthesized audio in the later audio phase. No marketplace model, extracted
game asset, or copied audio is present. The high-value world/player/NPC surfaces,
sky/textures/decals, GUI artwork, and audio have not entered production yet.

Credential probe output: not run in Phase 0 because no external generation service
is needed for the explicitly requested Blender probe. There is no claim that
credentials are missing. 3D generator, image generator, and audio generator skills
were read; the user's prescribed Blender/Codex image pipeline takes precedence
over provider recommendations in those skills.

## Phase ledger

| Work | Current scope and status |
| --- | --- |
| Phase 0 / gameplay systems | Passed: renderer, GLB load, camera/debug foundation |
| AAA graphics | Production art deferred to frozen references and Blender world phases |
| UI | Passed: camera selection/save, loading/error feedback, desktop/laptop/mobile fit; game HUD deferred to Phase 5 |
| Debug/profile | Passed: full-frame counters including shadows, fixed captures, native GPU measurement |
| QA/release | Passed: Phase 0 build and browser checks; public release deferred to Phase 7 |
| Phase 1 | Next session: greybox, movement, collision, full landmark traversal |
| Phases 2–7 | Pending; no city or MVP acceptance implied |

## Visual scorecard boundary

All city palette, silhouette, lighting, density, scale and HUD comparisons for
`cam_hill`, `cam_avenue` and `cam_gate` are **not yet assessable**: frozen references
and city geometry do not exist in Phase 0. The named probe cameras validate the
capture pipeline only. The hill-tree thumbnail acceptance applies when that
asset exists. An empty-scene FPS result cannot satisfy the final 60 FPS city gate.

## Verification evidence

Commands: `npm run build`, `npm audit`, `npm run preview`,
`node tools/verify-phase0.mjs`, and `git diff --check`. All passed. Build uses
Three.js 0.184.0 and Vite 8.0.16. The dependency audit reports zero vulnerabilities.
The initial scaffold's Vite patch was updated before acceptance.

Production preview URL: `http://127.0.0.1:4173/`. Development URL:
`http://127.0.0.1:5173/`. The `View` selector changes the active camera and
`Save frame` creates a real 1920×1080 PNG. All required debug methods and fields
are present. `cameraTransforms` confirms all six cameras are scene objects.

The independent Playwright QA script verified:

- Correct GLB path, exact dimensions, ground-centred bounds and triangle count.
- Visible blue cube using canvas pixel checks and reviewed screenshots.
- Actual UI selection/save path and all six named camera PNG files.
- Concurrent captures queue and restore current view, size, DPR and frame counts.
- Narrow-screen capture is byte-identical to the corresponding desktop capture
  and restores the original mobile projection.
- Landmark debug anchors and rejection of invalid camera/landmark/time inputs.
- Desktop 1920×1080, laptop 1280×720 and mobile 390×844 layout and canvas checks.
- Missing GLB and unavailable WebGL2 display errors with capture disabled.
- Invalid camera, cross-origin writes, incorrect method and malformed PNGs reject.
- Zero console errors, page errors, or failed network responses on the normal path.

Evidence: `tools/shots/phase0-qa.json`, `phase0-desktop.png`, `phase0-laptop.png`,
`phase0-mobile.png`, and all six `cam_*.png`. The packaged inspector additionally
hides UI while sampling pixels to prevent a HUD from making a blank canvas pass.

## Renderer and performance measurements

Native Codex in-app Chromium 152, Apple M4 Max through ANGLE Metal, production
bundle, 1920×1080 drawing buffer, DPR 1: **120.006 FPS** over 241 animation-frame
timestamps (240 intervals, approximately two seconds). The displayed renderer
reported 120 FPS, about 8.2 ms per frame, **3 draws and 90 triangles including
shadow rendering**, 2 geometries and 3 internal textures. Each mesh itself has
44 triangles; the ground adds 2 and the shadow pass renders the cube again.
One 1024² sun shadow map, one hemispheric fill, ACES tone mapping, PCF shadows,
no postprocessing chain, and DPR capped at 1.5 for normal display sizing.

The automated headless Chromium 148 test uses SwiftShader CPU rendering. Its
31.67 FPS result is retained honestly in the JSON report; it is not a laptop GPU
benchmark. Native hardware evidence is recorded in `tools/shots/phase0-native.json`.
Neither probe result establishes the eventual full-city 60 FPS contract on a
medium laptop GPU. That remains an acceptance gate for later phases.

## Corrections and remaining work

Visual QA found portrait clipping; responsive FOV now keeps the whole probe
visible while captures retain the fixed Blender lens composition. Review also
corrected counter resets to include shadow costs and preserved load-error state
if the context fails during GLB loading. The deprecated soft-PCF constant was
replaced with the current PCF constant; the final native bundle has no captured
console warnings or errors.

The build emits a size advisory for the 600.56 kB JS chunk (153.87 kB gzip),
principally Three.js and GLTFLoader. This is recorded rather than hidden; loading
and production preview pass. Optimization and release packaging remain later work.

No walking controller, physics, city geometry, NPCs, inventory/shop, travel, music,
or frozen art references exist yet. `player` and `goto` represent debug anchors;
they do not prove character traversal. All Phase 1–7 acceptance remains pending.
