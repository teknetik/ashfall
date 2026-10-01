# Docs snippet — birch canopy and bed uplights (1 October 2026)

## For unity/EDITING.md (after "Courtyard tree beds")

## Birch canopy and bed uplights (1 October 2026)

The courtyard birches `birch 3` and `birch 4b` stay TreesBundleB prefab instances (prefab links, LODGroups, trunk
capsules unchanged); their five LOD renderers use baked mesh copies (`Art/BirchCanopy/Meshes/BC_*`: crown occlusion,
per-card season/brightness/dryness in vertex colour, crown-volume leaf normals; positions and triangles identical) and
six materials on **Athen Hill/Ward Canopy** (`Shaders/WardCanopy`, a fork of the Ward Tree shader): base green leaf map
blended per card to the turned-leaf map, *Albedo saturation*, *Crown occlusion on ambient/direct*, leaf transmission
with *Sun transmission through the crown*, wind *bend start/end heights*, *Crown sway*, *Leaf flutter*. Change the look
on the materials or in `art/birch_canopy_20261001/canopy-tune.json` → `BirchCanopyPass --steps apply,verify`
(`-nographics`); change the bake (occlusion, season distribution, normals) → `--steps build,apply,verify`. Never
static-batch the birch LOD renderers (wind).

- Bed uplights (`TreeBed_Birch3/4b.prefab`, same light objects on the **Ward lighting clock**): an avenue-side trunk
  wash and an opposite crown beam per bed; the lens is `BC_UplightLens` (not the shared `VH_LampLens`). Values live in
  `canopy-tune.json`; `apply` recomputes the aim from the recorded positions. `CourtyardTreesPass` *Build assets* or
  *Retune uplights* put the old 70 / 14 m lights and `VH_LampLens` back — re-run `BirchCanopyPass --steps apply`.
- Review cameras `cam_bc_*` (**Birch canopy review cameras**); `--steps rollback` restores the vendor meshes and
  materials, bed lights and lens slots. Evidence and the 32-light finding: `evidence/birch-canopy/20261001/README.md`.
- Night lighting note: on OpenGL Core URP keeps only the 30 lights nearest the camera (plus sun and fill); lamps
  beyond ~26–36 m from the camera in the courtyard are not drawn. Judge a fixture from a camera near it.

## For AGENTS.md §3 baseline table (one row)

| Courtyard birch canopy | 1 Oct 2026 (`art/birch_canopy_20261001`): `birch 3` / `birch 4b` keep their TreesBundleB prefab links and trunk capsules; baked canopy meshes (crown occlusion, per-card yellow-green season mix and jitter, volume normals) on the Ward Canopy shader (wind, leaf transmission, no metallic); bed uplights split into trunk wash + crown beam with their own dimmer lens (`BC_UplightLens`). Not yet accepted by Carl. |
