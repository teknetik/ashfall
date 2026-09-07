# Phase 1 — greybox city, movement and collision

Date: 2026-09-07. **Phase 1 acceptance: PASS.**
Scope is Phase 1 of `AGENTS.md`, following the accepted Phase 0 commit `c77f946`.
This session does not start Phase 2 or claim final MVP/art acceptance.

## Playable slice and implementation

Walk from West Gate to the raised Hill Tree plaza, descend to the Ring Gate,
and follow an outer avenue north to the Lattice Jack. The scene contains all
named landmarks as untextured primitives, real staircase treads, shop porches,
shallow storefront interiors and two standable gate tunnels. Walls and roofs
have separate collision proxies. The player is a capsule scale marker.

Input → fixed character movement/physics → follow camera → render is explicit
in `game.ts`. Rapier 0.20.0 uses a kinematic capsule, 1.8 m height, 0.35 m radius,
0.015 m separation, 0.3 m autostep, 0.22 m minimum landing width, 0.4 m ground
snap, 45° maximum climbing slope. Walk/run speeds are 3.4/6 m/s; gravity is
-20 m/s² with a 30 m/s terminal fall speed. The fixed tick is 1/60 s; the frame
accumulator accepts at most 100 ms of wall time per frame. Hidden tabs discard
accumulated time and release input. No jump or combat is added.

The follow boom is 4.2 m, looking at feet +1.5 m. A sphere cast with radius
0.23 m avoids walls and corners; the boom contracts immediately and extends
smoothly after clearing an obstacle. Very close obstruction hides the capsule
marker to avoid seeing its inside. Named captures force marker visibility and
restore it afterward. Follow FOV caps at 85° on narrow screens.

The original Blender probe is retained as pipeline evidence. The live Blender
MCP read at phase entry succeeded and showed `AthenHill_Phase0_Probe`, including
`PROBE_CUBE` and all six cameras. No Blender geometry session was performed:
Phase 1 explicitly calls for raw primitives inside the game. The saved Blender
blockout and authored art belong to the later Blender-world phase.

## Skills, references and sourcing ledger

Loaded from `/Users/carl.draper/.agents/skills/`:

| Skill | Execution in this phase |
| --- | --- |
| `threejs-game-director/SKILL.md` | Phase scope, delegation, evidence gates |
| `threejs-gameplay-systems/SKILL.md` | Movement, physics, camera and runtime |
| `threejs-game-ui-designer/SKILL.md` | Controls, pause, survey tools, touch layout |
| `threejs-qa-release/SKILL.md` | Production preview and browser verification |

Required references read before the relevant implementation/QA:

- `threejs-gameplay-systems/references/gameplay-workflows.md`
- `threejs-gameplay-systems/references/physics-engine-selection.md`
- `threejs-gameplay-systems/references/checklists/new-game-definition-of-done.md`
- `threejs-game-ui-designer/references/ui-patterns.md`
- `threejs-game-ui-designer/references/checklists/game-ui-quality.md`
- `threejs-game-ui-designer/references/checklists/hud-readability.md`
- `threejs-game-ui-designer/references/checklists/responsive-ui-fit.md`
- `threejs-game-ui-designer/references/checklists/mobile-input.md`
- `threejs-qa-release/references/qa-release-checklists.md`
- `threejs-qa-release/references/checklists/visual-verification.md`
- `threejs-qa-release/references/checklists/playtest-qa.md`
- `threejs-qa-release/references/checklists/release.md`
- `threejs-aaa-graphics-builder/references/checklists/procedural-model-quality.md`
- `threejs-aaa-graphics-builder/references/checklists/material-lighting-quality.md`
- `threejs-aaa-graphics-builder/references/checklists/performance-safe-visual-detail.md`

