# Docs snippet for the orchestrator (night lighting and ambient life, 1 October 2026)

## For unity/EDITING.md

## Night lighting and ambient life (1 October 2026)

**Ward night life** (scene root, not a render-chunk source) lights the pockets that fell to moonlight at night and adds
small working effects. Children:

- **Street lamps** / **Wall lamps**: prefab instances of `Prefabs/NightLife/NL_StreetLampPost` and `NL_StreetLampWall`,
  merged-part versions of the authored Ward utility post and wall fixture (`Art/Quality/Lamps`; the five avenue lamps
  still use the 103-part originals as chunk sources). Three LODs (post 35.7k / 19.6k / 4.1k triangles, switching at
  about 33 m and 66 m), the masses cast sun shadows through a ShadowsOnly LOD2 copy, the post has a mast capsule and
  footing box collider. Each instance carries a scene-added warm spot
  (*Lamp warm street light*, straight down, 150°, intensity 6, range 15 m; *Lamp warm wall light*, tilted 25° out from
  the wall, 130°, intensity 4, range 10 m), unshadowed, listed in the **Ward lighting clock** CityLightCircuit as
  practical **and** night-only lights. Move a lamp by moving its instance; tune its light directly. Pockets: courtyard
  behind the mission terminals, Vanguard Hall east corner, Lattice court, hill-foot benches, both sides of the District
  gate apron, the south-wall collapse, the south lane (two wall brackets), the north collapse behind the Quantum Tube,
  the east rampart foot by the nanofab yard.
- **Mission terminal glow**: one cool point fill (0.75, 3 m, night-only on the circuit) in front of each Meshy mission
  terminal screen. The three terminals use `Art/NightLife/Terminal/MissionTerminal_Lit.mat` (the Meshy material plus an
  emission map of the MISSIONS display, the badge and the status button derived from the albedo; constant emission like
  the hill kiosks). The original `MissionTerminal.mat` is unchanged; put it back on the three renderers to revert.
- **Ambient life**: *Barrel fire* (flames and embers on `Art/NightLife/FX/NL_BarrelFlame` (HDR additive), smoke and a
  flickering fire light in the market rest-spot barrel),
  *Repairs flue smoke*, *Salvage stovepipe smoke*, *Air + Water relief steam* (intermittent puffs) and *Generator
  exhaust haze*. Ordinary ParticleSystems (cookfire materials, `Art/NightLife/FX/NL_Steam`, `NL_ExhaustHaze`) driven by
  **AmbientLife** (`Scripts/AmbientLife.cs`): Reduced Motion stops and clears them, *Day/Night Tint* scale the particle
  colour with the clock, *Puff Seconds / Min/Max Gap* make intermittent puffs, and the fire light flickers at night and
  is off by day (it is deliberately not on the circuit, which would overwrite the flicker).

Layout and validation: `art/night_life_20261001/night_layout.py` (routes, doors, stairs, NPC points, props, colliders)
→ `night-layout.json`. **Athen Hill → (batch) NightLifePass** steps: `relayout` (adds/moves/removes fixtures to match the
layout, keeps the light objects and their clock bindings), `retune` (light values), `rebuildfx` (recreates Ambient
life and the review cameras), `fxmats` (particle materials only), `lodcuts` (lamp LOD heights in place). Do not
re-run `build` after the install: it re-saves
the lamp prefabs under the installed instances. Install is one-time. Review cameras `cam_nl_*` (**Night life review
cameras**); evidence, A/B frame times and remaining defects: `evidence/night-life/20261001/README.md`.

## For the AGENTS.md baseline table (one row)

| Night lighting and ambient life | 1 Oct 2026 (`art/night_life_20261001`, scene root **Ward night life**): 8 merged-part Ward utility posts and 3 wall brackets in the dark pockets (courtyard/terminals, Lattice court, hall corner, hill benches, gate apron, both wall collapses, south lane, rampart foot), warm unshadowed spots on the light clock (night-only); the three Meshy mission terminals on an emissive variant (display, badge, button) with cool night fills; barrel fire with embers and flicker light, two flue smokes, Air + Water steam puffs, generator haze via `AmbientLife` (Reduced Motion aware). Not yet accepted by Carl. |
