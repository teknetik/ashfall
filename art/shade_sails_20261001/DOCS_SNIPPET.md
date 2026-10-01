# Docs snippet — shade sails (for the orchestrator to merge)

## For unity/EDITING.md

## Shade sails (1 October 2026)

**Ward shade sails** (scene root) holds four prefab instances (`Prefabs/ShadeSails/SS_Courtyard/Market/Apron/Lattice.prefab`):
tensioned canvas sails over the mission-terminal court, the market rest spot behind Air + Water, the caravan goods on the
West Gate apron and the approach to the Lattice step. Each prefab has three LODGroups — **Sail** (canvas, rolled hem,
corner plates, turnbuckles or lashings), **Rig** (raked steel poles on stone footings or sandbagged base plates, guys to
sandbagged anchors, wire-rope strops on the two retrofit service poles by the market) and **Festoons** (cable, lampholders,
bulbs) — plus **Festoon lights** (unshadowed points on the Ward lighting clock, practical + night-only; the bulb material
`SS_FestoonBulb` is on the clock's emissive list) and **Colliders** (pole capsules, footing/ballast and guy-anchor boxes,
and one camera-only mesh collider per canvas, ≥ 3.67 m up, so the follow camera stays under the sail).

- Shadows: the canvas renderers never cast; a ShadowsOnly copy of the coarse canvas 4 cm below each sail (one per LOD)
  casts the sail's shadow, so the cloth never shadows itself (its underside keeps the sun transmitted through it). Keep
  that arrangement if you replace a canvas. Poles and stone footings cast at LOD0 only.
- Canvas materials `Art/ShadeSails/Materials/SS_Sail_<Site>` use **Athen Hill/Ward Ground Cover** with its wind at 0:
  *Leaf light transmission* (0.18–0.32) is how much sun glows through the cloth, *ambient transmission* the shade side;
  alpha clip opens the worn-through holes. Pole paints `SS_PoleGrey/Red/Olive` are tinted copies of `VH_Steel`.
- Geometry, layout and textures are generated in `art/shade_sails_20261001` (`sails.py` layout and validation,
  `author_sails.py` Blender, `make_textures.py`), then **Athen Hill → Shade sails → Build assets**: it re-saves the prefabs
  in place and the installed instances keep their clock bindings (checked with `--steps build,verify`). If the number of
  sails or lights changes, use `RunBatch --steps build,reinstall,verify` (re-creates the instances, re-binds the lights,
  keeps the first rollback copy). Material values only: `--steps materials,verify`.
- Moving a sail means moving its poles: change `sails.py` and re-run the chain (the validator checks routes, doors,
  stairs, NPC points, sightlines to the Lattice ring and the terminals, and head clearance). Don't move an instance by hand.
- Review cameras `cam_ss_*` (**Shade sail review cameras**); evidence `evidence/shade-sails/20261001`.

## For the AGENTS.md baseline table

| Shade sails | 1 Oct 2026 (`art/shade_sails_20261001`, scene root **Ward shade sails**): four form-found canvas sails (madder, indigo, natural, natural/indigo cloths; patches, seams, stencils) over the terminal court, the market rest spot, the West Gate apron and the Lattice approach, on raked steel poles with stone footings or guyed sandbag bases (two tied to the retrofit service poles), festoon strings with 7 unshadowed clock lights; canvas shadow from offset ShadowsOnly proxies, camera-only canvas colliders. 98.5k / 28.8k triangles LOD0/1. Not yet accepted by Carl. |