Physics API was checked against the installed declarations and official Rapier
[character-controller documentation](https://rapier.rs/docs/user_guides/javascript/character_controller/).

External asset sourcing: original runtime primitives only, as requested for
Phase 1; no texture, external mesh, generated concept or audio production.
Generator credentials were not probed because no provider operation is required,
and none is reported missing. No premium visuals are claimed. Production world,
characters, UI artwork and audio remain in the guide's later phases.

## Phase ledger

| Work | State |
| --- | --- |
| Phase 0 | Accepted previously; probe sources/renders preserved |
| Phase 1 gameplay | Passed; continuous route and numerical regressions below |
| Phase 1 debug/UI | Player/fixed views, capture, pause/reset and touch controls |
| QA | Passed: production browser route, collision, inputs, captures and responsive checks |
| Phase 2 | Deferred to separate session; frozen refs not accepted here |
| Phases 3–7 | Authored world/characters, dialogue/shop, beauty/audio, release pending |

## Acceptance evidence

Commands passed: `npm run build`, `npm run verify:physics`,
`npm run verify:phase1` (against production preview), and `git diff --check`.
Dependency installation/audit reported zero vulnerabilities. The production
preview remains at `http://127.0.0.1:4173/`.

The final browser run lasted 144.2 seconds. Its uninterrupted keyboard route
lasted 69.1 seconds, traversed West Gate → Hill Tree → Ring Gate → Lattice Jack,
and used **zero teleports**. All 720 sampled gameplay states stayed on or above
the floor (minimum foot Y approximately +0.015 m), with conservative capsule
separation checks against the static proxies. Peak sampled cost was 25 draw
calls and 12,768 triangles, including shadows.

| Check | Result |
| --- | --- |
| Six 25 cm hill steps up, south stairs down | Grounded at the expected elevations |
| Shop porch, doorway and 2 m stage floor | Walkable in both directions |
| West gate tunnel | Traversable with 1.8 m standing headroom |
| Full sprint into perimeter wall | Stops at x57.635 m; no tunneling |
| Diagonal wall movement | Slides along wall while maintaining separation |
| Camera obstruction | Retracts to 0.455 m in shop, extends back to 4.2 m outside |
| Keyboard | WASD, arrows, Shift, RMB orbit, Escape pause/resume and R reset pass |
| Input lifecycle | Blur clears movement; pause freezes simulation; reset keeps one body/controller |
| Touch | A real touch hold moves the capsule; release and cancellation stop movement |
| Captures | All six 1920 × 1080 PNGs saved, queued, and restored view/projection/size/DPR/player visibility |
| Survey controls | Real view selector and save button work; returning to player view works |
| Responsive | 1920 × 1080, 1280 × 720 and 390 × 844 render nonblank; controls fit |
| Console/page/network errors | Zero on the final normal path |

Evidence: `tools/shots/phase1-qa.json`, `phase1-active-desktop.png`,
`phase1-laptop.png`, `phase1-mobile-active.png`, `phase1-camera-occlusion.png`,
`phase1-gate-tunnel.png`, and all six `cam_*.png`. The controller regression
suite and results are `tools/verify-physics.mjs` and
`tools/physics-regressions.json`.

## Defects found and corrected

The first full route exposed real lateral drift on flat ground before touching
the Basic General porch. A numerical fixture reproduced this with only the
capsule and the 120 × 0.6 × 90 m ground box present: six seconds of exact east
input produced 0.498 m lateral drift, 19 stalled ticks and feet briefly 0.018 m
below pavement. This was specific to that Rapier capsule/large-thin-box query
setup; it is not a claim about all Rapier character controllers.

The final ground proxy is an explicit upward `HalfSpace` at Y=0. The visible
floor and perimeter wall colliders stay the same. With the same movement and
adhesion settings, the three six-second direction tests have no stalled ticks,
less than 0.002 m lateral error, and feet consistently 0.01–0.02 m above paving.
Stair ascent/descent, sprint, sliding, camera sweep, teleport cleanup and a
non-climbable 0.5 m lip also pass. The old-box failure is retained in the numeric
report and `tools/shots/phase1-attempts/` for comparison.

Independent review also found a missing raised floor behind shop porches and
an avenue camera looking through a building. The stage floors now extend to
the back walls. `cam_avenue` moved into the clear central lane and farther back
to include the tree crown. Escape/R now work when survey controls hold focus,
and keyboard repeat no longer repeatedly resets camera extension smoothing.

## Visual scorecard and performance

These are **greybox scores against the written brief**, not matches to accepted
concept paintings. Frozen-reference palette and light-direction matching remain
N/A until Phase 2. Independent critic and final screenshot review agree that
the tree, raised steps, shop rows and twin gate openings are readable. The tree
remains recognizable at thumbnail size.

| Trait (0–5) | Hill | Avenue | Gate |
| --- | ---: | ---: | ---: |
| Palette against brief | 4 | 4 | 4 |
| Sky/haze | 3 | 3 | 3 |
| Landmark silhouette | 4 | 4 | 4 |
| Key-light readability | 4 | 4 | 4 |
| Matte roughness | 4 | 4 | 4 |
| Greybox density | 3 | 3 | 3 |
| Metre/human/door scale | 4 | 4 | 4 |
| Phase 1 controls readability | 4 | 4 | 4 |
| Native FPS at 1080p | 120.01 | 119.99 | 120.00 |

Native Codex Chromium 152 on Apple M4 Max/ANGLE Metal, production bundle,
1920 × 1080 drawing buffer at DPR 1: active avenue walking measured **120 FPS**
over 180 frame intervals/1.5 seconds, p95 8.4 ms, 24 draws and 12,724 triangles.
That sample injected DOM keyboard events; the separate full route used actual
Playwright keyboard/mouse input. The three hero-camera samples used 120 frame
intervals each and cost 21–24 draws / 11,780–12,724 triangles. Native captured
warning/error logs were empty. Evidence: `tools/shots/phase1-native.json`.

The automated headless browser used SwiftShader CPU rendering and measured
18.03 FPS. This is retained in its report and is not treated as a native GPU
benchmark. Native M4 Max samples exceed the Phase 1 58/60 FPS threshold on this
host; a medium laptop with final assets and all NPCs still needs qualification.

Renderer: 11 batched static material families, one original probe mesh, capsule
and direction marker; 14 geometries, three internal textures, one 2048² sun
shadow map, one hemisphere fill, ACES tone mapping and no postprocessing. No
authored textures or real-time GI were added. Physics has one kinematic body,
one controller, 193 static colliders (194 including the player), no sensors and
no CCD bodies; movement collision uses the character controller's shape sweeps.

## Remaining scope and limitations

Phase 1 is complete. There are no production character meshes, NPCs, conversations,
shop transactions, travel effects or audio yet. The flat sky, block geometry and
simple tree deliberately await the frozen concept and Blender phases. No final
beauty/MVP acceptance is claimed.

The JS bundle is 3,487.71 kB / 1,260.74 kB gzip, mainly Three.js plus Rapier's
embedded WASM. Vite reports a large-chunk advisory; boot and production preview
pass. Public release packaging, payload optimization and debug gating remain
Phase 7. This local milestone intentionally exposes survey tools/debug methods.
Real mobile hardware and the target medium laptop have not been tested.
