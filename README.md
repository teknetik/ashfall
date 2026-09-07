# Athen Hill

An original 2001 sci-fi MMO homage city slice, built with TypeScript, Vite,
Three.js and Rapier. Production meshes will be authored through Blender MCP.

**Current milestone: Phase 1 — greybox city, movement and collision.** Explore a
120 × 90 m city block with a raised tree plaza, shop porches, two west gate
tunnels, Vanguard Hall, a Ring Gate and a Lattice Jack. Geometry is deliberately
untextured and primitive. Concept art, authored characters, NPC dialogue, shop
transactions, travel effects and audio are later phases.

## Run locally

Requires Node 22.12+ (verified with Node 22.22.3).

```sh
npm ci
npm run dev
```

Development: http://127.0.0.1:5173/. To test the production bundle:

```sh
npm run build
npm run preview
```

Production preview: http://127.0.0.1:4173/.

## Controls

- **WASD / arrows**: walk relative to the camera.
- **Shift**: run.
- **Hold right mouse + drag**: rotate the camera. Pointer lock is unnecessary.
- **Esc / Pause**: pause or resume.
- **R / Return to gate**: reset position and movement.
- **Touch**: directional buttons to walk, hold Run to sprint, drag the city to look.
- **Survey tools**: select a fixed view and save a 1920 × 1080 frame.

Spawn at West Gate, walk east up the avenue to the Hill Tree, take the stairs
onto the plaza, head south to the Ring Gate, then north to the Lattice Jack.
The outer avenues pass around the hill. Porches and the two west tunnels are
walkable; buildings and perimeter walls block movement.

## Architecture and diagnostics

`src/layout.ts` defines safe landmark foot positions and collision data types.
`src/world.ts` batches static primitive geometry by material and supplies separate
simple collision proxies. `src/physics.ts` owns Rapier, `src/player.ts` owns the
kinematic capsule, `src/input.ts` collects keyboard/pointer/touch intents, and
`src/camera.ts` owns fixed cameras and the follow boom. `src/game.ts` runs input →
fixed physics → camera → render; `src/ui.ts` and `src/debug.ts` expose state.

World convention: one unit per metre, Three.js Y-up, north is negative Z. Player
positions use the **feet**, not the capsule centre. The controller is 1.8 m tall,
radius 0.35 m, with 0.3 m autostep, 45° maximum climb slope and 0.4 m ground snap.
Walk speed is 3.4 m/s, run speed 6 m/s. Physics advances at 60 Hz with frame delta
capped at 100 ms. The 4.2 m camera boom uses a 0.23 m sphere sweep.

The browser exposes `window.__ATHEN__`:

```js
await __ATHEN__.ready
__ATHEN__.player           // feet, yaw, grounded, velocity, contacts
__ATHEN__.renderer         // FPS, frame time, draws, triangles, buffer size
__ATHEN__.physics          // engine, timestep, body/collider counts, tuning
__ATHEN__.camera           // orbit, boom distance, obstruction, target
__ATHEN__.landmarks
__ATHEN__.goto('shop_row_e')
__ATHEN__.nearbyColliders(3)
__ATHEN__.view('cam_avenue')
await __ATHEN__.shot('cam_avenue')
__ATHEN__.view('follow')
__ATHEN__.pause(true)
__ATHEN__.reset()
```

Required named scene cameras: `cam_gate`, `cam_avenue`, `cam_hill`, `cam_grid`,
`cam_whompah`, `cam_hero`. The debug contract retains the guide's landmark IDs;
visible travel names are Lattice Jack and Ring Gate.

`shot(name)` saves under `tools/shots/` through a loopback-only Vite endpoint in
dev and preview. A static host downloads the PNG instead of claiming a local
repository write. Screenshot capture restores the active camera, canvas size,
pixel ratio and player visibility. Survey/debug tools deliberately remain in
this development milestone; public release packaging is Phase 7.

## Verification and phase evidence

With preview running:

```sh
npm run verify:phase1
npm run verify:physics
npm run inspect:canvas -- --url http://127.0.0.1:4173/
```

If the test browser is absent: `npx playwright install chromium`.

- `docs/phase-1.md`: current acceptance, diagnostics and limitations.
- `tools/verify-phase1.mjs`: real keyboard route, stairs, porches, tunnels,
  walls, camera collision, pause/reset/blur, touch and capture checks.
- `tools/shots/phase1-qa.json`: browser verification report and trace.
- `tools/physics-regressions.json`: ground stability, stair, wall and camera regressions.
- `tools/shots/phase1-native.json`: native GPU performance samples.
- `tools/shots/cam_*.png`: current fixed city views.
- `docs/phase-0.md`: accepted Blender probe evidence; the original source,
  export and renders remain under `blender/` and `previews/`.
- `tools/shots/phase0/`: archived Phase 0 named browser views.

The original `tools/verify-phase0.mjs` is historical and targets the Phase 0
commit; its cube-specific assertions do not apply to the city runtime.

## Next phase

Phase 2 freezes eight original concept frames under `refs/`; those images guide
the later Blender world and character work. No frozen image has been generated
or accepted in Phase 1. The project guide requires separate sessions and commits
for each accepted phase.

The finished-city target remains 60 FPS at 1920 × 1080 on a medium laptop GPU,
≤250,000 visible triangles and ≤80 draw calls. Greybox/native-host measurements
are evidence for this phase only; they do not establish performance with final
assets and NPCs.
