# Athen Hill

An original 2001 sci-fi MMO homage city slice, built with TypeScript, Vite, Three.js,
and meshes authored through a live Blender MCP session.

**Current milestone: Phase 0 — repo and Blender probe.** This build is a pipeline
test. The city, walking controller, characters, shops, travel interaction, and
audio belong to later phases. `AGENTS.md` is the project specification and requires
separate sessions and a commit for each accepted phase.

## Run locally

Requires Node 22.12+ (verified with Node 22.22.3).

```sh
npm ci
npm run dev
```

Open the local URL printed by Vite. The blue cube must load from
`public/assets/probe.glb`; asset-loading failures are surfaced in the page.
The default development URL is `http://127.0.0.1:5173/`; production preview is
`http://127.0.0.1:4173/`.

```sh
npm run build
npm run preview
```

The preview runs the production bundle. This Phase 0 build deliberately includes
debug instrumentation. Production UI and deployment are Phase 7 work.

With preview running, verify the pipeline with `node tools/verify-phase0.mjs`.
This writes a report and screenshots into `tools/shots/`. If the Playwright
browser is absent, install it with `npx playwright install chromium`.

## Phase 0 controls and debug contract

Choose a named view, then save its frame. The six cameras are real scene objects:
`cam_gate`, `cam_avenue`, `cam_hill`, `cam_grid`, `cam_whompah`, and `cam_hero`.
During Phase 0 they frame the probe; the city compositions come in Phase 1.

The browser console exposes `window.__ATHEN__` with `version`, `state`, `player`
(`x`, `y`, `z`, `yaw`), `fps`, `draws`, `tris`, `shot(name)`, `goto(landmark)`, and
`timeOfDay`. The player currently represents a debug anchor, not a character.
Movement and collision will be implemented in Phase 1.

`shot(name)` saves a PNG under `tools/shots/` through a local Vite endpoint in dev
and preview. A static host cannot write into this repository; see the in-page
capture feedback when a capture service is unavailable. The endpoint accepts only
the six named cameras and is served on loopback.

World convention: Three.js uses Y-up, one unit per metre. Map north is negative Z
(the guide's positive north/south layout coordinate is negated); Blender sources use Z-up and are
converted by the glTF exporter.

## Blender source and evidence

- `blender/probe.py`: reproducible script for execution inside Blender MCP.
- `blender/scenes/00_probe.blend`: probe scene with the original scene retained.
- `public/assets/probe.glb`: runtime mesh; original geometry, 2 m on each axis,
  ground-centred origin, unit scale, one material, two UV layers.
- `blender/exports/probe.glb`: identical export copy.
- `previews/probe.png`: required 512×512 probe render.
- `blender/previews/`: probe plus six fixed-camera Blender renders.
- `blender/probe-metadata.json`: dimensions, triangles, cameras and provenance.
- `tools/shots/`: browser captures and QA artifacts.
- `docs/phase-0.md`: acceptance evidence, skill/reference ledger, and remaining work.

Run `blender/probe.py` through the connected Blender MCP code executor with its
`__file__` set to its absolute path. It uses a new scene and refuses to overwrite
an existing probe scene. To reproduce, use a fresh Blender scene/file without an
`AthenHill_Phase0_Probe` scene, and retain accepted artifacts before a new version.
No Blender CLI or procedural runtime substitute satisfies the MCP gate.

## Next phase

Phase 1 builds the greybox layout, capsule movement, gravity, camera collision,
stairs, porches, and gate tunnels. Acceptance requires walking west gate → hill →
Ring Gate → Lattice Jack without falling through. Frozen references follow in
Phase 2; authored environment and characters follow those references.

The city performance target remains 60 FPS at 1920×1080, ≤250,000 visible triangles
and ≤80 draws. An empty-scene measurement cannot establish that target for the
finished city.
